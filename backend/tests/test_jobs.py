import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import db_manager, get_database
from app.db.job_repository import JobRepository
from app.models.job import JobStatus

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await db_manager.connect()
    await db_manager.db.jobs.delete_many({"job_id": {"$regex": "^(test-job|abandoned-job)"}})
    yield
    await db_manager.db.jobs.delete_many({"job_id": {"$regex": "^(test-job|abandoned-job)"}})
    await db_manager.close()

@pytest.mark.asyncio
async def test_job_repository_operations():
    repo = JobRepository()
    now = datetime.utcnow()
    job_id = f"test-job-{int(now.timestamp())}"

    # 1. Job Creation
    job_doc = {
        "job_id": job_id,
        "user_id": "test_user_1",
        "project_id": "test_proj_1",
        "job_type": "prd_generation",
        "status": JobStatus.QUEUED,
        "current_stage": "queued",
        "completed_stages": [],
        "total_stages": 6,
        "progress_metadata": {},
        "provider": "ollama",
        "model": "llama3.2",
        "force_mock": True,
        "created_at": now,
        "updated_at": now
    }
    created = await repo.create_job(job_doc)
    assert created["job_id"] == job_id

    # 2. Atomic Job Claiming
    claimed = await repo.claim_next_job(worker_id="worker-test-1")
    assert claimed is not None
    assert claimed["job_id"] == job_id
    assert claimed["status"] == JobStatus.RUNNING
    assert claimed["worker_id"] == "worker-test-1"

    # Second worker cannot claim the same job
    claimed_again = await repo.claim_next_job(worker_id="worker-test-2")
    assert claimed_again is None

    # 3. Progress Persistence
    prog_ok = await repo.update_progress(
        job_id=job_id,
        current_stage="requirements_engineering",
        completed_stages=["input_analysis"],
        progress_metadata={"stage_name": "Requirements", "step": 2, "total_steps": 6},
        worker_id="worker-test-1"
    )
    assert prog_ok is True
    updated = await repo.get_by_job_id(job_id)
    assert updated["current_stage"] == "requirements_engineering"
    assert "input_analysis" in updated["completed_stages"]

    # 4. Successful Completion
    comp_ok = await repo.complete_job(job_id=job_id, result_reference="ver_123")
    assert comp_ok is True
    completed = await repo.get_by_job_id(job_id)
    assert completed["status"] == JobStatus.COMPLETED
    assert completed["result_reference"] == "ver_123"

@pytest.mark.asyncio
async def test_job_cancellation():
    repo = JobRepository()
    now = datetime.utcnow()
    job_id = f"cancel-job-{int(now.timestamp())}"

    await repo.create_job({
        "job_id": job_id,
        "user_id": "user_owner",
        "project_id": "proj_cancel",
        "status": JobStatus.QUEUED
    })

    # Unauthorized user cannot cancel
    unauth_cancel = await repo.cancel_job(job_id, user_id="wrong_user")
    assert unauth_cancel is False

    # Owner can cancel
    auth_cancel = await repo.cancel_job(job_id, user_id="user_owner")
    assert auth_cancel is True
    cancelled = await repo.get_by_job_id(job_id)
    assert cancelled["status"] == JobStatus.CANCELLED
    assert await repo.is_cancelled(job_id) is True

@pytest.mark.asyncio
async def test_worker_abandoned_job_recovery():
    repo = JobRepository()
    now = datetime.utcnow()
    job_id = f"abandoned-job-{int(now.timestamp())}"

    # Stale heartbeat (2 minutes ago)
    stale_time = now - timedelta(seconds=120)
    await repo.create_job({
        "job_id": job_id,
        "user_id": "user_abandoned",
        "project_id": "proj_abandoned",
        "status": JobStatus.RUNNING,
        "worker_id": "dead_worker",
        "heartbeat_at": stale_time,
        "retry_count": 0
    })

    # Recover abandoned jobs
    recovered_count = await repo.recover_abandoned_jobs(stale_threshold_seconds=60)
    assert recovered_count >= 1

    recovered_job = await repo.get_by_job_id(job_id)
    assert recovered_job["status"] == JobStatus.QUEUED
    assert recovered_job["retry_count"] == 1
    assert recovered_job["worker_id"] is None

@pytest.mark.asyncio
async def test_duplicate_submission_prevention_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ts = int(datetime.utcnow().timestamp())
        reg_payload = {
            "username": f"job_user_{ts}",
            "email": f"job_{ts}@example.com",
            "password": "Password123!",
            "full_name": "Job User"
        }
        await ac.post("/api/v1/auth/register", json=reg_payload)
        login_res = await ac.post("/api/v1/auth/login", json={"username": f"job_user_{ts}", "password": "Password123!"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create Project
        proj_res = await ac.post("/api/v1/projects", json={"title": "Async PRD Proj"}, headers=headers)
        proj_id = proj_res.json()["id"]

        # First generate request -> 202 Accepted
        res1 = await ac.post(f"/api/v1/projects/{proj_id}/prd/generate?use_mock=true", headers=headers)
        assert res1.status_code == 202
        data1 = res1.json()
        assert "job_id" in data1
        assert data1["is_existing"] is False

        # Duplicate generate request while job is queued/running -> returns same job_id (is_existing=True)
        res2 = await ac.post(f"/api/v1/projects/{proj_id}/prd/generate?use_mock=true", headers=headers)
        assert res2.status_code == 202
        data2 = res2.json()
        assert data2["job_id"] == data1["job_id"]
        assert data2["is_existing"] is True

        # Check job status via GET /api/v1/jobs/{job_id}
        job_status_res = await ac.get(f"/api/v1/jobs/{data1['job_id']}", headers=headers)
        assert job_status_res.status_code == 200
        assert job_status_res.json()["status"] in [JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED]

        # Cross-user access rejection
        # Register a second user
        other_payload = {
            "username": f"other_user_{ts}",
            "email": f"other_{ts}@example.com",
            "password": "Password123!",
            "full_name": "Other User"
        }
        await ac.post("/api/v1/auth/register", json=other_payload)
        other_login = await ac.post("/api/v1/auth/login", json={"username": f"other_user_{ts}", "password": "Password123!"})
        other_token = other_login.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # Other user cannot access User 1's job
        cross_res = await ac.get(f"/api/v1/jobs/{data1['job_id']}", headers=other_headers)
        assert cross_res.status_code == 403

        # Cancel job
        cancel_res = await ac.post(f"/api/v1/jobs/{data1['job_id']}/cancel", headers=headers)
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] in [JobStatus.CANCELLED, JobStatus.FAILED, JobStatus.COMPLETED]

@pytest.mark.asyncio
async def test_worker_groq_failure_handling():
    from unittest.mock import patch
    from app.worker import BackgroundWorker
    from app.ai.exceptions import GroqAuthError, GroqRateLimitError, GroqTimeoutError

    repo = JobRepository()
    now = datetime.utcnow()
    worker = BackgroundWorker(worker_id="test-fail-worker")

    # 1. Groq HTTP 401 Auth Failure
    job_id_auth = f"test-job-auth-{int(now.timestamp())}"
    await repo.create_job({
        "job_id": job_id_auth,
        "user_id": "u1",
        "project_id": "p1",
        "status": JobStatus.RUNNING,
        "worker_id": "test-fail-worker",
        "created_at": now
    })

    with patch.object(worker.prd_service, "generate_full_prd", side_effect=GroqAuthError("Invalid Groq API key")):
        await worker._process_job(await repo.get_by_job_id(job_id_auth))

    failed_auth_job = await repo.get_by_job_id(job_id_auth)
    assert failed_auth_job["status"] == JobStatus.FAILED
    assert failed_auth_job["error_code"] == "GROQ_AUTH_FAILED"
    assert "Invalid Groq API key" in failed_auth_job["error_message"]

    # 2. Groq HTTP 429 Rate Limit Exhaustion
    job_id_429 = f"test-job-429-{int(now.timestamp())}"
    await repo.create_job({
        "job_id": job_id_429,
        "user_id": "u1",
        "project_id": "p1",
        "status": JobStatus.RUNNING,
        "worker_id": "test-fail-worker",
        "created_at": now
    })

    with patch.object(worker.prd_service, "generate_full_prd", side_effect=GroqRateLimitError("Rate limit exceeded after retries")):
        await worker._process_job(await repo.get_by_job_id(job_id_429))

    failed_429_job = await repo.get_by_job_id(job_id_429)
    assert failed_429_job["status"] == JobStatus.FAILED
    assert failed_429_job["error_code"] == "GROQ_RATE_LIMIT"

    # 3. Groq Request Timeout
    job_id_to = f"test-job-to-{int(now.timestamp())}"
    await repo.create_job({
        "job_id": job_id_to,
        "user_id": "u1",
        "project_id": "p1",
        "status": JobStatus.RUNNING,
        "worker_id": "test-fail-worker",
        "created_at": now
    })

    with patch.object(worker.prd_service, "generate_full_prd", side_effect=GroqTimeoutError("Groq request timed out")):
        await worker._process_job(await repo.get_by_job_id(job_id_to))

    failed_to_job = await repo.get_by_job_id(job_id_to)
    assert failed_to_job["status"] == JobStatus.FAILED
    assert failed_to_job["error_code"] == "GROQ_TIMEOUT"
