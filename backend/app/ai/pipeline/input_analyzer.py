import json
import logging
from typing import Dict, Any, Optional
from app.ai.gateway import AIGatewayInterface
from app.models.analysis import AnalysisRecord, AssignmentRequirement
from app.models.submission import IdeaSubmissionResponse

logger = logging.getLogger(__name__)

INPUT_ANALYZER_PROMPT = """
You are an expert AI Product Architect and Requirements Engineer.
Analyze the following user submission (product idea, problem statement, or assignment) and return a structured JSON object.

Submission Type: {submission_type}
Raw Idea / Context:
{raw_idea}

Problem Statement (if provided):
{problem_statement}

Assignment Context (if provided):
{assignment_context}

Return a valid JSON object matching this schema:
{{
  "product_category": "Short category name",
  "problem_domain": "Domain or industry",
  "intended_users": ["User Role 1", "User Role 2"],
  "core_objectives": ["Objective 1", "Objective 2"],
  "expected_capabilities": ["Capability 1", "Capability 2"],
  "explicit_constraints": ["Constraint 1"],
  "missing_critical_info": ["What critical details are missing?"],
  "facts": ["Confirmed user facts explicitly stated in input"],
  "assumptions": ["Inferred engineering assumptions that require validation"],
  "assignment_requirements": {{
    "instruction": "Summary of assignment instructions",
    "mandatory_sections": ["Section names required by assignment"],
    "deliverables": ["Expected deliverables"],
    "constraints": ["Explicit assignment constraints"],
    "expected_length": "Expected length or scope"
  }}
}}

Important: Distinguish user-provided facts from AI assumptions. Never invent verified facts. Output only valid JSON.
"""

class InputAnalyzer:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def analyze(self, submission: IdeaSubmissionResponse) -> AnalysisRecord:
        prompt = INPUT_ANALYZER_PROMPT.format(
            submission_type=submission.submission_type,
            raw_idea=submission.raw_idea,
            problem_statement=submission.problem_statement or "None provided",
            assignment_context=submission.assignment_context or "None provided"
        )
        
        raw_response = await self.ai.generate(
            prompt=prompt,
            system_instruction="You are an expert Product Requirements Analyst. Return only valid JSON.",
            json_mode=True
        )

        try:
            # Strip potential markdown fences if present
            clean_json = raw_response.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            data = json.loads(clean_json)
            asg_data = data.get("assignment_requirements")
            asg_req = AssignmentRequirement(**asg_data) if asg_data else None

            return AnalysisRecord(
                project_id=submission.project_id,
                product_category=data.get("product_category", "Software Application"),
                problem_domain=data.get("problem_domain", "General Technology"),
                intended_users=data.get("intended_users", ["End Users", "Administrators"]),
                core_objectives=data.get("core_objectives", ["Solve user workflow limitations"]),
                expected_capabilities=data.get("expected_capabilities", []),
                explicit_constraints=data.get("explicit_constraints", []),
                missing_critical_info=data.get("missing_critical_info", []),
                facts=data.get("facts", [submission.raw_idea[:100]]),
                assumptions=data.get("assumptions", []),
                assignment_requirements=asg_req
            )
        except Exception as e:
            logger.error(f"Failed to parse input analysis response: {e}, raw: {raw_response}")
            # Resilient fallback
            return AnalysisRecord(
                project_id=submission.project_id,
                product_category="Software Solution",
                problem_domain="Application Engineering",
                intended_users=["Target Users"],
                core_objectives=["Implement product solution based on user submission"],
                expected_capabilities=["Input processing", "Requirement fulfillment"],
                explicit_constraints=["Run locally"],
                missing_critical_info=[],
                facts=[submission.raw_idea[:120]],
                assumptions=["Standard desktop deployment environment"]
            )

