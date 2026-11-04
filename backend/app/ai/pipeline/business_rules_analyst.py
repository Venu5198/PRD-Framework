import json
import logging
from typing import List
from pydantic import BaseModel, Field
from app.ai.gateway import AIGatewayInterface

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0.0"

class BusinessRuleItem(BaseModel):
    id: str
    title: str
    description: str

class BusinessRulesInput(BaseModel):
    domain: str
    objectives: List[str]
    constraints: List[str]

class BusinessRulesOutput(BaseModel):
    business_rules: List[BusinessRuleItem] = Field(default_factory=list)
    prompt_version: str = PROMPT_VERSION

class BusinessRulesAnalyst:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def extract_rules(self, input_data: BusinessRulesInput) -> BusinessRulesOutput:
        rules = [
            BusinessRuleItem(
                id="BR-001",
                title="Version Immutability Constraint",
                description="Approved PRD versions must remain permanently immutable; modifications must create incremental version snapshots."
            ),
            BusinessRuleItem(
                id="BR-002",
                title="Local Data Sovereignty Invariant",
                description="Zero prompt data, uploaded reference files, or database records shall be transmitted outside the local host boundary."
            ),
            BusinessRuleItem(
                id="BR-003",
                title="Deterministic Validation Enforcement",
                description="PRD approval is blocked if critical structural sections or mandatory acceptance criteria linkages are missing."
            )
        ]
        return BusinessRulesOutput(business_rules=rules)
