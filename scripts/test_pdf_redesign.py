import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.document_model import DocumentParser
from app.services.export_service import ExportService
from app.models.prd import PRDVersion
import pdfplumber
import pypdfium2 as pdfium

md_path = Path("docs/benchmark/customer_support_prd_v2_3.md")
doc = DocumentParser.parse_from_markdown_file(str(md_path), "AI Customer Support Assistant")

exporter = ExportService(exports_dir=Path("docs/benchmark/unified_v2_3"))
output_pdf = exporter.export_document_to_pdf(doc, "PRD_Customer_Support_v2_3_test.pdf")

print(f"Generated test PDF: {output_pdf} ({output_pdf.stat().st_size} bytes)")

# Audit with pdfplumber
with pdfplumber.open(output_pdf) as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    for i, p in enumerate(pdf.pages):
        text = p.extract_text() or ""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        cid_count = text.count("(cid:")
        first_line = lines[0] if lines else "[EMPTY]"
        print(f"Page {i+1:02d} ({p.width:.1f}x{p.height:.1f}): {len(text)} chars | CID count: {cid_count} | First: {first_line[:60]}")
        if len(text) < 300 and i < len(pdf.pages) - 1:
            print(f"  WARNING: Page {i+1} has low char count ({len(text)} chars)")
