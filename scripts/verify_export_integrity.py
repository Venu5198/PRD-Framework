import os
import sys
import json
import hashlib
from pathlib import Path
import docx
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.models.prd import SECTION_TITLES, CANONICAL_SECTIONS

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def extract_text_from_md(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def extract_text_from_docx(path: Path) -> str:
    doc = docx.Document(str(path))
    full_text = []
    for p in doc.paragraphs:
        full_text.append(p.text)
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells)
            full_text.append(row_text)
    return "\n".join(full_text)

def extract_text_from_pdf(path: Path) -> str:
    text_parts = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)

def verify_exports():
    root = Path(__file__).resolve().parent.parent
    md_path = root / "PRD_Customer_Support_v2_4_6.md"
    docx_path = root / "PRD_Customer_Support_v2_4_6.docx"
    pdf_path = root / "PRD_Customer_Support_v2_4_6.pdf"
    manifest_path = root / "artifacts_manifest.json"

    print("================================================================")
    print("PHASE 2.4.6 MULTI-FORMAT EXPORT INTEGRITY & EXTRACTION AUDIT")
    print("================================================================")

    for p in [md_path, docx_path, pdf_path, manifest_path]:
        if not p.exists():
            print(f"ERROR: Missing expected deliverable: {p.name}")
            sys.exit(1)

    # 1. Manifest Hash Verification
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print("\n1. Authoritative Manifest Hash Audit:")
    for key, spec in manifest.get("artifacts", {}).items():
        filepath = root / spec["filename"]
        actual_hash = sha256_file(filepath)
        expected_hash = spec["sha256"]
        match = (actual_hash == expected_hash)
        status = "MATCH [PASS]" if match else "MISMATCH [FAIL]"
        print(f"   [{key.upper()}] {spec['filename']}")
        print(f"     Recorded SHA-256: {expected_hash}")
        print(f"     Actual SHA-256:   {actual_hash} -> {status}")
        if not match:
            print("ERROR: Hash mismatch between manifest and artifact!")
            sys.exit(1)

    # 2. Text Extraction
    print("\n2. Extracting Text from Artifacts:")
    md_text = extract_text_from_md(md_path)
    docx_text = extract_text_from_docx(docx_path)
    pdf_text = extract_text_from_pdf(pdf_path)

    print(f"   Markdown length: {len(md_text):,} chars | Lines: {len(md_text.splitlines()):,}")
    print(f"   DOCX length:     {len(docx_text):,} chars | Lines: {len(docx_text.splitlines()):,}")
    print(f"   PDF length:      {len(pdf_text):,} chars | Lines: {len(pdf_text.splitlines()):,}")

    assert len(md_text) > 5000, "Markdown text suspiciously small"
    assert len(docx_text) > 5000, "DOCX text suspiciously small"
    assert len(pdf_text) > 5000, "PDF text suspiciously small"

    # 3. Canonical Section Header Verification
    print("\n3. Cross-Format Section Header Parity Audit:")
    missing_sections = {"md": [], "docx": [], "pdf": []}
    for title in SECTION_TITLES.values():
        clean_title = title.split(". ", 1)[-1].lower()
        if clean_title not in md_text.lower():
            missing_sections["md"].append(title)
        if clean_title not in docx_text.lower():
            missing_sections["docx"].append(title)
        if clean_title not in pdf_text.lower():
            missing_sections["pdf"].append(title)

    for fmt, missing in missing_sections.items():
        if missing:
            print(f"   WARNING: Format '{fmt}' missing headers: {missing}")
        else:
            print(f"   [{fmt.upper()}] All 27 Canonical Section Headers Present [PASS]")
        assert len(missing) == 0, f"Format '{fmt}' missing canonical section headers: {missing}"

    # 4. Requirement ID Verification
    print("\n4. Requirement Traceability Parity Audit:")
    req_ids = ["FR-001", "FR-002", "FR-003", "FR-004", "NFR-001", "BR-001", "AC-001"]
    for rid in req_ids:
        in_md = rid in md_text
        in_docx = rid in docx_text
        in_pdf = rid in pdf_text
        print(f"   Requirement {rid}: MD={in_md} | DOCX={in_docx} | PDF={in_pdf}")
        assert in_md and in_docx and in_pdf, f"Requirement {rid} missing in one or more formats"

    # 5. Provenance Ledger Table Presence
    print("\n5. Provenance Ledger Presence Audit:")
    assert "Full Document Provenance Ledger" in md_text or "Provenance Ledger" in md_text, "MD missing provenance ledger"
    assert "Full Document Provenance Ledger" in docx_text or "Provenance Ledger" in docx_text, "DOCX missing provenance ledger"
    assert "Full Document Provenance Ledger" in pdf_text or "Provenance Ledger" in pdf_text, "PDF missing provenance ledger"
    print("   Provenance Ledger present in all 3 export formats [PASS]")

    print("\n================================================================")
    print("MULTI-FORMAT EXPORT INTEGRITY AUDIT: 100% PASSED")
    print("================================================================")

if __name__ == "__main__":
    verify_exports()
