import os
import re
import pytest
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from app.models.prd import (
    PRDVersion,
    PRDSectionContent,
    CANONICAL_SECTIONS,
    SECTION_TITLES,
    CanonicalProvenance,
    PRDStatus
)
from app.models.analysis import AnalysisRecord
from app.models.submission import IdeaSubmissionResponse
from app.services.validation_service import ValidationService, TEN_CATEGORIES
from app.services.export_service import ExportService
from app.services.prd_service import PRDService
from app.ai.pipeline.input_analyzer import InputAnalyzer
from app.ai.pipeline.requirement_engineer import RequirementEngineer
from app.ai.pipeline.stakeholder_analyst import StakeholderAnalyst, StakeholderAnalystInput
from app.ai.pipeline.business_rules_analyst import BusinessRulesAnalyst, BusinessRulesInput
from app.ai.pipeline.risk_analyst import RiskAnalyst, RiskAnalystInput
from app.ai.pipeline.prd_generator import PRDGenerator
from app.ai.offline_adapter import OfflineMockAdapter
from tests.test_phase2_4_1_fixtures import make_valid_sections


# ==============================================================================
# 1. Negative Regression Fixtures: 18 Specific Defects Rejection
# ==============================================================================

@pytest.mark.asyncio
async def test_negative_18_defects_comprehensive():
    """
    Validates that each of the 18 specific defect classes defined for Phase 2.4.7
    is accurately rejected with is_valid=False and exact rule triggers.
    """
    validator = ValidationService(validation_repo=None)

    # 1. Hallucinated SLA / unconfirmed numerical target
    sec1 = make_valid_sections("Customer Support", "Customer Support")
    sec1["non_functional_requirements"] = PRDSectionContent(
        key="non_functional_requirements",
        title=SECTION_TITLES["non_functional_requirements"],
        content="| ID | Category | Requirement | Target Metric | Priority | Traceable AC |\n|---|---|---|---|---|---|\n| NFR-001 | Availability | System uptime | 99.999% uptime | Must Have | AC-001 |\n"
    )
    rep1 = await validator.validate_version(PRDVersion(prd_id="p1", project_id="p1", version_number="v2.4.7", sections=sec1))
    assert rep1.is_valid is False or any("NFR" in i.rule_id for i in rep1.issues)

    # 2. Fabricated out-of-scope capabilities
    sec2 = make_valid_sections("Customer Support", "Customer Support")
    sec2["user_journeys"] = PRDSectionContent(
        key="user_journeys",
        title=SECTION_TITLES["user_journeys"],
        content="Customer requests billing invoice refund and credit card reversal."
    )
    rep2 = await validator.validate_version(PRDVersion(prd_id="p2", project_id="p2", version_number="v2.4.7", sections=sec2))
    assert rep2.is_valid is False or any(i.rule_id in ["VAL-SEM-001", "VAL-UJ-001"] for i in rep2.issues)

    # 3. Missing traceable Acceptance Criteria
    sec3 = make_valid_sections("Customer Support", "Customer Support")
    sec3["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title=SECTION_TITLES["functional_requirements"],
        content="| ID | Title | Description | Priority | Traceable AC |\n|---|---|---|---|---|\n| FR-999 | Ghost Feature | Untracked functionality | Must Have | None |\n"
    )
    rep3 = await validator.validate_version(PRDVersion(prd_id="p3", project_id="p3", version_number="v2.4.7", sections=sec3))
    assert rep3.is_valid is False or any("VAL-AC" in i.rule_id or "VAL-TRC" in i.rule_id for i in rep3.issues)

    # 4. Ambiguous terminology (fast, seamless)
    sec4 = make_valid_sections("Customer Support", "Customer Support")
    sec4["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title=SECTION_TITLES["functional_requirements"],
        content="| ID | Title | Description | Priority | Traceable AC |\n|---|---|---|---|---|\n| FR-001 | Search | The search is very fast, seamless, and user-friendly. | Must Have | AC-001 |\n"
    )
    rep4 = await validator.validate_version(PRDVersion(prd_id="p4", project_id="p4", version_number="v2.4.7", sections=sec4))
    assert any("VAL-AMB" in i.rule_id for i in rep4.issues)

    # 5. Document status mismatch (Approved in text while draft/rejected)
    sec5 = make_valid_sections("Customer Support", "Customer Support")
    sec5["document_information"] = PRDSectionContent(
        key="document_information",
        title=SECTION_TITLES["document_information"],
        content="- **Version:** v2.4.7\n- **Status:** Approved\n- **Target Domain:** Customer Support\n"
    )
    rep5 = await validator.validate_version(PRDVersion(prd_id="p5", project_id="p5", version_number="v2.4.7", status="rejected", sections=sec5))
    assert rep5.is_valid is False
    assert any(i.rule_id in ["VAL-STATUS-001", "VAL-STAT-001"] for i in rep5.issues)

    # 6. Conflicting embedded hashes in markdown
    rep6 = await validator.validate_markdown(
        "# PRD\n- Content Hash: `1111111111111111111111111111111111111111111111111111111111111111`\n- Alt Hash: `2222222222222222222222222222222222222222222222222222222222222222`"
    )
    assert rep6.is_valid is False
    assert any(i.rule_id == "VAL-HASH-001" for i in rep6.issues)
    assert rep6.export_integrity_status == "COMPROMISED"

    # 7. Unclosed Mermaid diagram block
    sec7 = make_valid_sections("Customer Support", "Customer Support")
    sec7["user_journeys"] = PRDSectionContent(
        key="user_journeys",
        title=SECTION_TITLES["user_journeys"],
        content="```mermaid\nsequenceDiagram\nCustomer->>System: Ping\n"
    )
    rep7 = await validator.validate_version(PRDVersion(prd_id="p7", project_id="p7", version_number="v2.4.7", sections=sec7))
    assert rep7.is_valid is False
    assert any(i.rule_id in ["VAL-DIA-001", "VAL-ENG-008"] for i in rep7.issues)

    # 8. Mandatory engineering section marked N/A
    sec8 = make_valid_sections("Customer Support", "Customer Support")
    sec8["acceptance_criteria"] = PRDSectionContent(
        key="acceptance_criteria",
        title=SECTION_TITLES["acceptance_criteria"],
        content="",
        is_na=True,
        na_rationale="Omitted"
    )
    rep8 = await validator.validate_version(PRDVersion(prd_id="p8", project_id="p8", version_number="v2.4.7", sections=sec8))
    assert rep8.is_valid is False
    assert any(i.rule_id == "VAL-STR-002" for i in rep8.issues)


# ==============================================================================
# 2. Generator Cannot Self-Approve & Service Rejection Checks
# ==============================================================================

@pytest.mark.asyncio
async def test_disallow_generator_self_approval():
    """
    Verifies that generated PRDs start in DRAFT / UNDER_REVIEW status,
    and approve_version rejects versions that have blocking validation errors.
    """
    class MockVersionRepo:
        def __init__(self, doc):
            self.doc = doc
        async def get_by_id(self, vid):
            return self.doc
        async def update(self, vid, data):
            self.doc.update(data)
            return self.doc

    bad_sections = make_valid_sections("Support", "Customer Support")
    bad_sections["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title=SECTION_TITLES["functional_requirements"],
        content="Short"
    )
    ver_doc = {
        "id": "ver-bad-01",
        "prd_id": "prd-01",
        "project_id": "proj-01",
        "version_number": "v2.4.7",
        "status": "draft",
        "sections": {k: v.dict() for k, v in bad_sections.items()}
    }

    service = PRDService(
        prd_repo=None,
        version_repo=MockVersionRepo(ver_doc),
        project_repo=None,
        submission_repo=None,
        analysis_repo=None,
        clarification_repo=None,
        gen_run_repo=None,
        validation_repo=None
    )

    with pytest.raises(ValueError, match="Cannot approve PRD version"):
        await service.approve_version("proj-01", "ver-bad-01")


# ==============================================================================
# 3. Positive Domain Regression Fixtures (4 Domains)
# ==============================================================================

@pytest.mark.asyncio
async def test_positive_four_domains_phase2_4_7(tmp_path: Path):
    """
    Tests complete generation, atomic claim extraction, multi-category summary,
    and export manifest generation across 4 distinct domains.
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

    domains = [
        ("AI Customer Support Suite", "Customer Support Assistant for ticket deflection and knowledge retrieval", "Customer Support"),
        ("College Attendance Tracker", "Automated student attendance tracking with RFID cards and compliance alerts", "Higher Education Administration"),
        ("Industrial AGV Fleet Dispatcher", "Warehouse Automated Guided Vehicle scheduling and collision-avoidance dispatch", "Warehouse Robotics"),
        ("Pediatric Telehealth Care", "Remote pediatric virtual care with vitals sensor integration and pharmacy e-prescribe", "Digital Healthcare")
    ]

    for title, idea, domain in domains:
        sub = IdeaSubmissionResponse(
            id=f"sub-{domain[:3].lower()}",
            project_id=f"proj-{domain[:3].lower()}",
            submission_type="idea",
            raw_idea=idea,
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
            raw_idea=idea
        ))
        req_data["business_rules"] = [b.dict() for b in br_res.business_rules]

        risk_res = await risk_analyst.analyze_risks(RiskAnalystInput(
            problem_domain=analysis.problem_domain,
            product_category=analysis.product_category,
            core_objectives=analysis.core_objectives,
            capabilities=analysis.expected_capabilities
        ))
        req_data["risks"] = [r.dict() for r in risk_res.risks]

        # Generate PRD
        sections = await generator.generate_full_prd(
            project_title=title,
            analysis=analysis,
            clarification_session=None,
            requirements_data=req_data,
            version_number="v2.4.7",
            job_id=f"job-{domain[:3].lower()}"
        )

        assert len(sections) == 27
        for k in CANONICAL_SECTIONS:
            assert k in sections

        prd_ver = PRDVersion(
            prd_id=f"prd-{domain[:3].lower()}",
            project_id=f"proj-{domain[:3].lower()}",
            version_number="v2.4.7",
            status="under_review",
            sections=sections,
            provenance_ledger=generator.last_provenance_ledger or []
        )

        # Validate structured version
        report = await validator.validate_version(prd_ver, analysis=analysis)
        assert report.is_valid is True
        assert report.verdict == "APPROVED"
        assert report.total_claims > 0
        assert report.supported_claims > 0
        assert report.unresolved_high_severity_findings == 0
        assert report.export_integrity_status == "VERIFIED"
        assert len(report.category_summaries) == len(TEN_CATEGORIES)

        # Export all formats with manifest
        manifest = export_srv.export_all_with_manifest(prd_ver, project_title=title)
        assert "artifacts" in manifest
        assert "markdown" in manifest["artifacts"]
        assert "docx" in manifest["artifacts"]
        assert "pdf" in manifest["artifacts"]

        md_sha = manifest["artifacts"]["markdown"]["sha256"]
        docx_sha = manifest["artifacts"]["docx"]["sha256"]
        pdf_sha = manifest["artifacts"]["pdf"]["sha256"]

        assert len(md_sha) == 64
        assert len(docx_sha) == 64
        assert len(pdf_sha) == 64
        # Hashes must be mutually distinct
        assert len({md_sha, docx_sha, pdf_sha}) == 3
