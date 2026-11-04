from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ClarificationQuestion(BaseModel):
    id: str
    priority: str = Field(..., description="'critical', 'medium', or 'low'")
    category: str = Field(..., description="e.g. 'Target Users', 'Architecture', 'Workflow', 'Security'")
    question: str
    rationale: str
    suggested_options: List[str] = Field(default_factory=list)
    user_answer: Optional[str] = None
    resolved_as_assumption: bool = False
    documented_assumption: Optional[str] = None

class ClarificationAnswerRequest(BaseModel):
    question_id: str
    answer: Optional[str] = None
    proceed_with_assumption: bool = False

class ClarificationSession(BaseModel):
    id: Optional[str] = None
    project_id: str
    questions: List[ClarificationQuestion] = Field(default_factory=list)
    status: str = Field(default="pending", description="'pending', 'in_progress', 'completed'")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
