import json
import logging
from typing import Optional, Dict, Any, List
from app.ai.gateway import AIGatewayInterface

logger = logging.getLogger(__name__)

class OfflineMockAdapter(AIGatewayInterface):
    """Deterministic local AI engine used when Ollama is offline or in test environments."""

    async def is_available(self) -> bool:
        return True

    async def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"name": "offline-deterministic-engine", "size": 0, "modified_at": "2026-11-04T00:00:00Z"},
            {"name": "llama3.2:latest (emulated)", "size": 2000000000, "modified_at": "2026-11-04T00:00:00Z"},
            {"name": "mistral:latest (emulated)", "size": 4100000000, "modified_at": "2026-11-04T00:00:00Z"}
        ]

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2
    ) -> str:
        prompt_lower = prompt.lower()

        # 1. Input Analysis stage
        if "analyze the following user submission" in prompt_lower or "input analyzer" in prompt_lower or "classify the following product submission" in prompt_lower:
            return json.dumps({
                "product_category": "Productivity & Developer Tools",
                "problem_domain": "Requirements Engineering Automation",
                "intended_users": ["Product Managers", "Software Engineers", "Technical Founders", "Business Analysts"],
                "core_objectives": ["Automate PRD generation", "Eliminate missing requirements", "Operate strictly local-first"],
                "expected_capabilities": ["Idea ingestion", "Interactive clarification", "Deterministic validation", "Multi-format export"],
                "explicit_constraints": ["No mandatory external cloud APIs", "Run on local desktop hardware", "Preserve audit history"],
                "missing_critical_info": ["Specific performance latency target", "Preferred local model quantization"],
                "facts": ["Input was provided by user", "Local deployment is mandatory"],
                "assumptions": ["Users have modern multicore CPU and minimum 8GB RAM", "Primary export formats are MD, DOCX, and PDF"],
                "assignment_requirements": {
                    "instruction": "Deliver an end-to-end local automated PRD engineering solution",
                    "mandatory_sections": ["Executive Summary", "Functional Requirements", "Non-Functional Requirements", "Validation"],
                    "deliverables": ["Backend service", "Frontend interface", "Export modules", "Docker setup"],
                    "constraints": ["Zero cloud leakage", "Deterministic validation"],
                    "expected_length": "Comprehensive PRD"
                }
            })

        # 1b. Assignment Parser stage
        if "assignment parser" in prompt_lower or "assignment instructions" in prompt_lower:
            return json.dumps({
                "instruction_summary": "Comprehensive PRD conforming to software engineering standards",
                "mandatory_sections": ["Executive Summary", "Functional Requirements", "Non-Functional Requirements", "Security"],
                "deliverables": ["PRD Specification", "Traceability Matrix", "Architecture Diagram"],
                "constraints": ["Zero cloud data transmission", "Deterministic quality checks"],
                "expected_length": "Comprehensive"
            })

        # 2. Clarification stage
        if "principal technical product manager" in prompt_lower or "clarification questions are necessary" in prompt_lower:
            return json.dumps({
                "questions": [
                    {
                        "id": "CQ-001",
                        "priority": "critical",
                        "category": "Target Users & Access",
                        "question": "What is the primary target deployment environment for the end users?",
                        "rationale": "Clarifies whether the product will run single-user on developer workstations or multi-tenant inside a private intranet.",
                        "suggested_options": ["Single-user local workstation", "Team intranet server", "Air-gapped enterprise cluster"]
                    },
                    {
                        "id": "CQ-002",
                        "priority": "medium",
                        "category": "Performance Limits",
                        "question": "What is the acceptable maximum generation latency per section?",
                        "rationale": "Guides choice of model size (3B vs 8B parameters) and whether streaming or batch background jobs are required.",
                        "suggested_options": ["Under 5 seconds per section", "Under 30 seconds per section", "Asynchronous background queue"]
                    },
                    {
                        "id": "CQ-003",
                        "priority": "low",
                        "category": "Document Styling",
                        "question": "Are custom branding templates required for generated PDF and DOCX files?",
                        "rationale": "Determines if custom corporate CSS and header logos must be configurable in MVP.",
                        "suggested_options": ["Standard clean engineering template", "Custom logo and corporate typography"]
                    }
                ]
            })

        # 3. Requirement Engineering stage
        if "lead requirements engineer" in prompt_lower or "generate structured requirements" in prompt_lower or "functional_requirements" in prompt_lower:
            return json.dumps({
                "functional_requirements": [
                    {
                        "id": "FR-001",
                        "title": "Natural Language Input Ingestion",
                        "description": "The system shall ingest raw natural language text representing product ideas, problem statements, or assignment prompts.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-001", "AC-002"]
                    },
                    {
                        "id": "FR-002",
                        "title": "Automated Input Analysis",
                        "description": "The system shall automatically categorize input, extract goals, identify target users, and detect missing information.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-003"]
                    },
                    {
                        "id": "FR-003",
                        "title": "Interactive Clarification Engine",
                        "description": "The system shall generate ranked clarification questions and allow users to supply answers or proceed with documented assumptions.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-004"]
                    },
                    {
                        "id": "FR-004",
                        "title": "Structured PRD Assembly",
                        "description": "The system shall generate a 27-section canonical PRD document with stable requirement identifiers and bidirectional traceability.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-005"]
                    },
                    {
                        "id": "FR-005",
                        "title": "Section-Level In-Place Editing and Regeneration",
                        "description": "The system shall allow users to edit individual sections and trigger AI regeneration with custom guidance.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-006"]
                    },
                    {
                        "id": "FR-006",
                        "title": "Deterministic Quality Validation",
                        "description": "The system shall perform automated structural, ID collision, duplicate, and acceptance criteria completeness verification.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-007"]
                    },
                    {
                        "id": "FR-007",
                        "title": "Multi-Format Export Engine",
                        "description": "The system shall export validated PRDs into Markdown, DOCX, and PDF formats preserving layout and metadata.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-008"]
                    }
                ],
                "non_functional_requirements": [
                    {
                        "id": "NFR-001",
                        "title": "Zero Cloud Data Leakage",
                        "description": "All telemetry, model inference, and persistence must execute strictly within the local host boundary.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-009"]
                    },
                    {
                        "id": "NFR-002",
                        "title": "Graceful Inference Degradation",
                        "description": "If local model inference times out or fails, existing document versions must remain intact without data corruption.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-010"]
                    }
                ],
                "business_rules": [
                    {
                        "id": "BR-001",
                        "title": "Immutable Versioning Rule",
                        "description": "Approved PRD versions cannot be overwritten. Any regeneration or edit must spawn a new incremental version."
                    },
                    {
                        "id": "BR-002",
                        "title": "Explicit Assumption Transparency",
                        "description": "AI must never present inferred details as verified user facts; unverified claims must carry explicit assumption badges."
                    }
                ],
                "acceptance_criteria": [
                    {
                        "id": "AC-001",
                        "requirement_id": "FR-001",
                        "statement": "Given an unstructured text prompt, when submitted, the system persists it and assigns a unique submission record ID."
                    },
                    {
                        "id": "AC-002",
                        "requirement_id": "FR-001",
                        "statement": "Given an uploaded PDF or TXT reference file, when processed, extracted text is attached to the project context."
                    },
                    {
                        "id": "AC-003",
                        "requirement_id": "FR-002",
                        "statement": "Given analyzed input, the system lists at least 1 product category, 2 intended user roles, and distinguishes facts from assumptions."
                    },
                    {
                        "id": "AC-004",
                        "requirement_id": "FR-003",
                        "statement": "Given unanswered clarification questions, the user can choose 'Proceed with assumptions' and continue generation."
                    },
                    {
                        "id": "AC-005",
                        "requirement_id": "FR-004",
                        "statement": "Given generation complete, all 27 canonical sections exist with populated content or documented N/A rationale."
                    },
                    {
                        "id": "AC-006",
                        "requirement_id": "FR-005",
                        "statement": "Given a modified section, saving generates a new minor version (e.g., v1.1) leaving v1.0 unmodified."
                    },
                    {
                        "id": "AC-007",
                        "requirement_id": "FR-006",
                        "statement": "Given a PRD missing acceptance criteria, the validation engine flags an error and outputs remediation recommendations."
                    },
                    {
                        "id": "AC-008",
                        "requirement_id": "FR-007",
                        "statement": "Given an export request, valid downloadable files for MD, DOCX, and PDF are generated on the filesystem."
                    },
                    {
                        "id": "AC-009",
                        "requirement_id": "NFR-001",
                        "statement": "Given a system inspection with network monitoring, zero outbound external calls are initiated."
                    },
                    {
                        "id": "AC-010",
                        "requirement_id": "NFR-002",
                        "statement": "Given an AI timeout error during section regeneration, the previous content of the section remains preserved."
                    }
                ]
            })

        # 4. Section Regeneration / Single section prompt
        if "regenerate section" in prompt_lower or "section content" in prompt_lower:
            return (
                "### Updated Section Analysis\n\n"
                "This section has been regenerated to reflect updated requirements and user guidance.\n"
                "- Enhanced clarity and precision for local-first operations.\n"
                "- Added concrete acceptance verification steps.\n"
                "- Ensured complete bidirectional alignment with project objectives."
            )

        # Default fallback
        if json_mode:
            return json.dumps({"status": "success", "message": "Processed successfully"})
        return "Deterministic response generated based on local requirements specification."
