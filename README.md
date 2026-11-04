# Local-First Automated PRD Engineering Framework

**Document ID:** PRD-001  
**Version:** 1.0.0  
**Core Principle:** *Idea in. Professionally engineered PRD out.*

A comprehensive, self-hosted, local-first AI system that converts unstructured product ideas, problem statements, and course assignments into production-grade, 27-section Product Requirements Documents (PRDs). Operates entirely within the local host boundary with zero mandatory cloud dependencies or external AI APIs.

---

## Architecture & Technology Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, Motor (Async MongoDB Driver).
- **AI Engine:** Local Ollama integration (`/api/generate`, `/api/tags`) with an intelligent, deterministic local offline fallback adapter.
- **Database:** MongoDB Community Edition with fallback support for in-memory testing.
- **Document Export:** Markdown (`.md`), Microsoft Word (`.docx`), Adobe PDF (`.pdf`).
- **Containerization:** Multi-stage Dockerfiles and Docker Compose orchestrating Frontend, Backend, MongoDB, and Ollama.

---

## Core Pipeline & Capabilities

1. **Natural Language Input & File Ingestion (FR-001 - FR-005):**
   - Ingests freeform product ideas, problem statements, or assignment briefs.
   - Preserves uploaded reference documents and original inputs.
2. **Input Understanding & Fact vs Assumption Separation (FR-010 - FR-015):**
   - Classifies domain and extracts target users, objectives, and capabilities.
   - Enforces a strict boundary between user-provided verified facts and AI-generated assumptions.
3. **Interactive Clarification Engine (FR-020 - FR-024):**
   - Evaluates missing critical information and formulates prioritized questions (`critical`, `medium`, `low`).
   - Supports answering questions or continuing with documented assumptions.
4. **Canonical 27-Section PRD Synthesis (FR-030 - FR-052):**
   - Generates all 27 standard sections (Executive Summary, Personas, User Stories, FRs, NFRs, Business Rules, System Workflows, Security, Acceptance Criteria, Risks, etc.).
   - Assigns stable IDs (`FR-001`, `NFR-001`, `BR-001`, `AC-001`) with bidirectional traceability.
5. **Section-Level Editing & AI In-Place Regeneration (FR-053 - FR-055):**
   - Edit any section's Markdown directly or trigger local AI regeneration with custom guidance.
   - Immutability guarantee: edits increment versions (e.g., `v1.0` -> `v1.1`), never silently overwriting prior versions.
6. **Deterministic Quality Validation Engine (FR-060 - FR-065):**
   - Structural completeness check (all 27 sections).
   - Duplicate requirement ID detection.
   - Orphan requirement checks (unmapped acceptance criteria).
   - Ambiguous term detector (`fast`, `easy to use`, `robust`, etc.).
   - Computes a deterministic 0-100 quality score and actionable remediation steps.
7. **Multi-Format Document Export (FR-056):**
   - High-fidelity export to **Markdown (.md)**, **Microsoft Word (.docx)**, and **Adobe PDF (.pdf)**.

---

## Quickstart: Local Setup

### Option 1: Native Local Development

#### 1. Backend Setup
```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Start backend service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API docs available at: `http://localhost:8000/docs`

#### 2. Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
Open web application at: `http://localhost:3000`

---

### Option 2: Docker Compose (Full Stack)

Start the entire system (Frontend, Backend, MongoDB, and Ollama) with one command:
```bash
docker-compose up --build
```
- **Web UI:** `http://localhost:3000`
- **FastAPI API:** `http://localhost:8000`
- **MongoDB:** `localhost:27017`
- **Ollama:** `http://localhost:11434`

---

## Executing Automated Tests

Run the full end-to-end verification suite:
```bash
python backend/tests/runner.py
```
This executes:
1. Authentication & security tests (bcrypt hashing, JWT tokens).
2. AI pipeline stages (Input analysis, clarification formulation, requirement engineering, 27-section assembly).
3. Deterministic validation engine tests (missing sections, ID collisions, unmapped criteria).
4. Multi-format export verification (Markdown, DOCX, PDF).
5. Full API workflow test (Register -> Login -> Create Project -> Submit Idea -> Analyze -> Clarify -> Generate PRD -> Validate -> Edit Section -> Regenerate Section -> Approve -> Export).

---

## Offline & Privacy Guarantees

- **Zero Cloud Leakage:** All data and prompts remain strictly on local storage (`/data/`).
- **Telemetry Free:** No external third-party telemetry, tracking, or mandatory API keys.
- **Offline Fallback Engine:** If the Ollama daemon is offline or downloading models, the system seamlessly uses the local deterministic offline engine.
