# Professional PRD Engineering v2 — End-to-End Data Flow Analysis

## 1. Complete Pipeline Data Flow Architecture

This document traces the transformation of user input through each sequential stage of the PRD Framework pipeline, pinpointing the exact coordinates where target-product context is preserved, diluted, overwritten, or replaced with framework-specific content.

```
[User Input: Raw Concept / Problem / Assignment]
                     |
                     v
+--------------------+---------------------+
|        STAGE 1: INPUT ANALYSIS          |  Status: Context Preserved
|        (`InputAnalyzer.analyze`)         |  Model: Real Ollama Inference
+--------------------+---------------------+
                     |
                     | Output: `AnalysisRecord` (Category, Domain, Objectives, Capabilities)
                     v
+--------------------+---------------------+
|      STAGE 2: CLARIFICATION ENGINE       |  Status: Context Preserved (or Leaked on Fallback)
|    (`ClarificationEngine.generate`)      |  Model: Real Ollama Inference
+--------------------+---------------------+
                     |
                     | Output: `ClarificationSession`
                     v
+--------------------+---------------------+
|    STAGE 3: REQUIREMENT ENGINEERING      |  Status: CONTEXT OVERWRITTEN ON PARSE FAILURE
|     (`RequirementEngineer.engineer`)     |  Model: Real Ollama Inference -> Silent Mock Fallback
+--------------------+---------------------+
                     |
                     | Output: `requirements_data` (FRs, NFRs, BRs, ACs)
                     v
+--------------------+---------------------+
|      STAGE 4: STAKEHOLDER ANALYST        |  Status: CONTEXT IGNORED (100% HARDCODED)
|     (`StakeholderAnalyst.analyze`)       |  Model: NONE (Zero AI Calls)
+--------------------+---------------------+
                     |
                     | Output: Overwrites `requirements_data["user_journeys"]` with Framework Steps
                     v
+--------------------+---------------------+
|     STAGE 5: BUSINESS RULES ANALYST      |  Status: Domain Rules Extracted + BR-001 Contamination
|   (`BusinessRulesAnalyst.extract_rules`) |  Model: Real Ollama Inference (or Attendance Fallback)
+--------------------+---------------------+
                     |
                     | Output: Appends to `requirements_data["business_rules"]`
                     v
+--------------------+---------------------+
|         STAGE 6: RISK ANALYST            |  Status: CONTEXT IGNORED (100% HARDCODED)
|       (`RiskAnalyst.analyze_risks`)      |  Model: NONE (Zero AI Calls)
+--------------------+---------------------+
                     |
                     | Output: Overwrites `requirements_data["risks"]` with Framework Risks
                     v
+--------------------+---------------------+
|       STAGE 7: PRD GENERATOR             |  Status: 15/27 SECTIONS HARDCODED FRAMEWORK CONTENT
|    (`PRDGenerator.generate_full_prd`)    |  Model: NONE (Zero AI Calls, Static Template String)
+--------------------+---------------------+
                     |
                     | Output: `Dict[str, PRDSectionContent]` (27 Sections)
                     v
+--------------------+---------------------+
|       STAGE 8: QUALITY VALIDATION        |  Status: BLIND TO SEMANTIC LEAKAGE (Awards 100% Score)
|   (`ValidationService.validate_version`) |  Model: Regex & Character Length Heuristics
+--------------------+---------------------+
                     |
                     v
[Final Persisted PRD Document: MongoDB `prd_versions` + PDF/Markdown Exports]
```

---

## 2. Stage-by-Stage Trace & Context Tracking

### Stage 1: Input Analysis (`InputAnalyzer`)
* **Input Received**:
  - `submission_type`: `"idea"`
  - `raw_idea`: `"Build an AI-powered customer support assistant that answers customer questions using approved knowledge-base articles, maintains conversation history, identifies uncertain answers, and escalates unresolved issues to human support agents."`
* **Execution**: Formats prompt and invokes Ollama `llama3.2` with `json_mode=True`.
* **Output Stored**:
  - `product_category`: `"Customer Support"`
  - `problem_domain`: `"Customer Support"`
  - `intended_users`: `["Customer", "Support Agent"]`
  - `core_objectives`: `["Answer customer questions", "Resolve issues efficiently"]`
  - `expected_capabilities`: `["Knowledge-base article retrieval", "Conversation history management", "Uncertain answer identification", "Escalation to human support agents"]`
  - `facts`: Target concept text.
  - `assumptions`: `["AI can understand natural language", "Knowledge-base articles are up-to-date and accurate"]`
* **Context Status**: **PRESERVED**. Complete target-product fidelity.

---

### Stage 2: Clarification Stage (`ClarificationEngine`)
* **Input Received**: `AnalysisRecord` from Stage 1.
* **Execution**: Formats prompt with extracted domain entities.
* **Output Stored**: `ClarificationSession` with targeted questions regarding escalation protocols and knowledge-base sync intervals.
* **Context Status**: **PRESERVED**. (Note: If model formatting fails, lines 91–108 inject fallback questions regarding local 3B/8B model sizes and desktop vs local network deployment).

---

### Stage 3: Requirement Engineering (`RequirementEngineer`)
* **Input Received**: `AnalysisRecord` + `ClarificationSession`.
* **Execution**: Invocations to Ollama request a complex nested JSON schema containing 6 FRs, 4 NFRs, 5 BRs, and 10 ACs.
* **Context Loss Mechanism**:
  - When the local model produces malformed JSON, markdown fence noise, or encounters token truncation, `RequirementEngineer.engineer()` catches the exception on line 114 (`except Exception as e:`).
  - Rather than surfacing an error or retrying, it executes:
    ```python
    logger.warning(f"Error parsing requirement engineering JSON: {e}. Returning robust defaults.")
    ```
  - It returns the hardcoded dictionary on lines 116–166:
    - `FR-001`: "Natural Language Input Processing" (Ingest unstructured user descriptions)
    - `FR-002`: "Automated PRD Synthesis" (Synthesize 27-section PRD)
    - `NFR-001`: "Local Host Confidentiality" (Local host storage)
    - `BR-001`: "Immutable Version Tracking" (Approved PRD versions immutable)
    - `AC-001`..`AC-003`: Acceptance criteria testing the PRD Framework submission record and generation engine.
* **Context Status**: **LOST & REPLACED**. Target product capabilities are completely replaced by self-referential PRD Framework features.

---

### Stage 4: Stakeholder Analysis (`StakeholderAnalyst`)
* **Input Received**: `product_category="Customer Support"`, `intended_users=["Customer", "Support Agent"]`, `domain="Customer Support"`.
* **Execution**: Line 36 defines `analyze()`. **No AI call is made**.
* **Context Loss Mechanism**:
  - Generates personas using the target user titles (`Customer`, `Support Agent`), but hardcodes their goals and frustrations:
    - Goals: `["Accelerate requirement definition", "Ensure complete edge case coverage"]`
    - Frustrations: `["Unclear expectations", "Manual documentation rework"]`
  - Generates `user_journeys` describing the 3-step usage of the PRD Framework tool:
    - Step 1: Submit raw concept or assignment text.
    - Step 2: Review high-impact questions and provide answers.
    - Step 3: Inspect generated 27 sections, review deterministic quality score, edit sections.
* **Context Status**: **OVERWRITTEN**. User journeys describe the developer using the PRD Framework, not the customer using the support assistant.

---

### Stage 5: Business Rules Analysis (`BusinessRulesAnalyst`)
* **Input Received**: `domain="Customer Support"`, `objectives=["Answer customer questions", "Resolve issues efficiently"]`.
* **Execution**: Successfully invokes Ollama. Generates 5 valid domain rules: GDPR privacy, 24h issue resolution, HIPAA/PCI-DSS compliance, data validation, and 24/7 coverage.
* **Context Loss Mechanism**:
  - In `prd_service.py:220-227`, the orchestrator reads `requirements_data.get("business_rules", [])`.
  - Because `RequirementEngineer` fallback previously injected `BR-001` ("Immutable Version Tracking" of PRDs), the orchestrator appends the real rules to `BR-001` and renumbers them `BR-001` through `BR-006`.
  - The final business rules list contains `BR-001: Immutable Version Tracking` (PRD Framework) alongside `BR-002: Customer Data Privacy` (Customer Support).
* **Context Status**: **CONTAMINATED**. Framework versioning rule injected into product business rules.

---

### Stage 6: Risk Analysis (`RiskAnalyst`)
* **Input Received**: `problem_domain`, `capabilities`, `constraints`.
* **Execution**: Line 32 defines `analyze_risks()`. **No AI call is made**.
* **Context Loss Mechanism**:
  - Always returns 4 hardcoded risks:
    - `RSK-001`: Local Model Resource Exhaustion (asynchronous timeouts)
    - `RSK-002`: AI Hallucination of Verification Evidence (fact vs assumption badges)
    - `RSK-003`: Local Storage Tampering or Traversal (upload path sanitization)
    - `RSK-004`: Ollama Daemon Unavailability (offline fallback engine)
* **Context Status**: **100% REPLACED**. Target product risks (e.g., incorrect AI customer advice, knowledge-base sync failure) are completely absent.

---

### Stage 7: Canonical 27-Section Assembly (`PRDGenerator`)
* **Input Received**: All upstream artifacts.
* **Execution**: Line 14 defines `generate_full_prd()`. **No AI call is made**.
* **Context Loss Mechanism**:
  - Interpolates dynamic variables into hardcoded template strings for:
    - Section 1: Title and Category
    - Section 2: Executive summary string
    - Section 3: Vision and capabilities list
    - Section 5: Objectives list
    - Section 6: Stakeholders list
    - Section 7: Persona 1 string
    - Section 12, 13, 16, 21: Markdown tables from `requirements_data`
    - Section 14: User stories string generated by formula: `| US-{i} | {user} | {fr.title.lower()} | {fr.description} | {fr.id} |`
  - **Permanently hardcodes static PRD Framework content for the remaining 15 sections**:
    - Section 8 (`existing_workflow_and_pain_points`): Unstructured notes, missing architecture constraints.
    - Section 9 (`proposed_solution`): Automated framework bridging raw concepts into requirements.
    - Section 10 (`product_scope`): MVP scope = local-first execution, clarification, validation, multi-format export.
    - Section 11 (`out_of_scope`): Non-goals = automatic code generation, SaaS sync, financial forecasting.
    - Section 15 (`user_journeys`): Mermaid sequence diagram of PRD Framework lifecycle (`User -> Framework -> Pipeline -> Validator`).
    - Section 17 (`system_workflows`): Input Ingestion, Domain Classification, Gap Resolution, Requirement Synthesis, Audit & Export.
    - Section 18 (`data_requirements`): Document collections, immutable version archives.
    - Section 19 (`integration_requirements`): Local AI Gateway (`http://localhost:11434`), Offline Fallback Engine, Markdown/DOCX/PDF binary writers.
    - Section 20 (`security_and_privacy_requirements`): Data sovereignty, JWT with bcrypt, file upload isolation.
    - Section 22 (`dependencies_and_constraints`): Python 3.10+, Node.js 18+, MongoDB, Ollama, 8GB RAM.
    - Section 23 (`risks_and_mitigation`): Table of PRD software risks.
    - Section 25 (`success_metrics`): 100% section completeness, 100% traceability, offline operation.
    - Section 26 (`release_considerations`): Single-command Docker Compose stack, versioned API `/api/v1`.
* **Context Status**: **MASSIVE FRAMEWORK LEAKAGE**. 15 of 27 sections describe the PRD Framework tool instead of the customer support product.

---

### Stage 8: Validation Quality Gate (`ValidationService`)
* **Input Received**: Completed `PRDVersion`.
* **Execution**: Iterates through sections, counts characters, runs regex for `FR-\d+` and `AC-\d+`.
* **Context Loss Mechanism**:
  - Does not evaluate semantic relevance.
  - Does not cross-reference requirements against the initial `raw_idea`.
  - Flags generic words like "fast" and "seamless", but ignores "PRD Framework", "Ollama", "Offline Fallback", "Document Information".
* **Context Status**: **IGNORED**. Grants a near-perfect validation score to heavily corrupted documents.

