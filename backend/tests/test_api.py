import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import db_manager

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await db_manager.connect()
    yield
    await db_manager.close()

@pytest.mark.asyncio
async def test_full_user_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. System Health
        res = await ac.get("/api/v1/system/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

        # 2. Register User
        import time
        ts = int(time.time())
        reg_payload = {
            "username": f"lead_dev_{ts}",
            "email": f"lead_{ts}@example.com",
            "password": "Password123!",
            "full_name": "Lead Developer"
        }
        res = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 200
        user_id = res.json()["id"]

        # 3. Login
        login_res = await ac.post("/api/v1/auth/login", json={"username": f"lead_dev_{ts}", "password": "Password123!"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 4. Create Project
        proj_res = await ac.post("/api/v1/projects", json={"title": "Local First PRD Tool", "description": "Offline requirements suite"}, headers=headers)
        assert proj_res.status_code == 200
        project_id = proj_res.json()["id"]

        # 5. Submit Idea
        sub_res = await ac.post(f"/api/v1/projects/{project_id}/submissions", json={
            "submission_type": "idea",
            "raw_idea": "Build an offline AI framework that turns user thoughts into comprehensive PRDs."
        }, headers=headers)
        assert sub_res.status_code == 200

        # 6. Analyze Input
        an_res = await ac.post(f"/api/v1/analysis/{project_id}/analyze?use_mock=true", headers=headers)
        assert an_res.status_code == 200
        analysis_data = an_res.json()
        assert len(analysis_data["core_objectives"]) > 0

        # 7. Generate Clarifications
        clar_res = await ac.post(f"/api/v1/analysis/{project_id}/clarifications/generate?use_mock=true", headers=headers)
        assert clar_res.status_code == 200
        qs = clar_res.json()["questions"]
        assert len(qs) > 0

        # 8. Answer first question
        first_q_id = qs[0]["id"]
        ans_res = await ac.post(f"/api/v1/analysis/{project_id}/clarifications/answer", json={
            "question_id": first_q_id,
            "answer": "Targeting local workstation environment",
            "proceed_with_assumption": False
        }, headers=headers)
        assert ans_res.status_code == 200

        # 9. Generate Full PRD (Using deterministic mock in rapid integration test)
        prd_res = await ac.post(f"/api/v1/prd/{project_id}/generate?use_mock=true", headers=headers)
        assert prd_res.status_code == 200
        prd_ver = prd_res.json()
        assert prd_ver["version_number"] == "v1.0"
        assert len(prd_ver["sections"]) == 27

        # 10. Validate PRD
        val_res = await ac.post(f"/api/v1/validation/{project_id}/validate", headers=headers)
        assert val_res.status_code == 200
        val_data = val_res.json()
        assert "score" in val_data
        assert val_data["score"] >= 70

        # 11. Edit a Section (Creates v1.1)
        patch_res = await ac.patch(
            f"/api/v1/prd/{project_id}/sections/executive_summary",
            json={"content": "Updated Executive Summary explicitly tailored for high efficiency."},
            headers=headers
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["version_number"] == "v1.1"

        # 12. Regenerate Section
        regen_res = await ac.post(
            f"/api/v1/prd/{project_id}/sections/proposed_solution/regenerate?use_mock=true",
            json={"guidance": "Emphasize security and offline guarantees."},
            headers=headers
        )
        assert regen_res.status_code == 200
        assert regen_res.json()["version_number"] == "v1.2"

        # 13. Approve Version
        latest_v_id = regen_res.json()["id"]
        app_res = await ac.post(f"/api/v1/prd/{project_id}/versions/{latest_v_id}/approve", headers=headers)
        assert app_res.status_code == 200
        assert app_res.json()["status"] == "approved"

        # 14. Export Markdown
        exp_md = await ac.get(f"/api/v1/export/{project_id}/markdown", headers=headers)
        assert exp_md.status_code == 200
        assert len(exp_md.content) > 100

        # 15. Export DOCX
        exp_docx = await ac.get(f"/api/v1/export/{project_id}/docx", headers=headers)
        assert exp_docx.status_code == 200
        assert len(exp_docx.content) > 1000

        # 16. Export PDF
        exp_pdf = await ac.get(f"/api/v1/export/{project_id}/pdf", headers=headers)
        assert exp_pdf.status_code == 200
        assert len(exp_pdf.content) > 1000
