import json
import re
import logging
from typing import Optional, Dict, Any, List
from app.ai.gateway import AIGatewayInterface

logger = logging.getLogger(__name__)

class OfflineMockAdapter(AIGatewayInterface):
    """Deterministic local AI engine used when Ollama is offline or in test environments."""

    async def is_available(self) -> bool:
        return True

    async def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"name": "offline-deterministic-engine", "size": 0, "modified_at": "2026-11-04T00:00:00Z"},
            {"name": "llama3.2:latest (emulated)", "size": 2000000000, "modified_at": "2026-11-04T00:00:00Z"},
            {"name": "mistral:latest (emulated)", "size": 4100000000, "modified_at": "2026-11-04T00:00:00Z"}
        ]

    def _detect_domain(self, prompt: str) -> Dict[str, Any]:
        p = prompt.lower()
        # If prompt has explicit product category/domain header, prioritize target header
        cat_match = re.search(r"product category:\s*([^\n]+)", p)
        dom_match = re.search(r"problem domain:\s*([^\n]+)", p)
        header_text = ((cat_match.group(1) if cat_match else "") + " " + (dom_match.group(1) if dom_match else "")).strip()
        target = header_text if header_text else p

        if "warehouse" in target or "robot" in target or "agv" in target:
            return {
                "category": "Autonomous Warehouse Robot Fleet Management",
                "domain": "Warehouse Robotics & Fleet Automation",
                "users": ["Floor Supervisor", "Fleet Dispatcher", "Maintenance Technician", "Operations Lead"],
                "objectives": [
                    "Schedule AGVs for pallet transport across warehouse grid",
                    "Calculate collision-free routing paths dynamically",
                    "Dispatch low-battery robots (< 20%) to charging docks",
                    "Alert floor supervisors on route blockage or vehicle obstruction"
                ],
                "capabilities": [
                    "Pallet transport mission dispatching",
                    "Collision-free grid routing calculation",
                    "Automated battery monitoring and dock assignment (< 20%)",
                    "Real-time route blockage detection and supervisor alerting"
                ],
                "constraints": [
                    "Robots with battery below 20% must immediately route to charging docks",
                    "Emergency stop latency must not exceed 100 milliseconds"
                ],
                "facts": [
                    "Fleet consists of autonomous guided vehicles on warehouse grid",
                    "Charging docks have limited physical capacity"
                ],
                "assumptions": [
                    "Warehouse grid map is synchronized via local Wi-Fi telemetry",
                    "Sensors detect obstacles in real-time"
                ],
                "missing": ["Specific floor map dimensions and docking port count"]
            }
        elif "customer support" in target or "support assistant" in target or "knowledge-base" in target or "knowledge base" in target:
            return {
                "category": "AI Customer Support Assistant",
                "domain": "Customer Support Automation",
                "users": ["Customer", "Support Agent", "Support Supervisor", "Knowledge Base Manager"],
                "objectives": [
                    "Answer user queries using verified knowledge-base articles",
                    "Maintain multi-turn conversation history",
                    "Detect low model confidence or user escalation requests",
                    "Perform seamless escalation and context handoff to human support dashboard"
                ],
                "capabilities": [
                    "Approved knowledge base article retrieval",
                    "Grounded question answering with citations",
                    "Session-scoped conversation history",
                    "Uncertainty detection and escalation thresholding (< 80%)",
                    "Human agent takeover with complete chat summary"
                ],
                "constraints": [
                    "Must strictly answer using verified company documentation",
                    "Hand off to human when confidence is below 80%",
                    "Preserve customer conversation privacy"
                ],
                "facts": [
                    "Knowledge base contains approved company documentation",
                    "Human safety net is required below 80% confidence"
                ],
                "assumptions": [
                    "Standard REST APIs exist for knowledge base search and ticket creation",
                    "Human support agents are available during standard operational hours"
                ],
                "missing": [
                    "Target average response latency SLA",
                    "Exact knowledge base storage format (Markdown, HTML, or Vector DB)"
                ]
            }
        elif "attendance" in target or "college" in target or "student" in target or "faculty" in target:
            return {
                "category": "College Attendance Management System",
                "domain": "Higher Education Administration",
                "users": ["Faculty Instructor", "Student", "Department Head", "Academic Administrator"],
                "objectives": [
                    "Enable instructors to quickly record classroom attendance per session",
                    "Provide students transparent real-time visibility into attendance records",
                    "Calculate cumulative attendance percentage per course",
                    "Issue automated warning notifications when attendance falls below 75%",
                    "Enforce institutional policies and condonation workflow rules"
                ],
                "capabilities": [
                    "Class session roster attendance marking",
                    "Student self-service attendance dashboard",
                    "Automated percentage calculation and low attendance warning alerts",
                    "Configurable course-level minimum attendance thresholds",
                    "Formal medical condonation and excuse submission workflow"
                ],
                "constraints": [
                    "Attendance marking window closes 30 minutes after class conclusion",
                    "Students must maintain at least 75% attendance to qualify for final exams",
                    "All retroactive edits require Department Head authorization"
                ],
                "facts": [
                    "Institution enforces a mandatory 75% attendance rule for exam eligibility",
                    "Faculty must record attendance per lecture session"
                ],
                "assumptions": [
                    "Student roster is synchronized with college SIS/ERP database",
                    "Students have access to mobile or web devices for attendance checks"
                ],
                "missing": [
                    "Biometric hardware integration requirements",
                    "SMS gateway provider for low-attendance parent notifications"
                ]
            }
        else:
            return {
                "category": "Enterprise Business Application",
                "domain": "Operational Process Automation",
                "users": ["Primary Operator", "Team Lead", "System Administrator", "Auditor"],
                "objectives": [
                    "Streamline end-to-end domain operational workflows",
                    "Provide real-time visibility and status tracking",
                    "Maintain data integrity and compliance audit trails"
                ],
                "capabilities": [
                    "Request ingestion and validation",
                    "Automated workflow routing and state transitions",
                    "Role-based operational dashboard",
                    "Audit event logging and exportable reporting"
                ],
                "constraints": [
                    "Strict role-based access control",
                    "Audit trails must be immutable"
                ],
                "facts": ["Operational records must be recorded accurately"],
                "assumptions": ["Users operate within a modern web browser environment"],
                "missing": ["Specific high-availability and disaster recovery requirements"]
            }

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2
    ) -> str:
        prompt_lower = prompt.lower()
        d = self._detect_domain(prompt)

        # 1. Input Analysis stage
        if "analyze the following user submission" in prompt_lower or "input analyzer" in prompt_lower or "classify the following product submission" in prompt_lower:
            return json.dumps({
                "product_category": d["category"],
                "problem_domain": d["domain"],
                "intended_users": d["users"],
                "core_objectives": d["objectives"],
                "expected_capabilities": d["capabilities"],
                "explicit_constraints": d["constraints"],
                "missing_critical_info": d["missing"],
                "facts": d["facts"],
                "assumptions": d["assumptions"],
                "assignment_requirements": {
                    "instruction": f"Deliver a professional engineering PRD for {d['category']}",
                    "mandatory_sections": ["Executive Summary", "Functional Requirements", "Non-Functional Requirements", "Security & Privacy", "Business Rules"],
                    "deliverables": ["PRD Specification", "Traceability Matrix", "Architecture Diagram"],
                    "constraints": d["constraints"],
                    "expected_length": "Comprehensive"
                }
            })

        # 1b. Problem Analyst stage
        if "problem analyst" in prompt_lower or "principal product strategy analyst" in prompt_lower:
            return json.dumps({
                "problem_domain": d["domain"],
                "root_pain_points": [
                    f"Manual, fragmented processes in {d['domain']}",
                    "Lack of timely visibility and error-prone record keeping",
                    "Delayed resolution of customer/student requests"
                ],
                "current_limitations": [
                    "Legacy paper or disconnected spreadsheet systems",
                    "No automated notifications or proactive alerts",
                    "High human overhead during peak operational periods"
                ],
                "desired_outcomes": d["objectives"]
            })

        # 1c. Assignment Parser stage
        if "assignment parser" in prompt_lower or "assignment instructions" in prompt_lower:
            return json.dumps({
                "instruction_summary": f"Professional requirements engineering PRD for {d['category']}",
                "mandatory_sections": ["Executive Summary", "Functional Requirements", "Non-Functional Requirements", "Security & Privacy", "Business Rules", "Acceptance Criteria"],
                "deliverables": ["Software Requirements Document", "Acceptance Verification Criteria", "Data and Workflow Specification"],
                "constraints": d["constraints"],
                "expected_length": "Comprehensive"
            })

        # 2. Clarification stage
        if "principal technical product manager" in prompt_lower or "clarification questions are necessary" in prompt_lower:
            return json.dumps({
                "questions": [
                    {
                        "id": "CQ-001",
                        "priority": "critical",
                        "category": "Operational Scope",
                        "question": f"What is the primary target deployment environment for {d['category']}?",
                        "rationale": f"Determines whether {d['category']} operates as a local service, private cloud, or hybrid architecture.",
                        "suggested_options": ["On-premises private server", "Secure cloud container", "Hybrid local appliance"]
                    },
                    {
                        "id": "CQ-002",
                        "priority": "medium",
                        "category": "Integration & Scaling",
                        "question": f"What existing third-party systems must {d['category']} integrate with?",
                        "rationale": "Clarifies API connector dependencies and authorization boundaries.",
                        "suggested_options": ["Standard REST / JSON webhooks", "Direct database synchronization", "Stand-alone operation without external connectors"]
                    },
                    {
                        "id": "CQ-003",
                        "priority": "low",
                        "category": "Policy Thresholds",
                        "question": "What is the initial threshold configuration for automated system warnings?",
                        "rationale": "Guides initial policy configuration for proactive notifications.",
                        "suggested_options": ["Standard strict default threshold", "Customizable department-level policy"]
                    }
                ]
            })

        # 3. Requirement Engineering stage
        if "lead requirements engineer" in prompt_lower or "generate structured requirements" in prompt_lower or "functional_requirements" in prompt_lower:
            if "customer support" in d["category"].lower():
                return json.dumps({
                    "functional_requirements": [
                        {
                            "id": "FR-001",
                            "title": "Approved Knowledge-Base Article Retrieval",
                            "description": "The assistant shall search and retrieve relevant text passages exclusively from verified company knowledge-base documentation.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-001", "AC-002"]
                        },
                        {
                            "id": "FR-002",
                            "title": "Grounded Response Generation with Citations",
                            "description": "The assistant shall synthesize answers strictly using retrieved knowledge facts and cite the source article title and section.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-003"]
                        },
                        {
                            "id": "FR-003",
                            "title": "Conversation Session History Management",
                            "description": "The system shall maintain multi-turn chat history for the active session to resolve anaphoric references and user context.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-004"]
                        },
                        {
                            "id": "FR-004",
                            "title": "Uncertainty Detection and Confidence Scoring",
                            "description": "The assistant shall calculate a confidence score for each generated response; if confidence is below 80%, automated response is suppressed.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-005"]
                        },
                        {
                            "id": "FR-005",
                            "title": "Seamless Human Agent Escalation and Handoff",
                            "description": "Upon low confidence (< 80%) or explicit user request, the system shall compile a concise conversation summary and route the session to the human agent dashboard.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-006"]
                        }
                    ],
                    "non_functional_requirements": [
                        {
                            "id": "NFR-001",
                            "title": "Response Time Latency",
                            "description": "Initial response generation shall complete within 3 seconds for 95% of standard knowledge queries.",
                            "classification": "Proposed target",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-007"]
                        },
                        {
                            "id": "NFR-002",
                            "title": "Conversation Privacy Protection",
                            "description": "Customer dialogue turns and session tokens shall be encrypted at rest and in transit.",
                            "classification": "Confirmed requirement",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-008"]
                        },
                        {
                            "id": "NFR-003",
                            "title": "System Availability & Service Continuity",
                            "description": "The assistant system shall target 99.5% service availability with local fallback queuing during transient network disruptions.",
                            "classification": "Proposed target",
                            "priority": "Should Have",
                            "acceptance_criteria_ids": []
                        }
                    ],
                    "business_rules": [
                        {
                            "id": "BR-001",
                            "title": "Zero Unverified Hallucination Invariant",
                            "description": "The assistant must never provide factual claims absent from approved documentation. When unverified, it must state lack of information.",
                            "provenance": "confirmed_user_input",
                            "rationale": "Prevents legal and brand exposure from inaccurate customer guidance."
                        },
                        {
                            "id": "BR-002",
                            "title": "Mandatory Escalation Threshold Rule",
                            "description": "Any response with confidence score < 80% must trigger immediate escalation to human support.",
                            "provenance": "confirmed_user_input",
                            "rationale": "Protects customer experience when automated confidence is insufficient."
                        },
                        {
                            "id": "BR-003",
                            "title": "Contextual Handoff Invariant",
                            "description": "Human escalations must transmit complete conversation history and structured issue summary to avoid asking customers to repeat themselves.",
                            "provenance": "confirmed_user_input",
                            "rationale": "Reduces customer frustration and accelerates human agent resolution."
                        }
                    ],
                    "acceptance_criteria": [
                        {
                            "id": "AC-001",
                            "requirement_id": "FR-001",
                            "statement": "Given a customer question, when evaluated against the knowledge base, the system retrieves only approved articles matching semantic keywords."
                        },
                        {
                            "id": "AC-002",
                            "requirement_id": "FR-001",
                            "statement": "Given outdated or unapproved documentation, when indexed, the retrieval pipeline excludes it from search candidates."
                        },
                        {
                            "id": "AC-003",
                            "requirement_id": "FR-002",
                            "statement": "Given a factual response, when rendered to the customer, it displays verified source links or citation titles."
                        },
                        {
                            "id": "AC-004",
                            "requirement_id": "FR-003",
                            "statement": "Given a follow-up query referencing a previous turn, when answered, the assistant accurately uses context from earlier turns in the same session."
                        },
                        {
                            "id": "AC-005",
                            "requirement_id": "FR-004",
                            "statement": "Given a query where retrieval similarity is below 0.80, when scored, the system flags the response as low confidence."
                        },
                        {
                            "id": "AC-006",
                            "requirement_id": "FR-005",
                            "statement": "Given an escalation trigger, when transferred, the human agent dashboard receives the full chat transcript and an AI-generated 3-bullet summary."
                        },
                        {
                            "id": "AC-007",
                            "requirement_id": "NFR-001",
                            "statement": "Given concurrent customer requests, 95% of first-token responses are delivered within 3000ms."
                        },
                        {
                            "id": "AC-008",
                            "requirement_id": "NFR-002",
                            "statement": "Given customer input containing credit card numbers or passwords, when persisted in logs, sensitive entities are redacted."
                        }
                    ]
                })
            elif "attendance" in d["category"].lower():
                return json.dumps({
                    "functional_requirements": [
                        {
                            "id": "FR-001",
                            "title": "Instructor Lecture Attendance Recording",
                            "description": "Faculty instructors shall record student attendance (Present, Absent, Late, Excused) for each scheduled course session.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-001", "AC-002"]
                        },
                        {
                            "id": "FR-002",
                            "title": "Student Self-Service Attendance Dashboard",
                            "description": "Students shall log in and view their subject-wise attended sessions, total sessions conducted, and attendance percentages.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-003"]
                        },
                        {
                            "id": "FR-003",
                            "title": "Automated Percentage Calculation Engine",
                            "description": "The system shall automatically compute cumulative attendance percentage immediately following each recorded class session.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-004"]
                        },
                        {
                            "id": "FR-004",
                            "title": "Low Attendance Warning Alerts (< 75%)",
                            "description": "The system shall trigger automated email and dashboard alert notifications whenever a student's attendance drops below 75%.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-005"]
                        },
                        {
                            "id": "FR-005",
                            "title": "Configurable Institutional Attendance Policies",
                            "description": "Academic administrators shall configure minimum percentage thresholds, grace days, and condonation approval rules per department.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-006"]
                        }
                    ],
                    "non_functional_requirements": [
                        {
                            "id": "NFR-001",
                            "title": "Roster Synchronization Latency",
                            "description": "Student enrollment roster updates shall synchronize across active sections within 10 seconds.",
                            "classification": "Proposed target",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-007"]
                        },
                        {
                            "id": "NFR-002",
                            "title": "Attendance Record Auditability",
                            "description": "All attendance modifications must retain previous state, editor identity, timestamp, and justification reason.",
                            "classification": "Confirmed requirement",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-008"]
                        },
                        {
                            "id": "NFR-003",
                            "title": "Examination Period Service Availability",
                            "description": "The attendance system shall maintain 99.9% uptime during active class registration and end-of-term examination qualification periods.",
                            "classification": "Proposed target",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": []
                        }
                    ],
                    "business_rules": [
                        {
                            "id": "BR-001",
                            "title": "Mandatory 75% Examination Eligibility Invariant",
                            "description": "Students with cumulative attendance strictly below 75% at course conclusion are ineligible for final examinations without approved condonation.",
                            "provenance": "confirmed_user_input",
                            "rationale": "Enforces institutional academic accreditation standards."
                        },
                        {
                            "id": "BR-002",
                            "title": "Same-Day Attendance Locking Rule",
                            "description": "Class session attendance becomes read-only 24 hours after session conclusion; retroactive edits require Department Head authorization.",
                            "provenance": "confirmed_user_input",
                            "rationale": "Prevents unauthorized retrospective attendance manipulation."
                        },
                        {
                            "id": "BR-003",
                            "title": "Excused Absence Condonation Invariant",
                            "description": "Official medical certificates or institutional duty certificates must be approved by the Department Head within 7 days of absence.",
                            "provenance": "confirmed_user_input",
                            "rationale": "Ensures verifiable medical records before attendance percentage adjustment."
                        }
                    ],
                    "acceptance_criteria": [
                        {
                            "id": "AC-001",
                            "requirement_id": "FR-001",
                            "statement": "Given an active class roster, when the faculty marks attendance and submits, the session status is recorded as submitted."
                        },
                        {
                            "id": "AC-002",
                            "requirement_id": "FR-001",
                            "statement": "Given a submitted attendance session, editing after 24 hours requires Department Head approval."
                        },
                        {
                            "id": "AC-003",
                            "requirement_id": "FR-002",
                            "statement": "Given an authenticated student, when visiting the dashboard, their course attendance percentage displays accurately."
                        },
                        {
                            "id": "AC-004",
                            "requirement_id": "FR-003",
                            "statement": "Given a new session recorded, student cumulative attendance percentage updates immediately without batch lag."
                        },
                        {
                            "id": "AC-005",
                            "requirement_id": "FR-004",
                            "statement": "Given a student attendance dropping below 75%, an automated warning email and in-app notification are dispatched within 5 minutes."
                        },
                        {
                            "id": "AC-006",
                            "requirement_id": "FR-005",
                            "statement": "Given an administrator updating threshold from 75% to 80%, new warning notifications adhere to the updated threshold."
                        },
                        {
                            "id": "AC-007",
                            "requirement_id": "NFR-001",
                            "statement": "Given a roster sync, 100% of newly enrolled students appear in instructor class rosters within 10 seconds."
                        },
                        {
                            "id": "AC-008",
                            "requirement_id": "NFR-002",
                            "statement": "Given any attendance modification, an immutable audit log record captures timestamp, author, and prior state."
                        }
                    ]
                })
            elif "warehouse" in d["category"].lower() or "robot" in d["category"].lower():
                return json.dumps({
                    "functional_requirements": [
                        {
                            "id": "FR-001",
                            "title": "Autonomous AGV Pallet Transport Mission Scheduling",
                            "description": "The system shall schedule and dispatch automated guided vehicles (AGVs) for pallet transport missions across warehouse locations.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-001"]
                        },
                        {
                            "id": "FR-002",
                            "title": "Dynamic Collision-Free Grid Routing Calculation",
                            "description": "The system shall calculate collision-free routing paths across the warehouse grid avoiding stationary obstacles and active robot paths.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-002"]
                        },
                        {
                            "id": "FR-003",
                            "title": "Automated Low-Battery Docking and Obstruction Alerting",
                            "description": "The system shall automatically route AGVs to charging docks when battery drops below 20% and trigger floor supervisor alerts on route blockage.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-003"]
                        }
                    ],
                    "non_functional_requirements": [
                        {
                            "id": "NFR-001",
                            "title": "Emergency Stop Telemetry Latency",
                            "description": "Emergency stop signals across all active AGVs must propagate within 100 milliseconds.",
                            "classification": "Proposed target",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-004"]
                        },
                        {
                            "id": "NFR-002",
                            "title": "Fleet Command Encryption & Safety",
                            "description": "All wireless telemetry and dispatch commands must be encrypted via TLS with HMAC message integrity checks.",
                            "classification": "Confirmed requirement",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": []
                        },
                        {
                            "id": "NFR-003",
                            "title": "Fleet Dispatch Service Availability",
                            "description": "Warehouse AGV fleet dispatch service shall maintain 99.9% uptime during active fulfillment shifts.",
                            "classification": "Proposed target",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": []
                        }
                    ],
                    "business_rules": [
                        {
                            "id": "BR-001",
                            "title": "Mandatory Low-Battery Docking Threshold (< 20%)",
                            "description": "Any AGV with state of charge strictly below 20% must immediately abort new mission assignments and route to an available charging dock.",
                            "provenance": "confirmed_user_input",
                            "rationale": "Prevents stranded vehicles on high-traffic warehouse floor paths."
                        }
                    ],
                    "acceptance_criteria": [
                        {
                            "id": "AC-001",
                            "requirement_id": "FR-001",
                            "statement": "Given an active pallet transport mission, When an AGV is assigned, Then mission status is dispatched and recorded in fleet ledger."
                        },
                        {
                            "id": "AC-002",
                            "requirement_id": "FR-002",
                            "statement": "Given two AGVs on converging grid coordinates, When routing is evaluated, Then the system recalculates paths with zero collision conflicts."
                        },
                        {
                            "id": "AC-003",
                            "requirement_id": "FR-003",
                            "statement": "Given an AGV battery reporting 19.9% (< 20%), When state of charge is checked, Then the robot is routed to an open charging dock immediately."
                        },
                        {
                            "id": "AC-004",
                            "requirement_id": "NFR-001",
                            "statement": "Given an obstacle sensor trigger, When emergency stop is initiated, Then vehicle halts within 100ms."
                        }
                    ]
                })
            else:
                return json.dumps({
                    "functional_requirements": [
                        {
                            "id": "FR-001",
                            "title": f"{d['category']} Core Workflow Ingestion",
                            "description": f"The system shall accept and validate input requests governing {d['domain']}.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-001"]
                        },
                        {
                            "id": "FR-002",
                            "title": f"{d['domain']} Automated Routing and State Transition",
                            "description": f"The system shall process operational transitions according to defined business rules in {d['domain']}.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-002"]
                        },
                        {
                            "id": "FR-003",
                            "title": f"{d['domain']} Audit Logging & Status Tracking",
                            "description": f"The system shall record state change transactions with author identity and timestamp in an immutable ledger.",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-003"]
                        }
                    ],
                    "non_functional_requirements": [
                        {
                            "id": "NFR-001",
                            "title": f"{d['domain']} Transaction Response Latency",
                            "description": f"Core operations in {d['domain']} shall complete within 2.0 seconds under nominal load.",
                            "classification": "Proposed target",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": ["AC-003"]
                        },
                        {
                            "id": "NFR-002",
                            "title": f"{d['domain']} Data Protection & Security",
                            "description": f"All domain entities and messages must be encrypted in transit via TLS and at rest via AES-256.",
                            "classification": "Confirmed requirement",
                            "priority": "Must Have",
                            "acceptance_criteria_ids": []
                        },
                        {
                            "id": "NFR-003",
                            "title": f"{d['domain']} Operational Availability",
                            "description": f"System targets 99.5% operational availability with automated error monitoring.",
                            "classification": "Proposed target",
                            "priority": "Should Have",
                            "acceptance_criteria_ids": []
                        }
                    ],
                    "business_rules": [
                        {
                            "id": "BR-001",
                            "title": "Operational Integrity Rule",
                            "description": f"All transactions in {d['domain']} must be authorized by designated role.",
                            "provenance": "confirmed_user_input",
                            "rationale": "Prevents unauthorized state changes."
                        }
                    ],
                    "acceptance_criteria": [
                        {
                            "id": "AC-001",
                            "requirement_id": "FR-001",
                            "statement": f"Given a valid request for {d['domain']}, when submitted, the system validates and logs the transaction."
                        },
                        {
                            "id": "AC-002",
                            "requirement_id": "FR-002",
                            "statement": f"Given an approved state transition, the system updates operational status and notifies stakeholders."
                        },
                        {
                            "id": "AC-003",
                            "requirement_id": "NFR-001",
                            "statement": f"Given any operational modification, an audit record captures editor ID and timestamp."
                        }
                    ]
                })

        # 4. Section Regeneration / Single section prompt
        if "regenerate section" in prompt_lower or "section content" in prompt_lower:
            return (
                f"### {d['category']} Specification\n\n"
                f"This section specifies operational requirements for {d['category']} within {d['domain']}.\n"
                f"- Clear domain workflow steps and stakeholder responsibilities.\n"
                f"- Deterministic acceptance criteria and performance thresholds.\n"
                f"- Traceable alignment with confirmed project objectives."
            )

        # Default fallback
        if json_mode:
            return json.dumps({"status": "success", "domain": d["domain"], "category": d["category"]})
        return f"Operational requirements specification for {d['category']}."
