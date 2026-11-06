import pytest
import json
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.submission import IdeaSubmissionResponse
from app.models.analysis import AnalysisRecord, AssignmentRequirement
from app.models.prd import PRDVersion, PRDSectionContent, CANONICAL_SECTIONS, SECTION_TITLES
from app.ai.offline_adapter import OfflineMockAdapter
from app.ai.pipeline.input_analyzer import InputAnalyzer
from app.ai.pipeline.requirement_engineer import RequirementEngineer
from app.ai.pipeline.business_rules_analyst import BusinessRulesAnalyst, BusinessRulesInput
from app.ai.pipeline.stakeholder_analyst import StakeholderAnalyst, StakeholderAnalystInput
from app.ai.pipeline.risk_analyst import RiskAnalyst, RiskAnalystInput
from app.ai.pipeline.prd_generator import PRDGenerator
from app.services.validation_service import ValidationService

# =====================================================================
# Test Suite A: AI Customer Support Assistant Regression
# =====================================================================
@pytest.mark.asyncio
async def test_ai_customer_support_assistant_regression():
    adapter = OfflineMockAdapter()
    analyzer = InputAnalyzer(adapter)
    req_eng = RequirementEngineer(adapter)
    sh_analyst = StakeholderAnalyst(adapter)
    br_analyst = BusinessRulesAnalyst(adapter)
    risk_analyst = RiskAnalyst(adapter)
    generator = PRDGenerator(adapter)
    validator = ValidationService(validation_repo=None)

    raw_concept = (
        "Build an AI-powered customer support assistant that answers customer questions using "
        "approved knowledge-base articles, maintains conversation history, identifies low-confidence "
        "answers below 80%, and escalates complex queries to human agents with a summarized context."
    )

    sub = IdeaSubmissionResponse(
        id="sub-cs-1",
        project_id="proj-cs-1",
        submission_type="idea",
        raw_idea=raw_concept,
        created_at=datetime.utcnow()
    )

    # 1. Input Analysis
    analysis = await analyzer.analyze(sub)
    assert "Customer Support" in analysis.product_category or "Support" in analysis.problem_domain
    assert len(analysis.core_objectives) >= 3

    # 2. Requirement Engineering
    req_data = await req_eng.engineer(analysis, None)
    frs = req_data.get("functional_requirements", [])
    assert len(frs) >= 4

    fr_titles_lower = " ".join(f.get("title", "").lower() + " " + f.get("description", "").lower() for f in frs)
    # A1. Knowledge retrieval
    assert any(k in fr_titles_lower for k in ["knowledge", "article", "retriev"])
    # A2. Grounded answers
    assert any(k in fr_titles_lower for k in ["grounded", "answer", "citation", "fact"])
    # A3. Conversation history
    assert any(k in fr_titles_lower for k in ["conversation", "history", "session", "turn"])
    # A4. Uncertainty detection
    assert any(k in fr_titles_lower for k in ["uncertainty", "confidence", "threshold", "80%"])
    # A5. Human escalation
    assert any(k in fr_titles_lower for k in ["escalat", "human", "handoff", "summary"])

    # 3. Stakeholder Analysis
    sh_res = await sh_analyst.analyze(StakeholderAnalystInput(
        product_category=analysis.product_category,
        intended_users=analysis.intended_users,
        domain=analysis.problem_domain
    ))
    req_data["stakeholders"] = [p.dict() for p in sh_res.personas]
    req_data["user_journeys"] = [j.dict() for j in sh_res.user_journeys]

    # 4. Business Rules
    br_res = await br_analyst.extract_rules(BusinessRulesInput(
        domain=analysis.problem_domain,
        objectives=analysis.core_objectives,
        constraints=analysis.explicit_constraints,
        confirmed_facts=analysis.facts
    ))
    req_data["business_rules"] = [b.dict() for b in br_res.business_rules]
    # Verify provenance tags
    for b in req_data["business_rules"]:
        assert "provenance" in b
        assert b["provenance"] in [
            "confirmed_user_input", "explicit_clarification", "assignment_instruction",
            "ai_proposed_assumption", "recommendation", "unresolved_open_decision", "unresolved_decision",
            "USER_CONFIRMED", "ASSIGNMENT_REQUIRED", "REFERENCE_SUPPORTED", "INFERRED", "PROPOSED", "UNRESOLVED"
        ]

    # 5. Risk Analysis
    risk_res = await risk_analyst.analyze_risks(RiskAnalystInput(
        problem_domain=analysis.problem_domain,
        product_category=analysis.product_category,
        core_objectives=analysis.core_objectives,
        capabilities=analysis.expected_capabilities
    ))
    req_data["risks"] = [r.dict() for r in risk_res.risks]

    # 6. Assembly of 27 Canonical Sections
    sections = await generator.generate_full_prd(
        project_title="AI Customer Support Assistant",
        analysis=analysis,
        clarification_session=None,
        requirements_data=req_data,
        version_number="v1.0"
    )
    assert len(sections) == 27
    for key in CANONICAL_SECTIONS:
        assert key in sections
        assert len(sections[key].content.strip()) >= 20

    # 7. Zero Leakage Verification
    all_content = " ".join(s.content for s in sections.values())
    assert "PRD Framework" not in all_content
    assert "Attendance Window" not in all_content
    assert "student attendance" not in all_content.lower()

    # 8. Semantic Validation
    prd_version = PRDVersion(
        prd_id="prd-cs-1",
        project_id="proj-cs-1",
        version_number="v1.0",
        sections=sections,
        changelog="Initial generation"
    )
    report = await validator.validate_version(prd_version, analysis=analysis)
    assert report.is_valid is True
    assert report.score >= 80
    assert not any(i.rule_id == "VAL-SEM-001" for i in report.issues)


# =====================================================================
# Test Suite B: College Attendance Management System Regression
# =====================================================================
@pytest.mark.asyncio
async def test_college_attendance_management_regression():
    adapter = OfflineMockAdapter()
    analyzer = InputAnalyzer(adapter)
    req_eng = RequirementEngineer(adapter)
    sh_analyst = StakeholderAnalyst(adapter)
    br_analyst = BusinessRulesAnalyst(adapter)
    risk_analyst = RiskAnalyst(adapter)
    generator = PRDGenerator(adapter)
    validator = ValidationService(validation_repo=None)

    raw_concept = (
        "Build a College Attendance Management System where faculty instructors record daily attendance, "
        "students can view their attendance percentage, automated warning notifications are sent if "
        "attendance falls below 75%, and department heads configure attendance policies and condonation rules."
    )

    sub = IdeaSubmissionResponse(
        id="sub-att-1",
        project_id="proj-att-1",
        submission_type="idea",
        raw_idea=raw_concept,
        created_at=datetime.utcnow()
    )

    analysis = await analyzer.analyze(sub)
    assert "Attendance" in analysis.product_category or "Education" in analysis.problem_domain

    req_data = await req_eng.engineer(analysis, None)
    frs = req_data.get("functional_requirements", [])
    fr_titles_lower = " ".join(f.get("title", "").lower() + " " + f.get("description", "").lower() for f in frs)

    # B1. Teacher attendance marking
    assert any(k in fr_titles_lower for k in ["instructor", "teacher", "record", "faculty", "marking"])
    # B2. Student attendance visibility
    assert any(k in fr_titles_lower for k in ["student", "visibility", "dashboard", "view"])
    # B3. Attendance percentage calculation
    assert any(k in fr_titles_lower for k in ["percentage", "calculation", "compute", "cumulative"])
    # B4. Notification below 75%
    assert any(k in fr_titles_lower for k in ["notification", "alert", "75%", "warning"])
    # B5. Configurable attendance policies
    assert any(k in fr_titles_lower for k in ["policy", "configurable", "rule", "condonation", "threshold"])

    # Verify zero customer support leakage in Attendance PRD
    assert "knowledge-base" not in fr_titles_lower
    assert "customer support" not in fr_titles_lower

    # Stakeholder & Business Rules
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
        confirmed_facts=analysis.facts
    ))
    req_data["business_rules"] = [b.dict() for b in br_res.business_rules]

    risk_res = await risk_analyst.analyze_risks(RiskAnalystInput(
        problem_domain=analysis.problem_domain,
        product_category=analysis.product_category,
        core_objectives=analysis.core_objectives,
        capabilities=analysis.expected_capabilities
    ))
    req_data["risks"] = [r.dict() for r in risk_res.risks]

    sections = await generator.generate_full_prd(
        project_title="College Attendance Management System",
        analysis=analysis,
        clarification_session=None,
        requirements_data=req_data,
        version_number="v1.0"
    )
    assert len(sections) == 27
    for key in CANONICAL_SECTIONS:
        assert key in sections

    all_content = " ".join(s.content for s in sections.values())
    assert "PRD Framework" not in all_content
    assert "Customer Support" not in all_content

    prd_version = PRDVersion(
        prd_id="prd-att-1",
        project_id="proj-att-1",
        version_number="v1.0",
        sections=sections,
        changelog="Attendance v1.0 release"
    )
    report = await validator.validate_version(prd_version, analysis=analysis)
    assert report.is_valid is True
    assert report.score >= 80


# =====================================================================
# Test Suite C: Failure & Robustness Scenarios
# =====================================================================
class MalformedJSONAdapter(OfflineMockAdapter):
    """Returns invalid/unparsable JSON to test parser resilience."""
    async def generate(self, *args, **kwargs) -> str:
        return '```json\n{"functional_requirements": [{"id": "FR-001", "title": "Truncated json...'

class RetryExhaustionAdapter(OfflineMockAdapter):
    """Simulates persistent model failures that exhaust retry loops."""
    async def generate(self, *args, **kwargs) -> str:
        raise RuntimeError("Inference daemon timeout: context deadline exceeded")

@pytest.mark.asyncio
async def test_malformed_json_resilience():
    adapter = MalformedJSONAdapter()
    req_eng = RequirementEngineer(adapter)
    analysis = AnalysisRecord(
        project_id="p-malformed",
        product_category="Fleet Logistics",
        problem_domain="Supply Chain Tracking",
        intended_users=["Fleet Manager", "Dispatcher"],
        expected_capabilities=["GPS Vehicle Tracking", "Delivery Confirmation"],
        core_objectives=["Track fleet real-time", "Reduce delivery delays"]
    )
    # Should not raise; must gracefully repair or synthesize domain-grounded fallback
    req_data = await req_eng.engineer(analysis, None)
    assert "functional_requirements" in req_data
    assert len(req_data["functional_requirements"]) >= 2
    # Check that fallback is tailored to Supply Chain Tracking (not PRD framework)
    fr_str = " ".join(f.get("title", "") for f in req_data["functional_requirements"])
    assert "Fleet" in fr_str or "Vehicle" in fr_str or "Delivery" in fr_str or "Tracking" in fr_str

@pytest.mark.asyncio
async def test_retry_exhaustion_resilience():
    adapter = RetryExhaustionAdapter()
    req_eng = RequirementEngineer(adapter)
    analysis = AnalysisRecord(
        project_id="p-exhaustion",
        product_category="Healthcare Telemedicine",
        problem_domain="Remote Patient Monitoring",
        intended_users=["Physician", "Patient"],
        expected_capabilities=["Video Consultation", "Vitals Telemetry"],
        core_objectives=["Enable remote visits", "Capture vital signs"]
    )
    # Must recover gracefully without crashing
    req_data = await req_eng.engineer(analysis, None)
    assert "functional_requirements" in req_data
    fr_str = " ".join(f.get("title", "") for f in req_data["functional_requirements"])
    assert "Consultation" in fr_str or "Telemetry" in fr_str or "Healthcare" in fr_str or "Patient" in fr_str

@pytest.mark.asyncio
async def test_semantic_validation_domain_relevance_detection():
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        project_id="p-semantic",
        product_category="FinTech Investment Platform",
        problem_domain="Stock Trading Execution",
        intended_users=["Trader", "Portfolio Manager"],
        core_objectives=["Execute market orders with low latency"]
    )

    # Construct PRD where FRs have zero connection to stock trading or fintech
    bogus_sections = {
        key: PRDSectionContent(key=key, title=key, content="Standard operational baseline specification.")
        for key in CANONICAL_SECTIONS
    }
    bogus_sections["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title="12. Functional Requirements",
        content="| ID | Title | Description | Priority | Traceable AC |\n|---|---|---|---|---|\n| **FR-001** | Student Classroom Roster | Record attendance per lecture | High | AC-001 |\n"
    )
    bogus_sections["acceptance_criteria"] = PRDSectionContent(
        key="acceptance_criteria",
        title="21. Acceptance Criteria",
        content="| AC ID | Associated Requirement | Acceptance Criteria |\n|---|---|---|\n| **AC-001** | FR-001 | Given a class session, when attendance is marked, then save record. |\n"
    )

    bogus_ver = PRDVersion(
        prd_id="prd-bogus",
        project_id="p-semantic",
        version_number="v1.0",
        sections=bogus_sections,
        changelog="Bogus PRD"
    )

    report = await validator.validate_version(bogus_ver, analysis=analysis)
    # Must detect semantic irrelevance error
    assert any(i.rule_id == "VAL-SEM-001" for i in report.issues)
    assert report.is_valid is False

@pytest.mark.asyncio
async def test_traceability_and_duplicate_id_validation():
    validator = ValidationService(validation_repo=None)

    sections = {
        key: PRDSectionContent(key=key, title=key, content="Substantial engineering specifications.")
        for key in CANONICAL_SECTIONS
    }
    # Create duplicate FR-001 and unmapped FR-002
    sections["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title="12. Functional Requirements",
        content=(
            "| ID | Title | Description |\n"
            "|---|---|---|\n"
            "| **FR-001** | Duplicate First | First duplicate requirement |\n"
            "| **FR-001** | Duplicate Second | Second duplicate requirement |\n"
            "| **FR-002** | Unmapped Requirement | Has no AC mapped |\n"
        )
    )
    sections["acceptance_criteria"] = PRDSectionContent(
        key="acceptance_criteria",
        title="21. Acceptance Criteria",
        content="| AC ID | Associated Requirement | Statement |\n|---|---|---|\n| **AC-001** | FR-001 | Given valid input, When processed, Then verify. |\n"
    )

    ver = PRDVersion(prd_id="prd-trc", project_id="p-trc", version_number="v1.0", sections=sections)
    report = await validator.validate_version(ver)

    rule_ids = {i.rule_id for i in report.issues}
    assert "VAL-REQ-001" in rule_ids  # Duplicate ID
    assert "VAL-AC-001" in rule_ids   # Unmapped AC for FR-002


# =====================================================================
# Test Suite E: Phase 2.1 Engineering Readiness Quality Gates
# =====================================================================
@pytest.mark.asyncio
async def test_engineering_readiness_validation_rules():
    validator = ValidationService(validation_repo=None)

    sections = {
        key: PRDSectionContent(key=key, title=key, content="Substantial engineering specifications and architectural context.")
        for key in CANONICAL_SECTIONS
    }

    # 1. Inject repetitive FR description -> VAL-ENG-001
    sections["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title="12. Functional Requirements",
        content=(
            "| ID | Title | Description | Priority | Traceable AC |\n"
            "|---|---|---|---|---|\n"
            "| **FR-001** | Process Payment | The system shall implement process payment for Ecommerce users. | Must Have | AC-001 |\n"
        )
    )

    # 2. Inject generic boilerplate AC -> VAL-ENG-002
    sections["acceptance_criteria"] = PRDSectionContent(
        key="acceptance_criteria",
        title="21. Acceptance Criteria",
        content=(
            "| AC ID | Associated Requirement | Acceptance Criteria |\n"
            "|---|---|---|\n"
            "| **AC-001** | FR-001 | Given an active session, When the user triggers process payment, Then the system executes successfully and logs the result. |\n"
        )
    )

    # 3. Inject all rules as assumptions despite explicit constraints -> VAL-ENG-003
    sections["business_rules"] = PRDSectionContent(
        key="business_rules",
        title="16. Business Rules",
        content=(
            "| ID | Rule Title | Operational Statement | Provenance | Rationale |\n"
            "|---|---|---|---|---|\n"
            "| **BR-001** | Retention Limit | Retain logs for 30 days | `ai_proposed_assumption` | Compliance standard |\n"
        )
    )

    # 4. Inject fabricated compliance without open decision -> VAL-ENG-004
    sections["security_and_privacy_requirements"] = PRDSectionContent(
        key="security_and_privacy_requirements",
        title="20. Security and Privacy Requirements",
        content="- Mandatory adherence: The platform certifies full GDPR and HIPAA compliance with European data sovereignty."
    )

    # 5. Inject generic placeholder risk -> VAL-ENG-005
    sections["risks_and_mitigation"] = PRDSectionContent(
        key="risks_and_mitigation",
        title="23. Risks and Mitigation",
        content=(
            "| Risk ID | Risk Description | Category | Impact | Mitigation Strategy | Contingency Plan |\n"
            "|---|---|---|---|---|---|\n"
            "| **RSK-001** | Operational risk | Operational | High | Monitor and log | Manual administrative intervention |\n"
            "| **RSK-002** | Operational risk | Functional | Medium | Monitor and log | Manual administrative intervention |\n"
            "| **RSK-003** | Operational risk | Security | High | Monitor and log | Manual administrative intervention |\n"
        )
    )

    analysis = AnalysisRecord(
        project_id="p-eng-test",
        product_category="E-commerce Gateway",
        problem_domain="Payment Processing",
        intended_users=["Merchant", "Customer"],
        core_objectives=["Authorize transactions securely"],
        expected_capabilities=["Payment processing", "Refunds"],
        explicit_constraints=["Enforce multi-factor authorization threshold"],
        facts=["System processes credit card transactions"]
    )

    ver = PRDVersion(prd_id="prd-eng", project_id="p-eng-test", version_number="v1.0", sections=sections)
    report = await validator.validate_version(ver, analysis=analysis)

    detected_rules = {i.rule_id for i in report.issues}
    assert "VAL-ENG-001" in detected_rules, f"Expected VAL-ENG-001 in {detected_rules}"
    assert any(r in detected_rules for r in ["VAL-ENG-002", "VAL-AC-003"]), f"Expected VAL-ENG-002 or VAL-AC-003 in {detected_rules}"
    assert "VAL-ENG-003" in detected_rules or "VAL-PROV-001" in detected_rules, f"Expected VAL-ENG-003 or VAL-PROV-001 in {detected_rules}"
    assert "VAL-ENG-004" in detected_rules, f"Expected VAL-ENG-004 in {detected_rules}"
    assert "VAL-ENG-005" in detected_rules, f"Expected VAL-ENG-005 in {detected_rules}"


@pytest.mark.asyncio
async def test_phase2_1_negative_validation_behavior():
    """
    Step 5 Negative Testing: Proves that ValidationService reliably flags or rejects:
    1. Generic framework requirements lacking domain relevance (VAL-SEM-001).
    2. Tautological / repetitive functional requirements (VAL-ENG-001).
    3. User stories without meaningful user outcome or business value (VAL-ENG-006).
    4. Generic boilerplate acceptance criteria (VAL-ENG-002).
    5. Unsupported compliance claims (VAL-ENG-004).
    6. Unsupported extreme numerical performance targets (VAL-ENG-007).
    7. Contradictory scope and integration requirements (VAL-SEM-004).
    8. Invalid or truncated Mermaid diagrams (VAL-ENG-008).
    9. Mislabeled business rule provenance (VAL-ENG-003).
    10. Confirms that legitimate domain terms ('attendance', 'support') are NOT rejected.
    """
    validator = ValidationService(validation_repo=None, analysis_repo=None)

    sections: Dict[str, PRDSectionContent] = {}
    for key in CANONICAL_SECTIONS:
        sections[key] = PRDSectionContent(
            key=key,
            title=SECTION_TITLES.get(key, key),
            content=f"Substantive domain specification content for {key} with adequate character count."
        )

    # 1. Generic framework requirement lacking domain tokens -> VAL-SEM-001 & VAL-ENG-001
    sections["functional_requirements"] = PRDSectionContent(
        key="functional_requirements",
        title="12. Functional Requirements",
        content=(
            "| ID | Title | Description | Priority | Traceable AC |\n"
            "|---|---|---|---|---|\n"
            "| **FR-001** | Pipeline Ingestion | The system shall implement pipeline ingestion for system users. | High | AC-001 |\n"
        )
    )

    # 2. Generic boilerplate AC -> VAL-ENG-002
    sections["acceptance_criteria"] = PRDSectionContent(
        key="acceptance_criteria",
        title="21. Acceptance Criteria",
        content=(
            "| AC ID | Associated Requirement | Acceptance Criteria |\n"
            "|---|---|---|\n"
            "| **AC-001** | FR-001 | Given an active session, When the user triggers pipeline ingestion, Then the system executes successfully and logs the result. |\n"
        )
    )

    # 3. User story without user value -> VAL-ENG-006
    sections["user_stories"] = PRDSectionContent(
        key="user_stories",
        title="14. User Stories",
        content=(
            "| Story ID | As a... | I want to... | So that... | Linked FR |\n"
            "|---|---|---|---|---|\n"
            "| **US-001** | Operator | pipeline ingestion | it is done | FR-001 |\n"
        )
    )

    # 4. Out-of-scope vs integration contradiction -> VAL-SEM-004
    sections["product_scope"] = PRDSectionContent(
        key="product_scope",
        title="10. Product Scope",
        content="- Core transaction processing"
    )
    sections["out_of_scope"] = PRDSectionContent(
        key="out_of_scope",
        title="11. Out of Scope",
        content="- Direct payment gateway biometric integration"
    )
    sections["integration_requirements"] = PRDSectionContent(
        key="integration_requirements",
        title="19. Integration Requirements",
        content="- Direct payment gateway biometric integration must be implemented via REST API."
    )

    # 5. Unsupported extreme numerical targets -> VAL-ENG-007
    sections["non_functional_requirements"] = PRDSectionContent(
        key="non_functional_requirements",
        title="13. Non-Functional Requirements",
        content="- Availability: The platform guarantees 99.999% availability with zero downtime. Latency: < 10ms."
    )

    # 6. Unsupported compliance claim -> VAL-ENG-004
    sections["security_and_privacy_requirements"] = PRDSectionContent(
        key="security_and_privacy_requirements",
        title="20. Security and Privacy Requirements",
        content="- Mandatory compliance: Certified full GDPR and HIPAA adherence across all storage clusters."
    )

    # 7. Malformed / truncated Mermaid diagram -> VAL-ENG-008
    sections["user_journeys"] = PRDSectionContent(
        key="user_journeys",
        title="15. User Journeys",
        content=(
            "```mermaid\n"
            "actor User\n"
            "User->>System: Incomplete sequence diagram without header\n"
        )
    )

    # 8. Mislabeled provenance -> VAL-ENG-003
    sections["business_rules"] = PRDSectionContent(
        key="business_rules",
        title="16. Business Rules",
        content=(
            "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
            "|---|---|---|---|---|---|---|\n"
            "| **BR-001** | Rule One | Statement | `ai_proposed_assumption` | Ref | Rationale | Yes |\n"
        )
    )

    analysis = AnalysisRecord(
        project_id="p-negative-audit",
        product_category="Healthcare Patient Records",
        problem_domain="Clinical Healthcare Administration",
        intended_users=["Doctor", "Nurse"],
        core_objectives=["Record vital patient indicators"],
        expected_capabilities=["Patient charts", "Vitals monitoring"],
        explicit_constraints=["Enforce minimum staff-to-patient ratio threshold"],
        facts=["Hospitals maintain electronic health records"]
    )

    ver = PRDVersion(prd_id="prd-neg", project_id="p-negative-audit", version_number="v1.0", sections=sections)
    report = await validator.validate_version(ver, analysis=analysis)

    detected_rules = {i.rule_id for i in report.issues}
    assert "VAL-SEM-001" in detected_rules, f"Expected VAL-SEM-001 in {detected_rules}"
    assert "VAL-ENG-001" in detected_rules, f"Expected VAL-ENG-001 in {detected_rules}"
    assert any(r in detected_rules for r in ["VAL-ENG-002", "VAL-AC-003"]), f"Expected VAL-ENG-002 or VAL-AC-003 in {detected_rules}"
    assert "VAL-ENG-003" in detected_rules or "VAL-PROV-001" in detected_rules, f"Expected VAL-ENG-003 or VAL-PROV-001 in {detected_rules}"
    assert "VAL-ENG-004" in detected_rules, f"Expected VAL-ENG-004 in {detected_rules}"
    assert any(r in detected_rules for r in ["VAL-ENG-006", "VAL-US-001"]), f"Expected VAL-ENG-006 or VAL-US-001 in {detected_rules}"
    assert "VAL-ENG-007" in detected_rules, f"Expected VAL-ENG-007 in {detected_rules}"
    assert "VAL-ENG-008" in detected_rules, f"Expected VAL-ENG-008 in {detected_rules}"
    assert "VAL-SEM-004" in detected_rules, f"Expected VAL-SEM-004 in {detected_rules}"


# =====================================================================
# Test Suite D: Phase 2.2 Semantic Correctness & Cross-Domain Validation
# =====================================================================
@pytest.mark.asyncio
async def test_val_xdom_001_cross_domain_contamination():
    """VAL-XDOM-001 detects alien domain terminology injected into PRDs."""
    validator = ValidationService(validation_repo=None, analysis_repo=None)

    sections: Dict[str, PRDSectionContent] = {}
    for key in CANONICAL_SECTIONS:
        sections[key] = PRDSectionContent(
            key=key,
            title=SECTION_TITLES.get(key, key),
            content=f"Proper substantive domain content for {key}."
        )

    # Contaminate Customer Support PRD with attendance terminology
    sections["business_rules"] = PRDSectionContent(
        key="business_rules",
        title="16. Business Rules",
        content=(
            "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
            "|---|---|---|---|---|---|---|\n"
            "| **BR-001** | Support Escalation | Resolve query or escalate | `confirmed_user_input` | 75% attendance threshold | Maintain queue | No |\n"
        )
    )

    analysis_support = AnalysisRecord(
        project_id="p-xdom-test",
        product_category="AI Customer Support Assistant",
        problem_domain="Customer Support Automation",
        intended_users=["Support Agent", "End Customer"],
        core_objectives=["Answer customer questions using knowledge base articles"],
        expected_capabilities=["Q&A Retrieval", "Escalation"],
        explicit_constraints=["Escalate if confidence is below 80%"],
        facts=["Knowledge base articles exist"]
    )

    ver = PRDVersion(prd_id="prd-xdom", project_id="p-xdom-test", version_number="v2.2", sections=sections)
    report = await validator.validate_version(ver, analysis=analysis_support)

    detected_rules = {i.rule_id for i in report.issues}
    assert "VAL-XDOM-001" in detected_rules, f"Expected VAL-XDOM-001 in {detected_rules}"
    assert "VAL-ENG-003" in detected_rules, f"Expected VAL-ENG-003 in {detected_rules}"


@pytest.mark.asyncio
async def test_val_ver_001_version_and_content_hash_integrity():
    """VAL-VER-001 enforces version consistency and SHA-256 header presence."""
    validator = ValidationService(validation_repo=None, analysis_repo=None)

    sections: Dict[str, PRDSectionContent] = {}
    for key in CANONICAL_SECTIONS:
        sections[key] = PRDSectionContent(
            key=key,
            title=SECTION_TITLES.get(key, key),
            content=f"Substantive domain content for section {key} with adequate length."
        )

    # Document information specifies v1.0 while PRDVersion is v2.2, with missing hash
    sections["document_information"] = PRDSectionContent(
        key="document_information",
        title="1. Document Information",
        content="**Version:** v1.0\n**Document ID:** PRD-TEST\n**Status:** Draft"
    )

    analysis = AnalysisRecord(
        project_id="p-ver-test",
        product_category="Inventory Tracker",
        problem_domain="Supply Chain Operations",
        intended_users=["Warehouse Manager"],
        core_objectives=["Track inventory count"],
        expected_capabilities=["Stock counting"],
        explicit_constraints=["Barcode scanning only"],
        facts=["Warehouse has 1000 items"]
    )

    ver = PRDVersion(
        prd_id="prd-ver",
        project_id="p-ver-test",
        version_number="v2.2",
        job_id="job-abc-123",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        sections=sections
    )
    report = await validator.validate_version(ver, analysis=analysis)

    detected_rules = {i.rule_id for i in report.issues}
    assert "VAL-VER-001" in detected_rules, f"Expected VAL-VER-001 in {detected_rules}"


@pytest.mark.asyncio
async def test_generalization_third_domain_warehouse_robotics():
    """Pipeline generalizes cleanly to a third unfamiliar domain without cross-contamination or leakage."""
    adapter = OfflineMockAdapter()
    analyzer = InputAnalyzer(adapter)
    req_eng = RequirementEngineer(adapter)
    sh_analyst = StakeholderAnalyst(adapter)
    br_analyst = BusinessRulesAnalyst(adapter)
    risk_analyst = RiskAnalyst(adapter)
    generator = PRDGenerator(adapter)
    validator = ValidationService(validation_repo=None)

    raw_concept = (
        "Build an Autonomous Warehouse Robot Fleet Management system that schedules automated guided vehicles "
        "(AGVs) for pallet transport, calculates collision-free routing across warehouse grids, dispatches low-battery "
        "robots to charging docks when battery charge is below 20%, and alerts floor supervisors on route blockage."
    )

    sub = IdeaSubmissionResponse(
        id="sub-agv-1",
        project_id="proj-agv-1",
        submission_type="idea",
        raw_idea=raw_concept,
        created_at=datetime.utcnow()
    )

    analysis = await analyzer.analyze(sub)
    assert any(term in (analysis.product_category + " " + analysis.problem_domain).lower() for term in ["robot", "warehouse", "fleet", "logistics", "automation"])

    req_data = await req_eng.engineer(analysis, None)
    frs = req_data.get("functional_requirements", [])
    assert len(frs) >= 3

    # Ensure AGV domain specificity
    all_fr_text = " ".join(f["title"] + " " + f["description"] for f in frs).lower()
    assert any(term in all_fr_text for term in ["robot", "agv", "routing", "battery", "dock", "fleet", "collision"])

    # Ensure zero customer support or attendance contamination
    assert "75% attendance" not in all_fr_text
    assert "knowledge-base" not in all_fr_text
    assert "student" not in all_fr_text

    # Complete assembly
    sections = await generator.generate_full_prd(
        project_title="Autonomous Warehouse Robot Fleet Management",
        analysis=analysis,
        clarification_session=None,
        requirements_data=req_data,
        version_number="v2.2",
        job_id="job-agv-mock"
    )
    assert len(sections) == 27

    # Check Document Information header
    doc_info = sections["document_information"].content
    assert "**Version:** v2.2" in doc_info
    assert "**Job ID:** job-agv-mock" in doc_info
    assert "**Content Hash (SHA-256):** `" in doc_info

    prd_version = PRDVersion(
        prd_id="prd-agv-1",
        project_id="proj-agv-1",
        version_number="v2.2",
        job_id="job-agv-mock",
        sections=sections
    )
    report = await validator.validate_version(prd_version, analysis=analysis)
    assert report.is_valid is True
    assert report.score >= 80
    assert not any(i.rule_id == "VAL-XDOM-001" for i in report.issues)


# =====================================================================
# Test Suite F: Phase 2.2.1 Provenance and Assignment-Aware Validations
# =====================================================================

@pytest.mark.asyncio
async def test_user_provided_numerical_constraints():
    """Verify that user-provided numerical constraints retain confirmed provenance and traceable source."""
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        project_id="p-test-prov-1",
        product_category="Support Automation",
        problem_domain="Customer Support",
        intended_users=["Agent"],
        core_objectives=["Grounded Q&A"],
        explicit_constraints=["Low-confidence threshold set to 80% per customer service policy"],
        facts=["System must flag queries below 80% confidence"]
    )

    valid_br_content = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Confidence Evaluation | Invariant score below 80% escalates. | `confirmed_user_input` | User Constraint: Low-confidence threshold set to 80% | Protects quality | No |\n"
    )
    sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain body content for testing.") for k in CANONICAL_SECTIONS}
    sections["business_rules"] = PRDSectionContent(key="business_rules", title=SECTION_TITLES["business_rules"], content=valid_br_content)

    prd_ver = PRDVersion(prd_id="prd-1", project_id="p-test-prov-1", version_number="v2.2", sections=sections)
    report = await validator.validate_version(prd_ver, analysis=analysis)
    assert not any(i.rule_id == "VAL-ENG-003" and "unconfirmed metric" in i.title.lower() for i in report.issues)
    assert not any(i.rule_id == "VAL-ENG-003" and "mislabeled rule provenance" in i.title.lower() for i in report.issues)


@pytest.mark.asyncio
async def test_assignment_provided_numerical_constraints():
    """Verify that assignment-provided numerical constraints are classified separately with assignment source."""
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        project_id="p-test-asg-1",
        product_category="Educational System",
        problem_domain="Academic Administration",
        intended_users=["Student", "Faculty"],
        core_objectives=["Manage course rosters"],
        assignment_requirements=AssignmentRequirement(
            instruction="Create attendance tracker",
            mandatory_sections=["System Architecture", "Implementation details"],
            constraints=["Minimum attendance requirement is strictly 75% per university policy"]
        )
    )

    br_content = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | University Attendance Policy | Attendance requirement is strictly 75%. | `assignment_instruction` | Assignment Constraint: Minimum attendance requirement is strictly 75% | Academic compliance | No |\n"
    )
    sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain body content for testing.") for k in CANONICAL_SECTIONS}
    sections["business_rules"] = PRDSectionContent(key="business_rules", title=SECTION_TITLES["business_rules"], content=br_content)

    prd_ver = PRDVersion(prd_id="prd-2", project_id="p-test-asg-1", version_number="v2.2", sections=sections)
    report = await validator.validate_version(prd_ver, analysis=analysis)
    assert not any(i.rule_id == "VAL-ENG-003" and "mislabeled rule provenance" in i.title.lower() for i in report.issues)
    assert not any(i.rule_id == "VAL-SEM-005" for i in report.issues)


@pytest.mark.asyncio
async def test_confirmed_clarification_responses():
    """Verify that confirmed clarifications are distinguished from initial input and retain clarification provenance."""
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        project_id="p-test-clarif-1",
        product_category="Warehouse Automation",
        problem_domain="Warehouse Fleet Robotics",
        intended_users=["Fleet Manager"],
        core_objectives=["Manage AGV charging"],
        facts=["AGVs transport pallets across grids"]
    )

    br_content = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Low Battery Docking | AGVs with battery below 20% must route to docks. | `explicit_clarification` | Confirmed Clarification: Q: What battery threshold triggers docking? A: Below 20% | Prevents stalled robots | No |\n"
    )
    sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain body content for testing.") for k in CANONICAL_SECTIONS}
    sections["business_rules"] = PRDSectionContent(key="business_rules", title=SECTION_TITLES["business_rules"], content=br_content)

    prd_ver = PRDVersion(prd_id="prd-3", project_id="p-test-clarif-1", version_number="v2.2", sections=sections)
    report = await validator.validate_version(prd_ver, analysis=analysis)
    assert not any(i.rule_id == "VAL-ENG-003" and "mislabeled rule provenance" in i.title.lower() for i in report.issues)


@pytest.mark.asyncio
async def test_ai_generated_assumptions():
    """Verify that AI-proposed assumptions remain unconfirmed and ungrounded numeric claims are flagged."""
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        project_id="p-test-assump-1",
        product_category="Customer Support",
        problem_domain="Customer Support",
        intended_users=["Agent"],
        core_objectives=["Answer queries"],
        facts=["Customers submit help tickets"]
    )

    # Negative case: ungrounded metric (99.9%) claimed as confirmed_user_input without user evidence
    br_bad = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Response Guarantee | System shall resolve 99.9% of tickets within 1 minute. | `confirmed_user_input` | User submission fact | High quality | No |\n"
    )
    sections_bad = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain body content for testing.") for k in CANONICAL_SECTIONS}
    sections_bad["business_rules"] = PRDSectionContent(key="business_rules", title=SECTION_TITLES["business_rules"], content=br_bad)
    prd_bad = PRDVersion(prd_id="prd-4b", project_id="p-test-assump-1", version_number="v2.2", sections=sections_bad)
    report_bad = await validator.validate_version(prd_bad, analysis=analysis)
    assert any(i.rule_id in ["VAL-ENG-003", "VAL-PROV-001"] and "unconfirmed metric '99.9%'" in i.title.lower() for i in report_bad.issues)

    # Positive case: properly marked as ai_proposed_assumption requiring confirmation
    br_good = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Response Guarantee | System shall target high availability. | `ai_proposed_assumption` | AI Proposed Assumption: Customer Support Operational Standard | High quality | Yes (Review needed) |\n"
    )
    sections_good = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain body content for testing.") for k in CANONICAL_SECTIONS}
    sections_good["business_rules"] = PRDSectionContent(key="business_rules", title=SECTION_TITLES["business_rules"], content=br_good)
    prd_good = PRDVersion(prd_id="prd-4g", project_id="p-test-assump-1", version_number="v2.2", sections=sections_good)
    report_good = await validator.validate_version(prd_good, analysis=analysis)
    assert not any("unconfirmed metric" in i.title.lower() for i in report_good.issues)


@pytest.mark.asyncio
async def test_recommendations():
    """Verify that recommendations are never presented as confirmed requirements without stakeholder approval."""
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        project_id="p-test-rec-1",
        product_category="Warehouse Fleet Robotics",
        problem_domain="Warehouse Fleet Robotics",
        intended_users=["Fleet Supervisor"],
        core_objectives=["Optimize robot paths"],
        facts=["AGVs transport pallets across grids"]
    )

    # Negative case: recommendation presented as confirmed requirement with confirmation_required = False
    br_bad = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Preventative Charging | Robots must be strictly enforced to charge at off-peak hours. | `recommendation` | Advisory Recommendation: Fleet Efficiency Guideline | Saves energy | False |\n"
    )
    sections_bad = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain body content for testing.") for k in CANONICAL_SECTIONS}
    sections_bad["business_rules"] = PRDSectionContent(key="business_rules", title=SECTION_TITLES["business_rules"], content=br_bad)
    prd_bad = PRDVersion(prd_id="prd-5b", project_id="p-test-rec-1", version_number="v2.2", sections=sections_bad)
    report_bad = await validator.validate_version(prd_bad, analysis=analysis)
    assert any(i.rule_id == "VAL-ENG-003" and "recommendation presented as confirmed requirement" in i.title.lower() for i in report_bad.issues)

    # Positive case: recommendation with confirmation_required = True
    br_good = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Preventative Charging | Recommend scheduling robot battery charging during shift changeovers. | `recommendation` | Advisory Recommendation: Fleet Efficiency Guideline | Saves energy | Yes (Review needed) |\n"
    )
    sections_good = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain body content for testing.") for k in CANONICAL_SECTIONS}
    sections_good["business_rules"] = PRDSectionContent(key="business_rules", title=SECTION_TITLES["business_rules"], content=br_good)
    prd_good = PRDVersion(prd_id="prd-5g", project_id="p-test-rec-1", version_number="v2.2", sections=sections_good)
    report_good = await validator.validate_version(prd_good, analysis=analysis)
    assert not any("recommendation presented as confirmed requirement" in i.title.lower() for i in report_good.issues)


@pytest.mark.asyncio
async def test_unrecognized_assignment_phrases():
    """Verify that unrecognized assignment phrases produce a meaningful validation warning (VAL-SEM-006)."""
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        project_id="p-test-unrec-1",
        product_category="Educational System",
        problem_domain="Academic Administration",
        intended_users=["Student"],
        core_objectives=["Track attendance"],
        assignment_requirements=AssignmentRequirement(
            instruction="Build attendance system",
            mandatory_sections=["System Architecture", "Quantum Hyper-Dimensional Storage Protocol"]
        )
    )

    sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain body content for testing.") for k in CANONICAL_SECTIONS}
    prd_ver = PRDVersion(prd_id="prd-6", project_id="p-test-unrec-1", version_number="v2.2", sections=sections)
    report = await validator.validate_version(prd_ver, analysis=analysis)

    # Must produce VAL-SEM-006 warning for unrecognized phrase
    unrec_issue = next((i for i in report.issues if i.rule_id == "VAL-SEM-006"), None)
    assert unrec_issue is not None
    assert unrec_issue.severity == "warning"
    assert "Quantum Hyper-Dimensional Storage Protocol" in unrec_issue.title
    # Must NOT produce false VAL-SEM-005 error for recognized phrase "System Architecture"
    assert not any(i.rule_id == "VAL-SEM-005" and "System Architecture" in i.title for i in report.issues)


@pytest.mark.asyncio
async def test_legitimate_cross_domain_terminology():
    """Verify that a legitimate hybrid product does not trigger false positive cross-domain contamination."""
    validator = ValidationService(validation_repo=None)
    # A hybrid product that legitimately combines Student Support and Customer Service
    analysis = AnalysisRecord(
        project_id="p-test-cross-1",
        product_category="Student Support Helpdesk",
        problem_domain="Customer Support and Higher Education Administration",
        intended_users=["Student", "Support Agent"],
        core_objectives=["Answer student queries regarding course attendance and exam eligibility"]
    )

    sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain content mentioning student attendance thresholds and customer support escalation queues.") for k in CANONICAL_SECTIONS}
    prd_ver = PRDVersion(prd_id="prd-7", project_id="p-test-cross-1", version_number="v2.2", sections=sections)
    report = await validator.validate_version(prd_ver, analysis=analysis)

    # Must NOT produce VAL-XDOM-001 error because domain context legitimately includes both
    assert not any(i.rule_id == "VAL-XDOM-001" for i in report.issues)


@pytest.mark.asyncio
async def test_conflicting_provenance_references():
    """Verify that conflicting provenance references (e.g. confirmed_user_input citing assignment or non-user source) are flagged."""
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        project_id="p-test-conflict-1",
        product_category="Support Automation",
        problem_domain="Customer Support",
        intended_users=["Agent"],
        core_objectives=["Grounded Q&A"],
        facts=["Customers submit support questions"]
    )

    # Negative case: rule claims confirmed_user_input but cites Assignment Requirement
    br_conflict = (
        "| ID | Rule Title | Operational Statement | Provenance | Source Reference | Rationale | Confirmation Required |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **BR-001** | Response Guarantee | Responses must be verified against approved articles. | `confirmed_user_input` | Assignment Requirement: Course Guideline 4.1 | Policy enforcement | No |\n"
    )
    sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid domain body content for testing.") for k in CANONICAL_SECTIONS}
    sections["business_rules"] = PRDSectionContent(key="business_rules", title=SECTION_TITLES["business_rules"], content=br_conflict)

    prd_ver = PRDVersion(prd_id="prd-8", project_id="p-test-conflict-1", version_number="v2.2", sections=sections)
    report = await validator.validate_version(prd_ver, analysis=analysis)

    conflict_issue = next((i for i in report.issues if i.rule_id == "VAL-ENG-003" and "conflicting provenance reference" in i.title.lower()), None)
    assert conflict_issue is not None
    assert conflict_issue.severity == "warning"


@pytest.mark.asyncio
async def test_phase2_3_mandatory_rejection_gates_verdict():
    """Verify that any mandatory quality failure triggers is_valid=False and verdict='REJECTED'."""
    validator = ValidationService(validation_repo=None)

    # 1. Gate A: Attendance Mathematical Inversion (BR-002 'miss more than 75%')
    att_analysis = AnalysisRecord(
        project_id="p-gate-1",
        product_category="Attendance Management",
        problem_domain="Education Management",
        intended_users=["Faculty Instructor", "Student"],
        core_objectives=["Attendance tracking"]
    )
    sections_a = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid baseline content with faculty instructor and student.") for k in CANONICAL_SECTIONS}
    sections_a["business_rules"] = PRDSectionContent(
        key="business_rules",
        title=SECTION_TITLES["business_rules"],
        content="| ID | Title | Statement | Provenance | Source | Rationale | Conf |\n|---|---|---|---|---|---|---|\n| **BR-001** | Rule | Regular rule | `confirmed_user_input` | User fact | Integrity | No |\n| **BR-002** | Missed Threshold | Students who miss more than 75% of classes will receive an early warning alert. | `confirmed_user_input` | User fact | Warning | No |\n"
    )
    prd_a = PRDVersion(prd_id="prd-ga", project_id="p-gate-1", version_number="v2.3", sections=sections_a)
    rep_a = await validator.validate_version(prd_a, analysis=att_analysis)
    assert rep_a.is_valid is False
    assert rep_a.verdict == "REJECTED"
    assert any(i.rule_id == "VAL-MTH-001" and "mathematical inversion" in i.title.lower() for i in rep_a.issues)

    # 2. Gate B: Customer Support Unsupported Response/Hold Limit
    cs_analysis = AnalysisRecord(
        project_id="p-gate-2",
        product_category="Customer Support",
        problem_domain="Customer Support",
        intended_users=["Customer", "Customer Service Representative"],
        core_objectives=["Provide accurate responses"]
    )
    sections_b = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid baseline content for customer and customer service representative.") for k in CANONICAL_SECTIONS}
    sections_b["business_rules"] = PRDSectionContent(
        key="business_rules",
        title=SECTION_TITLES["business_rules"],
        content="| ID | Title | Statement | Provenance | Source | Rationale | Conf |\n|---|---|---|---|---|---|---|\n| **BR-001** | Rule | Answers grounded in KB | `confirmed_user_input` | User fact | Accuracy | No |\n| **BR-002** | Hold Limit | Hold times should not exceed 2 minutes for first-level support requests. | `confirmed_user_input` | User fact | Speed | No |\n"
    )
    prd_b = PRDVersion(prd_id="prd-gb", project_id="p-gate-2", version_number="v2.3", sections=sections_b)
    rep_b = await validator.validate_version(prd_b, analysis=cs_analysis)
    assert rep_b.is_valid is False
    assert rep_b.verdict == "REJECTED"
    assert any(i.rule_id == "VAL-NUM-002" for i in rep_b.issues)

    # 3. Gate C: Fabricated Persona in Attendance (Support / Admin Role)
    sections_c = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content="Valid baseline content with faculty instructor and student.") for k in CANONICAL_SECTIONS}
    sections_c["user_personas"] = PRDSectionContent(
        key="user_personas",
        title=SECTION_TITLES["user_personas"],
        content="#### Persona 1: Faculty Instructor\n- Responsibilities: Teaching.\n#### Persona 2: Support / Admin Role\n- Responsibilities: IT setup."
    )
    prd_c = PRDVersion(prd_id="prd-gc", project_id="p-gate-1", version_number="v2.3", sections=sections_c)
    rep_c = await validator.validate_version(prd_c, analysis=att_analysis)
    assert rep_c.is_valid is False
    assert rep_c.verdict == "REJECTED"
    assert any(i.rule_id == "VAL-SEM-002" and "support / admin" in i.title.lower() for i in rep_c.issues)


@pytest.mark.asyncio
async def test_phase2_3_four_domains_generalization():
    """Verify that all 4 diverse domains generate valid, high-integrity PRDs passing independent validation."""
    adapter = OfflineMockAdapter()
    analyzer = InputAnalyzer(adapter)
    req_eng = RequirementEngineer(adapter)
    sh_analyst = StakeholderAnalyst(adapter)
    br_analyst = BusinessRulesAnalyst(adapter)
    risk_analyst = RiskAnalyst(adapter)
    generator = PRDGenerator(adapter)
    validator = ValidationService(validation_repo=None)

    domains = [
        (
            "AI Customer Support Assistant",
            "Build an AI-powered customer support assistant that answers customer questions using "
            "approved knowledge-base articles, maintains conversation history, identifies low-confidence "
            "answers below 80%, and escalates complex queries to human agents with a summarized context.",
            "Customer Support"
        ),
        (
            "College Attendance Management System",
            "Build a College Attendance Management System where faculty instructors record daily attendance, "
            "students can view their attendance percentage, automated warning notifications are sent if "
            "attendance falls below 75%, and department heads configure attendance policies and condonation rules.",
            "Education Management"
        ),
        (
            "Autonomous Warehouse Robot Fleet Management",
            "Build an Autonomous Warehouse Robot Fleet Management system that schedules automated guided vehicles "
            "(AGVs) for pallet transport, calculates collision-free routing across warehouse grids, dispatches low-battery "
            "robots to charging docks when battery charge is below 20%, and alerts floor supervisors on route blockage.",
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

    for title, concept, expected_domain_keyword in domains:
        sub = IdeaSubmissionResponse(
            id=f"sub-gen-{title[:3].lower()}",
            project_id=f"proj-gen-{title[:3].lower()}",
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

        sections = await generator.generate_full_prd(
            project_title=title,
            analysis=analysis,
            clarification_session=None,
            requirements_data=req_data,
            version_number="v2.3",
            job_id="job-test-gen"
        )
        assert len(sections) == 27
        for sec_key in CANONICAL_SECTIONS:
            assert sec_key in sections
            assert len(sections[sec_key].content.strip()) >= 20

        prd_version = PRDVersion(
            prd_id=f"prd-gen-{title[:3].lower()}",
            project_id=f"proj-gen-{title[:3].lower()}",
            version_number="v2.3",
            job_id="job-test-gen",
            sections=sections
        )
        report = await validator.validate_version(prd_version, analysis=analysis)
        assert report.is_valid is True, f"Domain '{title}' failed validation with errors: {[i.title for i in report.issues if i.severity == 'error']}"
        assert report.verdict == "APPROVED"
        assert report.score >= 80


# =====================================================================
# Phase 2.4 Semantic Quality & Validation Suite
# =====================================================================
@pytest.mark.asyncio
async def test_val_ac_003_boundary_and_duplicate_conditions():
    """Verify VAL-AC-003 catches generic boilerplate and duplicates, and accepts 80% boundary criteria."""
    validator = ValidationService(validation_repo=None)

    # 1. Boilerplate / duplicate test
    bad_ac_content = (
        "| Criterion ID | Requirement ID | Given (Precondition) | When (Action / Trigger) | Then (Observable Outcome) |\n"
        "| :--- | :--- | :--- | :--- | :--- |\n"
        "| AC-001 | FR-001 | User asks query | System executes action | executes successfully and logs the result |\n"
        "| AC-002 | FR-002 | User submits query | System evaluates state | executes successfully and logs the result |\n"
    )
    bad_sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content=f"Section {k} text with sufficient length for testing.") for k in CANONICAL_SECTIONS}
    bad_sections["acceptance_criteria"] = PRDSectionContent(key="acceptance_criteria", title=SECTION_TITLES["acceptance_criteria"], content=bad_ac_content)
    prd_bad = PRDVersion(prd_id="prd-bad-ac", project_id="p-1", version_number="v2.4", sections=bad_sections)
    report_bad = await validator.validate_version(prd_bad)
    ac_issues = [i for i in report_bad.issues if i.rule_id == "VAL-AC-003"]
    assert len(ac_issues) >= 1
    assert any(i.severity == "error" for i in ac_issues)
    assert report_bad.score <= 65
    assert report_bad.verdict == "REJECTED"

    # 2. Rich 80% boundary criteria test
    good_ac_content = (
        "| Criterion ID | Requirement ID | Given (Precondition) | When (Action / Trigger) | Then (Observable Outcome) |\n"
        "| :--- | :--- | :--- | :--- | :--- |\n"
        "| AC-001 | FR-001 | Confidence is 79.9% (< 80.0%) | Evaluation completes | Escalates to human agent queue |\n"
        "| AC-002 | FR-002 | Confidence is exactly 80.0% | Evaluation completes | Grounded answer returned with citation |\n"
        "| AC-003 | FR-003 | Confidence is 80.1% (> 80.0%) | Evaluation completes | Grounded response delivered to user |\n"
        "| AC-004 | FR-004 | Target article deleted | Retrieval runs | Triggers graceful missing article fallback |\n"
        "| AC-005 | FR-005 | Cosine similarity service offline | Evaluation triggered | Safe degradation to human queue |\n"
        "| AC-006 | FR-006 | Complex multi-intent query | Ambiguity detected | Clarification requested from user |\n"
    )
    bad_sections["acceptance_criteria"] = PRDSectionContent(key="acceptance_criteria", title=SECTION_TITLES["acceptance_criteria"], content=good_ac_content)
    prd_good = PRDVersion(prd_id="prd-good-ac", project_id="p-1", version_number="v2.4", sections=bad_sections)
    report_good = await validator.validate_version(prd_good)
    ac_errors = [i for i in report_good.issues if i.rule_id == "VAL-AC-003" and i.severity == "error"]
    assert len(ac_errors) == 0


@pytest.mark.asyncio
async def test_val_us_001_human_persona_and_system_actor_rejection():
    """Verify VAL-US-001 rejects system actors and internal tasks in user stories."""
    validator = ValidationService(validation_repo=None)

    # 1. System actor test ("System", "Backend")
    bad_us_content = (
        "| Story ID | Role / Persona | I want to (Action / Capability) | So that (Business Value / Outcome) |\n"
        "| :--- | :--- | :--- | :--- |\n"
        "| US-001 | System | calculate confidence score | low quality answers are filtered out reliably |\n"
        "| US-002 | Backend | process background job | queued tasks complete within operational SLAs |\n"
    )
    sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content=f"Section {k} text with sufficient length for testing.") for k in CANONICAL_SECTIONS}
    sections["user_stories"] = PRDSectionContent(key="user_stories", title=SECTION_TITLES["user_stories"], content=bad_us_content)
    prd = PRDVersion(prd_id="prd-bad-us", project_id="p-1", version_number="v2.4", sections=sections)
    report = await validator.validate_version(prd)
    us_issues = [i for i in report.issues if i.rule_id == "VAL-US-001"]
    assert len(us_issues) >= 1
    assert any("Invalid System Actor" in i.title or "Internal System Task" in i.title for i in us_issues)
    assert report.is_valid is False
    assert report.score <= 65


@pytest.mark.asyncio
async def test_val_xsec_cross_section_consistency():
    """Verify VAL-XSEC-001 through 005 detect cross-section contradictions."""
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        id="an-1",
        project_id="p-1",
        project_title="Support Assistant",
        problem_domain="Customer Support",
        product_category="AI Support Assistant",
        core_objectives=["Provide instant AI responses", "Escalate low confidence queries"],
        explicit_constraints=["Escalate when confidence is below 80%"],
        facts=["Approved knowledge base used"]
    )

    base_sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content=f"Section {k} valid content with adequate length.") for k in CANONICAL_SECTIONS}

    # 1. VAL-XSEC-001: Escalation threshold conflict (0.5 vs 80%)
    s1 = dict(base_sections)
    s1["functional_requirements"] = PRDSectionContent(key="functional_requirements", title=SECTION_TITLES["functional_requirements"], content="Escalate to human agent when relevance score is below 0.5 threshold.")
    prd1 = PRDVersion(prd_id="prd-x1", project_id="p-1", version_number="v2.4", sections=s1)
    rep1 = await validator.validate_version(prd1, analysis=analysis)
    assert any(i.rule_id == "VAL-XSEC-001" for i in rep1.issues)

    # 2. VAL-XSEC-002: Retention conflict (24h vs 30d)
    s2 = dict(base_sections)
    s2["product_scope"] = PRDSectionContent(key="product_scope", title=SECTION_TITLES["product_scope"], content="Chat session transcripts are preserved for 24 hours.")
    s2["security_and_privacy_requirements"] = PRDSectionContent(key="security_and_privacy_requirements", title=SECTION_TITLES["security_and_privacy_requirements"], content="Chat transcripts are retained for 30 days and deleted.")
    prd2 = PRDVersion(prd_id="prd-x2", project_id="p-1", version_number="v2.4", sections=s2)
    rep2 = await validator.validate_version(prd2, analysis=analysis)
    assert any(i.rule_id == "VAL-XSEC-002" for i in rep2.issues)

    # 3. VAL-XSEC-003: Channel conflict (WhatsApp in web-chat only MVP)
    s3 = dict(base_sections)
    s3["product_scope"] = PRDSectionContent(key="product_scope", title=SECTION_TITLES["product_scope"], content="Product scope is strictly a web chat only MVP.")
    s3["integration_requirements"] = PRDSectionContent(key="integration_requirements", title=SECTION_TITLES["integration_requirements"], content="Provides WhatsApp integration for mobile inbound tickets.")
    prd3 = PRDVersion(prd_id="prd-x3", project_id="p-1", version_number="v2.4", sections=s3)
    rep3 = await validator.validate_version(prd3, analysis=analysis)
    assert any(i.rule_id == "VAL-XSEC-003" for i in rep3.issues)

    # 4. VAL-XSEC-004: Ticketing conflict (Mandatory Zendesk in deferred ticketing scope)
    s4 = dict(base_sections)
    s4["product_scope"] = PRDSectionContent(key="product_scope", title=SECTION_TITLES["product_scope"], content="External ticketing integration is out of scope for MVP.")
    s4["integration_requirements"] = PRDSectionContent(key="integration_requirements", title=SECTION_TITLES["integration_requirements"], content="Mandatory Zendesk API integration for human agent dispatch.")
    prd4 = PRDVersion(prd_id="prd-x4", project_id="p-1", version_number="v2.4", sections=s4)
    rep4 = await validator.validate_version(prd4, analysis=analysis)
    assert any(i.rule_id == "VAL-XSEC-004" for i in rep4.issues)

    # 5. VAL-XSEC-005: Cloud vendor lock-in
    s5 = dict(base_sections)
    s5["dependencies_and_constraints"] = PRDSectionContent(key="dependencies_and_constraints", title=SECTION_TITLES["dependencies_and_constraints"], content="The system must run on AWS Bedrock exclusively.")
    prd5 = PRDVersion(prd_id="prd-x5", project_id="p-1", version_number="v2.4", sections=s5)
    rep5 = await validator.validate_version(prd5, analysis=analysis)
    assert any(i.rule_id == "VAL-XSEC-005" for i in rep5.issues)


@pytest.mark.asyncio
async def test_val_prov_001_canonical_provenance():
    """Verify VAL-PROV-001 enforces canonical 6 provenances and flags mislabeled unconfirmed metrics."""
    validator = ValidationService(validation_repo=None)
    analysis = AnalysisRecord(
        id="an-prov",
        project_id="p-prov",
        product_category="AI Customer Support Assistant",
        problem_domain="Customer Support",
        core_objectives=["Answer customer queries"],
        explicit_constraints=["80% answer confidence threshold"],
        facts=["Approved articles only"]
    )
    sections = {k: PRDSectionContent(key=k, title=SECTION_TITLES[k], content=f"Section {k} text with sufficient length for testing.") for k in CANONICAL_SECTIONS}
    # Bad provenance value ('draft_v1') and unconfirmed metric (95% not in user constraints)
    bad_br = (
        "| Rule ID | Title | Rule Statement | Provenance | Source Reference | Stakeholder Confirmation Required |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| BR-001 | Quality Bar | System must meet 95% satisfaction | `confirmed_user_input` | User submission quote | No |\n"
        "| BR-002 | Legacy Rule | Escalates on error | `draft_heuristic` | Internal notes | Yes |\n"
    )
    sections["business_rules"] = PRDSectionContent(key="business_rules", title=SECTION_TITLES["business_rules"], content=bad_br)
    prd = PRDVersion(prd_id="prd-prov", project_id="p-prov", version_number="v2.4", sections=sections)
    rep = await validator.validate_version(prd, analysis=analysis)
    prov_issues = [i for i in rep.issues if i.rule_id == "VAL-PROV-001"]
    assert len(prov_issues) >= 2
    assert any("Assertion of Unconfirmed Metric" in i.title for i in prov_issues)
    assert any("Non-Canonical Provenance Value" in i.title for i in prov_issues)




