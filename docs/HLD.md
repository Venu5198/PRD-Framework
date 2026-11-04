# High-Level Design (HLD)
## Local-First Automated PRD Engineering Framework

**Status:** As-Built Architecture  
**Version:** 1.0.0

---

## 1. System Topology

```mermaid
graph TD
    UserClient["Client Web Browser (React + TS + Tailwind)"] -->|HTTP / JSON (Port 3000 -> 8000)| APIGateway["FastAPI Gateway (/api/v1)"]
    
    subgraph "Local Host Application Boundary"
        APIGateway --> AuthSvc["Authentication Service (Bcrypt + JWT)"]
        APIGateway --> ProjSvc["Project & Submission Service"]
        APIGateway --> Orchestrator["PRD Pipeline Orchestrator"]
        APIGateway --> ValidationSvc["Deterministic Validation Service"]
        APIGateway --> ExportSvc["Document Export Engine"]

        Orchestrator --> AIGateway["AI Gateway Interface"]
        AIGateway --> OllamaAdapter["Ollama Client Adapter (localhost:11434)"]
        AIGateway --> OfflineAdapter["Deterministic Offline Adapter"]

        ProjSvc --> MongoDB[("Local MongoDB Community (27017)")]
        Orchestrator --> MongoDB
        ValidationSvc --> MongoDB

        ExportSvc --> LocalFS[("Local File Storage: /data/uploads, /data/exports")]
    end
```

---

## 2. Key Technology Choices

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | High performance, zero runtime overhead, responsive layout, type safety. |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2 | High concurrency async I/O, strict JSON schema validation, automatic OpenAPI docs. |
| **Database** | MongoDB Community 7.0 / 8.3 | Document-oriented model natural for nested PRD sections and immutable version snapshots. |
| **AI Inference** | Ollama local daemon (`llama3.2`, `mistral`) | Private, GPU-accelerated local inference without third-party network egress. |
| **Document Export** | `reportlab`, `python-docx`, `markdown` | Native binary document generation with formatted tables, headers, and metadata. |
| **Containerization** | Docker, Docker Compose | Single-command deployment replicating local workstation topology. |

---

## 3. Communication and Data Flow

1. **Submission Flow:** User provides text/files -> validated by `projects.py` -> stored in `idea_submissions`.
2. **Analysis Flow:** Triggered via `/api/v1/analysis/{id}/analyze` -> `InputAnalyzer`, `AssignmentParser`, and `ProblemAnalyst` process raw input -> structured `AnalysisRecord` saved.
3. **Clarification Flow:** `ClarificationEngine` evaluates missing critical information -> produces ranked `ClarificationSession`.
4. **Synthesis Flow:** `RequirementEngineer`, `StakeholderAnalyst`, `BusinessRulesAnalyst`, and `RiskAnalyst` produce structured requirements -> `PRDGenerator` synthesizes all 27 canonical sections -> stored as immutable `PRDVersion`.
5. **Quality Gate Flow:** `ValidationService` runs deterministic structural and semantic checks -> reports score (0-100) and actionable remediation findings.
6. **Export Flow:** `ExportService` compiles version sections into `.md`, `.docx`, or `.pdf` on the local filesystem.
