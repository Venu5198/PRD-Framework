from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class CanonicalProvenance(str, Enum):
    USER_CONFIRMED = "USER_CONFIRMED"
    ASSIGNMENT_REQUIRED = "ASSIGNMENT_REQUIRED"
    SOURCE_SUPPORTED = "SOURCE_SUPPORTED"
    INFERRED = "INFERRED"
    PROPOSED = "PROPOSED"
    UNRESOLVED = "UNRESOLVED"
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"
    # Legacy alias support
    REFERENCE_SUPPORTED = "SOURCE_SUPPORTED"

    @classmethod
    def normalize(cls, val: str) -> "CanonicalProvenance":
        if not val:
            return cls.INFERRED
        clean = str(val).strip().upper()
        if clean in ("CONFIRMED_USER_INPUT", "USER_INPUT", "USER_CONFIRMED"):
            return cls.USER_CONFIRMED
        if clean in ("REFERENCE_SUPPORTED", "SOURCE_SUPPORTED", "DOCUMENT_SUPPORTED"):
            return cls.SOURCE_SUPPORTED
        if clean in ("ASSIGNMENT_REQUIRED", "ASSIGNMENT"):
            return cls.ASSIGNMENT_REQUIRED
        if clean in ("EXTERNAL_REFERENCE", "EXTERNAL"):
            return cls.EXTERNAL_REFERENCE
        if clean in ("PROPOSED", "RECOMMENDED"):
            return cls.PROPOSED
        if clean in ("UNRESOLVED", "OPEN_QUESTION"):
            return cls.UNRESOLVED
        if clean in ("INFERRED", "ASSUMPTION"):
            return cls.INFERRED
        try:
            return cls(clean)
        except ValueError:
            return cls.INFERRED

class PRDStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    BLOCKED = "blocked"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    REJECTED = "rejected"

class ProvenanceEntry(BaseModel):
    statement_id: str
    claim_id: Optional[str] = None
    section_key: str
    section_name: Optional[str] = None
    statement_text: str
    classification: str
    source_document: Optional[str] = "User Submission"
    source_reference: str
    source_excerpt: Optional[str] = None
    source_location: Optional[str] = None
    related_requirement_id: Optional[str] = "N/A"
    verification_result: str = "VERIFIED"
    verification_method: str = "DETERMINISTIC_ENTAILMENT"
    final_disposition: str = "NORMATIVE_BASELINE"
    confidence_or_status: Optional[str] = None
    is_approved_baseline: bool = True

CANONICAL_SECTIONS = [
    "document_information",
    "executive_summary",
    "product_overview",
    "problem_statement",
    "product_vision_and_objectives",
    "target_users_and_stakeholders",
    "user_personas",
    "existing_workflow_and_pain_points",
    "proposed_solution",
    "product_scope",
    "out_of_scope",
    "functional_requirements",
    "non_functional_requirements",
    "user_stories",
    "user_journeys",
    "business_rules",
    "system_workflows",
    "data_requirements",
    "integration_requirements",
    "security_and_privacy_requirements",
    "acceptance_criteria",
    "dependencies_and_constraints",
    "risks_and_mitigation",
    "assumptions_and_open_questions",
    "success_metrics",
    "release_considerations",
    "appendix_and_glossary",
]

SECTION_TITLES = {
    "document_information": "1. Document Information",
    "executive_summary": "2. Executive Summary",
    "product_overview": "3. Product Overview",
    "problem_statement": "4. Problem Statement",
    "product_vision_and_objectives": "5. Product Vision and Objectives",
    "target_users_and_stakeholders": "6. Target Users and Stakeholders",
    "user_personas": "7. User Personas",
    "existing_workflow_and_pain_points": "8. Existing Workflow and Pain Points",
    "proposed_solution": "9. Proposed Solution",
    "product_scope": "10. Product Scope",
    "out_of_scope": "11. Out of Scope",
    "functional_requirements": "12. Functional Requirements",
    "non_functional_requirements": "13. Non-Functional Requirements",
    "user_stories": "14. User Stories",
    "user_journeys": "15. User Journeys",
    "business_rules": "16. Business Rules",
    "system_workflows": "17. System Workflows",
    "data_requirements": "18. Data Requirements",
    "integration_requirements": "19. Integration Requirements",
    "security_and_privacy_requirements": "20. Security and Privacy Requirements",
    "acceptance_criteria": "21. Acceptance Criteria",
    "dependencies_and_constraints": "22. Dependencies and Constraints",
    "risks_and_mitigation": "23. Risks and Mitigation",
    "assumptions_and_open_questions": "24. Assumptions and Open Questions",
    "success_metrics": "25. Success Metrics",
    "release_considerations": "26. Release Considerations",
    "appendix_and_glossary": "27. Appendix and Glossary",
}

class RequirementItem(BaseModel):
    id: str = Field(..., description="e.g. 'FR-001' or 'NFR-001'")
    title: str
    description: str
    priority: str = Field(default="Must Have", description="'Must Have', 'Should Have', 'Could Have'")
    acceptance_criteria_ids: List[str] = Field(default_factory=list)
    source: str = Field(default="user_input")

class PRDSectionContent(BaseModel):
    key: str
    title: str
    content: str
    is_na: bool = False
    na_rationale: Optional[str] = None
    last_modified: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("content", mode="before")
    @classmethod
    def coerce_content_to_str(cls, v: Any) -> str:
        if isinstance(v, list):
            return "\n".join(f"- {item}" if not str(item).startswith("-") else str(item) for item in v)
        elif isinstance(v, dict):
            return "\n".join(f"- **{k}**: {val}" for k, val in v.items())
        return str(v) if v is not None else ""

class PRDVersion(BaseModel):
    id: Optional[str] = None
    prd_id: str
    project_id: str
    version_number: str = "v1.0"
    job_id: Optional[str] = None
    content_hash: Optional[str] = None
    status: str = Field(default="draft", description="'draft', 'approved', 'archived', 'rejected', 'under_review'")
    sections: Dict[str, PRDSectionContent] = Field(default_factory=dict)
    provenance_ledger: List[Dict[str, Any]] = Field(default_factory=list)
    changelog: str = "Initial generation"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"

class PRDDocument(BaseModel):
    id: Optional[str] = None
    project_id: str
    title: str
    current_version_id: Optional[str] = None
    current_version_number: str = "v1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SectionUpdatePayload(BaseModel):
    content: str
    is_na: bool = False
    na_rationale: Optional[str] = None

class SectionRegeneratePayload(BaseModel):
    guidance: Optional[str] = Field(default=None, description="Optional extra prompt/guidance for regeneration")

