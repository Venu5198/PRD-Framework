# Professional PRD Engineering v2 — Root Cause Analysis Report

## 1. Executive Summary

This report establishes the verified code-level root causes of framework-specific content leaking into generated PRDs. The investigation confirms that framework leakage is caused by **hardcoded static template logic and silent mock fallback returns across multiple pipeline components**, rather than model hallucination.

The asynchronous job infrastructure, MongoDB persistence, worker daemon, and Ollama adapter boundaries function correctly and must remain intact. The remediation scope for Phase 2 onward is strictly bounded to the AI pipeline components, prompt architecture, and validation service.

---

## 2. Classification of Findings

```
+---------------------------------------------------------------------------------------------------+
|                                      FINDINGS CLASSIFICATION                                      |
+---------------------------------------------------------------------------------------------------+
| CONFIRMED ROOT CAUSES:                                                                            |
|   1. PRDGenerator Static Assembly: 15/27 sections permanently hardcoded to PRD Framework tool    |
|   2. RequirementEngineer Silent Fallback: Swallows JSON parse errors -> returns PRD Framework FRs |
|   3. StakeholderAnalyst Mock Implementation: Hardcodes PRD Framework user journeys (Zero AI)     |
|   4. RiskAnalyst Mock Implementation: Hardcodes local Ollama/MongoDB infrastructure risks (Zero AI)|
|   5. BusinessRulesAnalyst Fallback Contamination: Hardcodes student attendance rules              |
+---------------------------------------------------------------------------------------------------+
| CONTRIBUTING FACTORS:                                                                             |
|   1. ValidationService Blindness: Evaluates only syntax, IDs, and lengths; ignores semantic leaks |
|   2. Test Suite Blind Spots: Unit & E2E tests assert structure (`len == 27`) instead of content   |
|   3. Monolithic Requirement Prompt: Asks 3B model for 25+ complex nested schema items at once     |
|   4. Discarded Upstream Analysis: ProblemAnalyst output is discarded by orchestration service    |
+---------------------------------------------------------------------------------------------------+
| HYPOTHESES:                                                                                       |
|   1. Multi-Stage Section Synthesis: Generating sections in discrete topical waves will prevent    |
|      JSON schema parsing failures and eliminate the need for fallbacks.                           |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Confirmed Root Causes (Code-Level Evidence)

### Confirmed Root Cause 1: Static PRDGenerator Template Hardcoding
* **File Path**: [`backend/app/ai/pipeline/prd_generator.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/prd_generator.py)
* **Class & Function**: `PRDGenerator.generate_full_prd()`
* **Code Location**: Lines 14–318 (specifically lines 130–168, 184–247, 253–273, 285–303)
* **Explanation of Defect**:
  `PRDGenerator` was implemented as a purely static string formatter. Although it accepts an `AIGatewayInterface` instance in its constructor (`self.ai = ai_gateway`), it **never calls `self.ai.generate()` anywhere in `generate_full_prd()`**. Fifteen canonical sections are populated with immutable static strings describing the PRD Framework itself:
  - Section 8: Existing Workflow (Manual ideation, unstructured notes, inconsistent docs)
  - Section 9: Proposed Solution ("introduces an end-to-end automated framework that bridges raw concepts into verified, production-grade requirements...")
  - Section 10: Product Scope ("In-Scope Capabilities for MVP: Complete workflow automation... Local-first execution... Multi-format export...")
  - Section 11: Out of Scope ("Non-Goals: Automatic code generation... SaaS synchronization... financial forecasting")
  - Section 15: User Journeys (Hardcoded Mermaid sequence diagram: `User -> Framework -> Pipeline -> Validator`)
  - Section 17: System Workflows (Input Ingestion -> Domain Classification -> Gap Resolution -> Requirement Synthesis -> Audit & Export)
  - Section 18: Data Requirements (Document-oriented collections, immutable version archives, local file storage)
  - Section 19: Integration Requirements (Local AI Gateway at `http://localhost:11434`, Offline Fallback Engine, MD/DOCX/PDF binary writers)
  - Section 20: Security & Privacy (Data sovereignty, JWT bcrypt auth, file upload sanitation)
  - Section 22: Dependencies & Constraints (Python 3.10+, Node.js 18+, MongoDB, Ollama, 8GB RAM)
  - Section 23: Risks & Mitigation (Local inference timeout, hallucinated facts, version overwrite, validation failure)
  - Section 25: Success Metrics (100% section completeness, 100% FR-AC traceability, offline operation)
  - Section 26: Release Considerations (Single-command Docker Compose stack, versioned API `/api/v1`)
* **Reproduction Evidence**:
  Inspected the live generated customer support document ([`docs/benchmark/generated_customer_support_prd.md`](file:///c:/PRD-Framework/docs/benchmark/generated_customer_support_prd.md)). Every single one of these 15 sections is an exact character-for-character match of the Python string literals in `prd_generator.py`.
* **Recommended Correction**:
  Refactor `PRDGenerator` to dynamically construct section prompts based on `analysis.product_category`, `analysis.core_objectives`, and `analysis.expected_capabilities`, calling the AI engine to author domain-specific content for all narrative, scope, workflow, and architecture sections.

---

### Confirmed Root Cause 2: RequirementEngineer Silent Fallback to Framework Requirements
* **File Path**: [`backend/app/ai/pipeline/requirement_engineer.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/requirement_engineer.py)
* **Class & Function**: `RequirementEngineer.engineer()`
* **Code Location**: Lines 114–166
* **Explanation of Defect**:
  When Ollama generates invalid JSON or output with trailing tokens, `RequirementEngineer` catches the exception (`except Exception as e:`) and silently returns a hardcoded fallback dictionary instead of raising an error or retrying.
  The hardcoded dictionary contains:
  ```python
  "functional_requirements": [
      {
          "id": "FR-001",
          "title": "Natural Language Input Processing",
          "description": "The system shall ingest and parse unstructured user product descriptions.",
          ...
      },
      {
          "id": "FR-002",
          "title": "Automated PRD Synthesis",
          "description": "The system shall synthesize functional and non-functional requirements into a canonical 27-section PRD.",
          ...
      }
  ],
  "non_functional_requirements": [
      {
          "id": "NFR-001",
          "title": "Local Host Confidentiality",
          "description": "All data processing and persistence shall occur strictly on local host storage.",
          ...
      }
  ],
  "business_rules": [
      {
          "id": "BR-001",
          "title": "Immutable Version Tracking",
          "description": "Approved PRD versions shall remain immutable to preserve auditability."
      }
  ],
  "acceptance_criteria": [
      {
          "id": "AC-001",
          "requirement_id": "FR-001",
          "statement": "Given a submitted prompt, when saved, the system creates an identifiable submission record."
      },
      ...
  ]
  ```
  Furthermore, `prd_generator.py:51-57` derives User Stories (`US-001`, `US-002`) directly from these requirements, generating:
  *"As a Customer I want to natural language input processing so that The system shall ingest and parse unstructured user product descriptions."*
* **Reproduction Evidence**:
  Observed directly in `docs/benchmark/generated_customer_support_prd.md:102-126`.
* **Recommended Correction**:
  Eliminate static fallback dictionaries. Enforce strict JSON repair parsing, modularize requirement prompts into smaller chunks (FR, NFR, AC separately), and allow the retry mechanism to regenerate failed sections rather than poisoning the document with framework features.

---

### Confirmed Root Cause 3: StakeholderAnalyst Mock Implementation
* **File Path**: [`backend/app/ai/pipeline/stakeholder_analyst.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/stakeholder_analyst.py)
* **Class & Function**: `StakeholderAnalyst.analyze()`
* **Code Location**: Lines 36–64
* **Explanation of Defect**:
  `StakeholderAnalyst` does not call `self.ai.generate()`. It formats personas using the target user names, but hardcodes their goals and user journey stages:
  - Step 1: "Submit raw concept or assignment text" -> "Persists input, extracts entities, and isolates facts vs assumptions"
  - Step 2: "Review high-impact questions and provide answers..."
  - Step 3: "Inspect generated 27 sections, review deterministic quality score... exports to MD, DOCX, and PDF"
* **Reproduction Evidence**:
  In `docs/benchmark/generated_customer_support_prd.md:64-70`, Persona 1 goals are: *"Rapidly execute domain workflows with minimal manual boilerplate."* and frustrations are: *"Incomplete documentation, ambiguous requirements, and manual rework."*
* **Recommended Correction**:
  Implement dynamic AI prompt in `StakeholderAnalyst` querying Ollama for actual end-user goals, daily tasks, pain points, and product interaction steps tailored to the target domain.

---

### Confirmed Root Cause 4: RiskAnalyst Mock Implementation
* **File Path**: [`backend/app/ai/pipeline/risk_analyst.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/risk_analyst.py)
* **Class & Function**: `RiskAnalyst.analyze_risks()`
* **Code Location**: Lines 32–67
* **Explanation of Defect**:
  `RiskAnalyst` never invokes AI inference. It returns four static risks explicitly describing the PRD Framework:
  - `RSK-001`: Local Model Resource Exhaustion (mitigated by fallback adapter and timeouts)
  - `RSK-002`: AI Hallucination of Verification Evidence (mitigated by fact/assumption badges)
  - `RSK-003`: Local Storage Tampering or Traversal (mitigated by upload sanitization)
  - `RSK-004`: Ollama Daemon Unavailability (mitigated by offline engine)
* **Reproduction Evidence**:
  In `docs/benchmark/generated_customer_support_prd.md:210-216`, the risk table contains these four framework risks verbatim.
* **Recommended Correction**:
  Connect `RiskAnalyst` to the AI gateway, passing product capabilities and domain to extract real product risks (e.g., data privacy breach, automated response hallucination, agent routing failure).

---

### Confirmed Root Cause 5: BusinessRulesAnalyst Fallback Contamination
* **File Path**: [`backend/app/ai/pipeline/business_rules_analyst.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/business_rules_analyst.py)
* **Class & Function**: `BusinessRulesAnalyst.extract_rules()`
* **Code Location**: Lines 70–98
* **Explanation of Defect**:
  When AI extraction fails or produces fewer than 4 rules, lines 70–98 return five hardcoded student attendance tracking rules:
  - `BR-001`: "Strict Attendance Window Restriction" (lecture windows + 5-minute grace period)
  - `BR-002`: "Proxy Detection and Single Device Binding" (student account duplicate device flag)
  - `BR-003`: "Immutable Attendance Record History" (faculty authorization required for corrections)
  - `BR-004`: "Local Data Sovereignty and Biometric Privacy Invariant" (facial biometric templates)
  - `BR-005`: "Offline Synchronization Conflict Resolution" (offline attendance logs sync within 24h)
* **Reproduction Evidence**:
  Identified in source code review. If fallback triggers, a healthcare, e-commerce, or customer support PRD receives student lecture attendance rules.
* **Recommended Correction**:
  Replace static attendance fallback with a domain-driven fallback generator that derives baseline business invariants directly from `input_data.domain` and `input_data.objectives`.

---

## 4. Contributing Factors

### Contributing Factor 1: ValidationService Semantic Blindness
* **File Path**: [`backend/app/services/validation_service.py`](file:///c:/PRD-Framework/backend/app/services/validation_service.py)
* **Explanation**:
  `ValidationService` validates strictly syntactic properties (string lengths $\ge 15$ or $\ge 20$, presence of `FR-\d+` and `AC-\d+` regexes, absence of generic words like "seamless"). It performs zero semantic checks, zero concept cross-referencing, and zero forbidden keyword validation.
  Consequently, a document composed entirely of leaked framework boilerplate passes with a **95–100% score**.

### Contributing Factor 2: Purely Structural Test Assertions
* **Files**: `backend/tests/test_components.py`, `backend/tests/test_pipeline.py`, `backend/tests/test_api.py`
* **Explanation**:
  The existing test suite contains zero assertions regarding document domain content:
  - `test_risk_analyst`: Asserts `len(res.risks) == 4` (passes on framework risks).
  - `test_stakeholder_analyst`: Asserts `len(res.personas) > 0` (passes on framework personas).
  - `test_requirement_engineer_and_prd_assembly`: Asserts `len(sections) == 27` (passes on framework boilerplate).
  No automated test failed when framework content leaked, preventing CI/CD detection.

### Contributing Factor 3: Monolithic Requirement Prompt Complexity
* **File Path**: [`backend/app/ai/pipeline/requirement_engineer.py`](file:///c:/PRD-Framework/backend/app/ai/pipeline/requirement_engineer.py)
* **Explanation**:
  `REQUIREMENT_PROMPT` asks a 3B local model (`llama3.2`) to output a single monolithic JSON payload containing 6 FRs, 4 NFRs, 5 BRs, and 10 ACs with cross-referencing arrays. Small quantized models frequently produce slight syntax defects on payloads of this size, triggering the `except Exception:` block and causing the silent fallback to execute.

---

## 5. Architectural Weaknesses

1. **Illusion of AI Inference**: 3 of the 10 pipeline components (`PRDGenerator`, `StakeholderAnalyst`, `RiskAnalyst`) take an `AIGateway` in their constructors but never invoke it, acting as decorative facades over static text.
2. **Fragile Exception Handling**: Components catch broad `Exception` and substitute hardcoded mock dictionaries rather than retrying, repairing JSON, or surfacing errors to the user.
3. **Template Scaffolding Pervasiveness**: The framework author wrote an internal PRD for the PRD Framework and used that exact text as the default template across the pipeline.

---

## 6. Recommended Phase 2 Implementation Roadmap

1. **Step 1: AI-Powered Section Generator (`PRDGenerator` overhaul)**
   - Replace static string dictionaries with dynamic AI section generation.
   - Group the 27 sections into topical synthesis prompts (Context & Problem, Scope & Strategy, System Architecture & Workflows, Risk & Lifecycle).
2. **Step 2: Connect Mock Components to Real AI Gateway**
   - Connect `StakeholderAnalyst` and `RiskAnalyst` to `ai_gateway.generate()`.
   - Remove hardcoded attendance rules from `BusinessRulesAnalyst`.
3. **Step 3: Robust Modular Requirement Synthesis**
   - Split `RequirementEngineer` into separate calls: Functional Requirements, Non-Functional Requirements, and Acceptance Criteria.
   - Implement robust JSON parsing with regex extractors. Remove hardcoded fallback requirements.
4. **Step 4: Semantic Anti-Leakage Quality Gates in `ValidationService`**
   - Add forbidden keyword checks ("PRD Framework", "Ollama", "Offline Fallback", "Attendance Window").
   - Add concept alignment checks verifying that the problem domain appears across functional requirements.
5. **Step 5: Semantic Content Regression Test Suite**
   - Add unit and E2E regression tests verifying that a Customer Support concept produces customer support requirements and zero framework boilerplate.

