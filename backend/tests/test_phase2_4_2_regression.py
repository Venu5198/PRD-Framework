import os
import re
import pytest
from typing import Dict
from app.models.prd import PRDVersion, PRDSectionContent, CANONICAL_SECTIONS, SECTION_TITLES
from app.models.analysis import AnalysisRecord
from app.services.validation_service import ValidationService
from tests.test_phase2_4_1_fixtures import make_valid_sections

def parse_markdown_to_sections(md_text: str) -> Dict[str, PRDSectionContent]:
    pattern = r"##\s+(\d+)\.\s+([^\n]+)\n"
    matches = list(re.finditer(pattern, md_text))
    sections = {}
    for i, m in enumerate(matches):
        sec_num = int(m.group(1))
        matched_key = CANONICAL_SECTIONS[sec_num - 1]
        start_idx = m.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        content = md_text[start_idx:end_idx].strip()
        sections[matched_key] = PRDSectionContent(
            key=matched_key,
            title=SECTION_TITLES[matched_key],
            content=content
        )
    return sections


@pytest.mark.asyncio
async def test_negative_customer_support_v2_4_1_artifact():
    """
    Mandatory Regression Gate:
    Validates the actual Phase 2.4.1 Customer Support PRD file on disk.
    Must be strictly REJECTED for all 6 verified semantic defects:
    1. Scope contradiction (FR-005 vs Out of Scope) -> VAL-SEM-004
    2. Generic boilerplate acceptance criteria (AC-007) -> VAL-AC-004
    3. Unsupported NFR SLA target (< 2s classified as Confirmed) -> VAL-NUM-001
    4. Unsupported user journey capabilities (manager approval, rep editing) -> VAL-UJ-001
    5. Contradictory retention policy (24h vs 30d in FR-002) -> VAL-XSEC-002
    6. Unconfirmed architectural decisions (failover to hot standby) -> VAL-ARCH-001
    """
    file_path = "docs/benchmark/PRD_Customer_Support_v2_4_1.md"
    if not os.path.exists(file_path):
        file_path = "/app/docs/benchmark/PRD_Customer_Support_v2_4_1.md"
    
    with open(file_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    sections = parse_markdown_to_sections(md_text)
    assert len(sections) == 27, f"Expected 27 canonical sections, got {len(sections)}"

    prd_ver = PRDVersion(
        prd_id="prd_cs_v2_4_1_legacy",
        project_id="proj_cs_1",
        version_number="v2.3",
        sections=sections
    )

    analysis = AnalysisRecord(
        project_id="proj_cs_1",
        problem_domain="Customer Support",
        product_category="Customer Support AI Assistant",
        intended_users=["Customer", "Customer Service Representative"],
        core_objectives=[
            "Answer customer questions using approved knowledge-base articles",
            "Maintain conversation history",
            "Escalate low-confidence queries below 80% to human agents with context summary"
        ],
        expected_capabilities=[
            "Knowledge retrieval",
            "Conversation history",
            "Low-confidence escalation",
            "Context summarization"
        ],
        explicit_constraints=["Web chat only", "80% confidence threshold"],
        facts=["Approved knowledge-base articles only", "Escalate when confidence < 80%"]
    )

    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver, analysis)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"
    assert report.score <= 65

    issue_rule_ids = {iss.rule_id for iss in report.issues if iss.severity == "error"}
    
    # 1. External integration vs MVP scope contradiction
    assert "VAL-SEM-004" in issue_rule_ids, "Expected VAL-SEM-004 for FR-005 vs Out of Scope"

    # 2. Generic boilerplate acceptance criteria
    assert "VAL-AC-004" in issue_rule_ids, "Expected VAL-AC-004 for generic AC-007 boilerplate"

    # 3. Unsupported NFR targets
    assert "VAL-NUM-001" in issue_rule_ids, "Expected VAL-NUM-001 for ungrounded SLA in NFR"

    # 4. Unsupported user journey capabilities
    assert "VAL-UJ-001" in issue_rule_ids, "Expected VAL-UJ-001 for out-of-scope journey capabilities"

    # 5. Retention policy contradiction
    assert "VAL-XSEC-002" in issue_rule_ids, "Expected VAL-XSEC-002 for 24h vs 30d retention conflict"

    # 6. Unconfirmed architectural decision asserted as mandatory
    assert "VAL-ARCH-001" in issue_rule_ids, "Expected VAL-ARCH-001 for unconfirmed failover architecture"


@pytest.mark.asyncio
async def test_positive_customer_support_prd_remediated():
    """
    Verify that remediated Customer Support PRD satisfies all semantic quality rules:
    - FR-001..FR-004 (no FR-005 external ticketing)
    - 24-hour active session memory with archival as an open decision
    - NFRs properly classified as Proposed target / Open decision
    - Scenario-specific Given-When-Then ACs
    - Clean user journeys without manager approvals or rep editing
    - Clean dependencies and constraints
    """
    sections = make_valid_sections("AI Customer Support Assistant", "Customer Support", version="v2.4.2", include_80_conf=True)
    
    # Ensure FR-005 is removed and only FR-001..FR-004 are present
    fr_clean = (
        "| ID | Title | Description | Priority | Traceable AC |\n"
        "|---|---|---|---|---|\n"
        "| **FR-001** | Automated KB-driven answer delivery | Queries evaluated against approved KB articles; answers delivered when confidence >= 80%. | Must Have | AC-001, AC-002, AC-003 |\n"
        "| **FR-002** | Per-session conversation history management | Active conversation turns cached in session memory up to 24 hours. | Must Have | AC-004, AC-005 |\n"
        "| **FR-003** | Low-confidence detection and automatic escalation | Queries with confidence < 80% suppressed from customer and routed to internal queue. | Must Have | AC-006, AC-007 |\n"
        "| **FR-004** | Context summarization for human escalation | Escalated conversations accompanied by concise context summary under 200 words. | Must Have | AC-008 |\n"
    )
    sections["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title=SECTION_TITLES["functional_requirements"],
        content=fr_clean
    )

    # Clean NFRs: Proposed target / Open decision without hot standby mandates
    nfr_clean = (
        "| ID | Title | Description | Classification | Priority |\n"
        "|---|---|---|---|---|\n"
        "| **NFR-001** | Response Latency | System targets response latency under 3.0 seconds under baseline network concurrency. | Proposed target | Must Have |\n"
        "| **NFR-002** | Data Protection in Transit and Rest | Customer dialogue turns encrypted via TLS and encrypted at rest with role-based access. | Proposed target | Must Have |\n"
        "| **NFR-003** | System Availability | System targets 99.5% operational availability with local diagnostic error logging. [Open Architectural Decision: Multi-zone standby pending review] | Open decision | Should Have |\n"
    )
    sections["non_functional_requirements"] = PRDSectionContent(
        key="non_functional_requirements",
        title=SECTION_TITLES["non_functional_requirements"],
        content=nfr_clean
    )

    # Clean ACs: Scenario-specific Given-When-Then criteria
    ac_clean = (
        "| AC ID | Associated Requirement | Acceptance Criteria (Given-When-Then / Rule) |\n"
        "|---|---|---|\n"
        "| **AC-001** | FR-001 | Given an evaluated answer candidate with confidence score of 79.9%, When evaluated, Then automated answer is suppressed and routed to human queue. |\n"
        "| **AC-002** | FR-001 | Given an evaluated answer candidate with confidence score of exactly 80.0%, When evaluated, Then the approved answer is delivered to the customer. |\n"
        "| **AC-003** | FR-001 | Given an evaluated answer candidate with confidence score of 80.1%, When evaluated, Then the approved answer is delivered to the customer. |\n"
        "| **AC-004** | FR-002 | Given an active customer session within the 24-hour window, When follow-up question is asked, Then system references preceding dialogue context. |\n"
        "| **AC-005** | FR-002 | Given a session inactive for more than 24 hours, When a new message arrives, Then system initializes a new session and treats archival retention as an open decision. |\n"
        "| **AC-006** | FR-003 | Given a query where no approved KB article matches, When evaluated, Then system suppresses automated reply and queues human escalation. |\n"
        "| **AC-007** | FR-003 | Given an internal calculation failure in confidence service, When exception occurs, Then system safely routes query to human escalation with error log. |\n"
        "| **AC-008** | FR-004 | Given a multi-turn conversation escalated to human support, When summary is generated, Then system compiles a concise summary under 200 words. |\n"
    )
    sections["acceptance_criteria"] = PRDSectionContent(
        key="acceptance_criteria",
        title=SECTION_TITLES["acceptance_criteria"],
        content=ac_clean
    )

    prd_ver = PRDVersion(
        prd_id="prd_cs_remediated",
        project_id="proj_cs_1",
        version_number="v2.4.2",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )

    analysis = AnalysisRecord(
        project_id="proj_cs_1",
        problem_domain="Customer Support",
        product_category="AI Customer Support Assistant",
        intended_users=["Customer", "Customer Service Representative"],
        core_objectives=["Provide accurate KB answers", "Maintain conversation history", "Escalate low-confidence queries below 80% with context summary"],
        expected_capabilities=["KB retrieval", "Conversation history", "80% confidence escalation", "Context summarization"],
        explicit_constraints=["Web chat only", "80% confidence threshold"],
        facts=["Approved knowledge-base articles only", "80% confidence threshold"]
    )

    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver, analysis)

    assert report.is_valid is True, f"Validation failed with errors: {[f'{i.rule_id}: {i.title}' for i in report.issues if i.severity == 'error']}"
    assert report.verdict == "APPROVED"
    assert report.score >= 85
    assert report.error_count == 0


@pytest.mark.asyncio
async def test_positive_attendance_prd_remains_valid():
    """Verify College Attendance Management PRD remains valid under Phase 2.4.2 rules."""
    sections = make_valid_sections("College Attendance Management System", "College Attendance Management System", version="v2.4.2", is_attendance=True)
    prd_ver = PRDVersion(
        prd_id="prd_att_valid",
        project_id="proj_att_1",
        version_number="v2.4.2",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_att_1",
        problem_domain="Higher Education Academic Administration",
        product_category="College Attendance Management System",
        intended_users=["Faculty Instructor", "Department Head"],
        core_objectives=["Record daily attendance roll calls", "Calculate percentage", "Enforce 75% threshold"],
        expected_capabilities=["Roll call recording", "Percentage calculation", "Early warning alerts"],
        explicit_constraints=["75% mandatory threshold", "Browser-based access"],
        facts=["75% attendance threshold", "Daily roll calls"]
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver, analysis)

    assert report.is_valid is True
    assert report.verdict == "APPROVED"
    assert report.score >= 85
    assert report.error_count == 0


@pytest.mark.asyncio
async def test_positive_warehouse_robotics_agv_prd_remains_valid():
    """Verify Autonomous Warehouse Robotics AGV PRD remains valid under Phase 2.4.2 rules."""
    sections = make_valid_sections("Autonomous Warehouse Robot Fleet Management", "Warehouse Robotics Logistics", version="v2.4.2", is_warehouse=True)
    prd_ver = PRDVersion(
        prd_id="prd_agv_valid",
        project_id="proj_agv_1",
        version_number="v2.4.2",
        content_hash="mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_agv_1",
        problem_domain="Industrial Logistics Automation",
        product_category="Warehouse Robot Fleet Management System",
        intended_users=["Floor Supervisor", "Fleet Maintenance Technician"],
        core_objectives=["Schedule AGVs for pallet transport", "Calculate collision-free routing", "Automate low-battery charging dispatch"],
        expected_capabilities=["AGV dispatch", "Grid routing", "Battery docking (< 20%)"],
        explicit_constraints=["20% battery threshold for docking", "Collision-free routing"],
        facts=["20% battery threshold", "Automated AGV fleet"]
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver, analysis)

    assert report.is_valid is True
    assert report.verdict == "APPROVED"
    assert report.score >= 85
    assert report.error_count == 0


@pytest.mark.asyncio
async def test_positive_unfamiliar_domain_generalization():
    """Verify unfamiliar domain (Pediatric Telehealth) generalizes cleanly without domain hardcoding."""
    sections = make_valid_sections("Remote Pediatric Telehealth Platform", "Pediatric Clinical Telehealth", version="v2.4.2", is_telehealth=True)
    prd_ver = PRDVersion(
        prd_id="prd_telehealth_valid",
        project_id="proj_telehealth",
        version_number="v2.4.2",
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
    report = await validator.validate_version(prd_ver, analysis)

    assert report.is_valid is True
    assert report.verdict == "APPROVED"
    assert report.score >= 85
    assert report.error_count == 0

