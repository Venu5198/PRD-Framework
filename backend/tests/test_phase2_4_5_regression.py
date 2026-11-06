import os
import re
import pytest
from datetime import datetime
from typing import Dict
from pathlib import Path

from app.models.prd import PRDVersion, PRDSectionContent, CANONICAL_SECTIONS, SECTION_TITLES, CanonicalProvenance
from app.models.analysis import AnalysisRecord
from app.models.submission import IdeaSubmissionResponse
from app.services.validation_service import ValidationService
from app.services.export_service import ExportService
from app.ai.pipeline.input_analyzer import InputAnalyzer
from app.ai.pipeline.requirement_engineer import RequirementEngineer
from app.ai.pipeline.stakeholder_analyst import StakeholderAnalyst, StakeholderAnalystInput
from app.ai.pipeline.business_rules_analyst import BusinessRulesAnalyst, BusinessRulesInput
from app.ai.pipeline.risk_analyst import RiskAnalyst, RiskAnalystInput
from app.ai.pipeline.prd_generator import PRDGenerator
from app.ai.offline_adapter import OfflineMockAdapter
from tests.test_phase2_4_1_fixtures import make_valid_sections
from tests.test_phase2_4_2_regression import parse_markdown_to_sections


@pytest.mark.asyncio
async def test_negative_fabricated_attributes_rejection():
    """
    VAL-REQ-002: Reject generic or fabricated requirement attributes.
    PRD must never default to invented boilerplate actions.
    """
    sections = make_valid_sections("AI Customer Support Assistant", "Customer Support", version="v2.4.5")
    
    # Inject fabricated boilerplate into functional requirements
    bad_fr = (
        "| ID | Title | Description | Priority | Traceable AC |\n"
        "|---|---|---|---|---|\n"
        "| **FR-001** | Automated Answer Delivery | Precondition: Actor has active authorized session. Input: Standard schema payload. System Behavior: Enforces strict domain validation rules. Expected Outcome: State transition is recorded and verified confirmation is returned. | Must Have | AC-001 |\n"
        "| **FR-002** | Context History Management | Precondition: User is logged in. System updates customer history ledger with timestamp and actor id. | Must Have | AC-002 |\n"
    )
    sections["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title=SECTION_TITLES["functional_requirements"],
        content=bad_fr
    )

    prd_ver = PRDVersion(
        prd_id="prd_neg_fab",
        project_id="proj_neg_fab",
        version_number="v2.4.5",
        status="draft",
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_neg_fab",
        problem_domain="Customer Support",
        product_category="AI Customer Support Assistant",
        intended_users=["Customer", "Support Representative"],
        core_objectives=["Provide automated KB answers", "Maintain context"],
        expected_capabilities=["KB retrieval", "Context management"],
        explicit_constraints=["Web chat only", "80% confidence threshold"],
        facts=["Approved knowledge-base articles only"]
    )

    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver, analysis=analysis)
    assert report.is_valid is False
    assert any(i.rule_id == "VAL-REQ-002" for i in report.issues)
    assert any("Fabricated Generic Requirement Attribute" in i.title for i in report.issues)


@pytest.mark.asyncio
async def test_negative_contradictory_hashes_in_markdown(tmp_path: Path):
    """
    VAL-HASH-001: Reject rendered markdown containing multiple conflicting embedded SHA-256 hashes.
    """
    hash1 = "1111111111111111111111111111111111111111111111111111111111111111"
    hash2 = "2222222222222222222222222222222222222222222222222222222222222222"
    
    sections = make_valid_sections("AI Customer Support Assistant", "Customer Support", version="v2.4.5")
    sections["document_information"] = PRDSectionContent(
        key="document_information",
        title=SECTION_TITLES["document_information"],
        content=f"- **Content Hash (SHA-256):** `{hash1}`\n- Alternate Hash: `{hash2}`"
    )
    
    prd_ver = PRDVersion(
        prd_id="prd_hash_test",
        project_id="proj_hash_test",
        version_number="v2.4.5",
        status="approved",
        sections=sections
    )
    
    export_srv = ExportService(exports_dir=tmp_path)
    md_file = export_srv.export_markdown(prd_ver, project_title="AI Customer Support Assistant")
    with open(md_file, "r", encoding="utf-8") as f:
        rendered_md = f.read()
    
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_markdown(rendered_md)
    assert report.is_valid is False
    assert any(i.rule_id == "VAL-HASH-001" for i in report.issues)


@pytest.mark.asyncio
async def test_negative_document_status_mismatch():
    """
    VAL-STATUS-001 / VAL-STAT-001: Document status in Section 1 must match the authoritative DB version status.
    """
    sections = make_valid_sections("AI Customer Support Assistant", "Customer Support", version="v2.4.5")
    # Body says Approved, but version record status is rejected
    sections["document_information"] = PRDSectionContent(
        key="document_information",
        title=SECTION_TITLES["document_information"],
        content="- **Version:** v2.4.5\n- **Status:** Approved\n- **Target Domain:** Customer Support\n"
    )

    prd_ver = PRDVersion(
        prd_id="prd_neg_stat",
        project_id="proj_neg_stat",
        version_number="v2.4.5",
        status="rejected",
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_neg_stat",
        problem_domain="Customer Support",
        product_category="AI Customer Support Assistant",
        intended_users=["Customer", "Support Representative"],
        core_objectives=["Answer queries"],
        expected_capabilities=["KB retrieval"],
        explicit_constraints=["Web chat only"],
        facts=["Approved KB"]
    )

    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver, analysis=analysis)
    assert report.is_valid is False
    assert any(i.rule_id in ["VAL-STATUS-001", "VAL-STAT-001"] for i in report.issues)


@pytest.mark.asyncio
async def test_negative_unclosed_or_truncated_mermaid_diagram():
    """
    VAL-DIA-001 / VAL-ENG-008: Reject unclosed, untyped, or truncated Mermaid diagram blocks.
    """
    sections = make_valid_sections("AI Customer Support Assistant", "Customer Support", version="v2.4.5")
    # Truncated sequence diagram line
    sections["user_journeys"] = PRDSectionContent(
        key="user_journeys",
        title=SECTION_TITLES["user_journeys"],
        content=(
            "```mermaid\n"
            "sequenceDiagram\n"
            "    Customer->>System: Asks question\n"
            "    System->>\n"
            "```\n"
        )
    )

    prd_ver = PRDVersion(
        prd_id="prd_neg_dia",
        project_id="proj_neg_dia",
        version_number="v2.4.5",
        sections=sections
    )
    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver)
    assert report.is_valid is False
    assert any(i.rule_id in ["VAL-DIA-001", "VAL-ENG-008"] for i in report.issues)


@pytest.mark.asyncio
async def test_negative_invented_customer_support_capabilities():
    """
    VAL-SEM-001 / VAL-UJ-001: Reject user journeys introducing out-of-scope capabilities like billing or supervisor editing.
    """
    sections = make_valid_sections("AI Customer Support Assistant", "Customer Support", version="v2.4.5")
    sections["user_journeys"] = PRDSectionContent(
        key="user_journeys",
        title=SECTION_TITLES["user_journeys"],
        content=(
            "```mermaid\n"
            "sequenceDiagram\n"
            "    actor Customer\n"
            "    actor BillingRep as Billing Specialist\n"
            "    Customer->>BillingRep: Submits invoice dispute and credit card chargeback request\n"
            "```\n"
            "1. Customer files an invoice dispute and requests billing refund.\n"
        )
    )

    prd_ver = PRDVersion(
        prd_id="prd_neg_sem",
        project_id="proj_neg_sem",
        version_number="v2.4.5",
        sections=sections
    )
    analysis = AnalysisRecord(
        project_id="proj_neg_sem",
        problem_domain="Customer Support",
        product_category="AI Customer Support Assistant",
        intended_users=["Customer", "Support Representative"],
        core_objectives=["Answer queries from KB articles", "Escalate complex queries"],
        expected_capabilities=["KB retrieval", "Escalation"],
        explicit_constraints=["Web chat only"],
        facts=["Approved articles only"]
    )

    validator = ValidationService(validation_repo=None)
    report = await validator.validate_version(prd_ver, analysis=analysis)
    assert report.is_valid is False
    assert any(i.rule_id in ["VAL-SEM-001", "VAL-UJ-001"] for i in report.issues)


@pytest.mark.asyncio
async def test_positive_four_domains_provenance_and_ledger(tmp_path: Path):
    """
    Positive Verification Across 4 Diverse Domains:
    1. AI Customer Support Assistant (Support)
    2. College Attendance Management System (Education)
    3. Autonomous Guided Vehicle (AGV) Fleet Management System (Robotics / Industrial)
    4. Remote Pediatric Telehealth Platform (Healthcare)

    Verifies:
    - Complete 27-section generation
    - Full provenance ledger with canonical provenance values
    - Zero fabricated boilerplate defaults
    - Parity: Both validate_version and validate_markdown PASS
    """
    adapter = OfflineMockAdapter()
    analyzer = InputAnalyzer(adapter)
    req_eng = RequirementEngineer(adapter)
    sh_analyst = StakeholderAnalyst(adapter)
    br_analyst = BusinessRulesAnalyst(adapter)
    risk_analyst = RiskAnalyst(adapter)
    generator = PRDGenerator(adapter)
    validator = ValidationService(validation_repo=None)
    export_srv = ExportService(exports_dir=tmp_path)

    canonical_set = {
        CanonicalProvenance.USER_CONFIRMED.value,
        CanonicalProvenance.ASSIGNMENT_REQUIRED.value,
        CanonicalProvenance.REFERENCE_SUPPORTED.value,
        CanonicalProvenance.INFERRED.value,
        CanonicalProvenance.PROPOSED.value,
        CanonicalProvenance.UNRESOLVED.value,
    }

    test_domains = [
        (
            "AI Customer Support Assistant",
            "Build an AI customer support assistant that answers user questions using approved knowledge-base articles, "
            "maintains conversation history, detects low-confidence answers below 80%, and escalates complex queries to human agents.",
            "Customer Support"
        ),
        (
            "College Attendance Management System",
            "Build a College Attendance Management System that tracks student class attendance, calculates aggregate percentage, "
            "alerts advisors when attendance drops below 75%, and generates weekly compliance audit reports for faculty.",
            "Higher Education Administration"
        ),
        (
            "Autonomous Guided Vehicle (AGV) Fleet Management System",
            "Design an industrial AGV Fleet Management system that schedules automated guided vehicles for pallet transport, "
            "calculates collision-free routing across warehouse grids, dispatches low-battery robots to charging docks below 20%, "
            "and alerts floor supervisors on route blockage.",
            "Warehouse Robotics"
        ),
        (
            "Remote Pediatric Telehealth Platform",
            "Build a Remote Pediatric Telehealth Platform where parents schedule virtual visits for children, "
            "pediatricians review vitals telemetry recorded by smart home medical devices, encrypted video consultations "
            "are established, and electronic prescriptions are dispatched to local pharmacies with guardian consent.",
            "Digital Healthcare"
        )
    ]

    for title, concept, domain_label in test_domains:
        sub = IdeaSubmissionResponse(
            id=f"sub-p245-{title[:4].lower()}",
            project_id=f"proj-p245-{title[:4].lower()}",
            submission_type="idea",
            raw_idea=concept,
            created_at=datetime.utcnow()
        )
        analysis = await analyzer.analyze(sub)
        req_data = await req_eng.engineer(analysis, None)
        sh_res = await sh_analyst.analyze(StakeholderAnalystInput(
            product_category=analysis.product_category,
            intended_users=analysis.intended_users,
            domain=analysis.problem_domain
        ))
        req_data["stakeholders"] = [p.dict() for p in sh_res.personas]
        req_data["user_journeys"] = [j.dict() for j in sh_res.user_journeys]

        br_res = await br_analyst.extract_rules(BusinessRulesInput(
            domain=analysis.problem_domain,
            objectives=analysis.core_objectives,
            constraints=analysis.explicit_constraints,
            confirmed_facts=analysis.facts,
            raw_idea=concept
        ))
        req_data["business_rules"] = [b.dict() for b in br_res.business_rules]

        risk_res = await risk_analyst.analyze_risks(RiskAnalystInput(
            problem_domain=analysis.problem_domain,
            product_category=analysis.product_category,
            core_objectives=analysis.core_objectives,
            capabilities=analysis.expected_capabilities
        ))
        req_data["risks"] = [r.dict() for r in risk_res.risks]

        # Generate Full PRD
        sections = await generator.generate_full_prd(
            project_title=title,
            analysis=analysis,
            clarification_session=None,
            requirements_data=req_data,
            version_number="v2.4.5",
            job_id="job-p245-test"
        )

        assert len(sections) == 27
        for sec_key in CANONICAL_SECTIONS:
            assert sec_key in sections
            assert len(sections[sec_key].content.strip()) >= 20

        # Verify Provenance Ledger existence and canonical classifications
        ledger = generator.last_provenance_ledger
        assert ledger is not None and len(ledger) > 0, f"Provenance ledger empty for domain '{title}'"
        for item in ledger:
            prov_val = item.get("classification") or item.get("provenance")
            assert prov_val in canonical_set, f"Non-canonical provenance '{prov_val}' in ledger for {item.get('statement_id')}"

        # Build Version Record (Draft state from generation)
        prd_ver = PRDVersion(
            prd_id=f"prd-p245-{title[:4].lower()}",
            project_id=f"proj-p245-{title[:4].lower()}",
            version_number="v2.4.5",
            status="draft",
            sections=sections,
            provenance_ledger=ledger
        )

        # 1. Structured Version Validation (Draft)
        ver_report = await validator.validate_version(prd_ver, analysis=analysis)
        assert ver_report.is_valid is True, (
            f"Domain '{title}' failed validate_version with errors: "
            f"{[f'{i.rule_id}: {i.title}' for i in ver_report.issues if i.severity == 'error']}"
        )

        # 2. Transition to Approved state (replicating worker.py synchronization)
        prd_ver.status = "approved"
        sections["document_information"].content = re.sub(
            r"(\*\*Status:\*\*)\s*[^\n]+",
            r"\1 Approved",
            sections["document_information"].content
        )
        approved_report = await validator.validate_version(prd_ver, analysis=analysis)
        assert approved_report.is_valid is True

        # 3. Markdown Export and Validation Parity
        md_file = export_srv.export_markdown(prd_ver, project_title=title)
        with open(md_file, "r", encoding="utf-8") as f:
            rendered_md = f.read()

        assert "## 27. Appendix and Glossary" in rendered_md or "## Appendix and Glossary" in rendered_md
        assert "### Full Document Provenance Ledger" in rendered_md

        md_report = await validator.validate_markdown(rendered_md, analysis=analysis)
        assert md_report.is_valid is True, (
            f"Domain '{title}' failed validate_markdown with errors: "
            f"{[f'{i.rule_id}: {i.title}' for i in md_report.issues if i.severity == 'error']}"
        )
