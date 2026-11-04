from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ValidationIssue(BaseModel):
    rule_id: str
    severity: str = Field(..., description="'error', 'warning', 'info'")
    section_key: Optional[str] = None
    title: str
    description: str
    recommendation: str

class ValidationReport(BaseModel):
    id: Optional[str] = None
    prd_version_id: str
    project_id: str
    is_valid: bool
    score: int = Field(..., ge=0, le=100)
    total_issues: int
    error_count: int
    warning_count: int
    info_count: int
    issues: List[ValidationIssue] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

