import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from app.ai.gateway import AIGatewayInterface

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0.0"

PROBLEM_ANALYST_PROMPT = """
You are a Principal Product Strategy Analyst.
Analyze the provided concept and problem statement to derive problem domain, root pain points, current limitations, and target outcomes.

Raw Concept:
{concept}

Problem Statement:
{problem_statement}

Output JSON schema:
{{
  "problem_domain": "Domain or industry name",
  "root_pain_points": ["Pain point 1", "Pain point 2"],
  "current_limitations": ["Current limitation 1", "Current limitation 2"],
  "desired_outcomes": ["Target outcome 1", "Target outcome 2"]
}}
"""

class ProblemAnalystInput(BaseModel):
    concept: str
    problem_statement: Optional[str] = None

class ProblemAnalystOutput(BaseModel):
    problem_domain: str
    root_pain_points: List[str] = Field(default_factory=list)
    current_limitations: List[str] = Field(default_factory=list)
    desired_outcomes: List[str] = Field(default_factory=list)
    prompt_version: str = PROMPT_VERSION

class ProblemAnalyst:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def analyze(self, input_data: ProblemAnalystInput) -> ProblemAnalystOutput:
        prompt = PROBLEM_ANALYST_PROMPT.format(
            concept=input_data.concept,
            problem_statement=input_data.problem_statement or "None explicitly provided"
        )
        raw_response = await self.ai.generate(
            prompt=prompt,
            system_instruction="You are an expert Problem Analyst. Return valid JSON only.",
            json_mode=True
        )

        try:
            clean_json = raw_response.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            data = json.loads(clean_json)
            return ProblemAnalystOutput(
                problem_domain=data.get("problem_domain", "Software Architecture"),
                root_pain_points=data.get("root_pain_points", ["Manual workflow inefficiencies", "Missing requirements"]),
                current_limitations=data.get("current_limitations", ["Lack of local automation", "Fragmented documentation"]),
                desired_outcomes=data.get("desired_outcomes", ["Streamlined local requirement engineering", "Complete PRD delivery"])
            )
        except Exception as e:
            logger.warning(f"Error parsing problem analyst JSON: {e}")
            return ProblemAnalystOutput(
                problem_domain="Software Engineering",
                root_pain_points=["Unstructured concept drafting", "Requirement ambiguity"],
                current_limitations=["Manual document creation"],
                desired_outcomes=["Standardized requirement generation"]
            )
