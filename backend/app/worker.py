import asyncio
import os
import socket
import uuid
import signal
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.core.database import db_manager
from app.db.job_repository import JobRepository
from app.db.repository import (
    PRDRepository,
    PRDVersionRepository,
    ProjectRepository,
    SubmissionRepository,
    AnalysisRepository,
    ClarificationRepository,
    GenerationRunRepository,
    ValidationRepository
)
from app.services.prd_service import PRDService
from app.services.validation_service import ValidationService
from app.models.job import JobStatus
from app.ai.exceptions import AIError

logger = logging.getLogger("prd_worker")

class BackgroundWorker:
    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"worker-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.shutdown_event = asyncio.Event()
        self.job_repo = JobRepository()
        self.current_job_id: Optional[str] = None
        self.prd_service = PRDService(
            prd_repo=PRDRepository(),
            version_repo=PRDVersionRepository(),
            project_repo=ProjectRepository(),
            submission_repo=SubmissionRepository(),
            analysis_repo=AnalysisRepository(),
            clarification_repo=ClarificationRepository(),
            gen_run_repo=GenerationRunRepository()
        )
        self.validation_service = ValidationService(ValidationRepository(), AnalysisRepository())

    def handle_signal(self, sig):
        logger.info(f"Worker {self.worker_id} received signal {sig}. Initiating graceful shutdown...")
        self.shutdown_event.set()

    async def start(self):
        logger.info(f"Starting PRD Generation Worker: {self.worker_id}")
        await db_manager.connect()

        # Register signal handlers if running in main thread
        try:
            loop = asyncio.get_running_loop()
            for s in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(s, lambda s=s: self.handle_signal(s))
        except (NotImplementedError, RuntimeError):
            # Windows or non-main thread fallback
            pass

        recovery_counter = 0

        while not self.shutdown_event.is_set():
            try:
                # 1. Recover abandoned jobs periodically (every ~30s / 15 iterations)
                recovery_counter += 1
                if recovery_counter >= 15:
                    recovery_counter = 0
                    recovered = await self.job_repo.recover_abandoned_jobs(stale_threshold_seconds=60)
                    if recovered > 0:
                        logger.warning(f"Worker recovered {recovered} abandoned/stale jobs.")

                # 2. Claim next available queued job
                job = await self.job_repo.claim_next_job(self.worker_id)
                if job:
                    self.current_job_id = job["job_id"]
                    logger.info(f"Claimed job {self.current_job_id} for project {job.get('project_id')} (force_mock={job.get('force_mock')})")
                    await self._process_job(job)
                    self.current_job_id = None
                else:
                    # Sleep when no work
                    await asyncio.sleep(1.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(2.0)

        logger.info(f"Worker {self.worker_id} shutdown completed.")
        await db_manager.close()

    async def _heartbeat_loop(self, job_id: str, stop_heartbeat: asyncio.Event):
        """Continuously update worker heartbeat in MongoDB every 8 seconds."""
        while not stop_heartbeat.is_set():
            try:
                await self.job_repo.update_heartbeat(job_id, self.worker_id)
            except Exception as e:
                logger.warning(f"Failed to pulse heartbeat for job {job_id}: {e}")
            try:
                await asyncio.wait_for(stop_heartbeat.wait(), timeout=8.0)
            except asyncio.TimeoutError:
                pass

    async def _process_job(self, job: Dict):
        job_id = job["job_id"]
        project_id = job["project_id"]
        user_id = job["user_id"]
        force_mock = job.get("force_mock", False)

        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(job_id, stop_heartbeat))

        async def on_progress(stage: str, completed: list, metadata: dict):
            # Check cancellation first
            if await self.job_repo.is_cancelled(job_id):
                raise asyncio.CancelledError("Job was cancelled by user.")
            await self.job_repo.update_progress(job_id, stage, completed, metadata, self.worker_id)

        async def check_cancelled() -> bool:
            return await self.job_repo.is_cancelled(job_id)

        try:
            # Execute pipeline
            version = await self.prd_service.generate_full_prd(
                project_id=project_id,
                user_id=user_id,
                force_mock=force_mock,
                on_progress=on_progress,
                check_cancelled=check_cancelled,
                job_id=job_id,
                requested_version=job.get("version_number") or "v2.4.4"
            )

            # Auto-validate version
            try:
                await self.validation_service.validate_version(version)
            except Exception as val_err:
                logger.warning(f"Auto-validation warning for job {job_id}: {val_err}")

            # Mark completed
            await self.job_repo.complete_job(
                job_id=job_id,
                result_reference=version.id,
                progress_metadata={
                    "stage_name": "Completed",
                    "step": 6,
                    "total_steps": 6,
                    "version_number": version.version_number
                }
            )
            logger.info(f"Successfully completed job {job_id}. Generated {version.version_number} ({version.id})")

        except asyncio.CancelledError:
            logger.info(f"Job {job_id} cancelled during processing.")
            # Repository cancellation status is already CANCELLED
        except AIError as ai_err:
            logger.error(f"AI engine error processing job {job_id}: {ai_err.message} (code: {ai_err.code})")
            await self.job_repo.fail_job(
                job_id=job_id,
                error_code=ai_err.code,
                error_message=ai_err.message,
                progress_metadata={"stage_name": "Failed", "error": ai_err.message}
            )
        except Exception as err:
            logger.error(f"Error processing job {job_id}: {err}", exc_info=True)
            await self.job_repo.fail_job(
                job_id=job_id,
                error_code="INTERNAL_PROCESSING_ERROR",
                error_message=str(err),
                progress_metadata={"stage_name": "Failed", "error": str(err)}
            )
        finally:
            stop_heartbeat.set()
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    worker = BackgroundWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("Worker stopped via KeyboardInterrupt.")

if __name__ == "__main__":
    main()
