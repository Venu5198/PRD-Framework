from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class IdeaSubmissionCreate(BaseModel):
    submission_type: str = Field(default="idea", description="'idea', 'problem_statement', 'assignment', or 'hybrid'")
    raw_idea: str = Field(..., min_length=10, description="Unstructured product idea or concept")
    problem_statement: Optional[str] = Field(default=None, description="Problem being solved")
    assignment_context: Optional[str] = Field(default=None, description="Course or client assignment instructions")
    target_audience: Optional[str] = None
    technical_constraints: Optional[str] = None

class IdeaSubmissionResponse(BaseModel):
    id: str
    project_id: str
    submission_type: str
    raw_idea: str
    problem_statement: Optional[str] = None
    assignment_context: Optional[str] = None
    target_audience: Optional[str] = None
    technical_constraints: Optional[str] = None
    file_attachments: List[str] = Field(default_factory=list)
    created_at: datetime
