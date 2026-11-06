import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    print("Beginning repository reorganization...")

    # 1. Create target directories
    target_dirs = [
        ROOT / "docs" / "architecture",
        ROOT / "docs" / "user-guide",
        ROOT / "docs" / "development",
        ROOT / "docs" / "examples",
        ROOT / "docs" / "archive" / "phase-reports",
        ROOT / "tests" / "fixtures" / "historical-prds",
    ]
    for d in target_dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"Ensured directory: {d.relative_to(ROOT)}")

    # 2. Copy historical PRD markdown files to tests/fixtures/historical-prds/
    fixture_files = [
        "PRD_Customer_Support_Final.md",
        "PRD_Customer_Support_v2_4_4.md",
        "PRD_Customer_Support_v2_4_5.md",
        "PRD_Customer_Support_v2_4_6.md",
    ]
    for f in fixture_files:
        src = ROOT / f
        dst = ROOT / "tests" / "fixtures" / "historical-prds" / f
        if src.exists():
            shutil.copy2(src, dst)
            print(f"Preserved fixture: {dst.relative_to(ROOT)}")

    # Also copy v2.4.1 and v2.4.2 from docs/benchmark if available
    benchmark_dir = ROOT / "docs" / "benchmark"
    for b in ["PRD_Customer_Support_v2_4_1.md", "PRD_Customer_Support_v2_4_2.md"]:
        src = benchmark_dir / b
        dst = ROOT / "tests" / "fixtures" / "historical-prds" / b
        if src.exists():
            shutil.copy2(src, dst)
            print(f"Copied benchmark fixture: {dst.relative_to(ROOT)}")

    # 3. Copy reference example to docs/examples/
    example_src = ROOT / "PRD_Customer_Support_v2_4_6.md"
    example_dst = ROOT / "docs" / "examples" / "customer_support_prd_example.md"
    if example_src.exists():
        shutil.copy2(example_src, example_dst)
        print(f"Published example PRD: {example_dst.relative_to(ROOT)}")

    # 4. Move historical phase reports into docs/archive/phase-reports/
    archive_dir = ROOT / "docs" / "archive" / "phase-reports"
    docs_dir = ROOT / "docs"
    
    # Reports in docs/
    report_patterns = [
        "PHASE_2_4_5_*.md",
        "PHASE_2_4_6_*.md",
        "PHASE_2_4_7_*.md",
        "PHASE_2_4_7_RELEASE_MANIFEST.json",
        "PRD_ENGINEERING_*.md",
        "PRD_OUTPUT_QUALITY_AUDIT.md",
        "ASYNC_GENERATION_VERIFICATION_REPORT.md",
        "ASYNC_JOB_QA_REPORT.md",
        "GROQ_INTEGRATION_IMPLEMENTATION_REPORT.md",
        "PLAYWRIGHT_FAILURE_ANALYSIS.md",
        "PLAYWRIGHT_QA_REPORT.md",
    ]
    import glob
    for pat in report_patterns:
        for file_path in docs_dir.glob(pat):
            # Don't move PRD_ENGINEERING_V2_DATA_FLOW.md to archive if it belongs in architecture
            if file_path.name == "PRD_ENGINEERING_V2_DATA_FLOW.md":
                continue
            dest_file = archive_dir / file_path.name
            shutil.move(file_path, dest_file)
            print(f"Archived report: {file_path.name} -> {dest_file.relative_to(ROOT)}")

    # Move artifacts_manifest.json and binary exports to archive
    root_manifest = ROOT / "artifacts_manifest.json"
    if root_manifest.exists():
        shutil.move(root_manifest, archive_dir / "artifacts_manifest_v2.4.6.json")
        print("Archived artifacts_manifest.json -> docs/archive/phase-reports/artifacts_manifest_v2.4.6.json")

    # Preserve historical binary exports under docs/archive/phase-reports/
    historical_binaries = [
        "PRD_Customer_Support_Final.pdf",
        "PRD_Customer_Support_v2_4_4.docx",
        "PRD_Customer_Support_v2_4_4.pdf",
        "PRD_Customer_Support_v2_4_5.docx",
        "PRD_Customer_Support_v2_4_5.pdf",
        "PRD_Customer_Support_v2_4_6.docx",
        "PRD_Customer_Support_v2_4_6.pdf",
    ]
    for hb in historical_binaries:
        src = ROOT / hb
        if src.exists():
            shutil.move(src, archive_dir / hb)
            print(f"Archived historical export: {hb} -> docs/archive/phase-reports/{hb}")

    # 5. Move architecture files to docs/architecture/
    arch_files = [
        "ARCHITECTURE.md",
        "HLD.md",
        "LLD.md",
        "ASYNC_JOB_ARCHITECTURE.md",
        "PRD_ENGINEERING_V2_DATA_FLOW.md",
    ]
    for af in arch_files:
        src = docs_dir / af
        if src.exists():
            shutil.move(src, ROOT / "docs" / "architecture" / af)
            print(f"Moved architecture doc: {af}")

    # 6. Move development guides to docs/development/
    dev_files = [
        "SECURITY.md",
        "TEST_STRATEGY.md",
        "PDF_FORMATTING_REPAIR_REPORT.md",
        "UNIFIED_PRD_FORMATTING_REPORT.md",
    ]
    for df in dev_files:
        src = docs_dir / df
        if src.exists():
            shutil.move(src, ROOT / "docs" / "development" / df)
            print(f"Moved development guide: {df}")

    # 7. Move user guide to docs/user-guide/
    prd_src = docs_dir / "PRD.md"
    if prd_src.exists():
        shutil.move(prd_src, ROOT / "docs" / "user-guide" / "PRD.md")
        print("Moved user-guide doc: PRD.md")

    # 8. Remove duplicate and temporary files from root
    root_to_remove = [
        "PHASE_2_4_5_IMPLEMENTATION_REPORT.md",
        "PHASE_2_4_5_PROVENANCE_AUDIT.md",
        "PHASE_2_4_5_VALIDATION_REPORT.md",
        "PRD_Customer_Support_Final.md",
        "PRD_Customer_Support_v2_4_4.md",
        "PRD_Customer_Support_v2_4_5.md",
        "PRD_Customer_Support_v2_4_6.md",
        ".coverage",
    ]
    for r in root_to_remove:
        path = ROOT / r
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"Cleaned root file: {r}")

    # Remove .pytest_cache if present
    pytest_cache = ROOT / ".pytest_cache"
    if pytest_cache.exists():
        shutil.rmtree(pytest_cache, ignore_errors=True)
        print("Cleaned .pytest_cache")

    print("\nReorganization complete!")

if __name__ == "__main__":
    main()
