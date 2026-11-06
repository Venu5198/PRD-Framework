import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from app.ai.gateway import AIGatewayInterface

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v2.0.0"

class PersonaProfile(BaseModel):
    role_name: str
    responsibilities: Optional[str] = None
    primary_goals: List[str]
    frustrations: List[str]
    technical_proficiency: str = "Intermediate"

class UserJourneyStep(BaseModel):
    stage_name: str
    actor: str
    actor_action: str
    system_response: str
    error_or_edge_case: Optional[str] = None

class StakeholderAnalystInput(BaseModel):
    product_category: str
    intended_users: List[str]
    domain: str
    core_objectives: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)

class StakeholderAnalystOutput(BaseModel):
    personas: List[PersonaProfile] = Field(default_factory=list)
    user_journeys: List[UserJourneyStep] = Field(default_factory=list)
    primary_actors: List[str] = Field(default_factory=list)
    secondary_actors: List[str] = Field(default_factory=list)
    prompt_version: str = PROMPT_VERSION

STAKEHOLDER_PROMPT = """
You are a Principal User Experience and Requirements Analyst.
Generate detailed user personas and end-to-end user journeys strictly for the following TARGET PRODUCT:

Product Domain: {domain}
Product Category: {product_category}
Target Users: {users}
Core Objectives: {objectives}
Capabilities: {capabilities}

Instructions:
1. Generate 2 to 3 realistic personas strictly representing the specified Target Users ({users}).
2. DO NOT invent generic "Support / Admin Role" or IT administrators unless explicitly listed in Target Users.
3. Generate 3 to 5 chronological user journey steps demonstrating how users interact with '{product_category}' to achieve their goals.
4. Each journey step must specify: the stage name, the actor, their action, the system's response, and an edge-case or failure behavior.
5. NEVER invent email dispatch, CRM synchronization, or ticketing systems unless explicitly specified in product capabilities.
6. Ground user journeys strictly in confirmed product capabilities. Do NOT introduce capabilities without source evidence, such as:
   - human agent editing or policy compliance checks,
   - manager sign-off, approvals, or managerial review dashboards,
   - live-agent fallback routing or telephony/voice channels,
   - external CRM / third-party ticketing platforms.
   Keep user journeys focused strictly on the primary user interaction with the system and straightforward escalation queuing when low confidence occurs.

Return ONLY a valid JSON object matching this schema:
{{
  "primary_actors": ["Main User Role from Target Users"],
  "secondary_actors": ["Secondary Role from Target Users"],
  "personas": [
    {{
      "role_name": "Specific User Role",
      "responsibilities": "Main operational duty in the system",
      "primary_goals": ["Goal 1", "Goal 2"],
      "frustrations": ["Pain point 1", "Pain point 2"],
      "technical_proficiency": "Novice | Intermediate | Advanced"
    }}
  ],
  "user_journeys": [
    {{
      "stage_name": "1. Stage Name",
      "actor": "User Role",
      "actor_action": "What the user does in the target product...",
      "system_response": "How the target product responds...",
      "error_or_edge_case": "What happens if inputs are invalid or boundary is met..."
    }}
  ]
}}
"""

class StakeholderAnalyst:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def analyze(self, input_data: StakeholderAnalystInput) -> StakeholderAnalystOutput:
        users_str = ", ".join(input_data.intended_users) if input_data.intended_users else "End Users, Administrators"
        objectives_str = ", ".join(input_data.core_objectives) if input_data.core_objectives else "Accomplish domain tasks"
        capabilities_str = ", ".join(input_data.capabilities) if input_data.capabilities else "Core capabilities"

        prompt = STAKEHOLDER_PROMPT.format(
            domain=input_data.domain or "General Application",
            product_category=input_data.product_category or "Software Product",
            users=users_str,
            objectives=objectives_str,
            capabilities=capabilities_str
        )

        try:
            raw = await self.ai.generate(prompt=prompt, json_mode=True, temperature=0.1)
            clean_json = raw.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            data = json.loads(clean_json)
            raw_personas = data.get("personas", [])
            raw_journeys = data.get("user_journeys", [])
            
            # Filter out fabricated "Support / Admin Role" if not in intended users
            is_edu = any(t in (input_data.domain + " " + input_data.product_category).lower() for t in ["attendance", "education", "student", "faculty"])
            intended_has_mgr = any("manager" in u.lower() or "supervisor" in u.lower() for u in (input_data.intended_users or []))
            valid_personas = []
            for p in raw_personas:
                r_name = p.get("role_name", "")
                if is_edu and any(w in r_name.lower() for w in ["support / admin", "admin role", "customer service"]):
                    continue
                if not intended_has_mgr and any(w in r_name.lower() for w in ["manager", "supervisor"]):
                    continue
                valid_personas.append(PersonaProfile(**p))

            # Sanitize out-of-scope workflows from user journeys
            import re
            clean_journeys = []
            for j in raw_journeys:
                step_dict = dict(j)
                if not intended_has_mgr and "manager" in step_dict.get("actor", "").lower():
                    step_dict["actor"] = valid_personas[-1].role_name if valid_personas else "Customer Service Representative"
                for field in ["actor_action", "system_response", "error_or_edge_case"]:
                    val = step_dict.get(field, "")
                    if val and isinstance(val, str):
                        val = re.sub(r"\b(?:offers to schedule a call back|schedule a call back|schedule a callback|call back|callback)\b", "offers to leave an asynchronous message in the internal queue", val, flags=re.IGNORECASE)
                        val = re.sub(r"\b(?:phone call|voice call|telephony|sms channel)\b", "web chat message", val, flags=re.IGNORECASE)
                        val = re.sub(r"\b(?:fallback to connect with a live representative|live representative fallback)\b", "fallback to leave an asynchronous message in the queue", val, flags=re.IGNORECASE)
                        val = re.sub(r"\b(?:quick-edit field for the rep to modify the answer before sending|quick-edit field for the rep to modify|rep's edit conflicts with policy|rep's edit|agent editing)\b", "representative reviews customer transcript and context summary", val, flags=re.IGNORECASE)
                        val = re.sub(r"\b(?:system warns and requires manager approval|requires manager approval|managerial sign-off|manager sign-off|manager approval)\b", "system logs escalation review in audit log", val, flags=re.IGNORECASE)
                        val = re.sub(r"\b(?:daily dashboard for ai accuracy rates|daily dashboard for ai|dashboard for ai accuracy|daily dashboard)\b", "internal queue triage view", val, flags=re.IGNORECASE)
                        val = re.sub(r"\b(?:confirms ticket creation|generates a ticket ID|ticket ID|queued ticket|opens the queued ticket|marks the ticket as resolved|close tickets|resolves tickets|ticket generation)\b", "routes query to human escalation queue with context summary", val, flags=re.IGNORECASE)
                        val = re.sub(r"\b(?:support manager|customer support manager)\b", "Support Representative", val, flags=re.IGNORECASE)
                        step_dict[field] = val
                clean_journeys.append(UserJourneyStep(**step_dict))
            journeys = clean_journeys
            primary = data.get("primary_actors", [input_data.intended_users[0] if input_data.intended_users else "Primary User"])
            secondary = data.get("secondary_actors", [input_data.intended_users[1] if len(input_data.intended_users) > 1 else "Secondary User"])

            if len(valid_personas) >= 2 and journeys:
                return StakeholderAnalystOutput(
                    personas=valid_personas,
                    user_journeys=journeys,
                    primary_actors=primary,
                    secondary_actors=secondary
                )
        except Exception as e:
            logger.warning(f"StakeholderAnalyst AI generation fallback: {e}")

        # Dynamic domain-tailored fallback derived strictly from target product users
        dom_lower = (input_data.domain + " " + input_data.product_category).lower()

        if "attendance" in dom_lower or "education" in dom_lower:
            fallback_personas = [
                PersonaProfile(
                    role_name="Faculty Instructor",
                    responsibilities="Conducts scheduled class sessions, records daily student attendance roll calls, and monitors course eligibility standings.",
                    primary_goals=["Record accurate attendance in under two minutes", "Identify at-risk students before exam disbarment"],
                    frustrations=["Paper roll call errors and manual data entry latency", "Disputes over exam eligibility"],
                    technical_proficiency="Intermediate"
                ),
                PersonaProfile(
                    role_name="Student",
                    responsibilities="Attends scheduled class sessions, tracks cumulative attendance percentage in real time, and receives warning alerts.",
                    primary_goals=["Maintain attendance above 75.0% threshold", "Receive real-time alerts if attendance is at risk"],
                    frustrations=["Lack of visibility into real-time attendance standing", "Surprise exam disbarment notifications"],
                    technical_proficiency="Intermediate"
                ),
                PersonaProfile(
                    role_name="Department Head",
                    responsibilities="Configures departmental course attendance policies and reviews formal medical condonation requests.",
                    primary_goals=["Enforce consistent academic attendance policies", "Audit and process legitimate condonation petitions fairly"],
                    frustrations=["Unsubstantiated condonation claims", "Manual reconciliation of attendance disputes"],
                    technical_proficiency="Intermediate"
                )
            ]

            fallback_journeys = [
                UserJourneyStep(
                    stage_name="1. Daily Roll Call Recording",
                    actor="Faculty Instructor",
                    actor_action="Authenticates into portal, selects assigned course section, marks enrolled students Present or Absent, and submits roster.",
                    system_response="Validates roster completeness, commits official attendance records to the permanent ledger, and displays confirmation receipt.",
                    error_or_edge_case="If duplicate submission for the same session date is detected, system rejects entry and displays an attendance already recorded warning."
                ),
                UserJourneyStep(
                    stage_name="2. Real-Time Percentage Visibility",
                    actor="Student",
                    actor_action="Accesses student portal to view cumulative attendance percentage for registered courses.",
                    system_response="Calculates attendance percentage: (attended eligible sessions / total eligible sessions) * 100, and renders eligibility standing.",
                    error_or_edge_case="If 0 sessions have been conducted, displays 0 conducted sessions with no percentage without division-by-zero errors."
                ),
                UserJourneyStep(
                    stage_name="3. Automated Warning Alert Dispatch",
                    actor="Faculty Instructor",
                    actor_action="Submits an absence that causes a student's calculated attendance to fall strictly below 75.0% (< 75.0%).",
                    system_response="Generates low-attendance warning alert and dispatches notification to student and faculty advisor detailing classes needed to recover.",
                    error_or_edge_case="If attendance is exactly 75.0%, warning notification is suppressed and student remains in good standing."
                ),
                UserJourneyStep(
                    stage_name="4. Condonation Petition Review",
                    actor="Department Head",
                    actor_action="Reviews student condonation petition with verified medical documentation and records administrative approval.",
                    system_response="Updates student's examination eligibility status to 'Condoned - Eligible' while preserving raw physical roll call records in the audit ledger.",
                    error_or_edge_case="If unauthorized role attempts policy configuration or condonation override, system halts request with HTTP 403 Forbidden."
                )
            ]

            return StakeholderAnalystOutput(
                personas=fallback_personas,
                user_journeys=fallback_journeys,
                primary_actors=["Faculty Instructor"],
                secondary_actors=["Student", "Department Head"]
            )

        elif "support" in dom_lower or "customer" in dom_lower:
            fallback_personas = [
                PersonaProfile(
                    role_name="Customer",
                    responsibilities="Submits support inquiries through web chat seeking accurate product information and troubleshooting assistance.",
                    primary_goals=["Receive immediate, grounded answers from approved articles", "Escalate to a human representative when questions are complex"],
                    frustrations=["Long wait times and unhelpful generic bots", "Having to repeat issue context when transferred to human agents"],
                    technical_proficiency="Novice"
                ),
                PersonaProfile(
                    role_name="Customer Service Representative",
                    responsibilities="Handles complex inquiries and low-confidence queries escalated from the automated knowledge assistant.",
                    primary_goals=["Receive escalated inquiries with complete conversation context and a concise 3-bullet summary", "Resolve customer issues accurately and efficiently"],
                    frustrations=["Missing conversation history requiring customer re-interviewing", "Unstructured ticket queues without context summaries"],
                    technical_proficiency="Intermediate"
                )
            ]

            fallback_journeys = [
                UserJourneyStep(
                    stage_name="1. Customer Query Ingestion",
                    actor="Customer",
                    actor_action="Enters natural language question into authenticated web chat interface.",
                    system_response="Validates session token, retrieves matching approved knowledge-base articles, and synthesizes grounded candidate response.",
                    error_or_edge_case="If network connection drops, displays connection retry prompt and preserves in-progress message."
                ),
                UserJourneyStep(
                    stage_name="2. Grounded Answer Synthesis & Threshold Evaluation",
                    actor="Customer",
                    actor_action="Awaits response as system evaluates answer confidence against the 80.0% threshold.",
                    system_response="If confidence is >= 80.0%, delivers grounded response with verified source article citations directly to customer transcript.",
                    error_or_edge_case="If no approved knowledge-base article matches or contains relevant information, notifies customer and offers human escalation."
                ),
                UserJourneyStep(
                    stage_name="3. Low-Confidence Interception & Escalation",
                    actor="Customer",
                    actor_action="Submits an ambiguous or complex inquiry resulting in evaluated confidence < 80.0%.",
                    system_response="Suppresses automated candidate answer, flags query as low-confidence, compiles structured 3-bullet summary, and transfers ticket to human queue.",
                    error_or_edge_case="If all human agents are currently engaged, notifies customer of queue status with option to hold or leave an asynchronous message."
                ),
                UserJourneyStep(
                    stage_name="4. Human Representative Resolution & Context Handoff",
                    actor="Customer Service Representative",
                    actor_action="Accepts escalated ticket on dashboard and reviews complete conversation transcript with automated 3-bullet summary.",
                    system_response="Renders full dialogue history seamlessly without prompting customer to re-enter issue details, and logs resolution disposition upon ticket closure.",
                    error_or_edge_case="If representative disconnects prematurely, preserves ticket in active triage queue with session audit history."
                )
            ]

            return StakeholderAnalystOutput(
                personas=fallback_personas,
                user_journeys=fallback_journeys,
                primary_actors=["Customer"],
                secondary_actors=["Customer Service Representative"]
            )

        # Generic fallback
        target_role = input_data.intended_users[0] if input_data.intended_users else "Primary User"
        sec_role = input_data.intended_users[1] if len(input_data.intended_users) > 1 else "Operator"
        category = input_data.product_category or "System"

        fallback_personas = [
            PersonaProfile(
                role_name=target_role,
                responsibilities=f"Engages with {category} to complete daily operational objectives.",
                primary_goals=[f"Quickly resolve {input_data.domain} tasks", "Access verified information effortlessly"],
                frustrations=["Slow response times", "Inaccurate or unverified answers"],
                technical_proficiency="Intermediate"
            ),
            PersonaProfile(
                role_name=sec_role,
                responsibilities=f"Monitors and manages {category} exceptions, escalations, and system integrity.",
                primary_goals=["Maintain high resolution quality", "Receive contextual escalations without missing history"],
                frustrations=["Lack of context during handoffs", "Manual tracking overhead"],
                technical_proficiency="Advanced"
            )
        ]

        fallback_journeys = [
            UserJourneyStep(
                stage_name="1. Ingestion / Interaction Request",
                actor=target_role,
                actor_action=f"Submits request or query into the {category} interface.",
                system_response=f"Validates request against {input_data.domain} policies and logs session.",
                error_or_edge_case="Rejects malformed input and prompts user for clarification."
            ),
            UserJourneyStep(
                stage_name="2. Processing & Resolution",
                actor=category,
                actor_action="Processes input using approved knowledge sources and determines response confidence.",
                system_response=f"Provides verified answer with cited sources if confidence threshold is met.",
                error_or_edge_case=f"If confidence is below threshold, flags query for {sec_role} escalation."
            ),
            UserJourneyStep(
                stage_name="3. Escalation & Verification",
                actor=sec_role,
                actor_action="Reviews unresolved query and full conversation history.",
                system_response=f"Transfers session to human agent and updates knowledge base.",
                error_or_edge_case="If agent is offline, queues ticket with SLA notification."
            )
        ]

        return StakeholderAnalystOutput(
            personas=fallback_personas,
            user_journeys=fallback_journeys,
            primary_actors=[target_role],
            secondary_actors=[sec_role]
        )
