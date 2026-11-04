from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

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

class PRDVersion(BaseModel):
    id: Optional[str] = None
    prd_id: str
    project_id: str
    version_number: str = "v1.0"
    status: str = Field(default="draft", description="'draft', 'approved', 'archived'")
    sections: Dict[str, PRDSectionContent] = Field(default_factory=dict)
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
