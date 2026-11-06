import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.document_model import DocumentParser

md_path = Path("docs/benchmark/customer_support_prd_v2_3.md")
doc = DocumentParser.parse_from_markdown_file(str(md_path), "AI Customer Support Assistant")

print(f"Total Sections: {len(doc.sections)}")
for sec in doc.sections:
    for block in sec.blocks:
        if block.__class__.__name__ == "TableNode":
            print(f"\nSection: {sec.title}")
            print(f"  Headers ({len(block.headers)}): {block.headers}")
            print(f"  Rows count: {len(block.rows)}")
            for idx, r in enumerate(block.rows[:2]):
                print(f"  Row {idx+1}: {r}")
