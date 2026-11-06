import os
import re
import pytest
from typing import Dict
from app.models.prd import PRDVersion, PRDSectionContent, CANONICAL_SECTIONS, SECTION_TITLES
from app.models.analysis import AnalysisRecord
from app.services.validation_service import ValidationService
from tests.test_phase2_4_1_fixtures import make_valid_sections
from tests.test_phase2_4_2_regression import parse_markdown_to_sections

@pytest.mark.asyncio
async def test_negative_customer_support_v2_4_2_artifact():
    """
    Mandatory Regression Gate (Phase 2.4.3):
    Validates the actual Phase 2.4.2 Customer Support PRD file on disk.
    Must be strictly REJECTED for verified Phase 2.4.2 semantic defects:
    1. VAL-SEM-004: Ticket creation / ticket IDs remaining in user journeys
    2. VAL-DUP-001: Duplicate BR-007
    3. VAL-DIA-001: Truncated Mermaid sequence diagram line
    4. VAL-NUM-003: Unsupported 40% wait-time / 60% query reduction
    5. VAL-XSEC-006: Conflicting 150-word and 200-word context summary limits
    6. VAL-SEM-005: Unsupported confirmation receipts in web chat
    7. VAL-SEM-007: Unsupported Support Manager supervisory persona
    8. VAL-PRIV-001: Unsupported GDPR compliance claims
    9. VAL-VER-001: Document version inconsistency
    """
    file_path = "docs/benchmark/PRD_Customer_Support_v2_4_2.md"
    if not os.path.exists(file_path):
        file_path = "/app/docs/benchmark/PRD_Customer_Support_v2_4_2.md"

    with open(file_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    sections = parse_markdown_to_sections(md_text)
    assert len(sections) == 27, f"Expected 27 canonical sections, got {len(sections)}"

    prd_ver = PRDVersion(
        prd_id="prd_cs_v2_4_2_fixture",
        project_id="proj_cs_1",
        version_number="v2.4.2",
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

    error_rule_ids = {iss.rule_id for iss in report.issues if iss.severity == "error"}
    
    # Verify the defect rules fired
    assert "VAL-SEM-004" in error_rule_ids, "Expected VAL-SEM-004 for ticket creation in journeys"
    assert "VAL-DUP-001" in error_rule_ids, "Expected VAL-DUP-001 for duplicate BR-007"
    assert "VAL-DIA-001" in error_rule_ids, "Expected VAL-DIA-001 for truncated sequence diagram"
    assert "VAL-NUM-003" in error_rule_ids, "Expected VAL-NUM-003 for unsupported 40%/60% reduction"
    assert "VAL-XSEC-006" in error_rule_ids, "Expected VAL-XSEC-006 for 150 vs 200 word limits"
    assert "VAL-SEM-005" in error_rule_ids, "Expected VAL-SEM-005 for unsupported confirmation receipts"
    assert "VAL-SEM-007" in error_rule_ids, "Expected VAL-SEM-007 for unsupported Support Manager role"
    assert "VAL-PRIV-001" in error_rule_ids, "Expected VAL-PRIV-001 for unsupported GDPR assertion"
    assert "VAL-VER-001" in error_rule_ids, "Expected VAL-VER-001 for version mismatch"


@pytest.mark.asyncio
async def test_negative_customer_support_v2_4_1_artifact():
    """Verify Phase 2.4.1 negative regression artifact remains rejected."""
    file_path = "docs/benchmark/PRD_Customer_Support_v2_4_1.md"
    if not os.path.exists(file_path):
        file_path = "/app/docs/benchmark/PRD_Customer_Support_v2_4_1.md"

    with open(file_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    sections = parse_markdown_to_sections(md_text)
    prd_ver = PRDVersion(
        prd_id="prd_cs_v2_4_1_fixture",
        project_id="proj_cs_1",
        version_number="v2.4.1",
        sections=sections
    )

    analysis = AnalysisRecord(
        project_id="proj_cs_1",
        problem_domain="Customer Support",
        product_category="Customer Support AI Assistant",
        intended_users=["Customer", "Customer Service Representative"],
        core_objectives=["Answer customer questions using approved KB", "Maintain conversation history", "Escalate queries < 80%"],
        expected_capabilities=["Knowledge retrieval", "Conversation history", "Low-confidence escalation", "Context summarization"],
        explicit_constraints=["Web chat only", "80% confidence threshold"],
        facts=["Approved knowledge-base articles only", "Escalate when confidence < 80%"]
    )

    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver, analysis)

    assert report.is_valid is False
    assert report.verdict == "REJECTED"


@pytest.mark.asyncio
async def test_positive_customer_support_prd_v2_4_3_clean():
    """
    Verify that clean, remediated Customer Support PRD v2.4.3 passes with zero errors:
    - FR-001..FR-004 (no external ticketing)
    - 24-hour active session memory (no 30-day conflict)
    - Correct Given-When-Then ACs without boilerplate or receipts
    - Clean user journeys without ticketing or Support Manager
    - No ungrounded 40%/60% reduction percentages
    - Consistent 'under 200 words' summary limit
    - Proper Proposed target / Open decision classifications
    """
    sections = make_valid_sections("AI Customer Support Assistant", "Customer Support", version="v2.4.3", include_80_conf=True)

    # Clean FRs
    fr_clean = (
        "| ID | Title | Description | Priority | Traceable AC |\n"
        "|---|---|---|---|---|\n"
        "| **FR-001** | Automated KB-driven answer delivery | Queries evaluated against approved KB articles; answers delivered when confidence >= 80%. | Must Have | AC-001, AC-002, AC-003 |\n"
        "| **FR-002** | Per-session conversation history management | Active conversation turns cached in session memory up to 24 hours. | Must Have | AC-004, AC-005 |\n"
        "| **FR-003** | Low-confidence detection and automatic escalation | Queries with confidence < 80% suppressed from customer and routed to internal human queue. | Must Have | AC-006, AC-007 |\n"
        "| **FR-004** | Context summarization for human escalation | Escalated conversations accompanied by concise context summary under 200 words. | Must Have | AC-008 |\n"
    )
    sections["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title=SECTION_TITLES["functional_requirements"],
        content=fr_clean
    )

    # Clean NFRs
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

    # Clean Business Rules with canonical provenance
    br_clean = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Grounded Knowledge-Base Delivery | Customer queries answered strictly from verified KB articles. | `USER_CONFIRMED` | User Input: approved KB articles | Ensures answer accuracy | No (Confirmed) |\n"
        "| **BR-002** | Escalation Threshold Boundary | Automated answers suppressed when confidence is below 80.0%. | `USER_CONFIRMED` | User Input: 80% confidence threshold | Prevents hallucination | No (Confirmed) |\n"
        "| **BR-003** | Per-Session Active Cache TTL | Conversation turns retained in session memory up to 24 hours. | `USER_CONFIRMED` | User Input: conversation history | Preserves context | No (Confirmed) |\n"
        "| **BR-004** | Context Summary Constraint | Escalation handoff summary strictly constrained to under 200 words. | `ASSIGNMENT_REQUIRED` | Assignment Specification | Quick agent triage | No (Confirmed) |\n"
        "| **BR-005** | Fallback on Service Timeout | Service timeouts safely route queries to human queue with diagnostic log. | `PROPOSED` | Domain Architecture Standard | Operational continuity | Yes (Review needed) |\n"
    )
    sections["business_rules"] = PRDSectionContent(
        key="business_rules",
        title=SECTION_TITLES["business_rules"],
        content=br_clean
    )

    # Clean ACs
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

    # Clean User Journeys with complete Mermaid sequence diagram
    uj_clean = (
        "```mermaid\n"
        "sequenceDiagram\n"
        "    actor Customer as Customer\n"
        "    actor SupportRep as Support Representative\n"
        "    participant AppSystem as Customer Support Assistant\n"
        "    Customer->>AppSystem: Submits a question via web chat widget\n"
        "    AppSystem-->>Customer: Retrieves verified KB answer and returns response\n"
        "    Note over AppSystem: Edge Case: If confidence < 80%, routes to escalation\n"
        "    AppSystem->>SupportRep: Dispatches low-confidence query with context summary\n"
        "    SupportRep-->>Customer: Representative provides direct assistance\n"
        "```\n\n"
        "### User Journey Stages\n\n"
        "1. **Initial Inquiry:** Customer submits query via web chat widget.\n"
        "2. **Confidence Evaluation:** System searches verified KB articles and computes confidence score.\n"
        "3. **Human Escalation:** Queries below 80% route to internal human queue with summary under 200 words.\n"
        "4. **Resolution:** Support representative reviews summary and assists customer.\n"
    )
    sections["user_journeys"] = PRDSectionContent(
        key="user_journeys",
        title=SECTION_TITLES["user_journeys"],
        content=uj_clean
    )

    # Clean Executive Summary without ungrounded 40%/60% or false GDPR claims
    sections["executive_summary"] = PRDSectionContent(
        key="executive_summary",
        title=SECTION_TITLES["executive_summary"],
        content=(
            "The AI Customer Support Assistant is a real-time web-chat agent designed to support customers "
            "by automatically delivering answers from approved knowledge-base articles and escalating complex queries "
            "to human representatives with a concise context summary. The initial MVP operates strictly as a self-contained "
            "web widget. Institutional data governance and privacy policies remain subject to formal compliance review."
        )
    )

    # Section 1 Document Information matching v2.4.3
    content_hash = "f1e2d3c4b5a697887766554433221100aabbccddeeff00112233445566778899"
    sections["document_information"] = PRDSectionContent(
        key="document_information",
        title=SECTION_TITLES["document_information"],
        content=(
            "# AI Customer Support Assistant - Product Requirements Document\n\n"
            "- **Version:** v2.4.3\n"
            "- **Status:** Authoritative Specification\n"
            f"- **Content Hash (SHA-256):** `{content_hash}`\n"
            "- **Author:** Principal Requirements Engineer\n"
            "- **Target Domain:** Customer Support\n"
        )
    )

    prd_ver = PRDVersion(
        prd_id="prd_cs_v2_4_3_clean",
        project_id="proj_cs_clean",
        version_number="v2.4.3",
        content_hash=content_hash,
        sections=sections
    )

    analysis = AnalysisRecord(
        project_id="proj_cs_clean",
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
    assert report.score >= 90
    assert report.error_count == 0


@pytest.mark.asyncio
async def test_provenance_classifications_accepted():
    """Verify that all 6 canonical provenance classifications are recognized without warnings."""
    sections = make_valid_sections("AI Customer Support Assistant", "Customer Support", version="v2.4.3")
    
    # Set business rules covering all 6 canonical tags
    br_content = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Rule One | Operation statement one. | `USER_CONFIRMED` | User Input: Fact 1 | Rationale 1 | No |\n"
        "| **BR-002** | Rule Two | Operation statement two. | `ASSIGNMENT_REQUIRED` | Assignment Ref: Asg 1 | Rationale 2 | No |\n"
        "| **BR-003** | Rule Three | Operation statement three. | `REFERENCE_SUPPORTED` | External Ref: Doc 1 | Rationale 3 | Yes |\n"
        "| **BR-004** | Rule Four | Operation statement four. | `INFERRED` | Inferred Standard | Rationale 4 | Yes |\n"
        "| **BR-005** | Rule Five | Operation statement five. | `PROPOSED` | Proposed Standard | Rationale 5 | Yes |\n"
        "| **BR-006** | Rule Six | Operation statement six. | `UNRESOLVED` | Open Question | Rationale 6 | Yes |\n"
    )
    sections["business_rules"] = PRDSectionContent(
        key="business_rules",
        title=SECTION_TITLES["business_rules"],
        content=br_content
    )

    content_hash = "mockhash1234567890abcdef1234567890abcdef1234567890abcdef12345678"
    prd_ver = PRDVersion(
        prd_id="prd_prov_test",
        project_id="proj_prov",
        version_number="v2.4.3",
        content_hash=content_hash,
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_prov",
        problem_domain="Customer Support",
        product_category="AI Customer Support Assistant",
        intended_users=["Customer", "Customer Service Representative"],
        core_objectives=["Assist users"],
        expected_capabilities=["Assistance"],
        explicit_constraints=["Standard"],
        facts=["Standard facts"]
    )

    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver, analysis)

    sem003_issues = [i for i in report.issues if i.rule_id == "VAL-SEM-003"]
    assert len(sem003_issues) == 0, f"Expected 0 VAL-SEM-003 warnings for canonical provenance tags, got {sem003_issues}"
