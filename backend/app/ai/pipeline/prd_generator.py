import logging
from typing import Dict, Any, Optional
from app.ai.gateway import AIGatewayInterface
from app.models.analysis import AnalysisRecord
from app.models.clarification import ClarificationSession
from app.models.prd import PRDSectionContent, SECTION_TITLES, CANONICAL_SECTIONS

logger = logging.getLogger(__name__)

class PRDGenerator:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def generate_full_prd(
        self,
        project_title: str,
        analysis: AnalysisRecord,
        clarification_session: Optional[ClarificationSession],
        requirements_data: Dict[str, Any]
    ) -> Dict[str, PRDSectionContent]:
        """
        Assembles all 27 canonical PRD sections with full traceability,
        ensuring every section conforms to professional requirements engineering standards.
        """
        frs = requirements_data.get("functional_requirements", [])
        nfrs = requirements_data.get("non_functional_requirements", [])
        brs = requirements_data.get("business_rules", [])
        acs = requirements_data.get("acceptance_criteria", [])

        # Format Functional Requirements
        fr_text = "| ID | Title | Description | Priority | Traceable AC |\n|---|---|---|---|---|\n"
        for item in frs:
            ac_str = ", ".join(item.get("acceptance_criteria_ids", [])) or "AC-Pending"
            fr_text += f"| **{item.get('id')}** | {item.get('title')} | {item.get('description')} | {item.get('priority')} | {ac_str} |\n"

        # Format Non-Functional Requirements
        nfr_text = "| ID | Title | Description | Priority |\n|---|---|---|---|\n"
        for item in nfrs:
            nfr_text += f"| **{item.get('id')}** | {item.get('title')} | {item.get('description')} | {item.get('priority')} |\n"

        # Format Business Rules
        br_text = "| ID | Rule Title | Operational Statement |\n|---|---|---|\n"
        for item in brs:
            br_text += f"| **{item.get('id')}** | {item.get('title')} | {item.get('description')} |\n"

        # Format Acceptance Criteria
        ac_text = "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n|---|---|---|\n"
        for item in acs:
            ac_text += f"| **{item.get('id')}** | {item.get('requirement_id')} | {item.get('statement')} |\n"

        # Generate User Stories derived from FRs
        us_text = "| Story ID | As a... | I want to... | So that... | Linked FR |\n|---|---|---|---|---|\n"
        for idx, item in enumerate(frs):
            us_text += f"| **US-{idx+1:03d}** | User | {item.get('title').lower()} | I achieve expected system outcomes | {item.get('id')} |\n"

        # Construct 27 sections
        sections: Dict[str, PRDSectionContent] = {
            "document_information": PRDSectionContent(
                key="document_information",
                title=SECTION_TITLES["document_information"],
                content=(
                    f"**Document Title:** Product Requirements Document for {project_title}\n\n"
                    f"**Document ID:** PRD-{analysis.project_id[:8].upper()}\n\n"
                    f"**Version:** 1.0 (Draft)\n\n"
                    f"**Target Domain:** {analysis.problem_domain}\n\n"
                    f"**Product Category:** {analysis.product_category}\n\n"
                    f"**Status:** Under Active Review"
                )
            ),
            "executive_summary": PRDSectionContent(
                key="executive_summary",
                title=SECTION_TITLES["executive_summary"],
                content=(
                    f"{project_title} addresses key workflow challenges within {analysis.problem_domain}. "
                    f"This document provides the authoritative engineering specification to implement "
                    f"the complete solution, ensuring local data sovereignty, deterministic execution, and rapid user delivery."
                )
            ),
            "product_overview": PRDSectionContent(
                key="product_overview",
                title=SECTION_TITLES["product_overview"],
                content=(
                    f"### Vision\n"
                    f"To deliver an autonomous, highly reliable system solving core operational pain points in {analysis.product_category}.\n\n"
                    f"### Key Capabilities\n"
                    + "\n".join(f"- {cap}" for cap in (analysis.expected_capabilities or ["Core workflow execution", "Data integrity management"]))
                )
            ),
            "problem_statement": PRDSectionContent(
                key="problem_statement",
                title=SECTION_TITLES["problem_statement"],
                content=(
                    f"Current practitioners in {analysis.problem_domain} experience friction due to manual, fragmented, or error-prone processes.\n\n"
                    f"**Identified Pain Points:**\n"
                    f"- Lack of automated structure and standardization.\n"
                    f"- Missing critical requirements and edge-case handling.\n"
                    f"- Heavy reliance on fragmented or proprietary external toolchains."
                )
            ),
            "product_vision_and_objectives": PRDSectionContent(
                key="product_vision_and_objectives",
                title=SECTION_TITLES["product_vision_and_objectives"],
                content=(
                    f"### Core Objectives\n"
                    + "\n".join(f"{idx+1}. {obj}" for idx, obj in enumerate(analysis.core_objectives))
                )
            ),
            "target_users_and_stakeholders": PRDSectionContent(
                key="target_users_and_stakeholders",
                title=SECTION_TITLES["target_users_and_stakeholders"],
                content=(
                    f"**Primary Stakeholders:**\n"
                    + "\n".join(f"- **{user}:** Primary user interacting with system capabilities." for user in analysis.intended_users)
                )
            ),
            "user_personas": PRDSectionContent(
                key="user_personas",
                title=SECTION_TITLES["user_personas"],
                content=(
                    f"#### Persona 1: Primary Practitioner ({analysis.intended_users[0] if analysis.intended_users else 'Lead Engineer'})\n"
                    f"- **Goals:** Rapidly execute domain workflows with minimal manual boilerplate.\n"
                    f"- **Frustrations:** Incomplete documentation, ambiguous requirements, and manual rework.\n"
                    f"- **Technical Proficiency:** Intermediate to Advanced."
                )
            ),
            "existing_workflow_and_pain_points": PRDSectionContent(
                key="existing_workflow_and_pain_points",
                title=SECTION_TITLES["existing_workflow_and_pain_points"],
                content=(
                    "1. **Manual ideation & drafting:** Practitioners write unstructured notes.\n"
                    "2. **Information gaps:** Crucial architectural constraints and non-functional requirements are forgotten.\n"
                    "3. **Inconsistent documentation:** Hand-offs to engineering teams fail due to missing acceptance criteria."
                )
            ),
            "proposed_solution": PRDSectionContent(
                key="proposed_solution",
                title=SECTION_TITLES["proposed_solution"],
                content=(
                    f"{project_title} introduces an end-to-end automated framework that bridges raw concepts into "
                    f"verified, production-grade requirements. It features structured pipeline processing, "
                    f"interactive clarification, and deterministic quality validation."
                )
            ),
            "product_scope": PRDSectionContent(
                key="product_scope",
                title=SECTION_TITLES["product_scope"],
                content=(
                    "**In-Scope Capabilities for MVP:**\n"
                    "- Complete workflow automation from user input to structured output.\n"
                    "- Local-first execution without external SaaS dependencies.\n"
                    "- Interactive clarification and assumption tracking.\n"
                    "- Deterministic quality validation and scoring.\n"
                    "- Multi-format export (Markdown, PDF, DOCX)."
                )
            ),
            "out_of_scope": PRDSectionContent(
                key="out_of_scope",
                title=SECTION_TITLES["out_of_scope"],
                content=(
                    "**Non-Goals (Out of Scope for Initial Release):**\n"
                    "- Automatic code generation or deployment of arbitrary target applications.\n"
                    "- Third-party cloud SaaS synchronization.\n"
                    "- Automated financial market viability forecasting."
                )
            ),
            "functional_requirements": PRDSectionContent(
                key="functional_requirements",
                title=SECTION_TITLES["functional_requirements"],
                content=fr_text
            ),
            "non_functional_requirements": PRDSectionContent(
                key="non_functional_requirements",
                title=SECTION_TITLES["non_functional_requirements"],
                content=nfr_text
            ),
            "user_stories": PRDSectionContent(
                key="user_stories",
                title=SECTION_TITLES["user_stories"],
                content=us_text
            ),
            "user_journeys": PRDSectionContent(
                key="user_journeys",
                title=SECTION_TITLES["user_journeys"],
                content=(
                    "```mermaid\n"
                    "sequenceDiagram\n"
                    "    actor User\n"
                    "    participant Framework as PRD Framework\n"
                    "    participant Pipeline as AI Processing Pipeline\n"
                    "    participant Validator as Quality Engine\n\n"
                    "    User->>Framework: Submit concept / assignment\n"
                    "    Framework->>Pipeline: Analyze input & identify gaps\n"
                    "    Pipeline-->>User: Clarification questions & assumptions\n"
                    "    User->>Pipeline: Confirm answers / accept defaults\n"
                    "    Pipeline->>Framework: Synthesize 27 canonical sections\n"
                    "    Framework->>Validator: Run deterministic checks\n"
                    "    Validator-->>User: Validation report & quality score\n"
                    "    User->>Framework: Edit/Approve & Export (MD/PDF/DOCX)\n"
                    "```"
                )
            ),
            "business_rules": PRDSectionContent(
                key="business_rules",
                title=SECTION_TITLES["business_rules"],
                content=br_text
            ),
            "system_workflows": PRDSectionContent(
                key="system_workflows",
                title=SECTION_TITLES["system_workflows"],
                content=(
                    "1. **Input Ingestion:** Receive text and attachments; persist raw input record.\n"
                    "2. **Domain Classification:** Parse assignment context or problem domain.\n"
                    "3. **Gap Resolution:** Clarify critical missing attributes or default to documented assumptions.\n"
                    "4. **Requirement Synthesis:** Formulate FRs, NFRs, BRs, and testable ACs.\n"
                    "5. **Audit & Export:** Validate schema, verify ID uniqueness, render document files."
                )
            ),
            "data_requirements": PRDSectionContent(
                key="data_requirements",
                title=SECTION_TITLES["data_requirements"],
                content=(
                    "- **Persistence Model:** Document-oriented collections with immutable version archives.\n"
                    "- **Data Integrity:** Strict foreign key references between requirements, acceptance criteria, and version snapshots.\n"
                    "- **Storage Isolation:** File attachments and exported documents reside in local system storage directories."
                )
            ),
            "integration_requirements": PRDSectionContent(
                key="integration_requirements",
                title=SECTION_TITLES["integration_requirements"],
                content=(
                    "- **Local AI Gateway:** REST communication with local Ollama daemon (`http://localhost:11434`).\n"
                    "- **Offline Fallback Engine:** In-process deterministic execution adapter when external inference engines are unavailable.\n"
                    "- **File Formats:** Direct binary writers for Markdown, DOCX (Office OpenXML), and PDF."
                )
            ),
            "security_and_privacy_requirements": PRDSectionContent(
                key="security_and_privacy_requirements",
                title=SECTION_TITLES["security_and_privacy_requirements"],
                content=(
                    "- **Data Sovereignty:** All telemetry, database records, and prompts remain strictly within the local host boundary.\n"
                    "- **Authentication:** JWT tokens with cryptographic hashing (bcrypt) for local access protection.\n"
                    "- **Input Sanitation:** File uploads are validated and isolated from execution paths."
                )
            ),
            "acceptance_criteria": PRDSectionContent(
                key="acceptance_criteria",
                title=SECTION_TITLES["acceptance_criteria"],
                content=ac_text
            ),
            "dependencies_and_constraints": PRDSectionContent(
                key="dependencies_and_constraints",
                title=SECTION_TITLES["dependencies_and_constraints"],
                content=(
                    "- **Runtime Dependencies:** Python 3.10+, Node.js 18+, MongoDB Community / in-memory instance, Ollama.\n"
                    "- **Hardware Constraints:** Minimum 8GB RAM recommended for local 3B/7B model execution.\n"
                    "- **Zero-Cloud Constraint:** The application must remain fully functional without outbound internet access."
                )
            ),
            "risks_and_mitigation": PRDSectionContent(
                key="risks_and_mitigation",
                title=SECTION_TITLES["risks_and_mitigation"],
                content=(
                    "| Risk | Category | Impact | Mitigation Strategy |\n"
                    "|---|---|---|---|\n"
                    "| Local inference timeout | Performance | High | Asynchronous job execution and fallback offline generation adapter. |\n"
                    "| Hallucinated business facts | Quality | High | Strict boundary separation between confirmed facts and labeled assumptions. |\n"
                    "| Accidental version overwrite | Data Integrity | Critical | Immutable version snapshots; all edits produce incremental versions. |\n"
                    "| Incomplete requirement coverage | Compliance | Medium | Deterministic validation engine flagging missing sections or ACs. |"
                )
            ),
            "assumptions_and_open_questions": PRDSectionContent(
                key="assumptions_and_open_questions",
                title=SECTION_TITLES["assumptions_and_open_questions"],
                content=(
                    "### Documented Assumptions\n"
                    + "\n".join(f"- [Assumed] {ass}" for ass in (analysis.assumptions or ["Standard modern desktop environment"]))
                    + "\n\n### Open Questions for Future Iterations\n"
                    "- Will real-time multi-peer collaboration be required in future versions?\n"
                    "- Is automated sync to issue trackers (Jira/GitHub) desirable in subsequent milestones?"
                )
            ),
            "success_metrics": PRDSectionContent(
                key="success_metrics",
                title=SECTION_TITLES["success_metrics"],
                content=(
                    "- **Document Generation Completeness:** 100% of canonical sections populated or documented as N/A.\n"
                    "- **Traceability Score:** 100% of Functional Requirements linked to at least one testable Acceptance Criterion.\n"
                    "- **Validation Pass Rate:** Zero critical validation errors prior to version approval.\n"
                    "- **Offline Operation:** Zero external network requests initiated during standard execution."
                )
            ),
            "release_considerations": PRDSectionContent(
                key="release_considerations",
                title=SECTION_TITLES["release_considerations"],
                content=(
                    "- **Deployment Formats:** Single-command Docker Compose stack and native local environment scripts.\n"
                    "- **Data Migration:** Automated schema migration hooks on service startup.\n"
                    "- **Backward Compatibility:** Versioned API endpoints under `/api/v1`."
                )
            ),
            "appendix_and_glossary": PRDSectionContent(
                key="appendix_and_glossary",
                title=SECTION_TITLES["appendix_and_glossary"],
                content=(
                    "- **PRD:** Product Requirements Document.\n"
                    "- **FR:** Functional Requirement.\n"
                    "- **NFR:** Non-Functional Requirement.\n"
                    "- **BR:** Business Rule.\n"
                    "- **AC:** Acceptance Criteria.\n"
                    "- **Local-First:** Software architecture prioritizing local execution and data ownership."
                )
            ),
        }

        return sections

