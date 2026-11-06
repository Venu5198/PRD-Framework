import time
import json
import sys
import urllib.request
import urllib.error

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
    with urllib.request.urlopen(req, timeout=120) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()
        if "application/json" in content_type:
            return resp.status, json.loads(raw.decode("utf-8"))
        return resp.status, raw

def main():
    print("=== LIVE GROQ PRD GENERATION & QUALITY AUDIT ===")
    
    # Check if existing project passed
    existing_pid = sys.argv[1] if len(sys.argv) > 1 else None
    existing_user = sys.argv[2] if len(sys.argv) > 2 else None

    if existing_pid and existing_user:
        username = existing_user
        password = "Password123!"
        _, auth_res = http_request("/auth/login", method="POST", data={
            "username": username,
            "password": password
        })
        headers = {"Authorization": f"Bearer {auth_res['access_token']}"}
        pid = existing_pid
        print(f"Auditing Existing Project: {pid} (User: {username})")
    else:
        ts = int(time.time())
        username = f"audit_user_{ts}"
        password = "Password123!"

        # 1. Register & Login
        http_request("/auth/register", method="POST", data={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "full_name": "Quality Auditor"
        })
        _, auth_res = http_request("/auth/login", method="POST", data={
            "username": username,
            "password": password
        })
        headers = {"Authorization": f"Bearer {auth_res['access_token']}"}

        # 2. Create Customer Support Project
        _, proj = http_request("/projects", method="POST", data={
            "title": "AI Customer Support Assistant",
            "description": "Enterprise customer service assistant with knowledge retrieval and human escalation",
            "target_domain": "Customer Support"
        }, headers=headers)
        pid = proj["id"]
        print(f"Created Project: {pid}")

        raw_concept = (
            "Build an AI-powered customer support assistant that answers customer questions using "
            "approved knowledge-base articles, maintains conversation history, identifies low-confidence "
            "answers below 80%, and escalates complex queries to human agents with a summarized context."
        )
        http_request(f"/projects/{pid}/submissions", method="POST", data={
            "submission_type": "idea",
            "raw_idea": raw_concept,
            "problem_statement": "Support representatives are overloaded with repetitive questions, leading to high wait times and inconsistent answer quality."
        }, headers=headers)

        # 3. Trigger Async Generation via Worker with Groq
        print("Triggering PRD Generation via Groq API (force_mock=False)...")
        t0 = time.perf_counter()
        code, gen_resp = http_request(f"/projects/{pid}/prd/generate", method="POST", data={
            "force_mock": False
        }, headers=headers)
        job_id = gen_resp["job_id"]
        print(f"Dispatched Job: {job_id}")

        # 4. Poll until completed
        for i in range(120):
            time.sleep(2)
            _, job = http_request(f"/jobs/{job_id}", headers=headers)
            status = job.get("status")
            stage = job.get("current_stage")
            completed = job.get("completed_stages", [])
            elapsed_sec = job.get("elapsed_seconds")
            print(f"[{i*2}s] Status: {status} | Current: {stage} | Completed: {len(completed)} stages | Elapsed: {elapsed_sec}s")
            if status in ("completed", "failed"):
                break

        elapsed_total = time.perf_counter() - t0
        print(f"\nJob Execution Finished in {elapsed_total:.2f}s with status={status}")
        assert status == "completed", f"Job failed: {job.get('error_message')}"
        ver_id = job.get("result_reference")

    # 5. Retrieve PRD Document & Active Version
    _, prd_data = http_request(f"/prd/{pid}", headers=headers)
    active_ver = prd_data.get("active_version", {})
    sections = active_ver.get("sections", {})
    metadata = active_ver.get("generation_metadata", {})

    print(f"\n--- GENERATED PRD INSPECTION ---")
    print(f"PRD Version ID:     {active_ver.get('id')}")
    print(f"Version Number:     {active_ver.get('version_number')}")
    print(f"Provider Used:      {metadata.get('provider')}")
    print(f"Model Used:         {metadata.get('model')}")
    print(f"Force Mock Flag:    {metadata.get('force_mock')}")
    print(f"Total Sections:     {len(sections)} / 27")

    # 6. Semantic Quality Audit Checks
    print("\n--- DETAILED QUALITY AUDIT ---")
    findings = []
    
    # Check A: Domain Relevance in every populated section (avoid cross-domain leakage from other benchmarks)
    off_domain_terms = ["attendance", "leave request", "classroom", "student roll", "warehouse agv", "fleet management", "robotics"]
    for s_key, sec in sections.items():
        text = sec.get("content", "").lower()
        matched = [w for w in off_domain_terms if w in text]
        if matched:
            findings.append(f"Cross-domain contamination in section '{s_key}': found {matched}")

    # Check B: Functional Requirements & Acceptance Criteria
    fr_section = sections.get("functional_requirements", {}).get("content", "")
    assert "FR-" in fr_section, "Functional requirements missing structured IDs (FR-001)"
    ac_section = sections.get("acceptance_criteria", {}).get("content", "")
    assert "Given" in ac_section and "When" in ac_section and "Then" in ac_section, "Acceptance criteria missing Given-When-Then format"

    # Check C: Business Rules & 80% Threshold Preservation
    br_section = sections.get("business_rules", {}).get("content", "")
    has_80 = "80%" in br_section or "80 percent" in br_section or "0.8" in br_section
    print(f"Preserved 80% Confidence Escalation Rule: {has_80}")
    if not has_80:
        findings.append("Business rules did not preserve explicit 80% confidence escalation threshold.")

    # Check D: Validation Report
    code, val_report = http_request(f"/validation/{pid}/validate?version_id={active_ver.get('id')}", method="POST", headers=headers)
    print(f"\nQuality Audit Score: {val_report.get('score')} / 100")
    print(f"Validation Verdict:  {val_report.get('verdict')}")
    print(f"Total Warnings:      {val_report.get('warning_count', 0)}")
    print(f"Total Errors:        {val_report.get('error_count', 0)}")

    for issue in val_report.get("issues", []):
        if issue.get("severity") == "error":
            findings.append(f"Validation Error [{issue.get('rule_id')}]: {issue.get('title')} - {issue.get('description')}")
        elif issue.get("severity") == "warning":
            print(f"  * Warning [{issue.get('rule_id')}]: {issue.get('title')}")

    # Check E: Unsupported Compliance/Infrastructure commitments
    unsupported_commitments = ["mandatory gdpr compliance certification", "cloud-only managed hosting required"]
    for comm in unsupported_commitments:
        if comm in fr_section.lower():
            findings.append(f"Unsupported absolute commitment found: {comm}")

    print(f"\nTotal Audit Defect Findings: {len(findings)}")
    for f in findings:
        print(f"  - [DEFECT] {f}")

    if not findings and val_report.get("verdict") == "APPROVED":
        print(f"\n=== PRD QUALITY VERIFICATION: PASS (Score: {val_report.get('score')}) ===")
    else:
        print(f"\n=== PRD QUALITY VERIFICATION: CONDITIONAL / FINDINGS IDENTIFIED (Verdict: {val_report.get('verdict')}, Score: {val_report.get('score')}) ===")

    # Write export of Markdown and PDF for review
    code, md_raw = http_request(f"/export/{pid}/markdown?version_id={active_ver.get('id')}", headers=headers)
    md_content = md_raw.decode("utf-8") if isinstance(md_raw, bytes) else str(md_raw)
    export_paths = [
        "docs/benchmark/PRD_Customer_Support_Final.md",
        "PRD_Customer_Support_Final.md"
    ]
    for path in export_paths:
        with open(path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"Exported Markdown to {path}")

    try:
        code, pdf_raw = http_request(f"/export/{pid}/pdf?version_id={active_ver.get('id')}", headers=headers)
        if isinstance(pdf_raw, bytes) and len(pdf_raw) > 500:
            pdf_paths = [
                "docs/benchmark/PRD_Customer_Support_Final.pdf",
                "PRD_Customer_Support_Final.pdf"
            ]
            for path in pdf_paths:
                with open(path, "wb") as f:
                    f.write(pdf_raw)
                print(f"Exported PDF to {path} ({len(pdf_raw)} bytes)")
    except Exception as e:
        print(f"PDF export warning: {e}")

if __name__ == "__main__":
    main()
