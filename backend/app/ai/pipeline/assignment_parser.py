import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from app.ai.gateway import AIGatewayInterface

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0.0"

ASSIGNMENT_PARSER_PROMPT = """
You are a Senior Academic and Enterprise Technical Specification Analyst.
Analyze the provided assignment instructions or RFP requirements.

Assignment Text:
{assignment_text}

Extract and structure requirements into valid JSON:
{{
  "instruction_summary": "High-level summary of assignment instructions",
  "mandatory_sections": ["Required section 1", "Required section 2"],
  "deliverables": ["Deliverable 1", "Deliverable 2"],
  "constraints": ["Constraint 1", "Constraint 2"],
  "expected_length": "e.g. 5-10 pages or comprehensive"
}}
"""

class AssignmentParserInput(BaseModel):
    assignment_text: str

class AssignmentParserOutput(BaseModel):
    instruction_summary: str
    mandatory_sections: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    expected_length: Optional[str] = "Comprehensive"
    prompt_version: str = PROMPT_VERSION

class AssignmentParser:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def parse(self, input_data: AssignmentParserInput) -> AssignmentParserOutput:
        if not input_data.assignment_text or not input_data.assignment_text.strip():
            return AssignmentParserOutput(
                instruction_summary="No specific assignment guidelines provided.",
                mandatory_sections=["Executive Summary", "Functional Requirements", "Non-Functional Requirements"],
                deliverables=["PRD Document", "Architecture Specification"],
                constraints=["Local execution", "Zero external cloud telemetry"]
            )

        prompt = ASSIGNMENT_PARSER_PROMPT.format(assignment_text=input_data.assignment_text)
        raw_response = await self.ai.generate(
            prompt=prompt,
            system_instruction="You are an expert Assignment Parser. Return JSON only.",
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
            return AssignmentParserOutput(
                instruction_summary=data.get("instruction_summary", "Parsed assignment"),
                mandatory_sections=data.get("mandatory_sections", []),
                deliverables=data.get("deliverables", []),
                constraints=data.get("constraints", []),
                expected_length=data.get("expected_length", "Standard PRD")
            )
        except Exception as e:
            logger.warning(f"Error parsing assignment JSON: {e}")
            return AssignmentParserOutput(
                instruction_summary=input_data.assignment_text[:120],
                mandatory_sections=["Product Scope", "Functional Requirements", "Acceptance Criteria"],
                deliverables=["PRD Export in Markdown, DOCX, and PDF"],
                constraints=["Local execution"]
            )

