import os
import sys
import hashlib
from pathlib import Path
import docx
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.services.document_model import DocumentParser
from app.services.export_service import ExportService


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def main():
    root = Path(__file__).resolve().parent.parent
    src_md = root / "docs" / "benchmark" / "customer_support_prd_v2_3.md"
    assert src_md.exists(), f"Source file {src_md} not found"

    out_dir = root / "docs" / "benchmark" / "unified_v2_3"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("================================================================")
    print("UNIFIED PRD FORMATTING PIPELINE: CUSTOMER SUPPORT PRD v2.3")
    print("================================================================")
    print(f"Reading source: {src_md} ({src_md.stat().st_size} bytes)")

    # 1. Parse into format-agnostic Document IR
    doc = DocumentParser.parse_from_markdown_file(
        str(src_md),
        project_title="AI Customer Support Assistant"
    )
    print(f"Parsed Document IR:")
    print(f"  Title: {doc.metadata.title}")
    print(f"  Version: {doc.metadata.version_number}")
    print(f"  Status: {doc.metadata.status}")
    print(f"  Total Sections in IR: {len(doc.sections)}")

    # 2. Render to all 3 export formats via ExportService
    service = ExportService(exports_dir=out_dir)

    md_path = service.export_document_to_markdown(doc, "PRD_Customer_Support_v2_3.md")
    print(f"\n1. Rendered Markdown: {md_path.name} ({md_path.stat().st_size} bytes)")
    print(f"   SHA-256: {sha256_file(md_path)}")

    docx_path = service.export_document_to_docx(doc, "PRD_Customer_Support_v2_3.docx")
    print(f"\n2. Rendered DOCX: {docx_path.name} ({docx_path.stat().st_size} bytes)")
    print(f"   SHA-256: {sha256_file(docx_path)}")

    pdf_path = service.export_document_to_pdf(doc, "PRD_Customer_Support_v2_3.pdf")
    print(f"\n3. Rendered PDF: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")
    print(f"   SHA-256: {sha256_file(pdf_path)}")

    # 3. Cross-Format Text Extraction & Parity Audit
    print("\n----------------------------------------------------------------")
    print("Cross-Format Content Extraction & Integrity Verification")
    print("----------------------------------------------------------------")

    md_text = md_path.read_text(encoding="utf-8")
    doc_file = docx.Document(str(docx_path))
    docx_text = "\n".join(p.text for p in doc_file.paragraphs) + "\n" + "\n".join(
        " | ".join(c.text for c in r.cells) for t in doc_file.tables for r in t.rows
    )

    with pdfplumber.open(str(pdf_path)) as pdf:
        pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        pdf_pages = len(pdf.pages)

    print(f"Markdown Text Length: {len(md_text):,} chars")
    print(f"DOCX Text Length:     {len(docx_text):,} chars | Tables: {len(doc_file.tables)}")
    print(f"PDF Text Length:      {len(pdf_text):,} chars | Pages: {pdf_pages}")

    # Verify Key IDs Across Formats
    key_ids = ["FR-001", "FR-002", "FR-003", "FR-004", "AC-001", "AC-002"]
    print("\nRequirement Traceability Check:")
    all_passed = True
    for req_id in key_ids:
        in_md = req_id in md_text
        in_docx = req_id in docx_text
        in_pdf = req_id in pdf_text
        status = "PASS" if (in_md and in_docx and in_pdf) else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"  [{status}] {req_id}: MD={in_md} | DOCX={in_docx} | PDF={in_pdf}")

    assert all_passed, "Cross-format requirement parity verification failed!"
    print("\n================================================================")
    print("PRD v2.3 UNIFIED EXPORT GENERATION: 100% SUCCESS")
    print("================================================================")


if __name__ == "__main__":
    main()
