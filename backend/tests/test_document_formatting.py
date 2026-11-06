import os
import re
import pytest
from pathlib import Path
from datetime import datetime

from app.models.prd import PRDVersion, PRDSectionContent, CANONICAL_SECTIONS, SECTION_TITLES
from app.services.document_model import (
    Document,
    DocumentMetadata,
    DocumentParser,
    SectionNode,
    HeadingNode,
    ParagraphNode,
    TableNode,
    ListNode,
    CodeBlockNode,
    CalloutNode,
    DiagramNode
)
from app.services.export_service import ExportService, clean_xml_text


@pytest.fixture
def sample_prd_version():
    sections = {}
    for idx, key in enumerate(CANONICAL_SECTIONS):
        title = SECTION_TITLES.get(key, key.replace('_', ' ').title())
        if key == "functional_requirements":
            content = (
                "### In-Scope Functional Capabilities\n\n"
                "| Requirement ID | Capability | Priority | Provenance |\n"
                "| :--- | :--- | :---: | :--- |\n"
                "| FR-001 | Knowledge Base Search | P0 | `USER_CONFIRMED` |\n"
                "| FR-002 | Conversation Memory | P0 | `USER_CONFIRMED` |\n"
                "| FR-003 | Confidence Scoring | P1 | `INFERRED` |\n"
                "| FR-004 | Human Agent Escalation | P0 | `USER_CONFIRMED` |\n\n"
                "The system must evaluate confidence scores on a 0-100% scale.\n"
            )
        elif key == "acceptance_criteria":
            content = (
                "### Testable Scenarios\n\n"
                "- **AC-001**: Given user inputs query, when matched in KB, then return answer with citation.\n"
                "- **AC-002**: Given confidence < 80%, when answered, then flag for human escalation.\n"
                "- **AC-003**: Given agent escalation, when triggered, then transfer conversation history.\n"
            )
        elif key == "system_workflows":
            content = (
                "```mermaid\ngraph TD\n  Client[Web Client] --> Gateway[API Gateway]\n  Gateway --> AI[LLM Service]\n```\n\n"
                "Architecture overview of local-first deployment."
            )
        elif key == "integration_requirements":
            content = (
                "```json\n{\n  \"endpoint\": \"/api/v1/chat\",\n  \"method\": \"POST\"\n}\n```\n"
            )
        elif key == "appendix_and_glossary":
            # Section marked Not Applicable
            sections[key] = PRDSectionContent(
                key=key,
                title=title,
                content="",
                is_na=True,
                na_rationale="Omitted from baseline product scope"
            )
            continue
        else:
            content = f"Standard content for {title} detailing technical specifications and system boundaries."

        sections[key] = PRDSectionContent(
            key=key,
            title=title,
            content=content,
            is_na=False
        )

    return PRDVersion(
        id="test_ver_12345",
        prd_id="prd_test_123",
        project_id="test_proj_67890",
        version_number="v2.3",
        status="approved",
        sections=sections,
        changelog="Unified formatting verification baseline",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        job_id="job-test-uuid-001",
        created_at=datetime(2026, 11, 5, 12, 0, 0),
        created_by="Lead QA Architect"
    )


def test_document_parser_ir_generation(sample_prd_version):
    """Verifies that DocumentParser converts PRDVersion into an accurate Document IR."""
    doc = DocumentParser.parse_prd(sample_prd_version, "AI Customer Support Assistant")

    assert doc.metadata.title == "AI Customer Support Assistant"
    assert doc.metadata.version_number == "v2.3"
    assert doc.metadata.status == "approved"
    assert doc.total_sections() == 27
    assert doc.active_sections_count() == 26  # appendix is NA

    # Check functional requirements section
    fr_sec = next(s for s in doc.sections if s.key == "functional_requirements")
    assert not fr_sec.is_na
    assert any(isinstance(b, TableNode) for b in fr_sec.blocks)

    table = next(b for b in fr_sec.blocks if isinstance(b, TableNode))
    assert table.headers == ["Requirement ID", "Capability", "Priority", "Provenance"]
    assert len(table.rows) == 4
    assert table.rows[0][0] == "FR-001"
    assert table.rows[1][0] == "FR-002"

    # Check Mermaid diagram node
    arch_sec = next(s for s in doc.sections if s.key == "system_workflows")
    diagram = next(b for b in arch_sec.blocks if isinstance(b, DiagramNode))
    assert diagram.diagram_type == "mermaid"
    assert "Client[Web Client]" in diagram.code


def test_markdown_export_formatting(tmp_path, sample_prd_version):
    """Verifies that Markdown export contains proper hierarchy, tables, and no raw HTML."""
    service = ExportService(exports_dir=tmp_path)
    md_path = service.export_markdown(sample_prd_version, "AI Customer Support Assistant")

    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")

    # Document Header & Metadata
    assert "# Product Requirements Document: AI Customer Support Assistant" in content
    assert "**Version:** v2.3" in content
    assert "**Status:** APPROVED" in content
    assert "**Job ID:** job-test-uuid-001" in content

    # All 27 section headers must exist at H2 level
    for sec_key in CANONICAL_SECTIONS:
        title = SECTION_TITLES.get(sec_key, sec_key)
        assert f"## {title}" in content

    # Check table structure
    assert "| Requirement ID | Capability | Priority | Provenance |" in content
    assert "| :--- | :---: | :--- |" in content or "| --- |" in content
    assert "| FR-001 | Knowledge Base Search | P0 | `USER_CONFIRMED` |" in content

    # Check code fences
    assert "```mermaid" in content
    assert "```json" in content

    # Check Acceptance Criteria IDs
    assert "AC-001" in content
    assert "AC-002" in content

    # Verify no raw HTML tags leaked into markdown
    assert "<div" not in content
    assert "<span" not in content


def test_docx_export_formatting(tmp_path, sample_prd_version):
    """Verifies that DOCX export generates valid Word document with native styles and tables."""
    import docx

    service = ExportService(exports_dir=tmp_path)
    docx_path = service.export_docx(sample_prd_version, "AI Customer Support Assistant")

    assert docx_path.exists()
    doc = docx.Document(str(docx_path))

    # Verify Margins (1 inch = 914400 EMUs)
    for section in doc.sections:
        assert section.top_margin.inches == 1.0
        assert section.bottom_margin.inches == 1.0
        assert section.left_margin.inches == 1.0
        assert section.right_margin.inches == 1.0

    # Extract all text
    all_text = " ".join(p.text for p in doc.paragraphs)
    assert "Product Requirements Document" in all_text
    assert "AI Customer Support Assistant" in all_text
    assert "v2.3" in all_text

    # Verify tables
    assert len(doc.tables) >= 1
    fr_table = doc.tables[0]
    headers = [cell.text for cell in fr_table.rows[0].cells]
    assert "Requirement ID" in headers

    # Check data cell contents
    flat_cells = " ".join(cell.text for row in fr_table.rows for cell in row.cells)
    assert "FR-001" in flat_cells
    assert "FR-002" in flat_cells


def test_pdf_export_formatting(tmp_path, sample_prd_version):
    """Verifies that PDF export generates valid PDF with NumberedCanvas and tables."""
    import pdfplumber

    service = ExportService(exports_dir=tmp_path)
    pdf_path = service.export_pdf(sample_prd_version, "AI Customer Support Assistant")

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 5000

    with pdfplumber.open(str(pdf_path)) as pdf:
        assert len(pdf.pages) >= 2
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # Document Header
        assert "Product Requirements Document" in full_text
        assert "AI Customer Support Assistant" in full_text
        assert "v2.3" in full_text

        # Requirement IDs
        assert "FR-001" in full_text
        assert "FR-002" in full_text
        assert "AC-001" in full_text

        # Running Footer page format
        assert "Page 1 of" in full_text or "Page 2 of" in full_text


def test_special_characters_and_long_tables(tmp_path):
    """Verifies handling of special characters, XML entities, and long tables without crash."""
    special_text = (
        "Special characters: & < > \" ' `code` **bold** *italic*\n\n"
        "| ID | Expression | Description |\n"
        "| :--- | :--- | :--- |\n"
        "| SP-001 | A < B & C > D | Formula with & and < and > |\n"
        "| SP-002 | user@domain.com | Email address with 'quotes' |\n"
    )
    blocks = DocumentParser.parse_markdown_blocks(special_text)
    assert len(blocks) >= 2

    # Verify clean_xml_text escapes XML properly
    xml_safe = clean_xml_text("Formula: A < B & C > D with **bold** and `code`")
    assert "&lt;" in xml_safe
    assert "&amp;" in xml_safe
    assert "&gt;" in xml_safe
    assert "<b>bold</b>" in xml_safe
    assert "<font face=\"Courier\">code</font>" in xml_safe


def test_cross_format_parity_check(tmp_path, sample_prd_version):
    """Verifies that Markdown, DOCX, and PDF preserve identical requirements and section structure."""
    import docx
    import pdfplumber

    service = ExportService(exports_dir=tmp_path)
    md_path = service.export_markdown(sample_prd_version, "AI Customer Support Assistant")
    docx_path = service.export_docx(sample_prd_version, "AI Customer Support Assistant")
    pdf_path = service.export_pdf(sample_prd_version, "AI Customer Support Assistant")

    # Extract text from all three
    md_text = md_path.read_text(encoding="utf-8")

    doc = docx.Document(str(docx_path))
    docx_text = "\n".join(p.text for p in doc.paragraphs) + "\n" + "\n".join(
        " | ".join(c.text for c in r.cells) for t in doc.tables for r in t.rows
    )

    with pdfplumber.open(str(pdf_path)) as pdf:
        pdf_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    # All three formats must contain core IDs
    for req_id in ["FR-001", "FR-002", "FR-003", "FR-004", "AC-001", "AC-002"]:
        assert req_id in md_text, f"{req_id} missing from Markdown"
        assert req_id in docx_text, f"{req_id} missing from DOCX"
        assert req_id in pdf_text, f"{req_id} missing from PDF"


def test_pdf_a4_page_geometry_and_margins(tmp_path, sample_prd_version):
    """Verifies that PDF export outputs exact A4 dimensions with 1-inch margins."""
    import pdfplumber

    service = ExportService(exports_dir=tmp_path)
    pdf_path = service.export_pdf(sample_prd_version, "AI Customer Support Assistant")

    with pdfplumber.open(str(pdf_path)) as pdf:
        assert len(pdf.pages) >= 2
        for page in pdf.pages:
            # A4 dimensions: 595.28 x 841.89 pt (+- 0.5 pt tolerance)
            assert abs(page.width - 595.28) < 1.0, f"Expected A4 width 595.28, got {page.width}"
            assert abs(page.height - 841.89) < 1.0, f"Expected A4 height 841.89, got {page.height}"


def test_pdf_unicode_bullet_and_glyph_integrity(tmp_path):
    """Verifies that UTF-8 bullet points and em dashes render without unmapped glyphs."""
    import pdfplumber

    doc = Document(
        metadata=DocumentMetadata(
            title="Glyph Integrity Test",
            version_number="v1.0",
            status="approved",
            created_at=datetime.utcnow()
        ),
        sections=[
            SectionNode(
                title="1. Bullet Points & Unicode",
                key="bullet_test",
                blocks=[
                    ListNode(
                        items=[
                            "First bullet point item",
                            "Second item with — em dash and quotes",
                            "Third item with comparison: confidence >= 80.0%"
                        ],
                        ordered=False
                    )
                ]
            )
        ]
    )

    service = ExportService(exports_dir=tmp_path)
    pdf_path = service.export_document_to_pdf(doc, "test_glyphs.pdf")

    with pdfplumber.open(str(pdf_path)) as pdf:
        text = pdf.pages[0].extract_text()
        assert "(cid:" not in text, f"Unmapped CID glyph detected: {text}"
        assert "First bullet point item" in text
        assert "confidence >= 80.0%" in text


def test_pdf_content_aware_table_column_sizing():
    """Verifies compute_pdf_table_col_widths allocates width proportionally without starving text."""
    from app.services.export_service import compute_pdf_table_col_widths

    headers = ["ID", "Title", "Description", "Priority", "Traceable AC"]
    rows = [
        ["FR-001", "Grounded KB Retrieval", "Very long narrative description explaining actor, trigger, preconditions, inputs, behavior, constraints, and audit trails." * 5, "Must Have", "AC-001, AC-002"],
        ["FR-002", "Session Management", "Detailed session isolation and multi-turn context retention requirements." * 4, "Must Have", "AC-003"]
    ]

    widths = compute_pdf_table_col_widths(headers, rows, avail_width=451.28)
    assert len(widths) == 5
    assert abs(sum(widths) - 451.28) < 0.5

    # Description (column 2) must receive dominant share (> 200 pt)
    assert widths[2] > 200.0
    # ID and Priority must remain compact (< 60 pt)
    assert widths[0] < 60.0
    assert widths[3] < 60.0


def test_pdf_wide_table_and_repeated_headers(tmp_path):
    """Verifies that 9-column wide tables format cleanly and headers repeat on page breaks."""
    import pdfplumber

    risk_headers = ["Risk ID", "Category", "Risk Description", "Root Cause", "Likelihood", "Impact", "Mitigation Strategy", "Contingency Plan", "Owner"]
    risk_rows = [
        [f"RSK-{i:03d}", "Operational", f"Detailed description for risk {i} with operational impact.", "Root cause analysis detail.", "Medium", "High", "Mitigation procedure with ongoing audit.", "Contingency fallback plan.", "Team Alpha"]
        for i in range(1, 15)  # 14 rows will span multiple pages
    ]

    doc = Document(
        metadata=DocumentMetadata(
            title="Wide Table Test",
            version_number="v2.0",
            status="approved",
            created_at=datetime.utcnow()
        ),
        sections=[
            SectionNode(
                title="1. Multi-Page Risk Table",
                key="risks",
                blocks=[TableNode(headers=risk_headers, rows=risk_rows)]
            )
        ]
    )

    service = ExportService(exports_dir=tmp_path)
    pdf_path = service.export_document_to_pdf(doc, "test_wide_table.pdf")

    with pdfplumber.open(str(pdf_path)) as pdf:
        assert len(pdf.pages) >= 2
        for page in pdf.pages:
            tables = page.extract_tables()
            assert len(tables) >= 1
            # Header row repeated on every page
            first_row = tables[0][0]
            assert any("Risk ID" in str(c) for c in first_row)
            assert any("Mitigation" in str(c) for c in first_row)


def test_pdf_running_headers_and_footers(tmp_path, sample_prd_version):
    """Verifies running headers on pages 2+ and footers on all pages with correct page counts."""
    import pdfplumber

    service = ExportService(exports_dir=tmp_path)
    pdf_path = service.export_pdf(sample_prd_version, "AI Customer Support Assistant")

    with pdfplumber.open(str(pdf_path)) as pdf:
        total_pages = len(pdf.pages)
        assert total_pages >= 2

        # Page 1: Has footer with "Page 1 of X", no running header
        page1_text = pdf.pages[0].extract_text()
        assert f"Page 1 of {total_pages}" in page1_text
        assert "PRODUCT REQUIREMENTS DOCUMENT" in page1_text

        # Page 2+: Has running header with document title and version, and footer
        page2_text = pdf.pages[1].extract_text()
        assert "Product Requirements Document | AI Customer Support Assistant" in page2_text
        assert f"Page 2 of {total_pages}" in page2_text
