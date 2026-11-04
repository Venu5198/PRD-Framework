from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class FactVsAssumption(BaseModel):
    statement: str
    is_user_fact: bool
    confidence: float = 1.0
    source_context: Optional[str] = None

class AssignmentRequirement(BaseModel):
    instruction: str
    mandatory_sections: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    expected_length: Optional[str] = None

class AnalysisRecord(BaseModel):
    id: Optional[str] = None
    project_id: str
    product_category: str
    problem_domain: str
    intended_users: List[str] = Field(default_factory=list)
    core_objectives: List[str] = Field(default_factory=list)
    expected_capabilities: List[str] = Field(default_factory=list)
    explicit_constraints: List[str] = Field(default_factory=list)
    missing_critical_info: List[str] = Field(default_factory=list)
    facts: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    assignment_requirements: Optional[AssignmentRequirement] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

