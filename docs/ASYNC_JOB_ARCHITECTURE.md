# Asynchronous AI Job Processing Architecture

## 1. Architectural Overview

The Local-First Automated PRD Engineering Framework executes deep, multi-stage language model inference to synthesize 27-section product requirement documents. On local consumer hardware without GPU acceleration, 4-bit quantized models (such as `llama3.2`) generate at approximately 0.65 to 7.0 tokens per second. Complete end-to-end synthesis across all six sequential pipeline stages requires between 11 and 16 minutes of sustained compute.

Synchronous HTTP request architectures inevitably fail under this latency profile:
1. Reverse proxies (Nginx, browser gateways) terminate idle connections with `504 Gateway Time-out` (commonly at 60s or 120s).
2. Browsers and client runtimes drop HTTP sockets.
3. Premature request termination previously caused silent fallbacks to `OfflineMockAdapter`, corrupting runtime integrity and masking real inference errors.

The asynchronous job processing architecture decouples client HTTP interaction from heavy background inference using an atomic, persistent MongoDB queue. No external message broker (such as Redis, Celery, or RabbitMQ) is required, adhering strictly to the local-first zero-bloat deployment constraint.

```
+-----------------------------------------------------------------------------------------+
|                                    CLIENT BROWSER                                       |
|                                                                                         |
|  [Tab 4: Generate PRD] ----> POST /api/v1/projects/{id}/prd/generate                    |
|                                  | (Returns HTTP 202 Accepted + job_id immediately)     |
|                                  v                                                      |
|  [Session Recovery] <------- Polling Loop (GET /api/v1/jobs/{id} every 2.5s)            |
|  [Elapsed Timer]             (Resumes tracking seamlessly across tab reload/close)       |
+------------------------------------------+----------------------------------------------+
                                           |
                                           v
+------------------------------------------+----------------------------------------------+
|                                   FASTAPI GATEWAY                                       |
|                                                                                         |
|  - Idempotency Gate: Re-routes duplicate clicks to existing running/queued job          |
|  - Job Creator: Inserts job document into MongoDB `generation_jobs` collection          |
|  - Status & Result Endpoints: GET /api/v1/jobs/{id}, GET /api/v1/jobs/{id}/result       |
+------------------------------------------+----------------------------------------------+
                                           |
                                           v
+------------------------------------------+----------------------------------------------+
|                                  MONGODB DATABASE                                       |
|                                                                                         |
|  Collection: `generation_jobs`                                                          |
|  Indexes:                                                                               |
|    - `job_id` (Unique)                                                                  |
|    - `project_id` + `status` (Compound, active job query optimization)                  |
|    - `status` + `created_at` (FIFO queue priority)                                      |
|    - `status` + `heartbeat_at` (Abandoned worker crash detection)                       |
+------------------------------------------+----------------------------------------------+
                      ^                                            ^
          Atomic Claim|Heartbeat Update                Stage Update|Result Persistence
                      v                                            v
+---------------------+--------------------------------------------+----------------------+
|                                 BACKGROUND WORKER                                       |
|                              (`python -m app.worker`)                                   |
|                                                                                         |
|  1. Queue Poller: Atomically claims queued jobs via `find_one_and_update`               |
|  2. Heartbeat Loop: Emits background heartbeat every 8 seconds                          |
|  3. Stale Recovery: Auto-reclaims abandoned jobs if heartbeat is older than 60s         |
|  4. Strict AI Pipeline: Executes 6 sequential PRD stages without silent fallback         |
|  5. Cooperative Cancellation: Checks `check_cancelled` hook before each stage          |
|  6. Graceful Shutdown: Listens for SIGINT/SIGTERM, finishes stage before exit           |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Job Persistence Schema

Jobs are persisted in the `generation_jobs` MongoDB collection. The document structure is strictly typed via Pydantic (`backend/app/models/job.py`):

```json
{
  "_id": "ObjectId(...)",
  "job_id": "job_9b3e1c0d4a",
  "user_id": "user_local_eng",
  "project_id": "proj_6aeb104e",
  "submission_id": "sub_92a104",
  "job_type": "prd_generation",
  "status": "running",
  "current_stage": "requirements_engineering",
  "completed_stages": [
    "input_analysis"
  ],
  "total_stages": 6,
  "progress_percentage": 16,
  "created_at": "2026-11-04T16:50:00Z",
  "updated_at": "2026-11-04T16:52:15Z",
  "started_at": "2026-11-04T16:50:05Z",
  "completed_at": null,
  "heartbeat_at": "2026-11-04T16:52:15Z",
  "worker_id": "worker-prd-worker-1-c519bb",
  "retry_count": 0,
  "max_retries": 3,
  "result_version_id": null,
  "error_code": null,
  "error_message": null,
  "error_details": null,
  "metadata": {
    "model_name": "llama3.2",
    "provider": "ollama",
    "force_mock": false,
    "elapsed_seconds": 130
  }
}
```

### 2.1 State Machine

```
               +-----------+
               |  QUEUED   |
               +-----+-----+
                     |
         Worker Claim (`claim_next_job`)
                     |
                     v
+------------+ +-----+-----+ +-------------+
| CANCELLED  |<+  RUNNING  |+>   FAILED    |
+------------+ +-----+-----+ +-------------+
                     |
            All 6 Stages Succeeded
                     |
                     v
               +-----+-----+
               | COMPLETED |
               +-----------+
```

* **`queued`**: Job accepted and waiting in FIFO order.
* **`running`**: Claimed by a worker; emits periodic heartbeats.
* **`completed`**: All 27 canonical PRD sections synthesized, validated, and persisted.
* **`failed`**: Inference error occurred or retry limit exceeded. Explicit error diagnostics attached.
* **`cancelled`**: Interrupted cooperatively by user request.

---

## 3. Pipeline Stage Breakdown

PRD generation consists of six sequential, deterministic stages:

| Stage # | Stage Key | Description | Output Artifacts |
|---|---|---|---|
| **1** | `input_analysis` | Extracts problem statements, goals, and constraints from raw inputs | `AnalysisResult` entities and constraints |
| **2** | `requirements_engineering` | Formulates functional (FR-1..n) and non-functional requirements (NFR-1..n) | Structured requirements matrix |
| **3** | `stakeholder_analysis` | Derives user personas, empathy maps, and primary user journeys | Persona specifications |
| **4** | `business_rules` | Identifies invariant business logic, boundary conditions, edge cases | Business rules catalogue |
| **5** | `risk_analysis` | Threat modeling, operational risks, failure modes, mitigations | Risk assessment table |
| **6** | `prd_assembly` | Synthesizes all 27 canonical sections into Markdown document | Full PRD Version (`v1.0`) |

---

## 4. API Endpoints

### 4.1 Initiate Asynchronous PRD Generation
* **Route**: `POST /api/v1/projects/{project_id}/prd/generate`
* **Response Status**: `202 Accepted`
* **Idempotency Guarantee**: If a job for `{project_id}` is already `queued` or `running`, returns the existing `job_id` with `is_existing: true`, preventing redundant inference load.
* **Response Body**:
  ```json
  {
    "job_id": "job_9b3e1c0d4a",
    "project_id": "proj_6aeb104e",
    "status": "queued",
    "message": "PRD generation job accepted and queued for processing.",
    "is_existing": false
  }
  ```

### 4.2 Query Job Status
* **Route**: `GET /api/v1/jobs/{job_id}`
* **Response Status**: `200 OK`
* **Authorization**: Rejects requests from non-owning users with `403 Forbidden`.
* **Response Body**:
  ```json
  {
    "job_id": "job_9b3e1c0d4a",
    "project_id": "proj_6aeb104e",
    "status": "running",
    "current_stage": "business_rules",
    "completed_stages": ["input_analysis", "requirements_engineering", "stakeholder_analysis"],
    "total_stages": 6,
    "progress_percentage": 50,
    "elapsed_seconds": 345,
    "error_code": null,
    "error_message": null
  }
  ```

### 4.3 Query Completed Job Result
* **Route**: `GET /api/v1/jobs/{job_id}/result`
* **Response Status**: `200 OK` (when `status == completed`) or `409 Conflict` (if still running).
* **Response Body**: Full `PRDVersion` document with 27 canonical sections.

### 4.4 Cancel Job
* **Route**: `POST /api/v1/jobs/{job_id}/cancel`
* **Response Status**: `200 OK`
* **Response Body**:
  ```json
  {
    "job_id": "job_9b3e1c0d4a",
    "status": "cancelled",
    "message": "Job marked as cancelled."
  }
  ```

### 4.5 Active Job Lookup for Project
* **Route**: `GET /api/v1/projects/{project_id}/prd/job`
* **Response Status**: `200 OK` (returns active `Job` or `null`).
* **Purpose**: Allows browser clients to recover active generation state instantly upon page refresh or navigation.

---

## 5. Worker Reliability & Fault Tolerance

### 5.1 Atomic Job Claiming
Workers query the database using atomic `find_one_and_update` on `{ "status": "queued" }` sorted by `created_at` ASC (FIFO). In a multi-worker deployment, race conditions are mathematically precluded without external locking infrastructure.

### 5.2 Heartbeat Loop & Stale Recovery
- While processing a job, the worker executes a dedicated background task that updates `heartbeat_at = datetime.utcnow()` every 8 seconds.
- Every polling cycle (every 3 seconds), the worker scans for abandoned jobs where `status == "running"` and `heartbeat_at < (now - 60 seconds)`.
- If a worker crashes, the abandoned job is automatically recovered, incrementing `retry_count`. Once `retry_count >= 3`, the job is marked `failed` with error code `ERR_WORKER_CRASHED`.

### 5.3 Zero-Fallback Strict Enforcement
When running real inference (`USE_OFFLINE_MOCK_IF_OLLAMA_DOWN=false` or `force_mock=False`):
- Connection drops raise `OllamaUnavailableError` (`ERR_OLLAMA_DISCONNECTED`).
- Gateway timeouts raise `OllamaTimeoutError` (`ERR_OLLAMA_TIMEOUT`).
- Invalid JSON structures raise `InvalidModelResponseError` (`ERR_MODEL_OUTPUT_INVALID`).
- Silent fallback to `OfflineMockAdapter` is strictly disabled. Errors are recorded with diagnostic tracebacks in `job.error_details`.

### 5.4 Cooperative Cancellation
Before launching each of the 6 pipeline stages, the worker invokes `check_cancelled()`. If a user issued a cancellation request, the worker halts immediately, logs the interrupt, and exits cleanly without polluting the version history.

