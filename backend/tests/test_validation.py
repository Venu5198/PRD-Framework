import pytest
from app.services.validation_service import ValidationService
from app.models.prd import PRDVersion, PRDSectionContent
from datetime import datetime
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_validation_missing_sections():
    mock_repo = AsyncMock()
    mock_repo.create.return_value = {"id": "rep-1"}
    svc = ValidationService(mock_repo)

    # Incomplete version with only 2 sections
    incomplete_version = PRDVersion(
        id="v-1",
        prd_id="prd-1",
        project_id="proj-1",
        version_number="v1.0",
        sections={
            "document_information": PRDSectionContent(key="document_information", title="1. Doc Info", content="Valid content here"),
            "executive_summary": PRDSectionContent(key="executive_summary", title="2. Exec Summary", content="Valid summary here")
        }
    )

    report = await svc.validate_version(incomplete_version)
    assert report.is_valid is False
    assert report.error_count > 0
    assert any(i.rule_id == "VAL-SEC-001" for i in report.issues)
    assert report.score < 50

@pytest.mark.asyncio
async def test_validation_duplicate_and_unmapped_fr():
    mock_repo = AsyncMock()
    mock_repo.create.return_value = {"id": "rep-2"}
    svc = ValidationService(mock_repo)

    from app.models.prd import CANONICAL_SECTIONS, SECTION_TITLES
    all_sections = {
        k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content=f"Valid detailed content for {k} exceeding fifteen chars.")
        for k in CANONICAL_SECTIONS
    }
    # Inject duplicate FR and missing AC
    all_sections["functional_requirements"].content = (
        "| ID | Title |\n|---|---|\n"
        "| FR-001 | Feature One |\n"
        "| FR-001 | Duplicate Feature One |\n"
        "| FR-002 | Feature Two without AC |\n"
    )
    all_sections["acceptance_criteria"].content = "| ID | Req | Statement |\n|---|---|---|\n| AC-001 | FR-001 | Statement |"

    ver = PRDVersion(
        id="v-2",
        prd_id="prd-1",
        project_id="proj-1",
        version_number="v1.0",
        sections=all_sections
    )

    report = await svc.validate_version(ver)
    assert any(i.rule_id == "VAL-REQ-001" for i in report.issues)  # duplicate FR
    assert any(i.rule_id == "VAL-AC-001" for i in report.issues)   # unmapped FR-002

