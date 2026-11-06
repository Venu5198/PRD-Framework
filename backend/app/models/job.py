from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Job(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    project_id: str
    submission_id: Optional[str] = None
    job_type: str = "prd_generation"
    status: str = JobStatus.QUEUED
    current_stage: str = "queued"
    completed_stages: List[str] = Field(default_factory=list)
    total_stages: int = 6
    progress_metadata: Dict[str, Any] = Field(default_factory=dict)
    provider: str = "ollama"
    model: str = "llama3.2"
    force_mock: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    heartbeat_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    retry_count: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    result_reference: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    project_id: str
    job_type: str
    status: str
    current_stage: str
    completed_stages: List[str]
    total_stages: int
    progress_metadata: Dict[str, Any]
    provider: str
    model: str
    force_mock: bool
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    elapsed_seconds: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    result_reference: Optional[str] = None

class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    message: str
    is_existing: bool = False
