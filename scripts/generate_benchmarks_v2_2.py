import os
import sys
import time
import json
import hashlib
import urllib.request
import urllib.error

sys.stdout.reconfigure(line_buffering=True)

BASE_URL = "http://localhost:8000/api/v1"

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
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                return resp.status, json.loads(raw.decode("utf-8"))
            return resp.status, raw
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        print(f"HTTPError on {method} {url}: {e.code} - {error_body}")
        try:
            return e.code, json.loads(error_body)
        except:
            return e.code, error_body

def main():
    print("=== PROFESSIONAL PRD ENGINEERING V2.2: LIVE BENCHMARK GENERATION ===")
    ts = int(time.time())
    username = f"bench_v2_2_{ts}"
    password = "Password123!"

    # 1. Register & Login
    print(f"\n[1/4] Registering test benchmark user: {username}")
    code, res = http_request("/auth/register", method="POST", data={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "full_name": "Benchmark V2.2 Engineer"
    })
    print(f"  Register status: {code}")

    code, res = http_request("/auth/login", method="POST", data={
        "username": username,
        "password": password
    })
    token = res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  Login status: {code}, Token acquired.")

    os.makedirs("docs/benchmark", exist_ok=True)

    # -------------------------------------------------------------
    # BENCHMARK 1: AI Customer Support Assistant
    # -------------------------------------------------------------
    print("\n[2/4] Executing Benchmark 1: AI Customer Support Assistant")
    code, proj1 = http_request("/projects", method="POST", data={
        "title": "AI Customer Support Assistant",
        "description": "Grounded Q&A assistant with approved knowledge base, history, and human escalation.",
        "target_domain": "Customer Support Automation"
    }, headers=headers)
    assert code == 200, f"Failed to create project: {code} {proj1}"
    pid1 = proj1["id"]
    print(f"  Created Project ID: {pid1}")

    cs_concept = (
        "Build an AI-powered customer support assistant that answers customer questions using "
        "approved knowledge-base articles, maintains conversation history, identifies low-confidence "
        "answers below 80%, and escalates complex queries to human agents with a summarized context."
    )
    code, sub1 = http_request(f"/projects/{pid1}/submissions", method="POST", data={
        "submission_type": "idea",
        "raw_idea": cs_concept,
        "problem_statement": "Customers experience long hold times and receive ungrounded or inconsistent answers from legacy chatbots."
    }, headers=headers)
    print(f"  Submitted Idea: HTTP {code}")

    print("  Running Stage 1: Input Analysis...")
    code, an1 = http_request(f"/analysis/{pid1}/analyze", method="POST", headers=headers)
    print(f"  Stage 1 Analysis complete: HTTP {code}")
    print(f"    Category: {an1.get('product_category')}")
    print(f"    Domain: {an1.get('problem_domain')}")
    print(f"    Objectives: {len(an1.get('core_objectives', []))}")

    print("  Triggering Asynchronous PRD Generation (force_mock=False, real Ollama llama3.2)...")
    code, job1 = http_request(f"/projects/{pid1}/prd/generate", method="POST", headers=headers)
    assert code == 202, f"Expected 202, got {code}"
    jid1 = job1["job_id"]
    print(f"  Dispatched Job ID: {jid1} (HTTP 202 Accepted)")

    # Poll until completed (Concurrency = 1)
    start_time = time.time()
    last_stage = ""
    while True:
        time.sleep(5)
        code, jstatus = http_request(f"/jobs/{jid1}", method="GET", headers=headers)
        status = jstatus.get("status")
        stage = jstatus.get("current_stage")
        if stage != last_stage:
            print(f"    -> Worker Stage: {stage} (Elapsed: {int(time.time() - start_time)}s)")
            last_stage = stage
        if status == "completed":
            print(f"  Job {jid1} completed successfully in {int(time.time() - start_time)}s!")
            break
        elif status in ["failed", "cancelled"]:
            print(f"  Job {jid1} {status}: {jstatus.get('error_message')}")
            sys.exit(1)
        if time.time() - start_time > 1800:
            print("  Timeout waiting for job completion.")
            sys.exit(1)

    # Validate Customer Support PRD
    print("  Running Semantic & Engineering Readiness Validation...")
    code, val1 = http_request(f"/validation/{pid1}/validate", method="POST", headers=headers)
    print(f"  Validation Score: {val1.get('score')}/100, Valid: {val1.get('is_valid')}, Errors: {val1.get('error_count')}, Warnings: {val1.get('warning_count')}")
    if val1.get("issues"):
        for iss in val1["issues"]:
            print(f"    - [{iss.get('severity').upper()}] {iss.get('rule_id')}: {iss.get('title')}")

    # Export Customer Support Markdown
    print("  Exporting Customer Support PRD Markdown (v2.2)...")
    code, md_bytes = http_request(f"/export/{pid1}/markdown", method="GET", headers=headers)
    md_text = md_bytes.decode("utf-8") if isinstance(md_bytes, bytes) else md_bytes
    with open("docs/benchmark/customer_support_prd_v2_2.md", "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"  Saved to docs/benchmark/customer_support_prd_v2_2.md ({len(md_text)} chars)")

    # Export Customer Support PDF
    print("  Exporting Customer Support PRD PDF (v2.2)...")
    code, pdf_bytes = http_request(f"/export/{pid1}/pdf", method="GET", headers=headers)
    if code == 200 and isinstance(pdf_bytes, bytes):
        with open("docs/benchmark/customer_support_prd_v2_2.pdf", "wb") as f:
            f.write(pdf_bytes)
        print(f"  Saved to docs/benchmark/customer_support_prd_v2_2.pdf ({len(pdf_bytes)} bytes)")

    # -------------------------------------------------------------
    # BENCHMARK 2: College Attendance Management System
    # -------------------------------------------------------------
    print("\n[3/4] Executing Benchmark 2: College Attendance Management System")
    code, proj2 = http_request("/projects", method="POST", data={
        "title": "College Attendance Management System",
        "description": "Comprehensive student and faculty attendance management with low-attendance warnings.",
        "target_domain": "Higher Education Administration"
    }, headers=headers)
    assert code == 200, f"Failed to create project: {code} {proj2}"
    pid2 = proj2["id"]
    print(f"  Created Project ID: {pid2}")

    att_concept = (
        "Build a College Attendance Management System where faculty instructors record daily attendance, "
        "students can view their attendance percentage, automated warning notifications are sent if "
        "attendance falls below 75%, and department heads configure attendance policies and condonation rules."
    )
    code, sub2 = http_request(f"/projects/{pid2}/submissions", method="POST", data={
        "submission_type": "idea",
        "raw_idea": att_concept,
        "problem_statement": "Manual paper roll calls lead to delayed percentage calculation, missed 75% threshold alerts, and disputes over exam eligibility."
    }, headers=headers)
    print(f"  Submitted Idea: HTTP {code}")

    print("  Running Stage 1: Input Analysis...")
    code, an2 = http_request(f"/analysis/{pid2}/analyze", method="POST", headers=headers)
    print(f"  Stage 1 Analysis complete: HTTP {code}")
    print(f"    Category: {an2.get('product_category')}")
    print(f"    Domain: {an2.get('problem_domain')}")

    print("  Triggering Asynchronous PRD Generation (force_mock=False, real Ollama llama3.2)...")
    code, job2 = http_request(f"/projects/{pid2}/prd/generate", method="POST", headers=headers)
    assert code == 202, f"Expected 202, got {code}"
    jid2 = job2["job_id"]
    print(f"  Dispatched Job ID: {jid2} (HTTP 202 Accepted)")

    # Poll until completed (Concurrency = 1)
    start_time = time.time()
    last_stage = ""
    while True:
        time.sleep(5)
        code, jstatus = http_request(f"/jobs/{jid2}", method="GET", headers=headers)
        status = jstatus.get("status")
        stage = jstatus.get("current_stage")
        if stage != last_stage:
            print(f"    -> Worker Stage: {stage} (Elapsed: {int(time.time() - start_time)}s)")
            last_stage = stage
        if status == "completed":
            print(f"  Job {jid2} completed successfully in {int(time.time() - start_time)}s!")
            break
        elif status in ["failed", "cancelled"]:
            print(f"  Job {jid2} {status}: {jstatus.get('error_message')}")
            sys.exit(1)
        if time.time() - start_time > 1800:
            print("  Timeout waiting for job completion.")
            sys.exit(1)

    # Validate Attendance PRD
    print("  Running Semantic & Engineering Readiness Validation...")
    code, val2 = http_request(f"/validation/{pid2}/validate", method="POST", headers=headers)
    print(f"  Validation Score: {val2.get('score')}/100, Valid: {val2.get('is_valid')}, Errors: {val2.get('error_count')}, Warnings: {val2.get('warning_count')}")
    if val2.get("issues"):
        for iss in val2["issues"]:
            print(f"    - [{iss.get('severity').upper()}] {iss.get('rule_id')}: {iss.get('title')}")

    # Export Attendance Markdown
    print("  Exporting Attendance PRD Markdown (v2.2)...")
    code, md_bytes2 = http_request(f"/export/{pid2}/markdown", method="GET", headers=headers)
    md_text2 = md_bytes2.decode("utf-8") if isinstance(md_bytes2, bytes) else md_bytes2
    with open("docs/benchmark/attendance_prd_v2_2.md", "w", encoding="utf-8") as f:
        f.write(md_text2)
    print(f"  Saved to docs/benchmark/attendance_prd_v2_2.md ({len(md_text2)} chars)")

    # Export Attendance PDF
    print("  Exporting Attendance PRD PDF (v2.2)...")
    code, pdf_bytes2 = http_request(f"/export/{pid2}/pdf", method="GET", headers=headers)
    if code == 200 and isinstance(pdf_bytes2, bytes):
        with open("docs/benchmark/attendance_prd_v2_2.pdf", "wb") as f:
            f.write(pdf_bytes2)
        print(f"  Saved to docs/benchmark/attendance_prd_v2_2.pdf ({len(pdf_bytes2)} bytes)")

    # -------------------------------------------------------------
    # QUALITY & ZERO-LEAKAGE AUDIT
    # -------------------------------------------------------------
    print("\n[4/4] Cross-Domain Quality, Provenance & Engineering Readiness Audit")
    
    # Check Customer Support PRD
    cs_leakage = []
    if "PRD Framework" in md_text: cs_leakage.append("PRD Framework self-reference")
    if "Attendance Window" in md_text: cs_leakage.append("Attendance Window rule")
    if "student attendance" in md_text.lower(): cs_leakage.append("Student attendance mention")
    if "75% attendance" in md_text.lower(): cs_leakage.append("75% attendance threshold")
    print(f"  Customer Support Contamination Defects: {cs_leakage or 'NONE (100% CLEAN)'}")

    # Check Attendance PRD
    att_leakage = []
    if "PRD Framework" in md_text2: att_leakage.append("PRD Framework self-reference")
    if "customer support" in md_text2.lower(): att_leakage.append("Customer support mention")
    if "knowledge-base" in md_text2.lower(): att_leakage.append("Knowledge base mention")
    if "80% confidence" in md_text2.lower(): att_leakage.append("80% confidence escalation")
    print(f"  Attendance PRD Contamination Defects: {att_leakage or 'NONE (100% CLEAN)'}")

    print("\n=== ALL V2.2 BENCHMARKS COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()

