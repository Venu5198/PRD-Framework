from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.job import Job, JobResponse, JobCreateResponse, JobStatus
from app.models.prd import PRDVersion
from app.db.job_repository import JobRepository
from app.db.repository import ProjectRepository, PRDVersionRepository
from app.api.deps import (
    get_job_repo,
    get_project_repo,
    get_version_repo,
    get_current_user
)

router = APIRouter()

def serialize_job(job: dict) -> JobResponse:
    now = datetime.utcnow()
    started = job.get("started_at")
    completed = job.get("completed_at")
    elapsed = None
    if started:
        end_time = completed or now
        elapsed = int((end_time - started).total_seconds())

    return JobResponse(
        job_id=job["job_id"],
        project_id=job["project_id"],
        job_type=job.get("job_type", "prd_generation"),
        status=job.get("status", JobStatus.QUEUED),
        current_stage=job.get("current_stage", "queued"),
        completed_stages=job.get("completed_stages", []),
        total_stages=job.get("total_stages", 6),
        progress_metadata=job.get("progress_metadata", {}),
        provider=job.get("provider", "ollama"),
        model=job.get("model", "llama3.2"),
        force_mock=job.get("force_mock", False),
        created_at=job.get("created_at", now),
        started_at=started,
        completed_at=completed,
        elapsed_seconds=elapsed,
        error_code=job.get("error_code"),
        error_message=job.get("error_message"),
        result_reference=job.get("result_reference")
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    job_repo: JobRepository = Depends(get_job_repo),
    current_user: dict = Depends(get_current_user)
):
    job = await job_repo.get_by_job_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied: Job does not belong to user.")
    return serialize_job(job)

@router.get("/{job_id}/result", response_model=PRDVersion)
async def get_job_result(
    job_id: str,
    job_repo: JobRepository = Depends(get_job_repo),
    version_repo: PRDVersionRepository = Depends(get_version_repo),
    current_user: dict = Depends(get_current_user)
):
    job = await job_repo.get_by_job_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied: Job does not belong to user.")

    if job.get("status") == JobStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Job failed ({job.get('error_code')}): {job.get('error_message')}"
        )
    if job.get("status") != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job is still {job.get('status')}. Current stage: {job.get('current_stage')}"
        )

    version_id = job.get("result_reference")
    if not version_id:
        raise HTTPException(status_code=404, detail="Job result reference not found.")

    version_doc = await version_repo.get_by_id(version_id)
    if not version_doc:
        raise HTTPException(status_code=404, detail="Generated PRD version record not found.")

    return PRDVersion(**version_doc)

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    job_repo: JobRepository = Depends(get_job_repo),
    current_user: dict = Depends(get_current_user)
):
    job = await job_repo.get_by_job_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied: Job does not belong to user.")

    success = await job_repo.cancel_job(job_id, current_user["id"])
    if not success:
        return {"job_id": job_id, "status": job.get("status"), "message": "Job cannot be cancelled (already completed or failed)."}

    return {"job_id": job_id, "status": JobStatus.CANCELLED, "message": "Job cancellation requested successfully."}
