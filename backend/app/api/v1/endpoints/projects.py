import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.models.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.models.submission import IdeaSubmissionCreate, IdeaSubmissionResponse
from app.db.repository import ProjectRepository, SubmissionRepository
from app.api.deps import get_project_repo, get_submission_repo, get_current_user
from app.core.config import settings

router = APIRouter()

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    project_repo: ProjectRepository = Depends(get_project_repo),
    current_user: dict = Depends(get_current_user)
):
    projects = await project_repo.get_by_owner(current_user["id"])
    return [ProjectResponse(**p) for p in projects]

@router.post("", response_model=ProjectResponse)
async def create_project(
    project_in: ProjectCreate,
    project_repo: ProjectRepository = Depends(get_project_repo),
    current_user: dict = Depends(get_current_user)
):
    data = project_in.dict()
    data["owner_id"] = current_user["id"]
    data["active_prd_id"] = None
    data["created_at"] = datetime.utcnow()
    data["updated_at"] = datetime.utcnow()
    
    created = await project_repo.create(data)
    return ProjectResponse(**created)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    current_user: dict = Depends(get_current_user)
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**project)

@router.post("/{project_id}/submissions", response_model=IdeaSubmissionResponse)
async def submit_idea(
    project_id: str,
    submission_in: IdeaSubmissionCreate,
    submission_repo: SubmissionRepository = Depends(get_submission_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    current_user: dict = Depends(get_current_user)
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    data = submission_in.dict()
    data["project_id"] = project_id
    data["file_attachments"] = []
    data["created_at"] = datetime.utcnow()

    created = await submission_repo.create(data)
    return IdeaSubmissionResponse(**created)

@router.post("/{project_id}/upload-reference")
async def upload_reference_document(
    project_id: str,
    file: UploadFile = File(...),
    submission_repo: SubmissionRepository = Depends(get_submission_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    current_user: dict = Depends(get_current_user)
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_name = f"{project_id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_dest = settings.UPLOADS_DIR / safe_name
    
    with open(file_dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Attach file to latest submission or create submission if none
    subs = await submission_repo.get_by_project(project_id)
    if subs:
        sub = subs[0]
        files = sub.get("file_attachments", [])
        files.append(str(file_dest))
        await submission_repo.update(sub["id"], {"file_attachments": files})
    else:
        # Create submission wrapper
        await submission_repo.create({
            "project_id": project_id,
            "submission_type": "reference_document",
            "raw_idea": f"Uploaded document: {file.filename}",
            "file_attachments": [str(file_dest)],
            "created_at": datetime.utcnow()
        })

    return {"filename": file.filename, "stored_path": str(file_dest), "status": "uploaded"}

@router.get("/{project_id}/submissions", response_model=List[IdeaSubmissionResponse])
async def list_submissions(
    project_id: str,
    submission_repo: SubmissionRepository = Depends(get_submission_repo),
    current_user: dict = Depends(get_current_user)
):
    subs = await submission_repo.get_by_project(project_id)
    return [IdeaSubmissionResponse(**s) for s in subs]
