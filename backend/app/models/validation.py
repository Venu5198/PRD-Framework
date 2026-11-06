from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from app.models.prd import CanonicalProvenance

class EntailmentOutcome(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    AMBIGUOUS = "AMBIGUOUS"

class ClaimModel(BaseModel):
    claim_id: str
    statement_text: str
    section_key: str
    source_type: str = "user_submission"
    source_document: Optional[str] = "User Submission"
    source_fingerprint: Optional[str] = None
    source_excerpt: Optional[str] = None
    source_offset: Optional[int] = None
    provenance: str = CanonicalProvenance.USER_CONFIRMED.value
    entailment_outcome: str = EntailmentOutcome.SUPPORTED.value
    adjudication_status: str = "ADJUDICATED"
    related_requirement_ids: List[str] = Field(default_factory=list)

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
    verdict: str = "APPROVED"  # "APPROVED" or "REJECTED"
    score: int = Field(..., ge=0, le=100)
    total_issues: int
    error_count: int
    warning_count: int
    info_count: int
    issues: List[ValidationIssue] = Field(default_factory=list)
    claims: List[ClaimModel] = Field(default_factory=list)
    total_claims: int = 0
    supported_claims: int = 0
    partially_supported_claims: int = 0
    contradicted_claims: int = 0
    unsupported_claims: int = 0
    ambiguous_claims: int = 0
    unresolved_high_severity_findings: int = 0
    structural_errors: int = 0
    cross_section_conflicts: int = 0
    export_integrity_status: str = "VERIFIED"
    category_summaries: Dict[str, int] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

