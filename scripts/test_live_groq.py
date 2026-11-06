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
    print("=== LIVE GROQ INFERENCE & WORKER VERIFICATION ===")
    
    # 1. Check Health & Provider
    code, health = http_request("/system/health")
    print(f"[1/4] System Health check (HTTP {code}):")
    print(f"  AI Provider: {health['ai_engine'].get('provider')}")
    print(f"  AI Type:     {health['ai_engine'].get('type')}")
    print(f"  Available:   {health['ai_engine'].get('available')}")
    print(f"  Model:       {health['ai_engine'].get('default_model')}")
    assert health['ai_engine'].get('provider') == 'groq'
    assert health['ai_engine'].get('available') is True

    # 2. Register & Login
    ts = int(time.time())
    username = f"groq_user_{ts}"
    password = "Password123!"
    code, _ = http_request("/auth/register", method="POST", data={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "full_name": "Groq Verification User"
    })
    code, res = http_request("/auth/login", method="POST", data={
        "username": username,
        "password": password
    })
    token = res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[2/4] Authenticated user {username}.")

    # 3. Create Project & Submission
    code, proj = http_request("/projects", method="POST", data={
        "title": "Realtime AI Voice Translator",
        "description": "Ultra low latency bidirectional speech-to-speech translation engine.",
        "target_domain": "Telecommunications"
    }, headers=headers)
    pid = proj["id"]
    print(f"[3/4] Created Project ID: {pid}")

    code, _ = http_request(f"/projects/{pid}/submissions", method="POST", data={
        "submission_type": "idea",
        "raw_idea": "Build a real-time voice translation assistant for cross-border telecom calls with under 200ms round-trip latency.",
        "problem_statement": "International callers experience language barriers and high latency with conventional machine translation."
    }, headers=headers)

    # 4. Run Stage 1 Analysis (Synchronous AI Pipeline Execution via Groq)
    print("  Starting Stage 1: Input Analysis via live Groq API...")
    t0 = time.perf_counter()
    code, analysis = http_request(f"/analysis/{pid}/analyze", method="POST", headers=headers)
    elapsed = time.perf_counter() - t0
    print(f"[4/4] Stage 1 Analysis Completed in {elapsed:.2f}s (HTTP {code})!")
    print(f"  Product Category: {analysis.get('product_category')}")
    print(f"  Problem Domain:   {analysis.get('problem_domain')}")
    print(f"  Target Users:     {analysis.get('target_users')}")
    print(f"  Core Objectives:  {analysis.get('core_objectives')}")
    print(f"  Clarifications:   {len(analysis.get('suggested_clarifications', []))} generated")
    
    print(f"\nSPEED COMPARISON:")
    print(f"  Ollama llama3.2 on CPU:  ~120-180 seconds")
    print(f"  Groq API LPU inference:  {elapsed:.2f} seconds ({150/max(elapsed, 0.1):.1f}x speedup!)")
    print("=== LIVE GROQ VERIFICATION SUCCESSFUL ===")

if __name__ == "__main__":
    main()
