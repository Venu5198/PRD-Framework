# Professional PRD Engineering v2 — Phase 1: Pipeline Source Code Audit

## 1. Executive Summary

This audit provides an exhaustive component-by-component investigation of the PRD Framework's generation pipeline. The investigation was initiated to diagnose why generated PRDs (such as the AI Customer Support Assistant) consistently contain requirements, user stories, user journeys, scope definitions, and system architectures describing the PRD Framework software itself rather than the target product.

The investigation examined all 10 pipeline components, the orchestration service (`PRDService`), the validator (`ValidationService`), and test suites.

**Primary Finding:**
The framework content leakage is **not** an LLM hallucination. It is caused by **direct source-code-level hardcoding**:
1. `PRDGenerator` is completely static and never invokes the AI model; it hardcodes the PRD Framework's own specification into 15 of 27 sections.
2. `StakeholderAnalyst` and `RiskAnalyst` do not invoke the AI model; they return hardcoded PRD Framework user journeys and technical risks.
3. `RequirementEngineer` swallows JSON parsing errors and falls back to hardcoded PRD Framework functional requirements (`FR-001`, `FR-002`).
4. `ValidationService` only performs character length and regex checks, awarding a 100% pass score to leaked boilerplate.

---

## 2. Component-by-Component Audit

### 2.1 Input Analyzer
* **File**: [`backend/app/ai/pipeline/input_analyzer.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/input_analyzer.py)
* **Responsibility**: Ingests unstructured user ideas, problem statements, and assignments; extracts product category, problem domain, intended users, core objectives, expected capabilities, facts, and assumptions.
* **Input**: `IdeaSubmissionResponse` (submission type, raw idea, problem statement, assignment context).
* **Output**: `AnalysisRecord` Pydantic model.
* **Uses Target Product Context?**: **YES**. Correctly formats prompt with user input and invokes `ai_gateway.generate(..., json_mode=True)`.
* **Injects Hardcoded Content?**: **NO** during standard execution; fallback values exist only on exception.
* **Downstream Consumption**: Fully consumed by `RequirementEngineer`, `StakeholderAnalyst`, `BusinessRulesAnalyst`, and `PRDGenerator`.
* **Audit Verdict**: **SOUND**. Accurately extracted Customer Support domain, capabilities, and objectives.

---

### 2.2 Assignment Parser
* **File**: [`backend/app/ai/pipeline/assignment_parser.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/assignment_parser.py)
* **Responsibility**: Parses academic course rubrics or RFP requirements into structured constraints and mandatory deliverables.
* **Input**: `AssignmentParserInput` (`assignment_text: str`).
* **Output**: `AssignmentParserOutput` (instruction summary, mandatory sections, deliverables, constraints).
* **Uses Target Product Context?**: **YES**, when `assignment_context` is present.
* **Injects Hardcoded Content?**: **YES, on empty input or fallback**:
  - Line 48: `deliverables=["PRD Document", "Architecture Specification"]`
  - Line 49: `constraints=["Local execution", "Zero external cloud telemetry"]`
  - Line 82: `deliverables=["PRD Export in Markdown, DOCX, and PDF"]`
* **Downstream Consumption**: Stored in `AnalysisRecord.assignment_requirements`.
* **Audit Verdict**: **CONTRIBUTING FACTOR**. Empty/fallback defaults introduce framework export mechanisms.

---

### 2.3 Problem Analyst
* **File**: [`backend/app/ai/pipeline/problem_analyst.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/problem_analyst.py)
* **Responsibility**: Deepens problem domain classification, root pain points, current limitations, and target outcomes.
* **Input**: `ProblemAnalystInput` (concept, problem statement).
* **Output**: `ProblemAnalystOutput` (problem domain, root pain points, current limitations, desired outcomes).
* **Uses Target Product Context?**: **YES**. Uses prompt interpolation and calls AI gateway.
* **Injects Hardcoded Content?**: **YES, on fallback**:
  - Line 71: `desired_outcomes=["Streamlined local requirement engineering", "Complete PRD delivery"]`
  - Line 78-79: `current_limitations=["Manual document creation"]`, `desired_outcomes=["Standardized requirement generation"]`
* **Downstream Consumption**: In `prd_service.py:90-91`, overrides `analysis.problem_domain`. Root pain points and limitations are NOT forwarded downstream to `PRDGenerator`.
* **Audit Verdict**: **DEFECTIVE INTEGRATION**. Rich output is discarded; only domain string is saved.

---

### 2.4 Clarification Engine
* **File**: [`backend/app/ai/pipeline/clarification_engine.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/clarification_engine.py)
* **Responsibility**: Generates 2 to 4 high-impact clarification questions based on missing information in the analysis record.
* **Input**: `AnalysisRecord`.
* **Output**: `ClarificationSession` (list of `ClarificationQuestion`).
* **Uses Target Product Context?**: **YES**, in AI prompt.
* **Injects Hardcoded Content?**: **YES, on JSON parse failure**:
  - Line 96: `question="Will the system run strictly as a single-user desktop tool or as a multi-user local network service?"`
  - Line 104: `question="What model size should be targeted as the primary inference default (e.g., 3B vs 8B parameters)?"`
* **Downstream Consumption**: User answers and resolved assumptions are passed into `RequirementEngineer`.
* **Audit Verdict**: **CONTRIBUTING FACTOR**. Fallback questions ask about the PRD framework's deployment architecture.

---

### 2.5 Stakeholder Analyst
* **File**: [`backend/app/ai/pipeline/stakeholder_analyst.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/stakeholder_analyst.py)
* **Responsibility**: Intended to generate persona profiles and user journey steps for the target product.
* **Input**: `StakeholderAnalystInput` (product category, intended users, domain).
* **Output**: `StakeholderAnalystOutput` (personas, user journeys).
* **Uses Target Product Context?**: **NO**. Accepts `ai_gateway` in constructor, but **never calls `ai_gateway.generate()`**.
* **Injects Hardcoded Content?**: **YES, 100% HARDCODED**:
  - Line 41: `primary_goals=["Accelerate requirement definition", "Ensure complete edge case coverage"]`
  - Line 42: `frustrations=["Unclear expectations", "Manual documentation rework"]`
  - Line 50: `actor_action="Submit raw concept or assignment text"`, `system_response="Persists input, extracts entities, and isolates facts vs assumptions"`
  - Line 55: `actor_action="Review high-impact questions..."`
  - Line 60: `actor_action="Inspect generated 27 sections... exports to MD, DOCX, and PDF"`
* **Downstream Consumption**: Injected into `requirements_data["stakeholders"]` and `requirements_data["user_journeys"]`.
* **Audit Verdict**: **CONFIRMED ROOT CAUSE**. The component is a pure static mock describing PRD Framework usage.

---

### 2.6 Requirement Engineer
* **File**: [`backend/app/ai/pipeline/requirement_engineer.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/requirement_engineer.py)
* **Responsibility**: Generates Functional Requirements, Non-Functional Requirements, Business Rules, and Acceptance Criteria.
* **Input**: `AnalysisRecord`, optional `ClarificationSession`.
* **Output**: `Dict[str, Any]` containing requirement lists.
* **Uses Target Product Context?**: **PARTIALLY**. Calls AI gateway with `REQUIREMENT_PROMPT`.
* **Injects Hardcoded Content?**: **YES, on JSON parse exception (Lines 115–166)**:
  - `FR-001`: "Natural Language Input Processing" ("The system shall ingest and parse unstructured user product descriptions.")
  - `FR-002`: "Automated PRD Synthesis" ("The system shall synthesize functional and non-functional requirements into a canonical 27-section PRD.")
  - `NFR-001`: "Local Host Confidentiality" ("All data processing and persistence shall occur strictly on local host storage.")
  - `BR-001`: "Immutable Version Tracking" ("Approved PRD versions shall remain immutable to preserve auditability.")
  - `AC-001`: "Given a submitted prompt, when saved, the system creates an identifiable submission record."
  - `AC-002`: "Given valid analysis inputs, when PRD generation runs, all canonical sections are generated."
  - `AC-003`: "Given execution in an offline environment, all operations complete without external network requests."
* **Downstream Consumption**: Formats Sections 12 (FR), 13 (NFR), 14 (User Stories), 16 (Business Rules), and 21 (Acceptance Criteria).
* **Audit Verdict**: **CONFIRMED ROOT CAUSE**. When model output contains formatting irregularities, it silently returns hardcoded PRD Framework requirements.

---

### 2.7 Business Rules Analyst
* **File**: [`backend/app/ai/pipeline/business_rules_analyst.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/business_rules_analyst.py)
* **Responsibility**: Extracts domain-specific non-negotiable invariants, validations, and operational requirements.
* **Input**: `BusinessRulesInput` (domain, objectives, constraints).
* **Output**: `BusinessRulesOutput` (list of `BusinessRuleItem`).
* **Uses Target Product Context?**: **YES**. Successfully extracts domain rules when AI succeeds.
* **Injects Hardcoded Content?**: **YES, on exception or <4 rules**:
  - Injects 5 attendance rules: `BR-001` (Strict Attendance Window), `BR-002` (Proxy Detection & Single Device Binding), `BR-003` (Immutable Attendance Record History), `BR-004` (Biometric Privacy), `BR-005` (Offline Sync Conflict Resolution).
* **Downstream Consumption**: Appended to `requirements_data["business_rules"]` in `prd_service.py:220-227`.
* **Audit Verdict**: **CONFIRMED ROOT CAUSE (ATTENDANCE CONTAMINATION)**. Fallback injects student attendance rules into unrelated domains.

---

### 2.8 Risk Analyst
* **File**: [`backend/app/ai/pipeline/risk_analyst.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/risk_analyst.py)
* **Responsibility**: Intended to evaluate technical, operational, and security risks of the target product.
* **Input**: `RiskAnalystInput` (problem domain, capabilities, constraints).
* **Output**: `RiskAnalystOutput` (list of `RiskItem`).
* **Uses Target Product Context?**: **NO**. Never calls `ai_gateway.generate()`.
* **Injects Hardcoded Content?**: **YES, 100% HARDCODED**:
  - `RSK-001`: "Local Model Resource Exhaustion" ("Implement in-process deterministic fallback adapter and asynchronous generation timeouts.")
  - `RSK-002`: "AI Hallucination of Verification Evidence" ("Strict separation of confirmed facts from inferred assumptions with mandatory badges.")
  - `RSK-003`: "Local Storage Tampering or Traversal" ("Sanitize file upload destinations...")
  - `RSK-004`: "Ollama Daemon Unavailability" ("Automatic fallback to local deterministic offline engine...")
* **Downstream Consumption**: Injected into `requirements_data["risks"]` in `prd_service.py:240`.
* **Audit Verdict**: **CONFIRMED ROOT CAUSE**. Pure static mock returning PRD Framework infrastructure risks.

---

### 2.9 PRD Generator
* **File**: [`backend/app/ai/pipeline/prd_generator.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/prd_generator.py)
* **Responsibility**: Assembles all 27 canonical sections into the final PRD document structure.
* **Input**: `project_title`, `AnalysisRecord`, `ClarificationSession`, `requirements_data`.
* **Output**: `Dict[str, PRDSectionContent]` (27 canonical sections).
* **Uses Target Product Context?**: **NO**. Takes `ai_gateway` in constructor, but **never calls `ai_gateway.generate()`** in `generate_full_prd()`.
* **Injects Hardcoded Content?**: **YES — 15 of 27 SECTIONS ARE HARDCODED FRAMEWORK CONTENT**:
  1. Section 8 (`existing_workflow_and_pain_points`): "1. Manual ideation & drafting: Practitioners write unstructured notes... 2. Information gaps... 3. Inconsistent documentation..."
  2. Section 9 (`proposed_solution`): "{project_title} introduces an end-to-end automated framework that bridges raw concepts into verified, production-grade requirements..."
  3. Section 10 (`product_scope`): "In-Scope Capabilities for MVP: Complete workflow automation from user input to structured output. Local-first execution without external SaaS dependencies. Interactive clarification... Multi-format export (Markdown, PDF, DOCX)."
  4. Section 11 (`out_of_scope`): "Non-Goals: Automatic code generation or deployment of arbitrary target applications. Third-party cloud SaaS synchronization. Automated financial market viability forecasting."
  5. Section 14 (`user_stories`): Derives stories by blindly wrapping FRs: "As a Customer I want to natural language input processing so that..."
  6. Section 15 (`user_journeys`): Hardcoded Mermaid sequence diagram: `User -> Framework as PRD Framework -> Pipeline as AI Processing Pipeline -> Validator as Quality Engine`.
  7. Section 17 (`system_workflows`): "1. Input Ingestion... 2. Domain Classification... 3. Gap Resolution... 4. Requirement Synthesis... 5. Audit & Export"
  8. Section 18 (`data_requirements`): "Document-oriented collections with immutable version archives... File attachments and exported documents reside in local system storage directories."
  9. Section 19 (`integration_requirements`): "Local AI Gateway: REST communication with local Ollama daemon (http://localhost:11434)... Offline Fallback Engine... File Formats: Markdown, DOCX, PDF"
  10. Section 20 (`security_and_privacy_requirements`): "Data Sovereignty: All telemetry... within local host... Authentication: JWT tokens with bcrypt... Input Sanitation: File uploads..."
  11. Section 22 (`dependencies_and_constraints`): "Runtime Dependencies: Python 3.10+, Node.js 18+, MongoDB Community / in-memory instance, Ollama..."
  12. Section 23 (`risks_and_mitigation`): Hardcoded table of PRD Framework software risks.
  13. Section 25 (`success_metrics`): "Document Generation Completeness: 100% of canonical sections... 100% FR to AC traceability... Offline Operation: Zero external network requests..."
  14. Section 26 (`release_considerations`): "Single-command Docker Compose stack and native local environment scripts... Versioned API endpoints under /api/v1."
  15. Section 27 (`appendix_and_glossary`): "PRD, FR, NFR, BR, AC, Local-First".
* **Downstream Consumption**: Persisted directly as the final PRD version in MongoDB and exported to PDF/Markdown.
* **Audit Verdict**: **CONFIRMED PRIMARY ROOT CAUSE**. `PRDGenerator` is a hardcoded static template formatter, not an AI generation engine.

---

### 2.10 PRD Validator & Validation Service
* **Files**: [`backend/app/ai/pipeline/prd_validator.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/prd_validator.py), [`backend/app/services/validation_service.py`](file:///c:/PRD-Framework/backend/app/services/validation_service.py)
* **Responsibility**: Performs automated quality analysis over generated PRD versions.
* **Validation Rules**:
  - `VAL-SEC-001`: Section present in `CANONICAL_SECTIONS`.
  - `VAL-SEC-002`: Section content length $\ge 15$ characters.
  - `VAL-REQ-001`: Duplicate `FR-xxx` regex identifiers.
  - `VAL-AC-001`: Every `FR-xxx` identifier referenced in `acceptance_criteria` text.
  - `VAL-AMB-001`: Scans for ambiguous buzzwords ("fast", "robust", "seamless").
  - `VAL-SCP-001` / `VAL-SCP-002`: Product scope and out-of-scope sections $\ge 20$ characters.
* **Deficiencies**:
  - **Zero Domain Semantic Validation**: Does not verify whether requirements relate to the target product.
  - **Zero Forbidden Keyword Checking**: Allows "PRD Framework", "Ollama", "Offline Fallback", "Attendance" to pass unconditionally.
  - **False Quality Guarantee**: A PRD composed 100% of leaked framework boilerplate passes with a **95–100% score**.
* **Audit Verdict**: **CONFIRMED CONTRIBUTING FACTOR**. The quality gate provides zero protection against domain leakage.

