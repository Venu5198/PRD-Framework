import sys
sys.path.insert(0, "backend")
import json
from pathlib import Path
from app.services.export_service import ExportService
from app.models.prd import PRDVersion
from tests.test_phase2_4_1_fixtures import make_valid_sections

def main():
    exports_dir = Path("exports")
    exports_dir.mkdir(parents=True, exist_ok=True)

    sections = make_valid_sections("AI Customer Support Suite", "Customer Support", version="v2.4.7")
    prd_ver = PRDVersion(
        prd_id="prd_cs_v2_4_7",
        project_id="proj_cs_v2_4_7",
        version_number="v2.4.7",
        status="approved",
        sections=sections
    )

    srv = ExportService(exports_dir=exports_dir)
    manifest = srv.export_all_with_manifest(prd_ver, "AI Customer Support Suite")

    print("Export Manifest generated:")
    for k, v in manifest["artifacts"].items():
        print(f"  {k}: {v['filename']} ({v['size_bytes']} bytes) - SHA256: {v['sha256']}")
    print(f"Manifest path: {manifest['manifest_path']}")

    # Write copy to docs/PHASE_2_4_7_RELEASE_MANIFEST.json
    release_manifest_path = Path("docs/PHASE_2_4_7_RELEASE_MANIFEST.json")
    with open(release_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved release manifest to: {release_manifest_path}")

if __name__ == "__main__":
    main()
