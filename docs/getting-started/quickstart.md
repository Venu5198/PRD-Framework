# PRD Engineering Framework: Quickstart Guide

This guide walks you through running the PRD Engineering Framework in 5 minutes or less.

---

## 1. Fast Track: Docker Compose (Recommended)

The easiest way to run the full stack (FastAPI backend, React frontend, MongoDB, Ollama, and asynchronous background worker):

```bash
# 1. Clone repository
git clone https://github.com/Venu5198/PRD-Framework.git
cd PRD-Framework

# 2. Configure environment
copy .env.example .env

# 3. Start all services
docker compose up -d
```

### Access Services
* **Web UI:** [http://localhost:3000](http://localhost:3000)
* **Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 2. Local Development Setup (Manual)

If you prefer running backend and frontend directly on your host machine:

### Prerequisites
* Python 3.11+
* Node.js 18+ and npm
* MongoDB running on `localhost:27017`

### Backend Setup
```bash
cd backend
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Background Worker Setup (Separate Terminal)
```bash
cd backend
.\venv\Scripts\Activate.ps1
python -m app.worker
```

### Frontend Setup (Separate Terminal)
```bash
cd frontend
npm install
npm run dev
```
Frontend will be available at [http://localhost:5173](http://localhost:5173) or [http://localhost:3000](http://localhost:3000).

---

## 3. Configuring AI Providers

Edit `.env` to select your preferred inference provider:

### Option A: Cloud Inference with Groq (Fastest)
```ini
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
AI_TIMEOUT_SECONDS=180
```

### Option B: 100% Local Inference with Ollama (Air-Gapped)
```ini
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama3.2
USE_OFFLINE_MOCK_IF_OLLAMA_DOWN=false
```
Pull the required model:
```bash
ollama pull llama3.2
```

---

## 4. End-to-End Workflow: Generating Your First PRD

1. **Open Dashboard:** Navigate to [http://localhost:3000](http://localhost:3000).
2. **Create Project:** Enter a project name (e.g., `Customer Support AI Copilot`).
3. **Submit Idea:** Provide your raw concept, problem statement, or course assignment brief.
4. **AI Analysis:** Review extracted capabilities, pain points, stakeholder personas, and technical constraints.
5. **Clarification Engine:** Answer generated questions or accept suggested assumptions.
6. **PRD Generation:** The system synthesizes a canonical 27-section PRD.
7. **Traceability & Validation:** Inspect the Requirements Matrix and 10-dimension Quality Validation score.
8. **Export:** Download professional PDF, DOCX, or Markdown technical specifications.

---

## 5. Verification Commands

Run test suites locally to ensure full system health:

```bash
# Run backend test suite (137 tests)
python -m pytest backend/tests/ -v

# Run frontend test suite
npm --prefix frontend run test -- --run

# Run frontend production build
npm --prefix frontend run build
```
