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
