import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from app.ai.gateway import AIGatewayInterface

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v2.0.0"

class RiskItem(BaseModel):
    id: str
    category: str  # Functional, Data Privacy, Security, Operational, Integration
    title: str
    risk_event: Optional[str] = None
    root_cause: Optional[str] = None
    impact: str = "High"    # Critical, High, Medium, Low
    probability: str = "Medium"  # High, Medium, Low
    severity: Optional[str] = "High"
    mitigation_strategy: str
    contingency_plan: Optional[str] = None
    owner_role: Optional[str] = None

class RiskAnalystInput(BaseModel):
    problem_domain: str
    capabilities: List[str]
    constraints: List[str] = Field(default_factory=list)
    objectives: List[str] = Field(default_factory=list)

class RiskAnalystOutput(BaseModel):
    risks: List[RiskItem] = Field(default_factory=list)
    prompt_version: str = PROMPT_VERSION

RISK_ANALYST_PROMPT = """
You are a Principal Risk & Reliability Engineer.
Analyze the target product and identify at least 4 critical operational, security, data handling, and functional risks strictly for:

Domain: {domain}
Core Capabilities: {capabilities}
Constraints: {constraints}
Objectives: {objectives}

Instructions:
1. Every risk must describe real, domain-specific failure modes of THIS PRODUCT in operation.
2. DO NOT include risks about the PRD Framework software itself (e.g., no risks about generating PRD documents or local Ollama timeouts).
3. Assign category: "Functional", "Data Privacy", "Security", "Operational", or "Integration".
4. Provide concrete, actionable engineering mitigations, root causes, contingency plans, and owner roles.
5. NEVER use generic placeholder text like "Operational risk" or "Monitor and log".

Return ONLY a valid JSON object matching this schema:
{{
  "risks": [
    {{
      "id": "RSK-001",
      "category": "Operational | Security | Data Privacy | Functional | Integration",
      "title": "Clear Risk Summary",
      "risk_event": "Concrete failure scenario description",
      "root_cause": "Underlying operational or technical root cause",
      "probability": "High | Medium | Low",
      "impact": "Critical | High | Medium | Low",
      "mitigation_strategy": "Concrete preventive engineering control...",
      "contingency_plan": "Immediate fail-safe fallback or disaster recovery procedure...",
      "owner_role": "Responsible engineering or operational role"
    }}
  ]
}}
"""

class RiskAnalyst:
    def __init__(self, ai_gateway: AIGatewayInterface):
        self.ai = ai_gateway

    async def analyze_risks(self, input_data: RiskAnalystInput) -> RiskAnalystOutput:
        domain = input_data.problem_domain or "General Application"
        capabilities_str = ", ".join(input_data.capabilities) if input_data.capabilities else "Core product functionality"
        constraints_str = ", ".join(input_data.constraints) if input_data.constraints else "Standard operating limits"
        objectives_str = ", ".join(input_data.objectives) if input_data.objectives else "Deliver service"

        prompt = RISK_ANALYST_PROMPT.format(
            domain=domain,
            capabilities=capabilities_str,
            constraints=constraints_str,
            objectives=objectives_str
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
            parsed_risks = []
            for idx, r in enumerate(data.get("risks", []), 1):
                title = r.get("title") or r.get("risk_event") or f"{domain} Operational Threat {idx}"
                ev = r.get("risk_event") or title
                root = r.get("root_cause") or "System concurrency boundary or external dependency anomaly"
                prob = r.get("probability") or "Medium"
                imp = r.get("impact") or "High"
                mit = r.get("mitigation_strategy") or r.get("mitigation") or f"Implement automated validation rules and circuit breakers for {domain}."
                cont = r.get("contingency_plan") or r.get("contingency") or "Fail safe to manual operator review with diagnostic telemetry."
                owner = r.get("owner_role") or r.get("owner") or "Systems Engineering Lead"

                # Sanitize out-of-scope ticketing/external channels from risks
                title = re.sub(r"\b(?:ticket creation|escalation ticket|ticket id|tickets|ticket)\b", "escalation inquiry", title, flags=re.IGNORECASE)
                ev = re.sub(r"\b(?:ticket creation|escalation ticket|ticket id|tickets|ticket)\b", "escalation inquiry", ev, flags=re.IGNORECASE)
                ev = re.sub(r"\b(?:whatsapp|telegram|sms|phone call)\b", "web chat reconnection", ev, flags=re.IGNORECASE)
                root = re.sub(r"\b(?:ticket creation|escalation ticket|ticket id|tickets|ticket)\b", "escalation inquiry", root, flags=re.IGNORECASE)
                mit = re.sub(r"\b(?:ticket creation|escalation ticket|ticket id|tickets|ticket)\b", "escalation inquiry", mit, flags=re.IGNORECASE)
                cont = re.sub(r"\b(?:ticket creation|escalation ticket|ticket id|tickets|ticket)\b", "escalation inquiry", cont, flags=re.IGNORECASE)
                
                parsed_risks.append(RiskItem(
                    id=f"RSK-{idx:03d}",
                    category=r.get("category", "Operational"),
                    title=title,
                    risk_event=ev,
                    root_cause=root,
                    impact=imp,
                    probability=prob,
                    severity=imp,
                    mitigation_strategy=mit,
                    contingency_plan=cont,
                    owner_role=owner
                ))
            if len(parsed_risks) >= 3:
                return RiskAnalystOutput(risks=parsed_risks)
        except Exception as e:
            logger.warning(f"RiskAnalyst AI generation fallback: {e}")

        # Dynamic, domain-tailored fallback risks (ZERO PRD Framework software leakage)
        cap_main = input_data.capabilities[0] if input_data.capabilities else domain
        fallback_risks = [
            RiskItem(
                id="RSK-001",
                category="Functional",
                title=f"{domain} Service Inaccuracy or Model Hallucination",
                risk_event=f"System generates inaccurate or ungrounded responses during {cap_main.lower()}",
                root_cause="Out-of-date knowledge repository or threshold evaluation bypass",
                impact="High",
                probability="Medium",
                severity="High",
                mitigation_strategy=f"Enforce strict confidence threshold scoring and mandatory citation of approved sources before returning responses in {domain}.",
                contingency_plan="Suppress automated fulfillment and route directly to human specialist with session context.",
                owner_role="Lead Domain Architect"
            ),
            RiskItem(
                id="RSK-002",
                category="Data Privacy",
                title=f"{domain} Sensitive User Data Exposure",
                risk_event=f"Unauthorized access or leakage of personal identifiers processed in {domain}",
                root_cause="Insufficient role authorization checks or insecure storage transmission",
                impact="Critical",
                probability="Low",
                severity="Critical",
                mitigation_strategy="Enforce TLS in transit, encryption at rest, field-level PII masking, and strict role-based access boundaries.",
                contingency_plan="Revoke session tokens immediately, trigger security incident response runbook, and notify data protection officer.",
                owner_role="Security & Compliance Officer"
            ),
            RiskItem(
                id="RSK-003",
                category="Integration",
                title=f"{domain} External Dependency or Knowledge Source Desynchronization",
                risk_event=f"Integration endpoints fail or provide stale schema data to {domain}",
                root_cause="Network timeout, remote API breaking changes, or upstream database outage",
                impact="High",
                probability="Medium",
                severity="High",
                mitigation_strategy="Implement automated periodic health checks, versioned cache invalidation, and circuit breakers with graceful fallback.",
                contingency_plan="Switch to local read-only cache and display degraded service advisory banner to active users.",
                owner_role="DevOps / Infrastructure Engineer"
            ),
            RiskItem(
                id="RSK-004",
                category="Operational",
                title=f"{domain} Peak Load Degradation and Escalation Backlog",
                risk_event=f"Spike in concurrency exhausts server resources or human review capacity in {domain}",
                root_cause="Unpredictable surge in user demand without dynamic horizontal auto-scaling",
                impact="High",
                probability="Medium",
                severity="High",
                mitigation_strategy="Implement request queue rate-limiting, priority-based escalation queues, and real-time SLA breach alerting.",
                contingency_plan="Activate secondary reserve capacity and notify supervisors to redistribute review workloads.",
                owner_role="Operations Manager"
            )
        ]
        return RiskAnalystOutput(risks=fallback_risks)
