import json
import logging
from typing import List
from pydantic import BaseModel, Field
from app.ai.gateway import AIGatewayInterface

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0.0"

class PersonaProfile(BaseModel):
    role_name: str
    primary_goals: List[str]
    frustrations: List[str]
    technical_proficiency: str = "Intermediate"

class UserJourneyStep(BaseModel):
    stage_name: str
    actor_action: str
    system_response: str

class StakeholderAnalystInput(BaseModel):
    product_category: str
    intended_users: List[str]
    domain: str

class StakeholderAnalystOutput(BaseModel):
    personas: List[PersonaProfile] = Field(default_factory=list)
    user_journeys: List[UserJourneyStep] = Field(default_factory=list)
    prompt_version: str = PROMPT_VERSION

class StakeholderAnalyst:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def analyze(self, input_data: StakeholderAnalystInput) -> StakeholderAnalystOutput:
        users_str = ", ".join(input_data.intended_users) or "Software Developers, Product Managers"
        personas = [
            PersonaProfile(
                role_name=user,
                primary_goals=["Accelerate requirement definition", "Ensure complete edge case coverage"],
                frustrations=["Unclear expectations", "Manual documentation rework"],
                technical_proficiency="Intermediate to Advanced"
            )
            for user in input_data.intended_users[:3]
        ]
        journeys = [
            UserJourneyStep(
                stage_name="1. Inception",
                actor_action="Submit raw concept or assignment text",
                system_response="Persists input, extracts entities, and isolates facts vs assumptions"
            ),
            UserJourneyStep(
                stage_name="2. Clarification",
                actor_action="Review high-impact questions and provide answers or accept assumptions",
                system_response="Updates analytical model with confirmed parameters"
            ),
            UserJourneyStep(
                stage_name="3. PRD Generation & Review",
                actor_action="Inspect generated 27 sections, review deterministic quality score, edit sections",
                system_response="Saves immutable version snapshots and exports to MD, DOCX, and PDF"
            )
        ]
        return StakeholderAnalystOutput(personas=personas, user_journeys=journeys)

