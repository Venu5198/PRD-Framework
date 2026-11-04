import json
import logging
from typing import List, Optional
from app.ai.gateway import AIGatewayInterface
from app.models.analysis import AnalysisRecord
from app.models.clarification import ClarificationQuestion, ClarificationSession

logger = logging.getLogger(__name__)

CLARIFICATION_PROMPT = """
You are a Principal Technical Product Manager.
Review the following project analysis record and determine if clarification questions are necessary before engineering the full PRD.

Product Category: {product_category}
Problem Domain: {problem_domain}
Core Objectives: {core_objectives}
Intended Users: {intended_users}
Explicit Constraints: {explicit_constraints}
Identified Missing Info: {missing_critical_info}
Assumptions made so far: {assumptions}

Guidelines:
1. Generate between 2 to 4 high-impact questions prioritized by 'critical', 'medium', or 'low'.
2. Avoid asking obvious questions that can be solved with sensible engineering defaults.
3. For each question, provide 2 to 3 practical suggested options.
4. Explain the rationale for why this question impacts the requirements.

Output ONLY valid JSON matching this schema:
{{
  "questions": [
    {{
      "id": "CQ-001",
      "priority": "critical",
      "category": "Target Architecture / Scope / Security / Workflow",
      "question": "The specific question text",
      "rationale": "Why this decision matters for the PRD",
      "suggested_options": ["Option A", "Option B", "Option C"]
    }}
  ]
}}
"""

class ClarificationEngine:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def generate_questions(self, analysis: AnalysisRecord) -> ClarificationSession:
        prompt = CLARIFICATION_PROMPT.format(
            product_category=analysis.product_category,
            problem_domain=analysis.problem_domain,
            core_objectives=", ".join(analysis.core_objectives),
            intended_users=", ".join(analysis.intended_users),
            explicit_constraints=", ".join(analysis.explicit_constraints),
            missing_critical_info=", ".join(analysis.missing_critical_info) or "None identified",
            assumptions=", ".join(analysis.assumptions) or "None identified"
        )

        raw_response = await self.ai.generate(
            prompt=prompt,
            system_instruction="You are an expert Clarification Analyst. Return only valid JSON.",
            json_mode=True
        )

        questions: List[ClarificationQuestion] = []
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
            raw_qs = data.get("questions", [])
            for idx, q in enumerate(raw_qs):
                q_id = q.get("id", f"CQ-{idx+1:03d}")
                questions.append(ClarificationQuestion(
                    id=q_id,
                    priority=q.get("priority", "medium"),
                    category=q.get("category", "Product Scope"),
                    question=q.get("question", "What is the primary constraint?"),
                    rationale=q.get("rationale", "Needed for accurate requirement sizing."),
                    suggested_options=q.get("suggested_options", ["Standard local configuration"]),
                    user_answer=None,
                    resolved_as_assumption=False
                ))
        except Exception as e:
            logger.warning(f"Failed to parse clarification JSON: {e}. Using baseline questions.")
            questions = [
                ClarificationQuestion(
                    id="CQ-001",
                    priority="critical",
                    category="Deployment Environment",
                    question="Will the system run strictly as a single-user desktop tool or as a multi-user local network service?",
                    rationale="Determines session and authentication boundaries.",
                    suggested_options=["Single-user desktop local", "Multi-user local network service"]
                ),
                ClarificationQuestion(
                    id="CQ-002",
                    priority="medium",
                    category="Performance & Model Size",
                    question="What model size should be targeted as the primary inference default (e.g., 3B vs 8B parameters)?",
                    rationale="Defines memory and response latency expectations.",
                    suggested_options=["Lightweight (3B parameters)", "Standard (7B - 8B parameters)"]
                )
            ]

        return ClarificationSession(
            project_id=analysis.project_id,
            questions=questions,
            status="pending" if questions else "completed"
        )
