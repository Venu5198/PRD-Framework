from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pymongo import ReturnDocument
from app.db.repository import BaseRepository, fix_id
from app.models.job import JobStatus

class JobRepository(BaseRepository):
    def __init__(self):
        super().__init__("jobs")

    async def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        if "created_at" not in job_data:
            job_data["created_at"] = datetime.utcnow()
        job_data["updated_at"] = datetime.utcnow()
        return await self.create(job_data)

    async def get_by_job_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"job_id": job_id})
        return fix_id(doc)

    async def get_active_job_for_project(self, project_id: str, job_type: str = "prd_generation") -> Optional[Dict[str, Any]]:
        """Find currently queued or actively processing job for a project."""
        query = {
            "project_id": project_id,
            "job_type": job_type,
            "status": {"$in": [JobStatus.QUEUED, JobStatus.RUNNING]}
        }
        doc = await self.collection.find_one(query, sort=[("created_at", -1)])
        return fix_id(doc)

    async def claim_next_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Atomically find and claim the oldest queued job.
        Prevents multiple workers from acquiring the same job.
        """
        now = datetime.utcnow()
        doc = await self.collection.find_one_and_update(
            filter={"status": JobStatus.QUEUED},
            update={
                "$set": {
                    "status": JobStatus.RUNNING,
                    "worker_id": worker_id,
                    "started_at": now,
                    "heartbeat_at": now,
                    "updated_at": now
                }
            },
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER
        )
        return fix_id(doc)

    async def update_heartbeat(self, job_id: str, worker_id: str) -> bool:
        now = datetime.utcnow()
        res = await self.collection.update_one(
            {"job_id": job_id, "worker_id": worker_id, "status": JobStatus.RUNNING},
            {"$set": {"heartbeat_at": now, "updated_at": now}}
        )
        return res.modified_count > 0

    async def update_progress(
        self,
        job_id: str,
        current_stage: str,
        completed_stages: List[str],
        progress_metadata: Dict[str, Any],
        worker_id: str
    ) -> bool:
        now = datetime.utcnow()
        res = await self.collection.update_one(
            {"job_id": job_id, "worker_id": worker_id, "status": JobStatus.RUNNING},
            {
                "$set": {
                    "current_stage": current_stage,
                    "completed_stages": completed_stages,
                    "progress_metadata": progress_metadata,
                    "heartbeat_at": now,
                    "updated_at": now
                }
            }
        )
        return res.modified_count > 0

    async def complete_job(
        self,
        job_id: str,
        result_reference: str,
        progress_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        now = datetime.utcnow()
        update_fields: Dict[str, Any] = {
            "status": JobStatus.COMPLETED,
            "current_stage": "completed",
            "completed_at": now,
            "updated_at": now,
            "result_reference": result_reference
        }
        if progress_metadata:
            update_fields["progress_metadata"] = progress_metadata
            
        res = await self.collection.update_one(
            {"job_id": job_id},
            {"$set": update_fields}
        )
        return res.modified_count > 0

    async def fail_job(
        self,
        job_id: str,
        error_code: str,
        error_message: str,
        progress_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        now = datetime.utcnow()
        update_fields: Dict[str, Any] = {
            "status": JobStatus.FAILED,
            "current_stage": "failed",
            "completed_at": now,
            "updated_at": now,
            "error_code": error_code,
            "error_message": error_message
        }
        if progress_metadata:
            update_fields["progress_metadata"] = progress_metadata

        res = await self.collection.update_one(
            {"job_id": job_id},
            {"$set": update_fields}
        )
        return res.modified_count > 0

    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        now = datetime.utcnow()
        res = await self.collection.update_one(
            {
                "job_id": job_id,
                "user_id": user_id,
                "status": {"$in": [JobStatus.QUEUED, JobStatus.RUNNING]}
            },
            {
                "$set": {
                    "status": JobStatus.CANCELLED,
                    "current_stage": "cancelled",
                    "completed_at": now,
                    "updated_at": now,
                    "error_code": "USER_CANCELLED",
                    "error_message": "Job cancelled by user request."
                }
            }
        )
        return res.modified_count > 0

    async def is_cancelled(self, job_id: str) -> bool:
        doc = await self.collection.find_one({"job_id": job_id}, {"status": 1})
        return doc is not None and doc.get("status") == JobStatus.CANCELLED

    async def recover_abandoned_jobs(self, stale_threshold_seconds: int = 60) -> int:
        """
        Reclaim jobs left in 'running' state whose worker has not sent a heartbeat
        within stale_threshold_seconds. Resets them to 'queued' or fails after max retries.
        """
        stale_cutoff = datetime.utcnow() - timedelta(seconds=stale_threshold_seconds)
        
        # 1. Recover stale jobs under retry threshold (increment retry_count, return to queued)
        cursor = self.collection.find({
            "status": JobStatus.RUNNING,
            "heartbeat_at": {"$lt": stale_cutoff},
            "$or": [
                {"retry_count": {"$lt": 3}},
                {"retry_count": None},
                {"retry_count": {"$exists": False}}
            ]
        })
        stale_docs = await cursor.to_list(100)
        recovered_count = 0
        for doc in stale_docs:
            current_retries = doc.get("retry_count") or 0
            res = await self.collection.update_one(
                {"_id": doc["_id"], "status": JobStatus.RUNNING},
                {
                    "$set": {
                        "status": JobStatus.QUEUED,
                        "worker_id": None,
                        "updated_at": datetime.utcnow(),
                        "retry_count": current_retries + 1
                    }
                }
            )
            if res.modified_count > 0:
                recovered_count += 1

        # 2. Mark permanently failed jobs that exceeded max retries
        await self.collection.update_many(
            {
                "status": JobStatus.RUNNING,
                "heartbeat_at": {"$lt": stale_cutoff},
                "retry_count": {"$gte": 3}
            },
            {
                "$set": {
                    "status": JobStatus.FAILED,
                    "error_code": "WORKER_TIMEOUT_EXCEEDED",
                    "error_message": "Worker heartbeat lost repeatedly. Job aborted.",
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return recovered_count
