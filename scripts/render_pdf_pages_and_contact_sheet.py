import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
import pdfplumber

def main():
    pdf_path = Path("docs/benchmark/unified_v2_3/PRD_Customer_Support_v2_3.pdf")
    pages_dir = Path("docs/screenshots/pdf_pages")
    pages_dir.mkdir(parents=True, exist_ok=True)
    contact_sheet_path = Path("docs/screenshots/pdf_contact_sheet.png")

    doc = pdfium.PdfDocument(pdf_path)
    total_pages = len(doc)
    print(f"Rendering {total_pages} pages from {pdf_path.name}...")

    rendered_images = []
    for i, page in enumerate(doc):
        page_num = i + 1
        img = page.render(scale=2.0).to_pil()
        page_file = pages_dir / f"page_{page_num:02d}.png"
        img.save(page_file)
        rendered_images.append(img)
        print(f"  Saved {page_file.name} ({img.width}x{img.height})")

    # Build Contact Sheet (3 columns x 5 rows)
    cols = 3
    rows = (total_pages + cols - 1) // cols
    thumb_w = 400
    thumb_h = int(thumb_w * (841.89 / 595.28))  # A4 ratio ~ 565px
    header_space = 28
    pad = 16

    grid_w = cols * thumb_w + (cols + 1) * pad
    grid_h = rows * (thumb_h + header_space) + (rows + 1) * pad + 60

    contact_sheet = Image.new("RGB", (grid_w, grid_h), color=(241, 245, 249)) # slate-100
    draw = ImageDraw.Draw(contact_sheet)

    # Title Banner
    draw.rectangle([(0, 0), (grid_w, 50)], fill=(15, 23, 42)) # slate-900
    draw.text((pad, 16), "Customer Support PRD v2.3 — PDF Visual Quality Inspection Contact Sheet (15 Pages)", fill=(255, 255, 255))

    for idx, img in enumerate(rendered_images):
        page_num = idx + 1
        c = idx % cols
        r = idx // cols

        x = pad + c * (thumb_w + pad)
        y = 60 + pad + r * (thumb_h + header_space + pad)

        # Label
        draw.text((x + 4, y), f"Page {page_num} of {total_pages}", fill=(51, 65, 85))

        # Thumbnail
        thumb = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        img_y = y + header_space
        contact_sheet.paste(thumb, (x, img_y))

        # Thin border
        draw.rectangle([(x, img_y), (x + thumb_w - 1, img_y + thumb_h - 1)], outline=(203, 213, 225), width=1)

    contact_sheet.save(contact_sheet_path)
    print(f"\nGenerated contact sheet: {contact_sheet_path} ({contact_sheet_path.stat().st_size} bytes)")

    # Section Mapping Audit
    print("\n--- Required Section Mapping Audit ---")
    section_targets = [
        "1. Title Page / Doc Info",
        "2. Executive Summary",
        "10. Product Scope",
        "12. Functional Requirements",
        "13. Non-Functional Requirements",
        "14. User Stories",
        "15. User Journeys",
        "21. Acceptance Criteria",
        "23. Risks and Mitigation",
        "27. Appendix and Glossary"
    ]

    with pdfplumber.open(pdf_path) as pdf:
        page_texts = [p.extract_text() or "" for p in pdf.pages]

    for target in section_targets:
        found_pages = []
        clean_target = target.split(". ", 1)[-1].lower()
        num_prefix = target.split(". ", 1)[0]
        for p_idx, text in enumerate(page_texts):
            p_lower = text.lower()
            if f"{num_prefix}. " in text or clean_target in p_lower:
                found_pages.append(p_idx + 1)
        print(f"  {target:35}: Pages {found_pages}")

if __name__ == "__main__":
    main()
