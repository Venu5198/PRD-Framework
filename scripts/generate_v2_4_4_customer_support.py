import time
import json
import sys
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
BASE_URL = "http://127.0.0.1:8000/api/v1"

def http_request(endpoint, method="GET", data=None, headers=None):
    req_headers = dict(headers) if headers else {}
    url = f"{BASE_URL}{endpoint}"
    req_body = None
    if data is not None:
        req_body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    elif method == "POST":
        req_body = b"{}"
        req_headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=req_body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=180) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()
        if "application/json" in content_type:
            return resp.status, json.loads(raw.decode("utf-8"))
        return resp.status, raw

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("================================================================")
    print("PHASE 2.4.4 REAL GROQ AI BENCHMARK: CUSTOMER SUPPORT PRD")
    print("================================================================")

    ts = int(time.time())
    username = f"phase244_auditor_{ts}"
    password = "Password123!"

    # 1. Register & Login
    print(f"\n1. Registering user '{username}'...")
    http_request("/auth/register", method="POST", data={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "full_name": "Phase 2.4.4 Auditor"
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
        "Build an AI-powered customer support assistant that answers customer questions using "
        "approved knowledge-base articles, maintains conversation history, identifies low-confidence "
        "answers below 80%, and escalates complex queries to human agents with a summarized context."
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
    for i in range(150):
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
    metadata = active_ver.get("generation_metadata", {})
    ver_id = active_ver.get("id")

    print(f"\n--- GENERATED PRD METADATA ---")
    print(f"PRD Version ID:     {ver_id}")
    print(f"Version Number:     {active_ver.get('version_number')}")
    print(f"Provider:           {metadata.get('provider')}")
    print(f"Model:              {metadata.get('model')}")
    print(f"Force Mock:         {metadata.get('force_mock')}")
    print(f"Total Sections:     {len(sections)} / 27")

    # 6. Validate PRD Document
    print(f"\n5. Running Strict Phase 2.4.4 Validation...")
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
    print(f"\n6. Exporting Phase 2.4.4 Deliverables...")
    # Markdown
    _, md_bytes = http_request(f"/export/{pid}/markdown?version_id={ver_id}", headers=headers)
    md_path = Path("PRD_Customer_Support_v2_4_4.md")
    with open(md_path, "wb") as f:
        f.write(md_bytes)
    print(f"   Saved: {md_path.name} ({len(md_bytes)} bytes)")

    # DOCX
    _, docx_bytes = http_request(f"/export/{pid}/docx?version_id={ver_id}", headers=headers)
    docx_path = Path("PRD_Customer_Support_v2_4_4.docx")
    with open(docx_path, "wb") as f:
        f.write(docx_bytes)
    print(f"   Saved: {docx_path.name} ({len(docx_bytes)} bytes)")

    # PDF
    _, pdf_bytes = http_request(f"/export/{pid}/pdf?version_id={ver_id}", headers=headers)
    pdf_path = Path("PRD_Customer_Support_v2_4_4.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"   Saved: {pdf_path.name} ({len(pdf_bytes)} bytes)")

    # 8. Compute Manifest
    print(f"\n7. Generating artifacts_manifest.json...")
    manifest = {
        "phase": "2.4.4",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "project_id": pid,
        "job_id": job_id,
        "prd_version_id": ver_id,
        "version_number": "v2.4.4",
        "provider": metadata.get("provider"),
        "model": metadata.get("model"),
        "force_mock": metadata.get("force_mock"),
        "validation": {
            "score": score,
            "verdict": verdict,
            "error_count": len(errors),
            "warning_count": len(warnings)
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

    manifest_path = Path("artifacts_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"   Saved: {manifest_path.name}")
    print(json.dumps(manifest, indent=2))

    print("\n================================================================")
    print("PHASE 2.4.4 GENERATION & AUDIT COMPLETED")
    print("================================================================")

if __name__ == "__main__":
    main()
