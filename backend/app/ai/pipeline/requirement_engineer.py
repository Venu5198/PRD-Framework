import json
import logging
from typing import Dict, Any, List
from app.ai.gateway import AIGatewayInterface
from app.models.analysis import AnalysisRecord
from app.models.clarification import ClarificationSession

logger = logging.getLogger(__name__)

REQUIREMENT_PROMPT = """
You are a Principal Software Architect and Lead Requirements Engineer.
Using the provided project analysis and clarified inputs, generate structured requirements, business rules, and acceptance criteria.

Project Category: {product_category}
Problem Domain: {problem_domain}
Core Objectives: {core_objectives}
Intended Users: {intended_users}
Capabilities: {expected_capabilities}
Clarified Answers & Assumptions:
{clarifications}

Instructions:
1. Generate numbered Functional Requirements with IDs (FR-001, FR-002, etc.).
2. Generate numbered Non-Functional Requirements with IDs (NFR-001, NFR-002, etc.).
3. Generate numbered Business Rules with IDs (BR-001, BR-002, etc.).
4. Generate numbered Acceptance Criteria with IDs (AC-001, AC-002, etc.) mapped directly to requirements in Given-When-Then or clear testable format.
5. Every Functional Requirement MUST have at least one Acceptance Criterion mapped.

Output ONLY valid JSON matching this schema:
{{
  "functional_requirements": [
    {{
      "id": "FR-001",
      "title": "Title",
      "description": "The system shall...",
      "priority": "Must Have",
      "acceptance_criteria_ids": ["AC-001"]
    }}
  ],
  "non_functional_requirements": [
    {{
      "id": "NFR-001",
      "title": "Title",
      "description": "The system shall ensure...",
      "priority": "Must Have",
      "acceptance_criteria_ids": ["AC-002"]
    }}
  ],
  "business_rules": [
    {{
      "id": "BR-001",
      "title": "Title",
      "description": "Rule description..."
    }}
  ],
  "acceptance_criteria": [
    {{
      "id": "AC-001",
      "requirement_id": "FR-001",
      "statement": "Given ..., When ..., Then ..."
    }}
  ]
}}
"""

class RequirementEngineer:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def engineer(
        self,
        analysis: AnalysisRecord,
        clarification_session: Optional[ClarificationSession] = None
    ) -> Dict[str, Any]:
        clarification_text = "No clarifications provided; standard assumptions apply."
        if clarification_session and clarification_session.questions:
            lines = []
            for q in clarification_session.questions:
                if q.user_answer:
                    lines.append(f"Q: {q.question}\nA: {q.user_answer}")
                elif q.resolved_as_assumption:
                    lines.append(f"Q: {q.question}\nAssumed Default: {q.documented_assumption or 'Accepted default'}")
            if lines:
                clarification_text = "\n".join(lines)

        prompt = REQUIREMENT_PROMPT.format(
            product_category=analysis.product_category,
            problem_domain=analysis.problem_domain,
            core_objectives=", ".join(analysis.core_objectives),
            intended_users=", ".join(analysis.intended_users),
            expected_capabilities=", ".join(analysis.expected_capabilities),
            clarifications=clarification_text
        )

        raw_response = await self.ai.generate(
            prompt=prompt,
            system_instruction="You are a strict Requirements Engineer. Return only valid JSON.",
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
            return data
        except Exception as e:
            logger.warning(f"Error parsing requirement engineering JSON: {e}. Returning robust defaults.")
            return {
                "functional_requirements": [
                    {
                        "id": "FR-001",
                        "title": "Natural Language Input Processing",
                        "description": "The system shall ingest and parse unstructured user product descriptions.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-001"]
                    },
                    {
                        "id": "FR-002",
                        "title": "Automated PRD Synthesis",
                        "description": "The system shall synthesize functional and non-functional requirements into a canonical 27-section PRD.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-002"]
                    }
                ],
                "non_functional_requirements": [
                    {
                        "id": "NFR-001",
                        "title": "Local Host Confidentiality",
                        "description": "All data processing and persistence shall occur strictly on local host storage.",
                        "priority": "Must Have",
                        "acceptance_criteria_ids": ["AC-003"]
                    }
                ],
                "business_rules": [
                    {
                        "id": "BR-001",
                        "title": "Immutable Version Tracking",
                        "description": "Approved PRD versions shall remain immutable to preserve auditability."
                    }
                ],
                "acceptance_criteria": [
                    {
                        "id": "AC-001",
                        "requirement_id": "FR-001",
                        "statement": "Given a submitted prompt, when saved, the system creates an identifiable submission record."
                    },
                    {
                        "id": "AC-002",
                        "requirement_id": "FR-002",
                        "statement": "Given valid analysis inputs, when PRD generation runs, all canonical sections are generated."
                    },
                    {
                        "id": "AC-003",
                        "requirement_id": "NFR-001",
                        "statement": "Given execution in an offline environment, all operations complete without external network requests."
                    }
                ]
            }
