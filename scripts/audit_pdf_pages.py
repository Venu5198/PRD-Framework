import pdfplumber
from pathlib import Path

pdf_path = Path("docs/benchmark/unified_v2_3/PRD_Customer_Support_v2_3.pdf")

with pdfplumber.open(pdf_path) as pdf:
    print(f"=== PDF AUDIT: {pdf_path.name} ===")
    print(f"Total Pages: {len(pdf.pages)}")
    
    for idx, page in enumerate(pdf.pages):
        page_num = idx + 1
        text = page.extract_text() or ""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        first_line = lines[0] if lines else "[EMPTY]"
        last_line = lines[-1] if lines else "[EMPTY]"
        
        # Check for headings on this page
        headings = [l for l in lines if any(l.startswith(f"{n}. ") for n in range(1, 28))]
        tables = page.extract_tables()
        cid_count = text.count("(cid:")
        
        print(f"\n--- Page {page_num:02d} ({page.width:.1f} x {page.height:.1f} pt) ---")
        print(f"  Lines: {len(lines)} | Text Length: {len(text)} chars")
        print(f"  First: {first_line[:65]}")
        print(f"  Last:  {last_line[:65]}")
        if headings:
            print(f"  Headings ({len(headings)}): {headings}")
        if tables:
            print(f"  Tables ({len(tables)}): rows={[len(t) for t in tables]}, cols={[len(t[0]) if t else 0 for t in tables]}")
        if cid_count > 0:
            print(f"  DEFECT: Found {cid_count} unmapped glyphs (cid:xxx) on this page")
        if len(text) < 400 and page_num < len(pdf.pages):
            print(f"  DEFECT: Premature page break / excessive whitespace (only {len(text)} chars)")
