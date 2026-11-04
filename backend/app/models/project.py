from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProjectBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    target_domain: Optional[str] = "General Software"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_domain: Optional[str] = None
    active_prd_id: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    owner_id: str
    active_prd_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

