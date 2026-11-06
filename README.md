# Local-First Automated PRD Engineering Framework

**Idea in. Professionally engineered PRD out.**

A local-first AI-powered application that converts product ideas, problem statements, and assignment requirements into structured Product Requirements Documents (PRDs).

The framework guides users through idea submission, AI analysis, clarification, PRD generation, requirements traceability, quality validation, version management, and document export.

---

## 1. Project Overview

The PRD Framework helps product teams, developers, students, and engineers convert unstructured ideas into organized product documentation.

Instead of manually writing a PRD from scratch, users provide their product concept and supporting information. The framework analyzes the input, identifies missing details, asks clarification questions, and generates a structured PRD.

### Key Features

- Natural-language product idea submission.
- Problem statement and assignment context support.
- Reference document upload.
- AI-powered idea analysis.
- Interactive clarification engine.
- Documented assumptions and unresolved decisions.
- Structured 27-section PRD generation.
- Functional and non-functional requirements.
- Business rules and acceptance criteria.
- Requirements traceability matrix.
- Quality validation and actionable findings.
- PRD version management.
- Section-level editing and regeneration.
- Markdown, DOCX, and PDF export.
- Local-first architecture with configurable AI providers.

---

## 2. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| Styling | Tailwind CSS |
| Backend | Python, FastAPI |
| Data Validation | Pydantic v2 |
| Database | MongoDB Community Edition |
| MongoDB Driver | Motor |
| Local AI | Ollama |
| Cloud AI | Groq, when configured |
| Document Export | Markdown, DOCX, PDF |
| Containerization | Docker, Docker Compose |
| Backend Testing | Pytest |
| Frontend Testing | Vitest |
| Frontend Build | Vite |

**AI provider configuration:** The application supports local inference through Ollama and can use a configured cloud provider such as Groq. Cloud inference requires the appropriate credentials and configuration. Do not assume that every execution is fully offline.

---

## 3. Application Screenshots

Screenshots are stored in the repository under:

```text
docs/
└── screenshots/
    ├── 01-dashboard.png
    ├── 02-submit-idea.png
    ├── 03-ai-analysis.png
    ├── 04-clarifications.png
    ├── 05-prd-document.png
    ├── 06-requirements-matrix.png
    ├── 07-quality-validation.png
    ├── 08-version-history.png
    └── 09-document-export.png
```

Add the actual screenshots to these paths. The following sections will display them automatically once the files are committed.

### 3.1 Dashboard

The dashboard is the entry point for accessing and managing PRD projects.

![Application Dashboard](docs/screenshots/01-dashboard.png)

### 3.2 Submit Product Idea

Users enter a product concept, optional problem statement, assignment constraints, and reference documents.

![Submit Product Idea](docs/screenshots/02-submit-idea.png)

### 3.3 AI Analysis

The AI analyzes the submitted idea and identifies the product domain, objectives, users, capabilities, and missing information.

![AI Analysis](docs/screenshots/03-ai-analysis.png)

### 3.4 Clarification Engine

The clarification engine asks questions about important missing information.

Users can:
- Select a suggested answer.
- Enter a custom answer.
- Save their answer.
- Accept an assumption where appropriate.

Unresolved decisions should remain visible instead of being silently treated as confirmed requirements.

![Clarification Engine](docs/screenshots/04-clarifications.png)

### 3.5 PRD Document

The generated PRD is presented as a structured document with a section outline.

Users can inspect the generated content and review the document before approval.

![PRD Document](docs/screenshots/05-prd-document.png)

### 3.6 Requirements Matrix

The requirements matrix provides stable identifiers and traceability across functional requirements, acceptance criteria, and business rules.

![Requirements Matrix](docs/screenshots/06-requirements-matrix.png)

### 3.7 Quality Validation

The validation stage checks the generated document and presents its quality score and findings.

A high score must not be treated as proof that every requirement is factually supported. Review critical findings and unresolved claims before approval.

![Quality Validation](docs/screenshots/07-quality-validation.png)

### 3.8 Version History

Version management helps users track document changes without silently overwriting previous versions.

![Version History](docs/screenshots/08-version-history.png)

### 3.9 Document Export

The framework supports exporting PRDs into Markdown, Word, and PDF formats.

![Document Export](docs/screenshots/09-document-export.png)

---

## 4. End-to-End Application Workflow

Follow these steps to generate and review a PRD.

### Step 1: Create a PRD Project

1. Open the application.
2. Navigate to the dashboard.
3. Create a new PRD project.
4. Enter the project name.
5. Open the project.

### Step 2: Submit the Product Idea

Navigate to **1. Submit Idea**.

Provide:

- Product idea or concept.
- Problem statement, if available.
- Assignment context or constraints, if applicable.
- Reference documents, if available.

Example:

```text
Build a no-code workflow automation platform.

Users should describe an automation in natural language
and generate a visual workflow with triggers, actions,
conditions, and integrations.
```

Click **Submit & Analyze Idea**.

### Step 3: Review AI Analysis

Navigate to **2. AI Analysis**.

Review the extracted information:

- Product domain.
- Problem definition.
- Product objectives.
- Target users.
- Core capabilities.
- Missing information.
- Identified assumptions.

Do not treat AI-generated suggestions as user-confirmed facts.

### Step 4: Answer Clarification Questions

Navigate to **3. Clarifications**.

The clarification engine generates questions based on missing information.

For each question:

1. Read the question and its impact.
2. Review suggested answers.
3. Enter your own answer where necessary.
4. Click **Save Answer**.
5. Use **Accept Assumption** only when you explicitly accept the proposed assumption.

Important: If an architectural decision, business rule, security requirement, or numerical target is unknown, keep it unresolved or mark it as a proposal. Do not invent a commitment just to complete the PRD.

### Step 5: Generate the PRD

Click **Generate 27-Section PRD**.

The framework generates the structured PRD using the submitted information, clarification answers, and documented assumptions.

### Step 6: Review the PRD Document

Navigate to **4. PRD Document**.

Review the complete document section by section.

Pay particular attention to:

- Executive summary.
- Problem statement.
- Product objectives.
- Scope and exclusions.
- User personas.
- User stories.
- Functional requirements.
- Non-functional requirements.
- Business rules.
- User journeys.
- Security and privacy.
- Architecture constraints.
- Acceptance criteria.
- Risks and assumptions.

Check that the document does not introduce functionality, integrations, technologies, security controls, or performance targets that were never confirmed or explicitly proposed.

### Step 7: Review the Requirements Matrix

Navigate to **5. Requirements Matrix**.

Verify:

- Functional requirement IDs are unique.
- Non-functional requirement IDs are unique.
- Business rule IDs are unique.
- Acceptance criteria reference valid requirements.
- Requirements have traceable sources.
- Priority classifications are justified.
- Proposed and unresolved items are not presented as confirmed requirements.

### Step 8: Run Quality Validation

Navigate to **6. Quality Validation**.

Run validation and inspect the findings.

Do not approve a PRD based only on its numerical quality score.

Review:
- Structural errors.
- Missing sections.
- Unsupported requirements.
- Contradictions.
- Missing traceability.
- Unsupported numerical commitments.
- Invalid acceptance criteria.
- Unresolved high-impact decisions.

Resolve critical findings before approval.

### Step 9: Approve the PRD Version

After reviewing the document and validation findings, use **Approve Version** when the PRD is ready.

Approval should represent an intentional review decision, not merely a successful generation operation.

### Step 10: Manage Versions and Export

Use the version management functionality to inspect previous versions and create new revisions.

Export the reviewed document in the required format:

- Markdown (`.md`)
- Microsoft Word (`.docx`)
- PDF (`.pdf`)

Always inspect exported files. A document that looks correct in the application may have formatting issues in PDF or DOCX.

---

## 5. Local Development Setup

### Prerequisites

Install the following:

- Python 3.11 or later.
- Node.js and npm.
- MongoDB Community Edition.
- Ollama, if using local inference.
- Git.
- Docker and Docker Compose, if using containerized deployment.

### Repository Structure

```text
PRD-Framework/
│
├── backend/
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
│
├── docs/
│   └── screenshots/
│
├── docker-compose.yml
├── README.md
└── ...
```

The exact repository structure may contain additional directories and configuration files.

### Backend Setup

Open a terminal:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend API:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

### Frontend Setup

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

Use the actual Vite development port configured in the project if it differs from 3000.

### Database Setup

Ensure MongoDB is running and that the backend connection string points to the correct database.

For a local MongoDB instance, a typical connection string is:

```text
mongodb://localhost:27017
```

Use the database and environment configuration defined by the backend. Never commit production credentials or API keys.

### Ollama Setup

Install and start Ollama if local inference is required.

Check available models:

```bash
ollama list
```

Pull a model only if it is not already installed:

```bash
ollama pull qwen3.5:4b
```

The actual model name must match the configured model in the application.

---

## 6. Docker Compose Setup

To start the containerized application:

```bash
docker compose up --build
```

To run in the background:

```bash
docker compose up --build -d
```

To inspect containers:

```bash
docker compose ps
```

To inspect logs:

```bash
docker compose logs -f
```

To stop services:

```bash
docker compose down
```

Verify the actual service names, ports, volumes, and environment variables in `docker-compose.yml`.

---

## 7. Testing

### Backend Tests

```bash
cd backend
pytest -v
```

### Frontend Tests

```bash
cd frontend
npm run test
```

### Frontend Lint

```bash
npm run lint
```

### Frontend Production Build

```bash
npm run build
```

### Full Test Runner

The existing README documents the following command:

```bash
python backend/tests/runner.py
```

Run it from the repository root.

Record the actual command output and exit code. A canceled or skipped test must not be reported as passed.

---

## 8. Troubleshooting

### MongoDB Duplicate Version Error

Example:

```text
E11000 duplicate key error collection:
prd_framework.prd_versions
index: uniq_prd_version

dup key:
{
  prd_id: "...",
  version_number: "v2.4.6"
}
```

**Cause:**

The database has a unique compound index on:

```text
prd_id + version_number
```

The application is trying to insert a version that already exists for the same PRD.

**Expected behavior:**

1. Check whether the version already exists.
2. If generation is a retry, handle it idempotently or return the existing generation result.
3. If this is a new revision, allocate the next available version number.
4. Use a database-safe version allocation strategy to handle concurrent requests.
5. Return a meaningful conflict or retry response instead of exposing a raw MongoDB exception.

Do not delete the existing version or drop the unique index as a workaround. The unique index protects version integrity.

### Backend Is Not Starting

Check:

- Python virtual environment is activated.
- Dependencies are installed.
- MongoDB is reachable.
- Environment variables are configured.
- The configured backend port is available.

### Frontend Cannot Connect to Backend

Check:

- Backend is running.
- API base URL is correct.
- CORS configuration permits the frontend origin.
- Browser network errors.
- Backend logs.

### AI Generation Fails

Check:

- The selected AI provider is available.
- Ollama is running when using local inference.
- The configured model is installed.
- Groq credentials are valid when using Groq.
- Provider timeout and rate-limit responses.
- Backend logs for the original exception.

Do not silently switch to a mock or fallback generator and present its output as genuine AI-generated content.

### PDF or DOCX Formatting Problems

Check:

- Markdown table rendering.
- Mermaid diagram rendering.
- Page breaks and content overflow.
- Font consistency.
- Table widths and wrapping.
- Exported document against the application preview.

A Markdown code block containing a table is not automatically a rendered table. Similarly, Mermaid source code is not automatically a rendered diagram. The export pipeline must explicitly convert these elements into the appropriate document structures or renderable images.

---

## 9. Important Engineering Principles

1. User-confirmed facts must remain distinguishable from AI assumptions.
2. Unresolved decisions must not become mandatory requirements.
3. Requirements must have stable identifiers.
4. Acceptance criteria must be traceable to their parent requirements.
5. Generated content must not invent business rules, integrations, metrics, or architecture decisions.
6. Version history must remain immutable.
7. Duplicate version creation must be handled safely.
8. Validation must inspect semantic correctness, not only document structure.
9. Exported documents must be checked independently.
10. A quality score must not replace human review.

---

## 10. Future Development Roadmap

The long-term direction is to extend the framework beyond PRD generation.

| Stage | Deliverable |
|---|---|
| 1 | Product Requirements Document (PRD) |
| 2 | High-Level Design (HLD) |
| 3 | Low-Level Design (LLD) |
| 4 | Implementation Plan |
| 5 | Development Workflow |
| 6 | Testing and Verification |

Each stage should maintain traceability to the approved upstream artifact.

Changes to an approved PRD should trigger impact analysis for downstream documents rather than silently changing them.

---

## 11. Contributing

1. Fork the repository.
2. Create a feature branch.
3. Implement the change.
4. Add or update tests.
5. Run the relevant quality checks.
6. Submit a pull request with implementation details and test evidence.

---

## 12. License

Add the applicable project license and ownership information before publishing or distributing the repository.
