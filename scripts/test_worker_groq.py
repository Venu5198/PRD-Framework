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
    with urllib.request.urlopen(req, timeout=60) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()
        if "application/json" in content_type:
            return resp.status, json.loads(raw.decode("utf-8"))
        return resp.status, raw

def main():
    print("=== LIVE GROQ ASYNC WORKER PRD GENERATION TEST ===")
    ts = int(time.time())
    username = f"worker_test_{ts}"
    password = "Password123!"
    
    # 1. Register & Login
    print(f"Registering {username}...")
    code, reg = http_request("/auth/register", method="POST", data={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "full_name": "Worker Groq Tester"
    })
    print(f"Registered (HTTP {code}). Logging in...")
    code, res = http_request("/auth/login", method="POST", data={
        "username": username,
        "password": password
    })
    token = res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Logged in successfully.")

    # 2. Create Project & Submission
    _, proj = http_request("/projects", method="POST", data={
        "title": "Smart Campus Shuttle Tracker",
        "description": "Real-time shuttle location tracking and arrival prediction for university students.",
        "target_domain": "Transit"
    }, headers=headers)
    pid = proj["id"]
    print(f"Created Project: {pid}")

    http_request(f"/projects/{pid}/submissions", method="POST", data={
        "submission_type": "idea",
        "raw_idea": "A mobile and web system providing GPS location of campus shuttles with arrival ETAs.",
        "problem_statement": "Students miss shuttles due to lack of schedule predictability."
    }, headers=headers)

    # 3. Trigger PRD Generation (dispatched to worker)
    print("Triggering PRD Generation via worker...")
    t0 = time.perf_counter()
    code, gen_resp = http_request(f"/projects/{pid}/prd/generate", method="POST", data={
        "force_mock": False
    }, headers=headers)
    job_id = gen_resp.get("job_id")
    print(f"Generation initiated: Job ID = {job_id} (HTTP {code})")

    # 4. Poll Job Status
    for i in range(120):
        time.sleep(2)
        code, job_status = http_request(f"/jobs/{job_id}", headers=headers)
        status = job_status.get("status")
        stage = job_status.get("current_stage", "")
        completed = job_status.get("completed_stages", [])
        elapsed_sec = job_status.get("elapsed_seconds")
        print(f"[{i*2}s] Status: {status} | Current Stage: {stage} | Completed: {len(completed)} stages | Elapsed: {elapsed_sec}s")
        if status in ("completed", "failed"):
            break
            
    elapsed = time.perf_counter() - t0
    print(f"\nFinal Job State after {elapsed:.2f}s: {status}")
    if status == "completed":
        print(f"PRD Version Result: {job_status.get('result_reference')}")
        print("=== LIVE ASYNC WORKER PRD GENERATION SUCCESSFUL ===")
    else:
        print(f"Job finished with state: {status}, error: {job_status.get('error_message')}")

if __name__ == "__main__":
    main()
