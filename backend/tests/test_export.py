import pytest
import os
from pathlib import Path
from datetime import datetime
from app.services.export_service import ExportService
from app.models.prd import PRDVersion, PRDSectionContent, CANONICAL_SECTIONS, SECTION_TITLES

def test_export_all_formats(tmp_path: Path):
    export_svc = ExportService(exports_dir=tmp_path)
    
    sections = {
        k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content=f"Detailed engineering specifications for {k}.\n| Col1 | Col2 |\n|---|---|\n| Data1 | Data2 |")
        for k in CANONICAL_SECTIONS
    }
    
    ver = PRDVersion(
        id="test-v-1",
        prd_id="prd-99",
        project_id="proj-9999",
        version_number="v1.0",
        sections=sections,
        changelog="Initial baseline"
    )

    # 1. Export Markdown
    md_path = export_svc.export_markdown(ver, "Sample Framework")
    assert md_path.exists()
    assert md_path.stat().st_size > 100
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
        assert "# Product Requirements Document: Sample Framework" in md_text
        assert "## 12. Functional Requirements" in md_text

    # 2. Export DOCX
    docx_path = export_svc.export_docx(ver, "Sample Framework")
    assert docx_path.exists()
    assert docx_path.stat().st_size > 1000

    # 3. Export PDF
    pdf_path = export_svc.export_pdf(ver, "Sample Framework")
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000


@pytest.mark.asyncio
async def test_version_aware_export_and_validation_api():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.core.database import db_manager
    import time

    await db_manager.connect()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ts = int(time.time() * 1000)
        u1_name = f"exp_user_{ts}"
        # 1. Register & login User 1
        reg_res = await ac.post("/api/v1/auth/register", json={
            "username": u1_name,
            "email": f"{u1_name}@example.com",
            "password": "Password123!",
            "full_name": "Export Tester"
        })
        assert reg_res.status_code == 200

        login_res = await ac.post("/api/v1/auth/login", json={
            "username": u1_name,
            "password": "Password123!"
        })
        token1 = login_res.json()["access_token"]
        h1 = {"Authorization": f"Bearer {token1}"}

        # 2. Create Project 1
        proj_res = await ac.post("/api/v1/projects", json={
            "title": "Versioned Fleet Manager",
            "target_domain": "Logistics"
        }, headers=h1)
        p1_id = proj_res.json()["id"]

        # Submit idea & analyze
        await ac.post(f"/api/v1/projects/{p1_id}/submissions", json={
            "submission_type": "idea",
            "raw_idea": "Build automated warehouse robotics scheduling and route planning."
        }, headers=h1)
        await ac.post(f"/api/v1/analysis/{p1_id}/analyze?use_mock=true", headers=h1)

        # Generate initial PRD (v1.0)
        prd_res = await ac.post(f"/api/v1/prd/{p1_id}/generate?use_mock=true", headers=h1)
        assert prd_res.status_code == 200
        v1_doc = prd_res.json()
        v1_id = v1_doc["id"]
        assert v1_doc["version_number"] == "v1.0"

        # Edit a section to produce v1.1
        patch_res = await ac.patch(f"/api/v1/prd/{p1_id}/sections/executive_summary", json={
            "content": "Updated Executive Summary for historical v1.1 snapshot."
        }, headers=h1)
        assert patch_res.status_code == 200
        v2_doc = patch_res.json()
        v2_id = v2_doc["id"]
        assert v2_doc["version_number"] == "v1.1"

        # 3. Test: Export omitting version_id defaults to current version (v1.1)
        exp_curr = await ac.get(f"/api/v1/export/{p1_id}/markdown", headers=h1)
        assert exp_curr.status_code == 200
        assert "**Version:** v1.1" in exp_curr.text
        assert "Updated Executive Summary for historical v1.1" in exp_curr.text

        # 4. Test: Export explicitly specifying older version_id exports v1.0
        exp_v1 = await ac.get(f"/api/v1/export/{p1_id}/markdown?version_id={v1_id}", headers=h1)
        assert exp_v1.status_code == 200
        assert "**Version:** v1.0" in exp_v1.text
        assert "Updated Executive Summary for historical v1.1" not in exp_v1.text

        # 5. Test: Export with DOCX and PDF with explicit version_id
        docx_res = await ac.get(f"/api/v1/export/{p1_id}/docx?version_id={v1_id}", headers=h1)
        assert docx_res.status_code == 200
        assert len(docx_res.content) > 500

        pdf_res = await ac.get(f"/api/v1/export/{p1_id}/pdf?version_id={v1_id}", headers=h1)
        assert pdf_res.status_code == 200
        assert len(pdf_res.content) > 500

        # 6. Test: Invalid version_id returns 404
        exp_inv = await ac.get(f"/api/v1/export/{p1_id}/markdown?version_id=nonexistent_version_123", headers=h1)
        assert exp_inv.status_code == 404

        # 7. Test: Tenant Isolation & Cross-Project Mismatch
        u2_name = f"tenant_user_{ts}"
        await ac.post("/api/v1/auth/register", json={
            "username": u2_name,
            "email": f"{u2_name}@example.com",
            "password": "Password123!",
            "full_name": "Tenant Two"
        })
        login_u2 = await ac.post("/api/v1/auth/login", json={
            "username": u2_name,
            "password": "Password123!"
        })
        h2 = {"Authorization": f"Bearer {login_u2.json()['access_token']}"}

        # User 2 attempts to export User 1's project -> 404
        unauth_exp = await ac.get(f"/api/v1/export/{p1_id}/markdown", headers=h2)
        assert unauth_exp.status_code == 404

        # User 2 creates their own Project 2
        proj2_res = await ac.post("/api/v1/projects", json={
            "title": "Tenant 2 Project"
        }, headers=h2)
        p2_id = proj2_res.json()["id"]
        await ac.post(f"/api/v1/projects/{p2_id}/submissions", json={
            "submission_type": "idea",
            "raw_idea": "Independent project"
        }, headers=h2)
        await ac.post(f"/api/v1/analysis/{p2_id}/analyze?use_mock=true", headers=h2)
        await ac.post(f"/api/v1/prd/{p2_id}/generate?use_mock=true", headers=h2)

        # Attempting to export Project 2 with Project 1's version_id -> 404 (does not belong to project)
        cross_exp = await ac.get(f"/api/v1/export/{p2_id}/markdown?version_id={v1_id}", headers=h2)
        assert cross_exp.status_code == 404

        # 8. Test: Version-Aware Validation
        val_v1 = await ac.get(f"/api/v1/validation/{p1_id}/report?version_id={v1_id}", headers=h1)
        assert val_v1.status_code == 200
        assert val_v1.json()["prd_version_id"] == v1_id

        val_v2 = await ac.get(f"/api/v1/validation/{p1_id}/report?version_id={v2_id}", headers=h1)
        assert val_v2.status_code == 200
        assert val_v2.json()["prd_version_id"] == v2_id

