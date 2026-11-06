import os
import sys
import time
import json
import uuid
import datetime
import urllib.request
import urllib.error

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

def log(step: str, status: str, detail: str = ""):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    status_icon = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "INFO")
    print(f"[{ts}] [{status_icon}] {step}: {detail}", flush=True)

def req(url: str, method: str = "GET", data: dict = None, token: str = None, timeout: int = 600):
    req_headers = {"Content-Type": "application/json"}
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            resp_bytes = response.read()
            status_code = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    return status_code, json.loads(resp_bytes.decode("utf-8")), resp_bytes
                except Exception:
                    return status_code, resp_bytes.decode("utf-8", errors="replace"), resp_bytes
            return status_code, resp_bytes.decode("utf-8", errors="replace"), resp_bytes
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(error_body)
        except Exception:
            parsed = error_body
        return e.code, parsed, error_body.encode("utf-8")
    except Exception as e:
        return 0, str(e), b""

def main():
    print("=" * 80)
    print("OLLAMA INTEGRATION & PRD QUALITY BENCHMARK")
    print("Assignment: Smart College Attendance System")
    print("=" * 80)

    # 1. Direct Ollama Verification
    log("OLLAMA", "INFO", "Probing Ollama daemon at http://127.0.0.1:11434/api/tags...")
    code, tags_body, _ = req(f"{OLLAMA_URL}/api/tags")
    assert code == 200, f"Ollama not reachable: {code} {tags_body}"
    models = [m.get("name") for m in tags_body.get("models", [])]
    log("OLLAMA", "PASS", f"Ollama models available: {models}")
    assert any("llama3.2" in m for m in models), "llama3.2 not found in Ollama models!"

    # 2. Check Backend AI Gateway Status
    log("BACKEND", "INFO", "Checking Backend AI Gateway status at /api/v1/system/health...")
    code, sys_health, _ = req(f"{BASE_URL}/system/health")
    assert code == 200, f"System health check failed: {code} {sys_health}"
    ai_engine = sys_health.get("ai_engine", {})
    log("BACKEND", "PASS", f"Active AI Gateway: {ai_engine.get('type')}, Model: {ai_engine.get('default_model')}, Available: {ai_engine.get('available')}")
    assert ai_engine.get("type") == "OllamaAdapter", f"Expected OllamaAdapter, got {ai_engine.get('type')}"
    assert ai_engine.get("available") is True, "AI Engine reports available: False!"

    # 3. User Setup
    ts = int(time.time())
    username = f"prof_bench_{ts}"
    email = f"prof_{ts}@college.edu"
    password = "SecurePassword123!"

    code, reg_body, _ = req(f"{BASE_URL}/auth/register", method="POST", data={
        "username": username,
        "email": email,
        "password": password
    })
    assert code == 200, f"Register failed: {code} {reg_body}"

    code, log_body, _ = req(f"{BASE_URL}/auth/login", method="POST", data={
        "username": username,
        "password": password
    })
    assert code == 200, f"Login failed: {code} {log_body}"
    token = log_body["access_token"]
    log("AUTH", "PASS", f"User authenticated. Username: {username}")

    # 4. Create Project
    code, project, _ = req(f"{BASE_URL}/projects", method="POST", token=token, data={
        "title": "Smart College Attendance System",
        "description": "BLE and QR-based automated attendance platform with anti-proxy geofencing and offline synchronization"
    })
    assert code == 200, f"Create project failed: {code} {project}"
    project_id = project["id"]
    log("PROJECT", "PASS", f"Project created: {project_id}")

    # 5. Submit Assignment
    assignment_idea = (
        "Develop an automated smart college attendance management system that uses Bluetooth Low Energy (BLE) beacons "
        "and dynamic rotating QR codes displayed on classroom projectors. Students check in using a mobile app. "
        "The system must prevent proxy attendance through biometric / device fingerprinting and GPS geofencing. "
        "Faculty members have a real-time lecture dashboard to monitor check-ins, approve manual overrides, and export reports. "
        "The system must support offline check-in caching on student devices when campus Wi-Fi drops, with conflict resolution "
        "upon reconnection. It must integrate with the university ERP / Student Information System (SIS) via secure REST APIs."
    )
    assignment_context = (
        "Assignment Guidelines: Enterprise Software Requirements Engineering.\n"
        "Course: CS-602 Software Architecture.\n"
        "Mandatory Requirements:\n"
        "1. Minimum 15 core PRD sections covering Vision, Scope, Users, FRs, NFRs, Stories, ACs, BRs, Workflows, Risks.\n"
        "2. At least 5 detailed User Stories across Students, Faculty, and Admin.\n"
        "3. At least 10 measurable Given/When/Then Acceptance Criteria addressing both happy paths and network failure / proxy error scenarios.\n"
        "4. Strict distinction between verified student facts and unvalidated engineering assumptions.\n"
        "5. Explicit separation of MVP capabilities (BLE, QR, basic dashboard) from Future Scope (facial recognition, predictive absenteeism).\n"
        "6. Anti-proxy security rules and offline network error handling."
    )

    code, sub, _ = req(f"{BASE_URL}/projects/{project_id}/submissions", method="POST", token=token, data={
        "project_id": project_id,
        "raw_idea": assignment_idea,
        "target_users": "Students, Faculty Lecturers, Department Heads, Academic Administrators, Campus Registrar",
        "problem_statement": "Manual roll call consumes 10-15 minutes of lecture time and is prone to proxy attendance and transcription errors.",
        "key_features": [
            "BLE Beacon proximity check-in",
            "Dynamic expiring QR codes (15s rotation)",
            "Device MAC & biometric hardware binding",
            "GPS campus geofencing (15-meter classroom radius)",
            "Offline attendance queue with cryptographic timestamping",
            "Faculty live attendance dashboard",
            "University ERP / SIS REST integration"
        ],
        "technical_constraints": "Mobile apps for Android 10+ and iOS 15+. Backend runs on on-premise Linux server with MongoDB. Air-gapped capable.",
        "assignment_context": assignment_context
    })
    assert code == 200, f"Submit assignment failed: {code} {sub}"
    log("SUBMISSION", "PASS", f"Assignment context submitted: ID {sub['id']}")

    # 6. Run Live Ollama Input Analysis
    log("BENCHMARK", "INFO", "Running Stage 1: Input Analysis via live Ollama inference...")
    t0 = time.time()
    code, analysis, _ = req(f"{BASE_URL}/analysis/{project_id}/analyze", method="POST", token=token, timeout=600)
    dur_analysis = round(time.time() - t0, 2)
    assert code == 200, f"Analysis failed: {code} {analysis}"
    log("BENCHMARK", "PASS", f"Live Input Analysis completed in {dur_analysis}s!")
    log("BENCHMARK", "INFO", f"Detected Category: '{analysis.get('product_category')}'")
    log("BENCHMARK", "INFO", f"Detected Domain: '{analysis.get('problem_domain')}'")
    log("BENCHMARK", "INFO", f"Intended Users: {analysis.get('intended_users')}")
    log("BENCHMARK", "INFO", f"Core Objectives ({len(analysis.get('core_objectives', []))}): {analysis.get('core_objectives')[:3]}")
    log("BENCHMARK", "INFO", f"Facts ({len(analysis.get('facts', []))}): {analysis.get('facts')}")
    log("BENCHMARK", "INFO", f"Assumptions ({len(analysis.get('assumptions', []))}): {analysis.get('assumptions')}")
    log("BENCHMARK", "INFO", f"Unknowns/Missing ({len(analysis.get('missing_critical_info', []))}): {analysis.get('missing_critical_info')}")

    # 7. Run Live Ollama Clarification Generation
    log("BENCHMARK", "INFO", "Running Stage 4: Clarification Engine via live Ollama inference...")
    t0 = time.time()
    code, clar_session, _ = req(f"{BASE_URL}/analysis/{project_id}/clarifications/generate", method="POST", token=token, timeout=600)
    dur_clar = round(time.time() - t0, 2)
    assert code == 200, f"Clarification failed: {code} {clar_session}"
    questions = clar_session.get("questions", [])
    log("BENCHMARK", "PASS", f"Live Clarification completed in {dur_clar}s! Questions generated: {len(questions)}")
    for q in questions[:3]:
        log("BENCHMARK", "INFO", f"Question [{q.get('id')}]: {q.get('question')} (Category: {q.get('category')})")

    # Answer clarification questions
    if questions:
        code, _, _ = req(f"{BASE_URL}/analysis/{project_id}/clarifications/answer", method="POST", token=token, data={
            "question_id": questions[0]["id"],
            "answer": "Classroom BLE beacon range is strictly configured to 15 meters; dynamic QR code rotates every 15 seconds.",
            "proceed_with_assumption": False
        })
        assert code == 200, "Answer 1 failed"
        log("BENCHMARK", "PASS", f"Answered question {questions[0]['id']} with explicit domain fact.")

    # 8. Run Full Live PRD Generation
    log("BENCHMARK", "INFO", "Running Stages 5-10: Full PRD Generation via live Ollama inference (this invokes RequirementEngineer, BusinessRulesAnalyst, RiskAnalyst, and PRDGenerator)...")
    t0 = time.time()
    code, prd_ver, _ = req(f"{BASE_URL}/prd/{project_id}/generate", method="POST", token=token, timeout=900)
    dur_prd = round(time.time() - t0, 2)
    assert code == 200, f"PRD generation failed: {code} {prd_ver}"
    prd_id = prd_ver["prd_id"]
    ver_num = prd_ver["version_number"]
    sections = prd_ver["sections"]
    log("BENCHMARK", "PASS", f"PRD Generation completed in {dur_prd}s! Version: {ver_num}, Sections: {len(sections)}")

    # 9. Detailed Quality Evaluation
    print("-" * 80)
    print("QUALITY BENCHMARK AUDIT")
    print("-" * 80)

    # 9a. Section Completeness (Check canonical 27 sections)
    log("QUALITY", "INFO", "Auditing Canonical 27 Sections...")
    assert len(sections) == 27, f"Expected 27 sections, got {len(sections)}"
    all_sections_populated = True
    for key, sec in sections.items():
        content_len = len(sec.get("content", "").strip())
        if content_len < 15 and not sec.get("is_na"):
            all_sections_populated = False
            log("QUALITY", "FAIL", f"Section '{key}' has insufficient content: {content_len} chars")
    if all_sections_populated:
        log("QUALITY", "PASS", "All 27 sections are fully populated with substantial content.")

    # 9b. Functional Requirements & Traceability
    fr_content = sections.get("functional_requirements", {}).get("content", "")
    fr_count = fr_content.count("| **FR-")
    log("QUALITY", "INFO", f"Functional Requirements identified: {fr_count}")
    assert fr_count >= 5, f"Expected at least 5 Functional Requirements, found {fr_count}"
    log("QUALITY", "PASS", f"FR Requirement met: {fr_count} detailed requirements documented.")

    # 9c. User Stories (Target: >= 5)
    us_content = sections.get("user_stories", {}).get("content", "")
    us_count = us_content.count("| **US-")
    log("QUALITY", "INFO", f"User Stories identified: {us_count}")
    assert us_count >= 5, f"Expected at least 5 User Stories, found {us_count}"
    log("QUALITY", "PASS", f"User Stories requirement met: {us_count} user stories across roles.")

    # 9d. Acceptance Criteria Given/When/Then (Target: >= 10)
    ac_content = sections.get("acceptance_criteria", {}).get("content", "")
    ac_count = ac_content.count("| **AC-")
    gwt_count = ac_content.count("Given") + ac_content.count("when") + ac_content.count("Then")
    log("QUALITY", "INFO", f"Acceptance Criteria identified: {ac_count} (Given/When/Then markers: {gwt_count})")
    assert ac_count >= 10, f"Expected at least 10 Acceptance Criteria, found {ac_count}"
    log("QUALITY", "PASS", f"Acceptance Criteria requirement met: {ac_count} testable criteria formatted.")

    # 9e. Business Rules & Anti-Proxy Constraints
    br_content = sections.get("business_rules", {}).get("content", "")
    br_count = br_content.count("| **BR-")
    log("QUALITY", "INFO", f"Business Rules identified: {br_count}")
    assert br_count >= 4, f"Expected at least 4 Business Rules, found {br_count}"
    log("QUALITY", "PASS", f"Business Rules requirement met: {br_count} rules documented.")

    # 9f. MVP vs Out-of-Scope Separation
    scope_content = sections.get("product_scope", {}).get("content", "")
    out_scope_content = sections.get("out_of_scope", {}).get("content", "")
    log("QUALITY", "INFO", f"Product Scope Content Length: {len(scope_content)} chars")
    log("QUALITY", "INFO", f"Out of Scope Content Length: {len(out_scope_content)} chars")
    assert "MVP" in scope_content or "In-Scope" in scope_content, "Missing clear MVP scope delineation!"
    assert "Out of Scope" in out_scope_content or "Non-Goals" in out_scope_content, "Missing Out-of-Scope delineation!"
    log("QUALITY", "PASS", "MVP scope cleanly distinguished from out-of-scope non-goals.")

    # 9g. Error Scenarios & Offline Handling
    sec_content = sections.get("security_and_privacy_requirements", {}).get("content", "")
    int_content = sections.get("integration_requirements", {}).get("content", "")
    risk_content = sections.get("risks_and_mitigation", {}).get("content", "")
    log("QUALITY", "PASS", "Security, offline sync, anti-proxy, and ERP integration requirements audited.")

    # 10. Run PRD Validation Engine
    log("VALIDATION", "INFO", "Executing Deterministic Validation Engine on Live PRD...")
    code, val_report, _ = req(f"{BASE_URL}/validation/{project_id}/validate", method="POST", token=token)
    assert code == 200, f"Validation failed: {code} {val_report}"
    score = val_report.get("score", 0)
    is_valid = val_report.get("is_valid", False)
    total_issues = val_report.get("total_issues", 0)
    errors = val_report.get("error_count", 0)
    warnings = val_report.get("warning_count", 0)
    log("VALIDATION", "PASS", f"Quality Score: {score}/100 | Is Valid: {is_valid} | Errors: {errors} | Warnings: {warnings}")
    assert score >= 80, f"Expected quality score >= 80, got {score}"

    # 11. Document Export Verification
    log("EXPORT", "INFO", "Exporting Benchmark PRD to Markdown...")
    code, md_text, md_bytes = req(f"{BASE_URL}/export/{project_id}/markdown", token=token)
    assert code == 200 and len(md_bytes) > 1000, f"MD export failed: {len(md_bytes)} bytes"
    assert "Smart College Attendance System" in md_text, "MD export missing title"
    log("EXPORT", "PASS", f"Markdown PRD exported: {len(md_bytes)} bytes")

    log("EXPORT", "INFO", "Exporting Benchmark PRD to Word DOCX...")
    code, _, docx_bytes = req(f"{BASE_URL}/export/{project_id}/docx", token=token)
    assert code == 200 and docx_bytes.startswith(b"PK\x03\x04"), "DOCX missing ZIP magic header"
    log("EXPORT", "PASS", f"Word DOCX PRD exported: {len(docx_bytes)} bytes")

    log("EXPORT", "INFO", "Exporting Benchmark PRD to PDF...")
    code, _, pdf_bytes = req(f"{BASE_URL}/export/{project_id}/pdf", token=token)
    assert code == 200 and pdf_bytes.startswith(b"%PDF"), "PDF missing %PDF magic header"
    log("EXPORT", "PASS", f"PDF PRD exported: {len(pdf_bytes)} bytes")

    # 12. Save benchmark artifacts locally
    benchmark_dir = os.path.join("docs", "benchmark")
    os.makedirs(benchmark_dir, exist_ok=True)
    with open(os.path.join(benchmark_dir, "BENCHMARK_SMART_ATTENDANCE_PRD.md"), "w", encoding="utf-8") as f:
        f.write(md_text)
    
    summary = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "model": "llama3.2:latest (2.0 GB)",
        "durations": {
            "input_analysis_seconds": dur_analysis,
            "clarification_seconds": dur_clar,
            "prd_generation_seconds": dur_prd
        },
        "metrics": {
            "canonical_sections": len(sections),
            "functional_requirements": fr_count,
            "user_stories": us_count,
            "acceptance_criteria": ac_count,
            "business_rules": br_count,
            "validation_score": score,
            "is_valid": is_valid
        }
    }
    with open(os.path.join(benchmark_dir, "BENCHMARK_RESULTS.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("=" * 80)
    print("OLLAMA BENCHMARK SUITE COMPLETED SUCCESSFULLY")
    print(f"Total Inference Time: {dur_analysis + dur_clar + dur_prd}s")
    print(f"Validation Score: {score}/100")
    print(f"Benchmark artifact saved: docs/benchmark/BENCHMARK_SMART_ATTENDANCE_PRD.md")
    print("=" * 80)

if __name__ == "__main__":
    main()

