import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from pymongo.errors import DuplicateKeyError

from app.core.database import db_manager, get_database
from app.db.repository import PRDRepository, PRDVersionRepository, ProjectRepository, SubmissionRepository
from app.db.job_repository import JobRepository
from app.models.prd import PRDStatus, can_transition_version
from app.services.version_allocation_service import (
    VersionAllocationService,
    parse_version_string,
    format_version
)
from app.services.prd_service import PRDService

TEST_PRD_ID = "test-prd-concurrency-101"
TEST_PROJECT_ID = "test-proj-concurrency-101"
TEST_USER_ID = "test-user-concurrency"

@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_records():
    await db_manager.connect()
    db = get_database()
    # Clean up test artifacts
    await db["prd_versions"].delete_many({"prd_id": {"$regex": "^test-prd"}})
    await db["prd_documents"].delete_many({"id": {"$regex": "^test-prd"}})
    await db["projects"].delete_many({"id": {"$regex": "^test-proj"}})
    await db["jobs"].delete_many({"project_id": {"$regex": "^test-proj"}})
    yield
    await db["prd_versions"].delete_many({"prd_id": {"$regex": "^test-prd"}})
    await db["prd_documents"].delete_many({"id": {"$regex": "^test-prd"}})
    await db["projects"].delete_many({"id": {"$regex": "^test-proj"}})
    await db["jobs"].delete_many({"project_id": {"$regex": "^test-proj"}})
    await db_manager.close()

def test_version_parsing_and_calculation():
    """Test semantic version parsing and calculation logic."""
    assert parse_version_string("v1.0") == (1, 0)
    assert parse_version_string("2.5") == (2, 5)
    assert parse_version_string("invalid") is None

    repo = PRDVersionRepository()
    svc = VersionAllocationService(repo)

    # Empty list defaults to v1.0
    assert svc.calculate_next_version([], is_major=True) == "v1.0"
    assert svc.calculate_next_version([], is_major=False) == "v1.0"

    # Major progression
    existing = ["v1.0", "v1.1", "v2.0"]
    assert svc.calculate_next_version(existing, is_major=True) == "v3.0"

    # Minor progression
    assert svc.calculate_next_version(existing, is_major=False) == "v2.1"
    assert svc.calculate_next_version(["v1.0"], is_major=False) == "v1.1"

def test_state_transitions():
    """Test valid and invalid PRD version lifecycle state transitions."""
    # Allowed transitions
    assert can_transition_version(PRDStatus.RESERVED.value, PRDStatus.GENERATING.value) is True
    assert can_transition_version(PRDStatus.GENERATING.value, PRDStatus.GENERATED.value) is True
    assert can_transition_version(PRDStatus.GENERATED.value, PRDStatus.VALIDATING.value) is True
    assert can_transition_version(PRDStatus.VALIDATING.value, PRDStatus.UNDER_REVIEW.value) is True
    assert can_transition_version(PRDStatus.UNDER_REVIEW.value, PRDStatus.APPROVED.value) is True
    assert can_transition_version(PRDStatus.FAILED.value, PRDStatus.RESERVED.value) is True

    # Disallowed transitions: Approved cannot jump directly to Generating
    assert can_transition_version(PRDStatus.APPROVED.value, PRDStatus.GENERATING.value) is False
    assert can_transition_version(PRDStatus.APPROVED.value, PRDStatus.RESERVED.value) is False

@pytest.mark.asyncio
async def test_idempotent_version_reservation():
    """Verify that multiple requests with the same idempotency key or job_id return the same version."""
    repo = PRDVersionRepository()
    svc = VersionAllocationService(repo)

    key = "idem-key-test-999"
    v1 = await svc.reserve_version(
        prd_id=TEST_PRD_ID,
        project_id=TEST_PROJECT_ID,
        user_id=TEST_USER_ID,
        idempotency_key=key,
        is_major=True
    )
    assert v1["status"] == PRDStatus.RESERVED.value
    assert v1["version_number"] == "v1.0"

    # Call again with the exact same idempotency key
    v2 = await svc.reserve_version(
        prd_id=TEST_PRD_ID,
        project_id=TEST_PROJECT_ID,
        user_id=TEST_USER_ID,
        idempotency_key=key,
        is_major=True
    )
    assert v2["id"] == v1["id"]
    assert v2["version_number"] == v1["version_number"]

    # Verify only 1 record exists in the DB
    records = await repo.get_by_prd(TEST_PRD_ID)
    assert len(records) == 1

@pytest.mark.asyncio
async def test_approved_version_immutability():
    """Verify that approved versions cannot be mutated or regenerated."""
    repo = PRDVersionRepository()
    svc = VersionAllocationService(repo)

    # Reserve and approve v1.0
    v1 = await svc.reserve_version(
        prd_id=TEST_PRD_ID,
        project_id=TEST_PROJECT_ID,
        user_id=TEST_USER_ID,
        requested_version="v1.0"
    )
    await svc.transition_version(v1["id"], PRDStatus.GENERATING)
    await svc.transition_version(v1["id"], PRDStatus.GENERATED)
    await svc.transition_version(v1["id"], PRDStatus.APPROVED)

    # Attempting to reserve or re-allocate requested_version="v1.0" must raise ValueError
    with pytest.raises(ValueError, match="already been approved and is immutable"):
        await svc.reserve_version(
            prd_id=TEST_PRD_ID,
            project_id=TEST_PROJECT_ID,
            user_id=TEST_USER_ID,
            requested_version="v1.0"
        )

@pytest.mark.asyncio
async def test_concurrent_version_reservations():
    """Stress test: 10 concurrent workers reserving versions on the same PRD.
    All must succeed and receive distinct, non-colliding version numbers without DuplicateKeyError leaking.
    """
    repo = PRDVersionRepository()
    svc = VersionAllocationService(repo)

    # Launch 10 concurrent reservation tasks
    async def worker_reserve(idx: int):
        await asyncio.sleep(0.01 * (idx % 3))  # slight jitter
        return await svc.reserve_version(
            prd_id=TEST_PRD_ID,
            project_id=TEST_PROJECT_ID,
            user_id=TEST_USER_ID,
            job_id=f"job-concurrent-{idx}",
            is_major=True
        )

    results = await asyncio.gather(*[worker_reserve(i) for i in range(10)])

    allocated_versions = [r["version_number"] for r in results]
    assert len(allocated_versions) == 10
    # All version numbers must be completely unique
    assert len(set(allocated_versions)) == 10

    # Verify DB has exactly 10 records for this PRD
    db_versions = await repo.get_by_prd(TEST_PRD_ID)
    assert len(db_versions) == 10
    db_version_numbers = [v["version_number"] for v in db_versions]
    assert len(set(db_version_numbers)) == 10

@pytest.mark.asyncio
async def test_failed_version_retry_recovery():
    """Verify that a failed version can be recovered or retried cleanly."""
    repo = PRDVersionRepository()
    svc = VersionAllocationService(repo)

    v = await svc.reserve_version(
        prd_id=TEST_PRD_ID,
        project_id=TEST_PROJECT_ID,
        user_id=TEST_USER_ID,
        job_id="job-fail-1",
        is_major=True
    )
    assert v["version_number"] == "v1.0"

    # Mark as failed
    await svc.transition_version(
        v["id"],
        PRDStatus.FAILED,
        error_details={"error": "LLM timeout"}
    )

    failed_doc = await repo.get_by_id(v["id"])
    assert failed_doc["status"] == PRDStatus.FAILED.value
    assert failed_doc["error_details"]["error"] == "LLM timeout"

    # Retry reserving requested_version="v1.0"
    retried = await svc.reserve_version(
        prd_id=TEST_PRD_ID,
        project_id=TEST_PROJECT_ID,
        user_id=TEST_USER_ID,
        requested_version="v1.0"
    )
    assert retried["id"] == v["id"]
    assert retried["status"] == PRDStatus.RESERVED.value


@pytest.mark.asyncio
async def test_minor_version_allocation_sequence():
    """Verify sequential minor allocations (v1.0 -> v1.1 -> v1.2) via VersionAllocationService."""
    repo = PRDVersionRepository()
    svc = VersionAllocationService(repo)

    # Initial v1.0
    v1_0 = await svc.reserve_version(
        prd_id=TEST_PRD_ID,
        project_id=TEST_PROJECT_ID,
        user_id=TEST_USER_ID,
        is_major=True
    )
    assert v1_0["version_number"] == "v1.0"
    await svc.transition_version(v1_0["id"], PRDStatus.GENERATED)

    # Minor bump 1: v1.1
    v1_1 = await svc.reserve_version(
        prd_id=TEST_PRD_ID,
        project_id=TEST_PROJECT_ID,
        user_id=TEST_USER_ID,
        is_major=False
    )
    assert v1_1["version_number"] == "v1.1"
    await svc.transition_version(v1_1["id"], PRDStatus.GENERATED)

    # Minor bump 2: v1.2
    v1_2 = await svc.reserve_version(
        prd_id=TEST_PRD_ID,
        project_id=TEST_PROJECT_ID,
        user_id=TEST_USER_ID,
        is_major=False
    )
    assert v1_2["version_number"] == "v1.2"
    await svc.transition_version(v1_2["id"], PRDStatus.GENERATED)

    # Next major bump after minor updates: v2.0
    v2_0 = await svc.reserve_version(
        prd_id=TEST_PRD_ID,
        project_id=TEST_PROJECT_ID,
        user_id=TEST_USER_ID,
        is_major=True
    )
    assert v2_0["version_number"] == "v2.0"

@pytest.mark.asyncio
async def test_api_endpoint_idempotency():
    """Verify that calling the PRD generation endpoint with an Idempotency-Key returns existing job/status."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    project_repo = ProjectRepository()
    proj = await project_repo.create({
        "id": "test-proj-api-idem",
        "title": "Idempotency Test Project",
        "owner_id": "test-user-concurrency",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    headers = {
        "Authorization": "Bearer mock-token",
        "Idempotency-Key": "client-gen-key-unique-777"
    }

    # Override auth dependency to return test user
    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user-concurrency", "username": "tester"}

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res1 = await ac.post("/api/v1/projects/test-proj-api-idem/prd/generate?use_mock=true", headers=headers)
            assert res1.status_code == 202
            data1 = res1.json()
            assert data1["is_existing"] is False
            job_id_1 = data1["job_id"]

            # Second call with same idempotency key
            res2 = await ac.post("/api/v1/projects/test-proj-api-idem/prd/generate?use_mock=true", headers=headers)
            assert res2.status_code == 202
            data2 = res2.json()
            assert data2["is_existing"] is True
            assert data2["job_id"] == job_id_1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await project_repo.delete("test-proj-api-idem")
