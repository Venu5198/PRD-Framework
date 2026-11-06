import pytest
import os
import re
from datetime import datetime
from app.models.prd import PRDVersion, PRDSectionContent, CANONICAL_SECTIONS, SECTION_TITLES
from app.models.analysis import AnalysisRecord
from app.services.validation_service import ValidationService

def make_clean_sections(domain: str = "support") -> dict:
    """Constructs a clean baseline set of 27 sections."""
    sections = {}
    for sec in CANONICAL_SECTIONS:
        sections[sec] = PRDSectionContent(
            key=sec,
            title=SECTION_TITLES[sec],
            content=f"Baseline verified technical specifications for {sec} in the {domain} domain."
        )

    sections["document_information"].content = (
        f"**Document Title:** Product Requirements Document\n\n"
        f"**Document ID:** PRD-TEST001\n\n"
        f"**Version:** v2.4.4\n\n"
        f"**Target Domain:** Customer Operations\n\n"
        f"**Product Category:** AI Assistant\n\n"
        f"**Status:** Draft"
    )

    sections["functional_requirements"].content = (
        "| ID | Title | Description | Priority | Traceable AC |\n"
        "|---|---|---|---|---|\n"
        "| **FR-001** | Query Ingestion | **Actor:** Customer. **Trigger:** Query submitted. **Preconditions:** Active session. **Inputs:** Text query. **System Behavior:** The system retrieves approved passages and synthesizes an answer citing source articles. **Business Constraints:** Answers must be grounded in approved KB. **Alternate & Failure Paths:** Escalates if confidence is low. **Expected Outcome:** Grounded answer delivered. **Relevant Data Changes:** Logs interaction. **Authorization Requirements:** Authenticated Customer. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-001 |\n"
        "| **FR-002** | Context Preservation | **Actor:** Customer. **Trigger:** Message sent. **Preconditions:** Active session. **Inputs:** Utterance. **System Behavior:** The system maintains chronological conversation history within the active support session. **Business Constraints:** Conversation history isolated per customer. **Alternate & Failure Paths:** Recovers from cache. **Expected Outcome:** History preserved. **Relevant Data Changes:** Appends dialogue turn. **Authorization Requirements:** Authenticated Customer. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-002 |\n"
        "| **FR-003** | Low-Confidence Escalation | **Actor:** AI Engine. **Trigger:** Answer evaluated. **Preconditions:** Confidence evaluated. **Inputs:** Confidence metric. **System Behavior:** The system evaluates answer confidence against the 80.0% threshold and escalates when confidence is below 80.0%. **Business Constraints:** Confidence threshold strictly 80.0%. **Alternate & Failure Paths:** Enqueues with context summary. **Expected Outcome:** Query escalated with summary. **Relevant Data Changes:** Updates queue ledger. **Authorization Requirements:** System Internal. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-003 |\n"
    )

    sections["non_functional_requirements"].content = (
        "| ID | Title | Description | Classification | Priority |\n"
        "|---|---|---|---|---|\n"
        "| **NFR-001** | Latency Target | System targets response generation under expected user bounds [Proposed Target: Subject to benchmark]. | Proposed target | Should Have |\n"
        "| **NFR-002** | Service Availability | System targets high operational availability with automated recovery [Proposed Target: Subject to deployment]. | Proposed target | Should Have |\n"
    )

    sections["business_rules"].content = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Confidence Gating | Automated answers require evaluated confidence >= 80.0%. | `USER_CONFIRMED` | User Objective | Quality assurance | No (Confirmed) |\n"
        "| **BR-002** | Knowledge Base Grounding | Answers must cite approved knowledge-base articles. | `USER_CONFIRMED` | User Objective | Hallucination prevention | No (Confirmed) |\n"
    )

    sections["acceptance_criteria"].content = (
        "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
        "|---|---|---|\n"
        "| **AC-001** | FR-001 | Given an active chat session, When customer submits query, Then the system retrieves verified article passages and returns grounded answer. |\n"
        "| **AC-002** | FR-002 | Given an ongoing conversation, When customer sends message, Then the system preserves chronological turn order. |\n"
        "| **AC-003** | FR-003 | Given an answer candidate with evaluated confidence below 80.0%, When evaluated, Then the system escalates to human queue with summary. |\n"
    )

    sections["user_journeys"].content = (
        "```mermaid\n"
        "sequenceDiagram\n"
        "    actor Customer as Customer\n"
        "    participant AppSystem as AI Support System\n"
        "    Customer->>AppSystem: Submits inquiry in chat window\n"
        "    AppSystem->>AppSystem: Evaluates answer confidence against 80% threshold\n"
        "    AppSystem-->>Customer: Delivers verified response citing approved source\n"
        "```\n\n"
        "### Step-by-Step User Journey Progression\n"
        "**Stage 1: Customer Inquiry**\n"
        "- **Actor (Customer):** Submits question.\n"
        "- **System Response:** Evaluates confidence and returns answer or escalates.\n"
    )

    sections["data_requirements"].content = (
        "Core entities: User, Session, Message, Article, EscalationInquiry.\n"
        "Persistence: Datastore technology selection (e.g. relational store, document store) is an [Open Architectural Decision] pending infrastructure review.\n"
        "Retention: Active dialogue transcripts retained for session duration. Long-term archival retention is an [Open Architectural Decision] pending legal compliance review."
    )

    sections["security_and_privacy_requirements"].content = (
        "RBAC enforced for Customer and Support Representative roles.\n"
        "Data Encryption: Industry-standard TLS for in-transit calls and AES at rest [Proposed Target: Encryption suite subject to security review].\n"
        "Regulatory Compliance: Statutory compliance frameworks (GDPR, CCPA) are subject to institutional privacy assessment and formal legal review [Open Decision]."
    )

    sections["dependencies_and_constraints"].content = (
        "Platform: Standard web browser viewports over secure HTTPS.\n"
        "Hosting: Deployment environment (cloud vs on-premises) is an [Open Architectural Decision] subject to infrastructure team review.\n"
        "Scope: External ticketing platforms and telephony channels are out of scope for MVP."
    )

    sections["success_metrics"].content = (
        "- **Threshold Adherence:** 100% of candidate answers with confidence < 80.0% escalated with summary.\n"
        "- **Grounded Response Rate:** 100% of delivered automated responses cite verified knowledge-base articles.\n"
        "- **Target Resolution Efficiency:** Target 70% resolution efficiency [Proposed Target: Subject to baseline benchmark]."
    )

    sections["out_of_scope"].content = (
        "The following capabilities are strictly out of scope for MVP:\n"
        "- External ticketing platforms (Zendesk, Jira, ServiceNow) and third-party ticketing integration.\n"
        "- Telephony and voice IVR channel integration.\n"
        "- Autonomous account modification without representative confirmation."
    )

    sections["user_personas"].content = (
        "| Persona ID | Role / Archetype | Responsibilities & Goals | Pain Points | Success Outcome |\n"
        "|---|---|---|---|---|\n"
        "| **P-001** | Customer | Submit operational inquiries and receive rapid, grounded answers. | Hallucinated or slow responses. | Accurate answer citing sources. |\n"
        "| **P-002** | Support Representative | Review escalated inquiries and maintain resolution queue. | Uncategorized or ungrounded escalations. | Clear summary context. |\n"
    )

    sections["risks_and_mitigation"].content = (
        "| Risk ID | Risk Category | Failure Scenario / Description | Severity | Likelihood | Mitigation Strategy | Contingency Plan |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **RSK-001** | AI Reliability | LLM produces hallucinated answer unsupported by source text. | High | Low | Enforce mandatory KB passage grounding and strict 80% confidence threshold. | Immediate human escalation with context summary. |\n"
        "| **RSK-002** | Escalation Queue | Escalation queue experiences traffic surge during peak hours. | High | Medium | Implement priority queuing and turn-level summary condensation. | Representative triage mode. |\n"
        "| **RSK-003** | Knowledge Base Staleness | Customer asks question on outdated or newly changed product terms. | Medium | Medium | Version and timestamp all ingested knowledge articles. | Flag outdated articles for maintainer review. |\n"
    )

    return sections

def make_clean_prd(version_number: str = "v2.4.4") -> PRDVersion:
    return PRDVersion(
        id="clean_ver_001",
        prd_id="prd_test_001",
        project_id="proj_test_001",
        version_number=version_number,
        status="draft",
        sections=make_clean_sections(),
        content_hash="a"*64,
        changelog="Clean test version"
    )

def make_analysis() -> AnalysisRecord:
    return AnalysisRecord(
        project_id="proj_test_001",
        problem_domain="Customer Support Operations",
        product_category="AI Support Assistant",
        core_objectives=["Answer customer questions using approved knowledge base", "Escalate low-confidence queries below 80% to human agents"],
        intended_users=["Customer", "Support Representative"],
        expected_capabilities=["Grounded answers", "Conversation history", "Smart escalation"],
        explicit_constraints=["Confidence threshold 80%", "Out of scope: external ticketing, telephony"],
        facts=["80% confidence threshold"]
    )

@pytest.mark.asyncio
async def test_negative_customer_support_v2_4_3_artifact_rejected():
    """Verify that the actual Phase 2.4.3 Customer Support PRD is strictly rejected due to identified defects."""
    val = ValidationService()
    path = "docs/benchmark/PRD_Customer_Support_Final.md"
    if not os.path.exists(path):
        path = "PRD_Customer_Support_Final.md"
    
    assert os.path.exists(path), f"PRD artifact {path} not found"
    with open(path, "r", encoding="utf-8") as f:
        md_text = f.read()

    sections = {}
    for sec_k in CANONICAL_SECTIONS:
        title = SECTION_TITLES[sec_k]
        pattern = rf"##\s*(?:\d+\.\s*)?{re.escape(title)}\s*\n([\s\S]*?)(?=\n##|\Z)"
        match = re.search(pattern, md_text)
        content = match.group(1).strip() if match else "Content not found"
        sections[sec_k] = PRDSectionContent(key=sec_k, title=title, content=content)

    prd_ver = PRDVersion(
        id="v2_4_3_artifact",
        prd_id="prd_cs",
        project_id="proj_cs",
        version_number="v2.4.3",
        status="draft",
        sections=sections,
        content_hash="501f03185b290057e33a14aeef774e53c10a9d29ab1b1e649c1dd5bc3b4e8177"
    )

    report = await val.validate_version(prd_ver, make_analysis())
    assert not report.is_valid, "Expected Phase 2.4.3 artifact to fail validation"
    assert report.verdict == "REJECTED", f"Expected REJECTED verdict, got {report.verdict}"
    assert report.error_count > 0, "Expected multiple blocking errors on Phase 2.4.3 artifact"

# =========================================================================
# 25 MANDATORY NEGATIVE REGRESSION FIXTURES
# =========================================================================

@pytest.mark.asyncio
async def test_negative_01_malformed_fr_grammar():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["functional_requirements"].content += "\n| **FR-004** | Bad Grammar | The system the AI searches and The system append data. | Must Have | AC-001 |\n"
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-GRAM-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_02_truncated_mermaid_diagram():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["user_journeys"].content = "```mermaid\nsequenceDiagram\nCustomer->>AppSystem: types a description of\n```"
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-DIA-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_03_incorrect_actor_responsibilities():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["user_journeys"].content = "```mermaid\nsequenceDiagram\nactor SupportRepresentative as Support Representative\nSupportRepresentative->>AppSystem: Calculates confidence score for generated answer\n```"
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-ACT-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_04_unsupported_wait_time_estimates():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["user_journeys"].content += "\nIf the queue is full, AI informs the customer of an expected wait time of 15 minutes."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-NUM-004" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_05_unsupported_success_metrics():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["success_metrics"].content = "1. AI-only resolution rate >= 70% of total queries. 2. Post-interaction CSAT score >= 4.5/5. 3. Average handling time <= 5 minutes."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-NUM-003" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_06_unsupported_latency_targets():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["non_functional_requirements"].content += "\n| **NFR-003** | Firm Latency | The system shall respond within 2 seconds under peak load. | Confirmed requirement | Must Have |\n"
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-NUM-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_07_unsupported_confidence_targets():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["business_rules"].content += "\n| **BR-003** | Wrong Conf | System targets 85% average confidence score for all answers. | confirmed_user_input | User | Quality | No |\n"
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id in ("VAL-NUM-002", "VAL-NUM-003", "VAL-ENG-003") for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_08_retention_conflict_24h_vs_30d():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["security_and_privacy_requirements"].content += "\nConversation transcripts are retained for 30 days before purge."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id in ("VAL-XSEC-002", "VAL-XSEC-004", "VAL-RET-001") for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_09_unsupported_analytics_and_audit_retention():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["security_and_privacy_requirements"].content += "\nAnalytics are aggregated and retained for 90 days, while audit logs are retained for 1 year."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-RET-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_10_unsupported_gdpr_compliance_claims():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["security_and_privacy_requirements"].content += "\nThe platform guarantees full compliance with GDPR and CCPA statutory requirements."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-PRIV-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_11_unconfirmed_postgresql_mandate():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["data_requirements"].content += "\nRelational store (e.g., PostgreSQL) for all users and sessions is mandatory."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-ARCH-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_12_unconfirmed_timeseries_database_mandate():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["data_requirements"].content += "\nTime-series or columnar store is required for all analytics telemetry."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-ARCH-002" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_13_unconfirmed_immutable_log_store_mandate():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["data_requirements"].content += "\nImmutable log store is mandated for tamper-proof auditing."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-ARCH-003" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_14_unsupported_cloud_onprem_hosting_mandate():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["dependencies_and_constraints"].content += "\nMust be hosted on-premise in local data center."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-ARCH-004" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_15_unsupported_multiregion_active_active_mandate():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["dependencies_and_constraints"].content += "\nHigh availability requires multi-region active-active deployment across two cloud zones."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-ARCH-005" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_16_acceptance_criteria_introducing_unsupported_functionality():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["acceptance_criteria"].content += "\n| **AC-008** | FR-002 | Given an inactive chat session exceeding the 24-hour active window, When a customer sends a new message, Then the system initializes a fresh session ID. |\n"
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-AC-002" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_17_conflicting_word_limits():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["functional_requirements"].content += "\nContext summary must be 150 words."
    prd.sections["acceptance_criteria"].content += "\nContext summary not exceeding 200 words."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-XSEC-006" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_18_proposed_nfr_incorrectly_marked_must_have():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["non_functional_requirements"].content = (
        "| ID | Title | Description | Classification | Priority |\n"
        "|---|---|---|---|---|\n"
        "| **NFR-001** | Answer Latency | Response generated under user expectations. | Proposed target | Must Have |\n"
    )
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-NFR-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_19_duplicate_business_rule_identifiers():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["business_rules"].content += "\n| **BR-001** | Duplicate BR | Operational statement duplicate. | `USER_CONFIRMED` | Ref | Rat | No |\n"
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-DUP-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_20_unsupported_stakeholder_roles():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["user_personas"].content += "\n### Support Manager\nResponsibilities include staffing optimization and reviewing escalation volumes on accuracy dashboard."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-SEM-007" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_21_draft_document_reported_as_approved():
    val = ValidationService()
    prd = make_clean_prd()
    # Has a failing issue AND claims Approved status
    prd.sections["functional_requirements"].content += "\nThe system the AI searches broken."
    prd.sections["document_information"].content = (
        f"**Document Title:** Product Requirements Document\n\n"
        f"**Document ID:** PRD-TEST001\n\n"
        f"**Version:** v2.4.4\n\n"
        f"**Status:** Approved"
    )
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-STAT-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_22_project_document_version_mismatch():
    val = ValidationService()
    prd = make_clean_prd(version_number="v2.4.4")
    prd.sections["document_information"].content = prd.sections["document_information"].content.replace("v2.4.4", "v1.0")
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-VER-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_23_invalid_artifact_hash():
    val = ValidationService()
    prd = make_clean_prd()
    prd.content_hash = "a" * 64
    prd.sections["document_information"].content += f"\n\n**SHA-256:** `{'b'*64}`"
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id == "VAL-HASH-001" for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_24_missing_provenance_for_material_claims():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["business_rules"].content = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Rule Without Provenance | Grounded answers strictly required. | `unverified_guess` | None | Rationale | No |\n"
    )
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id in ("VAL-PROV-001", "VAL-SEM-003") for i in report.issues)
    assert report.verdict == "REJECTED"

@pytest.mark.asyncio
async def test_negative_25_excluded_functionality_reintroduced():
    val = ValidationService()
    prd = make_clean_prd()
    prd.sections["system_workflows"].content += "\nWhen complex, system automatically creates Zendesk ticket via third-party ticketing integration."
    report = await val.validate_version(prd, make_analysis())
    assert any(i.rule_id in ("VAL-SEM-004", "VAL-SCP-002") for i in report.issues)
    assert report.verdict == "REJECTED"

# =========================================================================
# 4 POSITIVE DOMAIN FIXTURES
# =========================================================================

@pytest.mark.asyncio
async def test_positive_customer_support_prd_passes():
    val = ValidationService()
    prd = make_clean_prd()
    report = await val.validate_version(prd, make_analysis())
    assert report.is_valid, f"Expected clean Customer Support PRD to pass, got issues: {[i.rule_id + ': ' + i.title for i in report.issues]}"
    assert report.error_count == 0
    assert report.verdict == "APPROVED"
    assert report.score >= 85

@pytest.mark.asyncio
async def test_positive_attendance_management_prd_passes():
    val = ValidationService()
    prd = make_clean_prd()
    analysis = AnalysisRecord(
        project_id="proj_att",
        problem_domain="Academic Student Management",
        product_category="College Attendance System",
        core_objectives=["Record student lecture roll call", "Compute 75% examination eligibility threshold", "Trigger condonation warning when attendance is below 75%"],
        intended_users=["Course Instructor", "Student", "Department Head"],
        expected_capabilities=["Lecture roll call", "Eligibility calculation", "Condonation workflow"],
        explicit_constraints=["Minimum 75% lecture attendance required for exam eligibility"],
        facts=["75% attendance threshold for examination eligibility"]
    )
    prd.sections["document_information"].content = (
        "**Document Title:** Product Requirements Document for College Attendance System\n\n"
        "**Document ID:** PRD-ATT001\n\n**Version:** v2.4.4\n\n**Target Domain:** Academic Student Management\n\n"
        "**Product Category:** College Attendance System\n\n**Status:** Draft"
    )
    prd.sections["functional_requirements"].content = (
        "| ID | Title | Description | Priority | Traceable AC |\n"
        "|---|---|---|---|---|\n"
        "| **FR-001** | Roll Call Recording | **Actor:** Course Instructor. **Trigger:** Session roll call. **Preconditions:** Active lecture session. **Inputs:** Student attendance list. **System Behavior:** The system records student attendance for the conducted course section. **Business Constraints:** Rejects duplicate submissions for same section and date. **Alternate & Failure Paths:** Preserves records on network drop. **Expected Outcome:** Roll call persisted. **Relevant Data Changes:** Appends attendance records. **Authorization Requirements:** Authenticated Course Instructor. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-001 |\n"
        "| **FR-002** | Examination Eligibility Calculation | **Actor:** Course Instructor / Student. **Trigger:** Attendance inquiry. **Preconditions:** Active enrollment. **Inputs:** Student ID and Course code. **System Behavior:** The system computes percentage attendance as attended sessions divided by total conducted sessions multiplied by 100. **Business Constraints:** Minimum 75% attendance required for examination eligibility. **Alternate & Failure Paths:** Renders zero sessions without crash if total conducted is zero. **Expected Outcome:** Accurate percentage computed. **Relevant Data Changes:** Updates eligibility status. **Authorization Requirements:** Authenticated Student or Instructor. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-002 |\n"
        "| **FR-003** | Condonation Workflow | **Actor:** Department Head. **Trigger:** Condonation request. **Preconditions:** Student attendance below 75%. **Inputs:** Medical certificate. **System Behavior:** The system evaluates condonation justification and records formal waiver if approved. **Business Constraints:** Requires Department Head authorization. **Alternate & Failure Paths:** Rejects unverified requests. **Expected Outcome:** Condonation state updated. **Relevant Data Changes:** Appends condonation ledger. **Authorization Requirements:** Authenticated Department Head. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-003 |\n"
    )
    prd.sections["acceptance_criteria"].content = (
        "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
        "|---|---|---|\n"
        "| **AC-001** | FR-001 | Given Course CS-101 on a calendar date, When instructor submits roll call, Then the system records attendance and rejects duplicates. |\n"
        "| **AC-002** | FR-002 | Given a student who has attended 18 of 24 sessions (75.0%), When eligibility is evaluated, Then the system marks student Eligible for Examination. |\n"
        "| **AC-003** | FR-003 | Given a student with 70.8% attendance and verified medical certificate, When Department Head approves waiver, Then the system marks status Condoned - Eligible. |\n"
    )
    prd.sections["business_rules"].content = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Minimum Attendance Threshold | Students must maintain at least 75% attendance to qualify for semester examinations. | `USER_CONFIRMED` | Academic Policy | Academic standard | No (Confirmed) |\n"
        "| **BR-002** | Condonation Eligibility | Condonation waivers require formal Department Head sign-off with medical proof. | `USER_CONFIRMED` | Academic Regulation | Regulatory oversight | No (Confirmed) |\n"
    )
    report = await val.validate_version(prd, analysis)
    assert report.is_valid, f"Expected Attendance PRD to pass, got: {[i.rule_id + ': ' + i.title for i in report.issues]}"
    assert report.error_count == 0
    assert report.verdict == "APPROVED"

@pytest.mark.asyncio
async def test_positive_warehouse_agv_prd_passes():
    val = ValidationService()
    prd = make_clean_prd()
    analysis = AnalysisRecord(
        project_id="proj_agv",
        problem_domain="Industrial Warehouse Automation",
        product_category="Autonomous Guided Vehicle Dispatcher",
        core_objectives=["Dispatch AGV fleet for pallet transport", "Maintain collision-free path allocation", "Monitor battery telemetry and route to charging docks"],
        intended_users=["Fleet Supervisor", "Warehouse Material Handler"],
        expected_capabilities=["Fleet path dispatch", "Obstacle avoidance", "Automated charging docking"],
        explicit_constraints=["Maximum fleet speed 1.5 m/s", "Emergency stop within 300ms of obstacle detection"],
        facts=["AGV fleet navigation", "Maximum speed 1.5 m/s"]
    )
    prd.sections["document_information"].content = (
        "**Document Title:** Product Requirements Document for AGV Dispatcher\n\n"
        "**Document ID:** PRD-AGV001\n\n**Version:** v2.4.4\n\n**Target Domain:** Industrial Warehouse Automation\n\n"
        "**Product Category:** Autonomous Guided Vehicle Dispatcher\n\n**Status:** Draft"
    )
    prd.sections["functional_requirements"].content = (
        "| ID | Title | Description | Priority | Traceable AC |\n"
        "|---|---|---|---|---|\n"
        "| **FR-001** | Pallet Mission Dispatch | **Actor:** Warehouse Material Handler. **Trigger:** Transport mission created. **Preconditions:** AGV available in idle dock. **Inputs:** Pallet origin and destination. **System Behavior:** The system computes collision-free trajectory and dispatches mission to nearest available AGV. **Business Constraints:** Speed capped at 1.5 m/s. **Alternate & Failure Paths:** Re-routes if path is blocked. **Expected Outcome:** AGV executes transport. **Relevant Data Changes:** Updates mission status. **Authorization Requirements:** Authenticated Material Handler. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-001 |\n"
        "| **FR-002** | Obstacle Safety Halt | **Actor:** Fleet Supervisor. **Trigger:** Telemetry obstacle detection. **Preconditions:** AGV in active transit. **Inputs:** LiDAR proximity sensor vector. **System Behavior:** The system triggers immediate deceleration to halt AGV within 300ms. **Business Constraints:** Mandatory safety deceleration. **Alternate & Failure Paths:** Alerts supervisor if stall persists. **Expected Outcome:** AGV safely halted. **Relevant Data Changes:** Records safety event log. **Authorization Requirements:** System Safety Controller. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-002 |\n"
    )
    prd.sections["acceptance_criteria"].content = (
        "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
        "|---|---|---|\n"
        "| **AC-001** | FR-001 | Given an idle AGV at Dock A, When pallet mission to Dock B is dispatched, Then the system routes AGV at speed not exceeding 1.5 m/s. |\n"
        "| **AC-002** | FR-002 | Given an AGV moving at nominal speed, When LiDAR detects an obstacle under 1 meter, Then the system halts vehicle motion within 300ms. |\n"
    )
    prd.sections["business_rules"].content = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Fleet Velocity Cap | AGVs must never exceed 1.5 m/s in pedestrian-shared warehouse aisles. | `USER_CONFIRMED` | Safety Regulation | OSHA compliance | No (Confirmed) |\n"
    )
    report = await val.validate_version(prd, analysis)
    assert report.is_valid, f"Expected AGV PRD to pass, got: {[i.rule_id + ': ' + i.title for i in report.issues]}"
    assert report.error_count == 0
    assert report.verdict == "APPROVED"

@pytest.mark.asyncio
async def test_positive_pediatric_telehealth_prd_passes():
    val = ValidationService()
    prd = make_clean_prd()
    analysis = AnalysisRecord(
        project_id="proj_telehealth",
        problem_domain="Healthcare and Telemedicine",
        product_category="Pediatric Telehealth Portal",
        core_objectives=["Connect pediatricians with pediatric patients via video consultation", "Require verified guardian consent before session initialization", "Transmit electronic prescriptions to verified pharmacies"],
        intended_users=["Pediatrician", "Parent / Legal Guardian"],
        expected_capabilities=["Encrypted video consultation", "Parental consent verification", "E-Prescription dispatch"],
        explicit_constraints=["HIPAA compliance mandatory", "Guardian identity verification mandatory"],
        facts=["HIPAA compliance required", "Guardian consent required"]
    )
    prd.sections["document_information"].content = (
        "**Document Title:** Product Requirements Document for Pediatric Telehealth Portal\n\n"
        "**Document ID:** PRD-PEDS001\n\n**Version:** v2.4.4\n\n**Target Domain:** Healthcare and Telemedicine\n\n"
        "**Product Category:** Pediatric Telehealth Portal\n\n**Status:** Draft"
    )
    prd.sections["functional_requirements"].content = (
        "| ID | Title | Description | Priority | Traceable AC |\n"
        "|---|---|---|---|---|\n"
        "| **FR-001** | Guardian Consent Verification | **Actor:** Parent / Legal Guardian. **Trigger:** Telehealth appointment check-in. **Preconditions:** Active appointment scheduled. **Inputs:** Guardian biometric or digital signature. **System Behavior:** The system validates legal guardian authorization before admitting patient to video room. **Business Constraints:** Unaccompanied minors strictly prohibited from clinical room entry. **Alternate & Failure Paths:** Blocks room entry if consent missing. **Expected Outcome:** Consent logged and admission granted. **Relevant Data Changes:** Records HIPAA consent record. **Authorization Requirements:** Authenticated Legal Guardian. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-001 |\n"
        "| **FR-002** | Secure Clinical Video Call | **Actor:** Pediatrician. **Trigger:** Patient admitted with guardian consent. **Preconditions:** Valid consent on file. **Inputs:** Peer-to-peer WebRTC signaling tokens. **System Behavior:** The system establishes an end-to-end encrypted video stream between pediatrician and patient. **Business Constraints:** Audio and video streams must be encrypted using SRTP. **Alternate & Failure Paths:** Re-negotiates connection on packet loss. **Expected Outcome:** Encrypted video call established. **Relevant Data Changes:** Logs consultation duration. **Authorization Requirements:** Licensed Pediatrician. **Priority:** Must Have. **Provenance:** `USER_CONFIRMED` (User Input). | Must Have | AC-002 |\n"
    )
    prd.sections["acceptance_criteria"].content = (
        "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
        "|---|---|---|\n"
        "| **AC-001** | FR-001 | Given a minor patient check-in, When parent signs digital consent, Then the system admits patient and logs HIPAA consent record. |\n"
        "| **AC-002** | FR-002 | Given an active video consultation, When streams are negotiated, Then the system enforces end-to-end SRTP encryption. |\n"
    )
    prd.sections["business_rules"].content = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Mandatory Guardian Presence | Minor patients must have an authorized legal guardian present throughout the clinical consultation. | `USER_CONFIRMED` | Medical Board Policy | Pediatric safety standard | No (Confirmed) |\n"
    )
    report = await val.validate_version(prd, analysis)
    assert report.is_valid, f"Expected Telehealth PRD to pass, got: {[i.rule_id + ': ' + i.title for i in report.issues]}"
    assert report.error_count == 0
    assert report.verdict == "APPROVED"
