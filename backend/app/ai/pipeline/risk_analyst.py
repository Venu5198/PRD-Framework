import json
import logging
from typing import List
from pydantic import BaseModel, Field
from app.ai.gateway import AIGatewayInterface

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0.0"

class RiskItem(BaseModel):
    id: str
    category: str  # Technical, Operational, Security, Dependency
    title: str
    impact: str    # High, Medium, Low
    probability: str  # High, Medium, Low
    mitigation_strategy: str

class RiskAnalystInput(BaseModel):
    problem_domain: str
    capabilities: List[str]
    constraints: List[str]

class RiskAnalystOutput(BaseModel):
    risks: List[RiskItem] = Field(default_factory=list)
    prompt_version: str = PROMPT_VERSION

class RiskAnalyst:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def analyze_risks(self, input_data: RiskAnalystInput) -> RiskAnalystOutput:
        risks = [
            RiskItem(
                id="RSK-001",
                category="Technical",
                title="Local Model Resource Exhaustion",
                impact="High",
                probability="Medium",
                mitigation_strategy="Implement in-process deterministic fallback adapter and asynchronous generation timeouts."
            ),
            RiskItem(
                id="RSK-002",
                category="Quality",
                title="AI Hallucination of Verification Evidence",
                impact="High",
                probability="Medium",
                mitigation_strategy="Strict separation of confirmed facts from inferred assumptions with mandatory badges."
            ),
            RiskItem(
                id="RSK-003",
                category="Security",
                title="Local Storage Tampering or Traversal",
                impact="Medium",
                probability="Low",
                mitigation_strategy="Sanitize file upload destinations, restrict allowed extensions, and enforce path resolution boundaries."
            ),
            RiskItem(
                id="RSK-004",
                category="Dependency",
                title="Ollama Daemon Unavailability",
                impact="High",
                probability="Medium",
                mitigation_strategy="Automatic fallback to local deterministic offline engine with clear status reporting."
            )
        ]
        return RiskAnalystOutput(risks=risks)
