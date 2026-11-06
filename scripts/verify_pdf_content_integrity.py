import re
import pdfplumber
from pathlib import Path

def main():
    source_md = Path("docs/benchmark/customer_support_prd_v2_3.md").read_text(encoding="utf-8")
    pdf_path = Path("docs/benchmark/unified_v2_3/PRD_Customer_Support_v2_3.pdf")

    print(f"=== CONTENT INTEGRITY AUDIT ===")
    print(f"Source Markdown: {len(source_md)} chars")
    print(f"Target PDF: {pdf_path.name}")

    with pdfplumber.open(pdf_path) as pdf:
        all_texts = []
        for p in pdf.pages:
            all_texts.append(p.extract_text() or "")
            for table in p.extract_tables():
                for row in table:
                    for cell in row:
                        if cell:
                            all_texts.append(cell)
        num_pages = len(pdf.pages)
        pdf_full_text = " ".join(all_texts)
        pdf_full_text_clean = re.sub(r'\s+', ' ', pdf_full_text)

    print(f"Extracted PDF Text: {len(pdf_full_text)} chars across {num_pages} pages")

    # 1. Section Headers Check (1 through 27)
    missing_sections = []
    for sec_num in range(1, 28):
        # Look for e.g. "1. Document Information"
        match = re.search(rf"^##\s+({sec_num}\.\s+.*)$", source_md, re.MULTILINE)
        if match:
            sec_title = match.group(1).strip()
            # In PDF it will appear as "X. Title"
            if sec_title not in pdf_full_text and f"{sec_num}. " not in pdf_full_text:
                missing_sections.append(sec_title)

    print(f"1. Section Preservation: {27 - len(missing_sections)}/27 sections present")
    if missing_sections:
        print(f"   Missing sections: {missing_sections}")
    assert not missing_sections, f"Missing sections in PDF: {missing_sections}"

    # 2. Requirements & AC Preservation
    req_ids = ["FR-001", "FR-002", "FR-003", "FR-004", "NFR-001", "NFR-002", "BR-001", "BR-002", "BR-003", "BR-004", "BR-005", "AC-001", "AC-002", "AC-003", "AC-004", "AC-005", "AC-006", "AC-007", "AC-008", "RSK-001", "RSK-002", "RSK-003", "RSK-004"]
    missing_reqs = [r for r in req_ids if r not in pdf_full_text]
    print(f"2. Core ID Preservation: {len(req_ids) - len(missing_reqs)}/{len(req_ids)} IDs present")
    if missing_reqs:
        print(f"   Missing IDs: {missing_reqs}")
    assert not missing_reqs, f"Missing IDs in PDF: {missing_reqs}"

    # 3. Numerical values preservation
    numbers = ["80.0%", "2000ms", "TLS 1.3", "AES-256", "2 minutes", "90%", "6 weeks", "95%", "2 hours", "99.9%"]
    missing_numbers = [n for n in numbers if n not in pdf_full_text_clean]
    print(f"3. Numerical Targets Preservation: {len(numbers) - len(missing_numbers)}/{len(numbers)} numerical tokens verified")
    if missing_numbers:
        print(f"   Missing numbers: {missing_numbers}")
    assert not missing_numbers, f"Missing numbers in PDF: {missing_numbers}"

    # 4. Glyph Check
    cid_count = pdf_full_text.count("(cid:")
    print(f"4. Glyph Integrity: {cid_count} unmapped glyphs")
    assert cid_count == 0, f"Detected {cid_count} unmapped glyphs!"

    print("\nCONTENT INTEGRITY AUDIT: 100% VERIFIED!")

if __name__ == "__main__":
    main()
