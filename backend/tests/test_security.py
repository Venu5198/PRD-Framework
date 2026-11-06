import pytest
import pytest_asyncio
import io
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.database import db_manager

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await db_manager.connect()
    yield
    await db_manager.close()

@pytest.mark.asyncio
async def test_security_auth_rejection():
    # When ALLOW_DEV_AUTO_AUTH is False, requests without Bearer token must return 401
    settings.ALLOW_DEV_AUTO_AUTH = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/projects")
        assert res.status_code == 401
        assert "Not authenticated" in res.json()["detail"]

@pytest.mark.asyncio
async def test_security_upload_restrictions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register and login
        import time
        ts = int(time.time() * 1000)
        await ac.post("/api/v1/auth/register", json={
            "username": f"sec_user_{ts}",
            "email": f"sec_{ts}@example.com",
            "password": "Password123!"
        })
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": f"sec_user_{ts}",
            "password": "Password123!"
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create project
        p_res = await ac.post("/api/v1/projects", json={"title": "Sec Proj"}, headers=headers)
        proj_id = p_res.json()["id"]

        # 1. Reject forbidden extension (e.g. malicious.exe)
        bad_ext_res = await ac.post(
            f"/api/v1/projects/{proj_id}/upload-reference",
            files={"file": ("malicious.exe", b"fake binary", "application/octet-stream")},
            headers=headers
        )
        assert bad_ext_res.status_code == 400
        assert "Unsupported file extension" in bad_ext_res.json()["detail"]

        # 2. Reject executable header (MZ Windows binary disguise)
        mz_res = await ac.post(
            f"/api/v1/projects/{proj_id}/upload-reference",
            files={"file": ("disguised.pdf", b"MZ\x90\x00\x03\x00\x00\x00", "application/pdf")},
            headers=headers
        )
        assert mz_res.status_code == 400
        assert "Executable files are forbidden" in mz_res.json()["detail"]

        # 3. Reject empty file
        empty_res = await ac.post(
            f"/api/v1/projects/{proj_id}/upload-reference",
            files={"file": ("empty.txt", b"", "text/plain")},
            headers=headers
        )
        assert empty_res.status_code == 400
        assert "Cannot upload an empty file" in empty_res.json()["detail"]

        # 4. Reject oversized file (> 15 MB)
        oversized_data = b"X" * (16 * 1024 * 1024)  # 16 MB
        oversized_res = await ac.post(
            f"/api/v1/projects/{proj_id}/upload-reference",
            files={"file": ("large.pdf", oversized_data, "application/pdf")},
            headers=headers
        )
        assert oversized_res.status_code == 413
        assert "File exceeds maximum allowed size" in oversized_res.json()["detail"]

        # 5. Path traversal defense: '../../etc/passwd.txt' must be safely sanitized
        traversal_res = await ac.post(
            f"/api/v1/projects/{proj_id}/upload-reference",
            files={"file": ("../../etc/passwd.txt", b"Safe plain text content", "text/plain")},
            headers=headers
        )
        assert traversal_res.status_code == 200
        data = traversal_res.json()
        assert ".." not in data["stored_path"]
        assert "passwd.txt" in data["stored_path"]

@pytest.mark.asyncio
async def test_security_duplicate_username_enforcement():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        import time
        ts = int(time.time() * 1000)
        u_name = f"uniq_user_{ts}"
        # First registration succeeds
        res1 = await ac.post("/api/v1/auth/register", json={
            "username": u_name,
            "email": f"{u_name}@example.com",
            "password": "Password123!"
        })
        assert res1.status_code == 200

        # Duplicate username is rejected
        res2 = await ac.post("/api/v1/auth/register", json={
            "username": u_name,
            "email": f"other_{ts}@example.com",
            "password": "Password123!"
        })
        assert res2.status_code == 400
        assert "already registered" in res2.json()["detail"]

@pytest.mark.asyncio
async def test_security_user_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        import time
        ts = int(time.time() * 1000)

        # Register User A & create project
        await ac.post("/api/v1/auth/register", json={
            "username": f"user_a_{ts}",
            "email": f"user_a_{ts}@example.com",
            "password": "Password123!"
        })
        log_a = await ac.post("/api/v1/auth/login", json={
            "username": f"user_a_{ts}",
            "password": "Password123!"
        })
        token_a = log_a.json()["access_token"]
        p_res = await ac.post("/api/v1/projects", json={"title": "Private Project A"}, headers={"Authorization": f"Bearer {token_a}"})
        proj_id = p_res.json()["id"]

        # Register User B
        await ac.post("/api/v1/auth/register", json={
            "username": f"user_b_{ts}",
            "email": f"user_b_{ts}@example.com",
            "password": "Password123!"
        })
        log_b = await ac.post("/api/v1/auth/login", json={
            "username": f"user_b_{ts}",
            "password": "Password123!"
        })
        token_b = log_b.json()["access_token"]

        # User B attempts to access User A's project
        cross_res = await ac.get(f"/api/v1/projects/{proj_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert cross_res.status_code == 404
        assert "Project not found" in cross_res.json()["detail"]
