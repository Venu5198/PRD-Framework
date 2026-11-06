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

def run_stage1_benchmark(label=""):
    print(f"\n--- RUNNING STAGE 1 BENCHMARK: {label} ---")
    code, health = http_request("/system/health")
    ai_engine = health.get("ai_engine", {})
    provider = ai_engine.get("provider")
    model = ai_engine.get("default_model")
    available = ai_engine.get("available")
    ai_type = ai_engine.get("type")
    
    print(f"Health Check (HTTP {code}):")
    print(f"  Configured Provider: {provider}")
    print(f"  Adapter Type:        {ai_type}")
    print(f"  Configured Model:    {model}")
    print(f"  Available:           {available}")
    
    ts = int(time.time())
    username = f"user_{provider}_{ts}"
    password = "Password123!"
    
    http_request("/auth/register", method="POST", data={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "full_name": f"{provider.capitalize()} Test User"
    })
    _, auth_res = http_request("/auth/login", method="POST", data={
        "username": username,
        "password": password
    })
    headers = {"Authorization": f"Bearer {auth_res['access_token']}"}

    _, proj = http_request("/projects", method="POST", data={
        "title": f"Benchmarking {provider.upper()} Engine",
        "description": "Cross-provider validation for Stage 1 Input Analysis",
        "target_domain": "Customer Support"
    }, headers=headers)
    pid = proj["id"]

    http_request(f"/projects/{pid}/submissions", method="POST", data={
        "submission_type": "idea",
        "raw_idea": "Intelligent automated customer ticket resolution platform with CRM integration and sentiment detection.",
        "problem_statement": "Support queues are overwhelmed with tier-1 repetitive questions."
    }, headers=headers)

    print(f"Starting Stage 1 Analysis with provider={provider}, model={model}...")
    t0 = time.perf_counter()
    code, analysis = http_request(f"/analysis/{pid}/analyze", method="POST", headers=headers)
    elapsed = time.perf_counter() - t0

    print(f"Analysis completed in {elapsed:.2f}s (HTTP {code})")
    print(f"  Category:        {analysis.get('product_category')}")
    print(f"  Domain:          {analysis.get('problem_domain')}")
    print(f"  Objectives:      {len(analysis.get('core_objectives', []))} items")
    print(f"  Capabilities:    {len(analysis.get('key_capabilities', []))} items")
    print(f"  Clarifications:  {len(analysis.get('suggested_clarifications', []))} items")
    
    # Assertions to verify real non-mock output
    assert analysis.get("product_category") is not None
    assert len(analysis.get("core_objectives", [])) > 0
    assert analysis.get("product_category") != "Mock Product Category"
    print(f"Verified: {provider} successfully executed Stage 1 without mock fallback!")
    return {
        "provider": provider,
        "model": model,
        "ai_type": ai_type,
        "elapsed_seconds": round(elapsed, 2),
        "status_code": code
    }

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    res = run_stage1_benchmark(label=mode)
    print("\nRESULT_JSON:" + json.dumps(res))

