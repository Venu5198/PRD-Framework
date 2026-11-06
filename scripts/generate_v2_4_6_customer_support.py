import time
import json
import sys
import hashlib
import urllib.request
import urllib.error
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.stdout.reconfigure(line_buffering=True)
BASE_URL = "http://127.0.0.1:8000/api/v1"

def http_request(endpoint, method="GET", data=None, headers=None, retries=5):
    req_headers = dict(headers) if headers else {}
    url = f"{BASE_URL}{endpoint}"
    req_body = None
    if data is not None:
        req_body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    elif method == "POST":
        req_body = b"{}"
        req_headers["Content-Type"] = "application/json"
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=req_body, headers=req_headers, method=method)
            with urllib.request.urlopen(req, timeout=180) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read()
                if "application/json" in content_type:
                    return resp.status, json.loads(raw.decode("utf-8"))
                return resp.status, raw
        except (urllib.error.URLError, ConnectionError) as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("================================================================")
    print("PHASE 2.4.6 REAL GROQ AI BENCHMARK: CUSTOMER SUPPORT PRD")
    print("================================================================")

    ts = int(time.time())
    username = f"phase246_auditor_{ts}"
    password = "Password123!"

    # 1. Register & Login
    print(f"\n1. Registering user '{username}'...")
    http_request("/auth/register", method="POST", data={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "full_name": "Phase 2.4.6 Principal Auditor"
    })
    _, auth_res = http_request("/auth/login", method="POST", data={
        "username": username,
        "password": password
    })
    headers = {"Authorization": f"Bearer {auth_res['access_token']}"}

    # 2. Create Customer Support Project
    print("2. Creating Project 'AI Customer Support Assistant'...")
    _, proj = http_request("/projects", method="POST", data={
        "title": "AI Customer Support Assistant",
        "description": "Enterprise customer service assistant with knowledge retrieval and human escalation",
        "target_domain": "Customer Support"
    }, headers=headers)
    pid = proj["id"]
    print(f"   Project ID: {pid}")

    raw_concept = (
        "Build an AI customer support assistant that answers user questions using approved knowledge-base articles, "
        "maintains conversation history, detects low-confidence answers below 80%, and escalates complex queries to human agents."
    )
    http_request(f"/projects/{pid}/submissions", method="POST", data={
        "submission_type": "idea",
        "raw_idea": raw_concept,
        "problem_statement": "Support representatives are overloaded with repetitive inquiries, leading to high wait times and inconsistent answer quality."
    }, headers=headers)

    # 3. Trigger Async Generation via Worker with Groq
    print("\n3. Dispatching Generation Job with Groq API (force_mock=False)...")
    t0 = time.perf_counter()
    code, gen_resp = http_request(f"/projects/{pid}/prd/generate", method="POST", data={
        "force_mock": False
    }, headers=headers)
    job_id = gen_resp["job_id"]
    print(f"   Job ID: {job_id}")

    # 4. Poll until completed
    print("\n4. Polling Job Status...")
    job = {}
    for i in range(250):
        time.sleep(2)
        _, job = http_request(f"/jobs/{job_id}", headers=headers)
        status = job.get("status")
        stage = job.get("current_stage")
        completed = job.get("completed_stages", [])
        elapsed_sec = job.get("elapsed_seconds")
        print(f"   [{i*2}s] Status: {status} | Current: {stage} | Completed: {len(completed)} stages | Elapsed: {elapsed_sec}s")
        if status in ("completed", "failed"):
            break

    elapsed_total = time.perf_counter() - t0
    print(f"\nJob Execution Finished in {elapsed_total:.2f}s with status={status}")
    if status != "completed":
        print(f"ERROR: Job failed with error: {job.get('error_message')}")
        sys.exit(1)

    # 5. Retrieve PRD Document & Active Version
    _, prd_data = http_request(f"/prd/{pid}", headers=headers)
    active_ver = prd_data.get("active_version", {})
    sections = active_ver.get("sections", {})
    ver_id = active_ver.get("id")
    provenance_ledger = active_ver.get("provenance_ledger", [])

    provider = job.get("provider", "groq")
    model = job.get("model", "openai/gpt-oss-20b")
    force_mock = job.get("force_mock", False)

    print(f"\n--- GENERATED PRD METADATA ---")
    print(f"PRD Version ID:     {ver_id}")
    print(f"Version Number:     {active_ver.get('version_number')}")
    print(f"Status:             {active_ver.get('status')}")
    print(f"Provider:           {provider}")
    print(f"Model:              {model}")
    print(f"Force Mock:         {force_mock}")
    print(f"Total Sections:     {len(sections)} / 27")
    print(f"Provenance Entries: {len(provenance_ledger)}")

    # 6. Validate PRD Document
    print(f"\n5. Running Strict Phase 2.4.6 Structured Validation...")
    code, val_report = http_request(f"/validation/{pid}/validate?version_id={ver_id}", method="POST", headers=headers)
    score = val_report.get("score")
    verdict = val_report.get("verdict")
    errors = [i for i in val_report.get("issues", []) if i.get("severity") == "error"]
    warnings = [i for i in val_report.get("issues", []) if i.get("severity") == "warning"]

    print(f"   Validation Score:    {score} / 100")
    print(f"   Validation Verdict:  {verdict}")
    print(f"   Error Count:         {len(errors)}")
    print(f"   Warning Count:       {len(warnings)}")

    if errors:
        print("\n[VALIDATION ERRORS]")
        for err in errors:
            print(f"   - [{err.get('rule_id')}] in {err.get('section_key')}: {err.get('title')}")
            print(f"     {err.get('description')}")
    if warnings:
        print("\n[VALIDATION WARNINGS]")
        for w in warnings:
            print(f"   - [{w.get('rule_id')}] in {w.get('section_key')}: {w.get('title')}")

    # 7. Export Artifacts
    print(f"\n6. Exporting Phase 2.4.6 Deliverables...")
    # Markdown
    _, md_bytes = http_request(f"/export/{pid}/markdown?version_id={ver_id}", headers=headers)
    md_path = Path("PRD_Customer_Support_v2_4_6.md")
    with open(md_path, "wb") as f:
        f.write(md_bytes)
    print(f"   Saved: {md_path.name} ({len(md_bytes)} bytes)")

    # DOCX
    _, docx_bytes = http_request(f"/export/{pid}/docx?version_id={ver_id}", headers=headers)
    docx_path = Path("PRD_Customer_Support_v2_4_6.docx")
    with open(docx_path, "wb") as f:
        f.write(docx_bytes)
    print(f"   Saved: {docx_path.name} ({len(docx_bytes)} bytes)")

    # PDF
    _, pdf_bytes = http_request(f"/export/{pid}/pdf?version_id={ver_id}", headers=headers)
    pdf_path = Path("PRD_Customer_Support_v2_4_6.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"   Saved: {pdf_path.name} ({len(pdf_bytes)} bytes)")

    # 8. Validate Rendered Markdown directly
    print(f"\n7. Validating Rendered Markdown File ({md_path.name})...")
    from app.services.validation_service import ValidationService
    from app.models.analysis import AnalysisRecord

    md_text = md_path.read_text(encoding="utf-8")
    validator = ValidationService(validation_repo=None)
    analysis_record = AnalysisRecord(
        project_id=pid,
        problem_domain="Customer Support",
        product_category="AI Customer Support Assistant",
        intended_users=["Customer", "Support Representative"],
        core_objectives=["Answer user questions using approved knowledge-base articles", "Maintain conversation history", "Detect low-confidence answers below 80%", "Escalate complex queries to human agents"],
        expected_capabilities=["KB retrieval", "Conversation history", "80% confidence evaluation", "Human escalation with context summary"],
        explicit_constraints=["Web chat only", "80% confidence threshold"],
        facts=["Approved knowledge-base articles only"]
    )
    md_report = asyncio.run(validator.validate_markdown(md_text, analysis=analysis_record))
    print(f"   Rendered Markdown Score:   {md_report.score} / 100")
    print(f"   Rendered Markdown Verdict: {md_report.verdict}")
    print(f"   Rendered Markdown Errors:  {md_report.error_count}")
    print(f"   Rendered Markdown Warnings:{md_report.warning_count}")

    # 9. Compute Manifest
    print(f"\n8. Generating artifacts_manifest.json...")
    manifest = {
        "phase": "2.4.6",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "project_id": pid,
        "job_id": job_id,
        "prd_version_id": ver_id,
        "version_number": "v2.4.6",
        "provider": provider,
        "model": model,
        "force_mock": force_mock,
        "validation": {
            "score": score,
            "verdict": verdict,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "markdown_score": md_report.score,
            "markdown_verdict": md_report.verdict,
            "markdown_error_count": md_report.error_count
        },
        "provenance_summary": {
            "total_entries": len(provenance_ledger),
            "categories": {}
        },
        "artifacts": {
            "markdown": {
                "filename": md_path.name,
                "size_bytes": len(md_bytes),
                "sha256": sha256_file(md_path)
            },
            "docx": {
                "filename": docx_path.name,
                "size_bytes": len(docx_bytes),
                "sha256": sha256_file(docx_path)
            },
            "pdf": {
                "filename": pdf_path.name,
                "size_bytes": len(pdf_bytes),
                "sha256": sha256_file(pdf_path)
            }
        }
    }

    for ple in provenance_ledger:
        cat = ple.get("classification") or ple.get("provenance", "UNKNOWN")
        manifest["provenance_summary"]["categories"][cat] = manifest["provenance_summary"]["categories"].get(cat, 0) + 1

    manifest_path = Path("artifacts_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"   Saved: {manifest_path.name}")
    print(json.dumps(manifest, indent=2))

    print("\n================================================================")
    print("PHASE 2.4.6 GENERATION & AUDIT COMPLETED")
    print("================================================================")

if __name__ == "__main__":
    main()
