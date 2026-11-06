import pytest
import re
import hashlib
from typing import Dict
from app.models.prd import PRDVersion, PRDSectionContent, CANONICAL_SECTIONS, SECTION_TITLES
from app.models.analysis import AnalysisRecord
from app.services.validation_service import ValidationService

def make_sec(key: str, content: str) -> PRDSectionContent:
    return PRDSectionContent(
        key=key,
        title=SECTION_TITLES.get(key, key),
        content=content
    )

# Helpers to build comprehensive mock PRD sections
def make_valid_sections(
    title: str,
    domain: str,
    version: str = "v2.4.1",
    include_80_conf: bool = True,
    is_attendance: bool = False,
    is_warehouse: bool = False,
    is_telehealth: bool = False
) -> Dict[str, PRDSectionContent]:
    content_hash = "mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678"
    sections = {}

    for sec_key in CANONICAL_SECTIONS:
        sections[sec_key] = make_sec(
            sec_key,
            f"Detailed specifications for {sec_key} in {domain} addressing operational workflows and stakeholder capabilities."
        )

    # Section 1: Document Information
    sections["document_information"] = make_sec(
        "document_information",
        (
            f"# {title} - Product Requirements Document\n\n"
            f"- **Version:** {version}\n"
            f"- **Status:** Authoritative Specification\n"
            f"- **Content Hash (SHA-256):** `{content_hash}`\n"
            f"- **Author:** Principal Requirements Engineer\n"
            f"- **Domain:** {domain}\n"
        )
    )

    # Section 2: Executive Summary
    sections["executive_summary"] = make_sec(
        "executive_summary",
        f"This document defines the authoritative engineering requirements for {title} operating within {domain}."
    )

    # Section 5: Product Scope
    if is_attendance:
        sections["product_scope"] = make_sec(
            "product_scope",
            "- Daily course attendance recording\n- Real-time attendance percentage calculation: (attended / total) * 100\n- Automated early warning notifications when attendance falls strictly below 75.0%\n- Duplicate roll call submission prevention\n- Department Head condonation governance"
        )
        sections["out_of_scope"] = make_sec(
            "out_of_scope",
            "- Biometric hardware scanning\n- GPS geofencing automated check-in\n- External university SIS automated writeback\n- Student tuition fee holds"
        )
    elif is_warehouse:
        sections["product_scope"] = make_sec(
            "product_scope",
            "- Automated guided vehicle (AGV) pallet transport scheduling\n- Dynamic collision-free grid routing\n- Automated low-battery docking (< 20%)\n- Floor supervisor obstruction alert notifications"
        )
        sections["out_of_scope"] = make_sec(
            "out_of_scope",
            "- External ERP procurement ordering\n- Multi-facility inter-warehouse dispatch\n- Robotic arm picking manipulator kinematics"
        )
    elif is_telehealth:
        sections["product_scope"] = make_sec(
            "product_scope",
            "- Secure video pediatric consultation session scheduling\n- Guardian parental authorization and consent verification\n- Real-time pediatric clinical encounter notes\n- Post-encounter consultation summary dispatch"
        )
        sections["out_of_scope"] = make_sec(
            "out_of_scope",
            "- Commercial payment processing and billing insurance claims\n- Automated pharmaceutical prescription fulfillment\n- Emergency 911 dispatch telephony integration"
        )
    else:
        sections["product_scope"] = make_sec(
            "product_scope",
            "- Grounded knowledge-base question and answer retrieval\n- Multi-turn conversation session history management\n- Low-confidence answer detection below 80.0% threshold\n- Automated delivery suppression for answers < 80.0%\n- Human customer service representative escalation routing with 3-bullet summary"
        )
        sections["out_of_scope"] = make_sec(
            "out_of_scope",
            "- External third-party ticketing platforms (Zendesk, Jira)\n- External CRM synchronization (Salesforce, HubSpot)\n- Telephony, voice calls, and phone hotline IVR\n- Multilingual speech translation"
        )

    # Section 12: Functional Requirements
    if is_attendance:
        sections["functional_requirements"] = make_sec(
            "functional_requirements",
            (
                "| ID | Title | Description | Priority | Traceable AC |\n"
                "|---|---|---|---|---|\n"
                "| **FR-001** | Lecture Attendance Recording | Faculty instructors record attendance for scheduled course sections | Must Have | AC-001, AC-002 |\n"
                "| **FR-002** | Real-Time Attendance Percentage Calculation | Computes cumulative attendance percentage as (attended / total) * 100 | Must Have | AC-003, AC-004, AC-005 |\n"
                "| **FR-003** | Duplicate Submission Prevention | Rejects duplicate roll call entries for the same course section on the same calendar date | Must Have | AC-006 |\n"
                "| **FR-004** | Low Attendance Warning Dispatch | Dispatches warning notification when attendance drops strictly below 75.0% | Must Have | AC-007 |\n"
                "| **FR-005** | Department Head Condonation Governance | Enables administrative review and approval of documented medical condonation petitions | Should Have | AC-008 |\n\n"
                "### Detailed Functional Requirement Specifications\n\n"
                "#### FR-001: Lecture Attendance Recording\n"
                "- **Actor:** Faculty Instructor\n"
                "- **System Behavior:** Authenticates instructor and commits roster roll call to the attendance ledger.\n"
                "- **Provenance:** `confirmed_user_input` (User Input: faculty instructors record attendance)\n\n"
                "#### FR-002: Real-Time Attendance Percentage Calculation\n"
                "- **Actor:** Student / Faculty\n"
                "- **System Behavior:** Computes (attended / total) * 100 and renders exam eligibility standing.\n"
                "- **Provenance:** `confirmed_user_input` (User Input: calculate attendance percentage)\n\n"
                "#### FR-003: Duplicate Submission Prevention\n"
                "- **Actor:** Faculty Instructor\n"
                "- **System Behavior:** Rejects duplicate submission and displays session already recorded warning.\n"
                "- **Provenance:** `confirmed_user_input` (User Input: prevent duplicate attendance)\n"
            )
        )
    elif is_warehouse:
        sections["functional_requirements"] = make_sec(
            "functional_requirements",
            (
                "| ID | Title | Description | Priority | Traceable AC |\n"
                "|---|---|---|---|---|\n"
                "| **FR-001** | Pallet Transport Dispatch | Schedules and dispatches AGV pallet transport missions across warehouse locations | Must Have | AC-001 |\n"
                "| **FR-002** | Collision-Free Grid Routing | Computes dynamic collision-free grid paths avoiding static and dynamic obstacles | Must Have | AC-002 |\n"
                "| **FR-003** | Automated Low-Battery Docking | Routes AGV to charging dock when battery falls strictly below 20% | Must Have | AC-003 |\n\n"
                "### Detailed Functional Requirement Specifications\n\n"
                "#### FR-001: Pallet Transport Dispatch\n"
                "- **Actor:** Warehouse Operator\n"
                "- **System Behavior:** Assigns pallet mission to nearest available AGV.\n"
                "- **Provenance:** `confirmed_user_input` (User Input: AGV pallet transport)\n"
            )
        )
    elif is_telehealth:
        sections["functional_requirements"] = make_sec(
            "functional_requirements",
            (
                "| ID | Title | Description | Priority | Traceable AC |\n"
                "|---|---|---|---|---|\n"
                "| **FR-001** | Pediatric Encounter Scheduling | Schedules remote video consultations with verified pediatrician availability | Must Have | AC-001 |\n"
                "| **FR-002** | Guardian Authorization Verification | Verifies legal guardian identity and signed digital consent prior to room admission | Must Have | AC-002 |\n"
                "| **FR-003** | Clinical Encounter Notes Ledger | Persists structured pediatric clinical notes with tamper-evident audit timestamps | Must Have | AC-003 |\n\n"
                "### Detailed Functional Requirement Specifications\n\n"
                "#### FR-001: Pediatric Encounter Scheduling\n"
                "- **Actor:** Parent / Guardian\n"
                "- **System Behavior:** Reserves consultation slot and verifies pediatrician credentials.\n"
                "- **Provenance:** `confirmed_user_input` (User Input: pediatric consultation)\n"
            )
        )
    else:
        sections["functional_requirements"] = make_sec(
            "functional_requirements",
            (
                "| ID | Title | Description | Priority | Traceable AC |\n"
                "|---|---|---|---|---|\n"
                "| **FR-001** | Grounded Knowledge-Base Q&A | Retrieves answers exclusively from approved knowledge-base articles | Must Have | AC-001, AC-002 |\n"
                "| **FR-002** | Conversation Session History | Preserves multi-turn conversation context across dialogue turns in active session memory | Must Have | AC-003, AC-004 |\n"
                "| **FR-003** | Low-Confidence Answer Detection | Evaluates confidence against 80.0% threshold and routes low-confidence answers to human escalation | Must Have | AC-005, AC-006 |\n"
                "| **FR-004** | Human Agent Escalation Routing | Transfers full transcript and structured 3-bullet context summary to human representative | Must Have | AC-007, AC-008 |\n"
                "| **FR-005** | Escalation Resolution Ledger | Commits agent disposition notes and session resolution timestamp to audit ledger | Should Have | AC-009 |\n\n"
                "### Detailed Functional Requirement Specifications\n\n"
                "#### FR-001: Grounded Knowledge-Base Q&A\n"
                "- **Actor:** Customer\n"
                "- **System Behavior:** Retrieves approved passages and formats verified response.\n"
                "- **Provenance:** `confirmed_user_input` (User Input: answers customer questions using approved knowledge-base articles)\n\n"
                "#### FR-002: Conversation Session History\n"
                "- **Actor:** Customer\n"
                "- **System Behavior:** Preserves multi-turn dialogue context in session cache; long-term archival duration is an open decision.\n"
                "- **Provenance:** `confirmed_user_input` (User Input: maintains conversation history)\n\n"
                "#### FR-003: Low-Confidence Answer Detection\n"
                "- **Actor:** AI Evaluation Engine\n"
                "- **System Behavior:** Suppresses answers below 80.0% confidence and routes to internal escalation queue.\n"
                "- **Provenance:** `confirmed_user_input` (User Input: identifies low-confidence answers below 80%)\n"
            )
        )

    # Section 13: Non-Functional Requirements
    sections["non_functional_requirements"] = make_sec(
        "non_functional_requirements",
        (
            "| ID | Title | Description | Classification | Priority |\n"
            "|---|---|---|---|---|\n"
            f"| **NFR-001** | Transaction Response Latency | System targets 95th percentile response times under 2.5s | Proposed target | Should Have |\n"
            f"| **NFR-002** | Session Dialogue Encryption & Security | All domain data encrypted via TLS 1.3 in transit and AES-256 at rest | Confirmed requirement | Must Have |\n"
            f"| **NFR-003** | High Availability & Resilient Failover | Service targets 99.5% operational uptime with automated logging | Proposed target | Should Have |\n"
        )
    )

    # Section 14: User Personas
    if is_attendance:
        sections["user_personas"] = make_sec(
            "user_personas",
            "- **Faculty Instructor:** Conducts lectures and records daily attendance.\n- **Student:** Attends lectures and monitors examination eligibility standing.\n- **Department Head:** Governs academic attendance policies and reviews condonation claims."
        )
    elif is_warehouse:
        sections["user_personas"] = make_sec(
            "user_personas",
            "- **Warehouse Floor Operator:** Initiates pallet transport requests and monitors route clearances.\n- **Fleet Operations Supervisor:** Monitors AGV health telemetry, charging docks, and obstacle alarms."
        )
    elif is_telehealth:
        sections["user_personas"] = make_sec(
            "user_personas",
            "- **Pediatrician:** Licensed clinical specialist conducting video pediatric encounters.\n- **Parent / Legal Guardian:** Authorized adult initiating consultation and providing patient history."
        )
    else:
        sections["user_personas"] = make_sec(
            "user_personas",
            "- **Customer:** Inquires about product troubleshooting via self-contained web chat.\n- **Customer Service Representative:** Handles complex inquiries and low-confidence escalations with 3-bullet context summary."
        )

    # Section 15: User Journeys
    if is_attendance:
        sections["user_journeys"] = make_sec(
            "user_journeys",
            (
                "1. **Roster Submission:** Faculty Instructor logs in, selects section, marks roster Present or Absent, and submits.\n"
                "2. **Percentage Viewing:** Student views real-time attendance percentage: `(attended / total) * 100`.\n"
                "3. **Warning Alert:** If calculated percentage falls strictly below 75.0%, system dispatches early warning notification.\n"
                "4. **Condonation Review:** Department Head reviews verified medical excuse and grants condonation approval."
            )
        )
    elif is_warehouse:
        sections["user_journeys"] = make_sec(
            "user_journeys",
            (
                "1. **Mission Dispatch:** Floor Operator triggers pallet transport from Staging Bay A to Rack 14.\n"
                "2. **Grid Navigation:** AGV navigates grid avoiding static obstacles via dynamic routing.\n"
                "3. **Low Battery Docking:** When battery reports 19.9% (< 20%), AGV aborts new missions and docks at Charger 2."
            )
        )
    elif is_telehealth:
        sections["user_journeys"] = make_sec(
            "user_journeys",
            (
                "1. **Consultation Scheduling:** Guardian reserves consultation time slot and uploads pediatric immunization records.\n"
                "2. **Identity Verification:** System verifies guardian consent and admits patient to encrypted waiting room.\n"
                "3. **Clinical Encounter:** Pediatrician conducts consultation, enters encounter notes, and dispatches care summary."
            )
        )
    else:
        sections["user_journeys"] = make_sec(
            "user_journeys",
            (
                "1. **Customer Query Ingestion:** Customer submits question in web chat; system retrieves matching approved KB passages.\n"
                "2. **Threshold Evaluation:** Evaluates candidate answer confidence against 80.0% threshold; if >= 80.0%, delivers grounded response with article citations.\n"
                "3. **Low-Confidence Escalation:** If confidence is strictly below 80.0%, system suppresses direct response, compiles 3-bullet summary, and transfers to human representative queue.\n"
                "4. **Agent Resolution:** Representative reviews complete transcript with summary and resolves customer inquiry."
            )
        )

    # Section 16: Business Rules
    if is_attendance:
        sections["business_rules"] = make_sec(
            "business_rules",
            (
                "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
                "|---|---|---|---|---|---|---|\n"
                "| **BR-001** | Attendance Authority | Only assigned faculty instructors can record class attendance | `confirmed_user_input` | User Input: faculty records attendance | Enforces accountability | No (Confirmed) |\n"
                "| **BR-002** | 75% Eligibility Invariant | Students strictly below 75.0% attendance are disbarred from final exams | `confirmed_user_input` | User Input: 75% minimum attendance | Academic accreditation | No (Confirmed) |\n"
                "| **BR-003** | Duplicate Prevention Rule | System strictly prohibits multiple roll call submissions for the same session date | `confirmed_user_input` | User Input: prevent duplicate attendance | Data integrity | No (Confirmed) |\n"
                "| **BR-004** | Division by Zero Guard | When total conducted sessions is zero, attendance is rendered as 0 conducted sessions with no percentage | `ai_proposed_assumption` | Domain Architectural Standard | Mathematical safety | Yes (Review needed) |\n"
            )
        )
    elif is_warehouse:
        sections["business_rules"] = make_sec(
            "business_rules",
            (
                "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
                "|---|---|---|---|---|---|---|\n"
                "| **BR-001** | Low Battery Docking Invariant | AGVs with battery strictly below 20.0% must immediately route to charging docks | `confirmed_user_input` | User Input: 20% battery threshold | Prevents vehicle stranding | No (Confirmed) |\n"
                "| **BR-002** | Grid Collision Separation | AGVs must maintain minimum 1.5-meter separation during dynamic transit | `ai_proposed_assumption` | Domain Safety Standard | Physical safety | Yes (Review needed) |\n"
                "| **BR-003** | Emergency Halt Priority | Emergency halt telemetry signals override all active mission dispatch commands | `confirmed_user_input` | User Input: emergency stop | Personnel protection | No (Confirmed) |\n"
            )
        )
    elif is_telehealth:
        sections["business_rules"] = make_sec(
            "business_rules",
            (
                "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
                "|---|---|---|---|---|---|---|\n"
                "| **BR-001** | Legal Guardian Consent | Consultations for minors require verified parental consent prior to video stream connection | `confirmed_user_input` | User Input: pediatric guardian consent | Legal compliance | No (Confirmed) |\n"
                "| **BR-002** | Pediatric Credential Verification | Only licensed pediatric practitioners may initiate consultations in pediatric clinic | `confirmed_user_input` | User Input: pediatrician licensing | Clinical standards | No (Confirmed) |\n"
                "| **BR-003** | Clinical Note Finalization | Clinical encounter notes become immutable 24 hours post-consultation | `ai_proposed_assumption` | Medical Record Standard | Audit compliance | Yes (Review needed) |\n"
            )
        )
    else:
        sections["business_rules"] = make_sec(
            "business_rules",
            (
                "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
                "|---|---|---|---|---|---|---|\n"
                "| **BR-001** | Grounded Knowledge Base Answers | Answers must be derived strictly from approved articles with source citations | `confirmed_user_input` | User Input: approved knowledge-base articles | Prevents hallucinations | No (Confirmed) |\n"
                "| **BR-002** | 80% Confidence Escalation Threshold | Responses with confidence score below 80.0% must be suppressed and escalated | `confirmed_user_input` | User Input: identifies low-confidence answers below 80% | Protects customer trust | No (Confirmed) |\n"
                "| **BR-003** | Multi-Turn Context Retention | Chat session history must be preserved across conversation turns | `confirmed_user_input` | User Input: maintains conversation history | Contextual continuity | No (Confirmed) |\n"
                "| **BR-004** | Agent Handoff Summary | Escalated sessions must deliver complete transcript and 3-bullet summary to representative | `confirmed_user_input` | User Input: escalates complex queries with summary | Reduces triage latency | No (Confirmed) |\n"
                "| **BR-005** | Chat Retention Policy (Open Decision) | Archival transcript retention duration beyond 24-hour cache is subject to privacy review | `unresolved_decision` | Unresolved Decision: Data Retention Policy | Statutory compliance | Yes (Review needed) |\n"
            )
        )

    # Section 18: Data Requirements
    if is_attendance:
        sections["data_requirements"] = make_sec(
            "data_requirements",
            "- Core entities: Student, FacultyInstructor, CourseSection, AttendanceRecord, CondonationPetition.\n- Real-time calculation: `(attended eligible sessions / total eligible sessions) * 100`.\n- Tamper-evident ledger logging with instructor identity and timestamp."
        )
    elif is_warehouse:
        sections["data_requirements"] = make_sec(
            "data_requirements",
            "- Core entities: AGVUnit, WarehouseGridNode, PalletMission, DockStation, RouteObstruction.\n- Immutable mission dispatch telemetry log with microsecond timestamp."
        )
    elif is_telehealth:
        sections["data_requirements"] = make_sec(
            "data_requirements",
            "- Core entities: PediatricPatient, GuardianAccount, PediatricianProfile, ConsultationSession, ClinicalNote.\n- Immutable clinical encounter audit log with practitioner cryptographic signature."
        )
    else:
        sections["data_requirements"] = make_sec(
            "data_requirements",
            "- Core entities: CustomerSession, ChatMessage, KBArticleReference, EscalationTicket, ResolutionAudit.\n- Active chat session state is cached up to 24 hours; archival retention duration is documented as an Open Architectural Decision pending privacy review."
        )

    # Section 20: Security and Privacy Requirements
    sections["security_and_privacy_requirements"] = make_sec(
        "security_and_privacy_requirements",
        "- Role-Based Access Control (RBAC) enforced across all endpoints.\n- Data encrypted in transit using TLS 1.3 and at rest using AES-256.\n- Statutory regulatory compliance (GDPR, FERPA, HIPAA) marked as Open Decision pending institutional legal review."
    )

    # Section 21: Acceptance Criteria
    if is_attendance:
        sections["acceptance_criteria"] = make_sec(
            "acceptance_criteria",
            (
                "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
                "|---|---|---|\n"
                "| **AC-001** | FR-001 | Given an authenticated Faculty Instructor assigned to Course CS-101, When the instructor marks students Present or Absent and submits, Then official attendance records are committed to the ledger. |\n"
                "| **AC-002** | FR-001 | Given an instructor submitting an incomplete roster, When submission is evaluated, Then the system flags unrecorded students and prompts for completion. |\n"
                "| **AC-003** | FR-002 | Given a student with exactly 18 out of 24 attended sessions (75.0%), When attendance percentage is calculated, Then the system marks student as Eligible and suppresses warning alerts. |\n"
                "| **AC-004** | FR-002 | Given a student with 17 out of 24 attended sessions (70.83%), When calculated, Then the system marks student At Risk and triggers early warning notification. |\n"
                "| **AC-005** | FR-002 | Given a student with 20 out of 24 attended sessions (83.33%), When calculated, Then the system marks student In Good Standing with no warnings. |\n"
                "| **AC-006** | FR-003 | Given attendance has already been recorded for Course CS-101 on the selected date, When a second roll call is submitted, Then system rejects duplicate submission with an Attendance already recorded warning. |\n"
                "| **AC-007** | FR-004 | Given a student dropping strictly below 75.0%, When attendance falls below threshold, Then automated notification is dispatched to student and advisor detailing classes required to recover. |\n"
                "| **AC-008** | FR-005 | Given a documented medical excuse submitted to Department Head, When approved, Then student eligibility is updated to Condoned - Eligible while preserving physical roll call records. |\n"
            )
        )
    elif is_warehouse:
        sections["acceptance_criteria"] = make_sec(
            "acceptance_criteria",
            (
                "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
                "|---|---|---|\n"
                "| **AC-001** | FR-001 | Given an active pallet mission request, When an AGV is assigned, Then mission status is dispatched and committed to fleet ledger. |\n"
                "| **AC-002** | FR-002 | Given two AGVs on converging grid coordinates, When routing is evaluated, Then collision-free paths are calculated avoiding intersection conflicts. |\n"
                "| **AC-003** | FR-003 | Given an AGV battery reporting 19.9% (< 20.0%), When state of charge is checked, Then the robot is routed to an open charging dock immediately. |\n"
            )
        )
    elif is_telehealth:
        sections["acceptance_criteria"] = make_sec(
            "acceptance_criteria",
            (
                "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
                "|---|---|---|\n"
                "| **AC-001** | FR-001 | Given a verified pediatric consultation request, When confirmed, Then video room tokens are generated and sent to guardian. |\n"
                "| **AC-002** | FR-002 | Given an unverified guardian account, When video room admission is requested, Then access is halted until digital parental consent is executed. |\n"
                "| **AC-003** | FR-003 | Given a concluded clinical consultation, When pediatrician submits encounter notes, Then encrypted records are committed to patient chart with audit timestamp. |\n"
            )
        )
    else:
        sections["acceptance_criteria"] = make_sec(
            "acceptance_criteria",
            (
                "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
                "|---|---|---|\n"
                "| **AC-001** | FR-001 | Given a customer submits a question, When evaluated against the knowledge base, Then answers cite approved source article references. |\n"
                "| **AC-002** | FR-001 | Given an answer candidate with no approved KB article, When evaluated, Then automated answer is suppressed and customer offered human escalation. |\n"
                "| **AC-003** | FR-002 | Given a multi-turn chat session, When customer asks a follow-up question, Then conversation context from previous turns is preserved. |\n"
                "| **AC-004** | FR-002 | Given an active chat session, When session continues across dialogue turns, Then transcript continuity is maintained in session memory. |\n"
                "| **AC-005** | FR-003 | Given an answer candidate with evaluated confidence of 79.9% (< 80.0%), When evaluated, Then automatic response is prohibited and query is escalated to a human agent with conversation summary. |\n"
                "| **AC-006** | FR-003 | Given an answer candidate with evaluated confidence of exactly 80.0%, When evaluated, Then automatic response is permitted and delivered to customer. |\n"
                "| **AC-007** | FR-004 | Given an answer candidate with evaluated confidence of 80.1%, When evaluated, Then automatic response is permitted with verified article citations. |\n"
                "| **AC-008** | FR-004 | Given an escalation event occurs, When transferred to a representative, Then the agent dashboard receives the full transcript and structured 3-bullet summary without prompting customer to re-enter issue details. |\n"
                "| **AC-009** | FR-005 | Given a human representative completes inquiry handling, When ticket is resolved, Then disposition notes and handling duration are committed to permanent audit ledger. |\n"
            )
        )

    return sections

# ----------------------------------------------------------------------
# POSITIVE FIXTURES (4 Domains)
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_positive_customer_support_prd():
    """Verify clean, domain-grounded Customer Support PRD passes with score >= 85 and verdict APPROVED."""
    sections = make_valid_sections("AI Customer Support Assistant", "AI Customer Support Assistant", version="v2.4.1")
    prd_version = PRDVersion(
        prd_id="prd_cust_supp",
        project_id="proj_cust_supp",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_cust_supp",
        problem_domain="Customer Support Operations",
        product_category="AI Customer Support Assistant",
        intended_users=["Customer", "Customer Service Representative"],
        core_objectives=["Provide grounded answers using approved knowledge base articles", "Escalate low-confidence queries below 80% to human agents with 3-bullet summary"],
        expected_capabilities=["Grounded Q&A retrieval", "Multi-turn session memory", "80% confidence threshold evaluation", "Human agent escalation"],
        explicit_constraints=["Web chat only", "80% confidence threshold for answer delivery", "No external CRM sync in MVP", "No external ticketing in MVP"],
        facts=["Answers must cite approved knowledge-base articles", "Confidence threshold is 80%"]
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version, analysis)

    assert report.is_valid is True, f"Validation failed: {[f'{i.rule_id}: {i.title}' for i in report.issues if i.severity == 'error']}"
    assert report.verdict == "APPROVED"
    assert report.score >= 85
    assert report.error_count == 0

@pytest.mark.asyncio
async def test_positive_attendance_management_prd():
    """Verify clean College Attendance Management PRD passes with score >= 85 and verdict APPROVED."""
    sections = make_valid_sections("College Attendance Management System", "Collegiate Attendance Management", version="v2.4.1", is_attendance=True)
    prd_version = PRDVersion(
        prd_id="prd_attendance",
        project_id="proj_attendance",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_attendance",
        problem_domain="Collegiate Attendance Management",
        product_category="College Attendance Management System",
        intended_users=["Faculty Instructor", "Student", "Department Head"],
        core_objectives=["Record daily attendance roll calls", "Calculate cumulative attendance percentage", "Alert students below 75% threshold"],
        expected_capabilities=["Lecture roll call recording", "Attendance percentage calculation", "Low-attendance warning dispatch", "Duplicate entry prevention"],
        explicit_constraints=["75% minimum attendance eligibility threshold", "Only assigned faculty record attendance", "No biometric scanning hardware"],
        facts=["Attendance threshold is 75%", "Roll calls recorded by faculty"]
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version, analysis)

    assert report.is_valid is True, f"Validation failed: {[f'{i.rule_id}: {i.title}' for i in report.issues if i.severity == 'error']}"
    assert report.verdict == "APPROVED"
    assert report.score >= 85
    assert report.error_count == 0

@pytest.mark.asyncio
async def test_positive_warehouse_robotics_agv_prd():
    """Verify Autonomous Warehouse AGV Fleet PRD passes with score >= 85 and verdict APPROVED."""
    sections = make_valid_sections("Autonomous Warehouse AGV Fleet", "Autonomous Logistics & Warehouse Robotics", version="v2.4.1", is_warehouse=True)
    prd_version = PRDVersion(
        prd_id="prd_warehouse",
        project_id="proj_warehouse",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_warehouse",
        problem_domain="Autonomous Logistics & Warehouse Robotics",
        product_category="Autonomous Warehouse AGV Fleet",
        intended_users=["Warehouse Floor Operator", "Fleet Operations Supervisor"],
        core_objectives=["Schedule autonomous AGV pallet missions", "Avoid grid collisions", "Route to charging docks below 20% battery"],
        expected_capabilities=["Mission dispatch", "Collision-free routing", "Automated low-battery docking"],
        explicit_constraints=["20% minimum battery docking threshold", "Grid navigation only", "Emergency halt takes precedence"],
        facts=["Low-battery threshold is 20%"]
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version, analysis)

    assert report.is_valid is True, f"Validation failed: {[f'{i.rule_id}: {i.title}' for i in report.issues if i.severity == 'error']}"
    assert report.verdict == "APPROVED"
    assert report.score >= 85
    assert report.error_count == 0

@pytest.mark.asyncio
async def test_positive_pediatric_telehealth_prd():
    """Verify Remote Pediatric Telehealth PRD passes with score >= 85 and verdict APPROVED."""
    sections = make_valid_sections("Remote Pediatric Telehealth Platform", "Pediatric Clinical Telehealth", version="v2.4.1", is_telehealth=True)
    prd_version = PRDVersion(
        prd_id="prd_telehealth",
        project_id="proj_telehealth",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_telehealth",
        problem_domain="Pediatric Clinical Telehealth",
        product_category="Remote Pediatric Telehealth Platform",
        intended_users=["Pediatrician", "Parent / Legal Guardian"],
        core_objectives=["Conduct secure video pediatric encounters", "Verify guardian legal consent", "Maintain audit-compliant encounter notes"],
        expected_capabilities=["Pediatric encounter scheduling", "Guardian authorization verification", "Clinical encounter notes ledger"],
        explicit_constraints=["Guardian consent mandatory before video admission", "Licensed pediatricians only", "Encrypted video streams"],
        facts=["Parental consent required for pediatric care"]
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version, analysis)

    assert report.is_valid is True, f"Validation failed: {[f'{i.rule_id}: {i.title}' for i in report.issues if i.severity == 'error']}"
    assert report.verdict == "APPROVED"
    assert report.score >= 85
    assert report.error_count == 0

# ----------------------------------------------------------------------
# NEGATIVE FIXTURES (8 Defects)
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_negative_conflicting_retention_periods():
    """Negative Fixture 1: Conflicting retention periods (24h in Section 18 vs 30d in Section 12). Fails VAL-XSEC-002."""
    sections = make_valid_sections("AI Customer Support Assistant", "AI Customer Support Assistant", version="v2.4.1")
    # Inject 30-day retention conflict in FR-002
    sections["functional_requirements"] = make_sec(
        "functional_requirements",
        sections["functional_requirements"].content + "\n\n**Retention Policy:** The system shall enforce retention of at least 30 days for all customer conversation transcripts."
    )
    prd_version = PRDVersion(
        prd_id="prd_neg_ret",
        project_id="proj_neg_ret",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"
    assert report.score <= 65
    assert any(i.rule_id == "VAL-XSEC-002" for i in report.issues)

@pytest.mark.asyncio
async def test_negative_external_ticketing_contradiction():
    """Negative Fixture 2: External ticketing declared out-of-scope, but mandatory Zendesk API required in integration. Fails VAL-XSEC-004."""
    sections = make_valid_sections("AI Customer Support Assistant", "AI Customer Support Assistant", version="v2.4.1")
    # Inject mandatory Zendesk API in integration requirements
    sections["integration_requirements"] = make_sec(
        "integration_requirements",
        "- Mandatory Zendesk API integration for escalation handling and external ticket synchronization."
    )
    prd_version = PRDVersion(
        prd_id="prd_neg_ticket",
        project_id="proj_neg_ticket",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"
    assert report.score <= 65
    assert any(i.rule_id in ["VAL-XSEC-004", "VAL-SEM-004"] for i in report.issues)

@pytest.mark.asyncio
async def test_negative_unsupported_numerical_sla():
    """Negative Fixture 3: Unsupported operational latency SLA ('within 2 seconds') claimed as firm FR without provenance. Fails VAL-NUM-001."""
    sections = make_valid_sections("AI Customer Support Assistant", "AI Customer Support Assistant", version="v2.4.1")
    sections["functional_requirements"] = make_sec(
        "functional_requirements",
        sections["functional_requirements"].content + "\n\n#### FR-006: Operational Latency Guarantee\n- **Description:** Human escalation handoff must be initiated within 2 seconds of detection.\n- **Priority:** Must Have\n- **Provenance:** `confirmed_user_input`"
    )
    analysis = AnalysisRecord(
        project_id="proj_neg_num",
        problem_domain="Customer Support",
        product_category="AI Assistant",
        intended_users=["Customer"],
        core_objectives=["Support customers"],
        explicit_constraints=["Web chat only"],
        facts=["80% confidence threshold"]
    )
    prd_version = PRDVersion(
        prd_id="prd_neg_num",
        project_id="proj_neg_num",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version, analysis)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"
    assert report.score <= 65
    assert any(i.rule_id == "VAL-NUM-001" for i in report.issues)

@pytest.mark.asyncio
async def test_negative_generic_duplicate_acceptance_criteria():
    """Negative Fixture 4: Acceptance criteria uses formulaic field concatenation run-on sentence. Fails VAL-AC-004."""
    sections = make_valid_sections("AI Customer Support Assistant", "AI Customer Support Assistant", version="v2.4.1")
    sections["acceptance_criteria"] = make_sec(
        "acceptance_criteria",
        (
            "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
            "|---|---|---|\n"
            "| **AC-001** | FR-001 | Given Customer initiates grounded Q&A with valid question, When processed under business rules, Then the system fulfills the requirement and records outcome. |\n"
            "| **AC-002** | FR-001 | Given Customer initiates grounded Q&A with valid question, When processed under business rules, Then the system fulfills the requirement and records outcome. |\n"
            "| **AC-003** | FR-002 | Given Customer initiates session history with session token, When processed under governing rules, Then the system fulfills the requirement and records outcome. |\n"
        )
    )
    prd_version = PRDVersion(
        prd_id="prd_neg_ac",
        project_id="proj_neg_ac",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"
    assert report.score <= 65
    assert any(i.rule_id in ["VAL-AC-004", "VAL-AC-003"] for i in report.issues)

@pytest.mark.asyncio
async def test_negative_empty_mandatory_nfr_section():
    """Negative Fixture 5: Empty mandatory NFR section with table header and 0 data rows. Fails VAL-STR-002."""
    sections = make_valid_sections("AI Customer Support Assistant", "AI Customer Support Assistant", version="v2.4.1")
    # Empty NFR table header only
    sections["non_functional_requirements"] = make_sec(
        "non_functional_requirements",
        "| ID | Title | Description | Classification | Priority |\n|---|---|---|---|---|\n"
    )
    prd_version = PRDVersion(
        prd_id="prd_neg_nfr",
        project_id="proj_neg_nfr",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"
    assert report.score <= 65
    assert any(i.rule_id == "VAL-STR-002" for i in report.issues)

@pytest.mark.asyncio
async def test_negative_unsupported_user_journey_capabilities():
    """Negative Fixture 6: User journey includes unsupported out-of-scope capability ('schedule a call back'). Fails VAL-UJ-001."""
    sections = make_valid_sections("AI Customer Support Assistant", "AI Customer Support Assistant", version="v2.4.1")
    # Inject unsupported callback in user journeys
    sections["user_journeys"] = make_sec(
        "user_journeys",
        sections["user_journeys"].content + "\n- Edge Case: If no human representative is active, the assistant offers to schedule a call back over telephone."
    )
    prd_version = PRDVersion(
        prd_id="prd_neg_uj",
        project_id="proj_neg_uj",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"
    assert report.score <= 65
    assert any(i.rule_id == "VAL-UJ-001" for i in report.issues)

@pytest.mark.asyncio
async def test_negative_provenance_misclassification():
    """Negative Fixture 7: Business rule uses ungrounded metric ('85%') tagged as confirmed_user_input. Fails VAL-PROV-001."""
    sections = make_valid_sections("AI Customer Support Assistant", "AI Customer Support Assistant", version="v2.4.1")
    sections["business_rules"] = make_sec(
        "business_rules",
        (
            "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
            "|---|---|---|---|---|---|---|\n"
            "| **BR-001** | Strict 85% Confidence Rule | Automated responses require 85% confidence score | `confirmed_user_input` | User Constraints | Accuracy | No (Confirmed) |\n"
        )
    )
    analysis = AnalysisRecord(
        project_id="proj_neg_prov",
        problem_domain="Customer Support",
        product_category="AI Assistant",
        intended_users=["Customer"],
        core_objectives=["Support"],
        explicit_constraints=["80% threshold"],
        facts=["80% threshold"]
    )
    prd_version = PRDVersion(
        prd_id="prd_neg_prov",
        project_id="proj_neg_prov",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version, analysis)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"
    assert report.score <= 65
    assert any(i.rule_id == "VAL-PROV-001" for i in report.issues)

@pytest.mark.asyncio
async def test_negative_document_version_mismatch():
    """Negative Fixture 8: Document header states v1.0 while PRDVersion states v2.4.1. Fails VAL-VER-001."""
    sections = make_valid_sections("AI Customer Support Assistant", "AI Customer Support Assistant", version="v1.0")
    prd_version = PRDVersion(
        prd_id="prd_neg_ver",
        project_id="proj_neg_ver",
        version_number="v2.4.1",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_version)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"
    assert report.score <= 65
    assert any(i.rule_id == "VAL-VER-001" for i in report.issues)
