import pytest
from app.ai.offline_adapter import OfflineMockAdapter
from app.ai.pipeline.assignment_parser import AssignmentParser, AssignmentParserInput
from app.ai.pipeline.problem_analyst import ProblemAnalyst, ProblemAnalystInput
from app.ai.pipeline.stakeholder_analyst import StakeholderAnalyst, StakeholderAnalystInput
from app.ai.pipeline.business_rules_analyst import BusinessRulesAnalyst, BusinessRulesInput
from app.ai.pipeline.risk_analyst import RiskAnalyst, RiskAnalystInput

@pytest.mark.asyncio
async def test_assignment_parser():
    ai = OfflineMockAdapter()
    parser = AssignmentParser(ai)
    inp = AssignmentParserInput(assignment_text="Deliver a full PRD adhering to IEEE-830 guidelines with 5 functional requirements.")
    res = await parser.parse(inp)
    assert len(res.mandatory_sections) > 0
    assert len(res.deliverables) > 0

@pytest.mark.asyncio
async def test_problem_analyst():
    ai = OfflineMockAdapter()
    analyst = ProblemAnalyst(ai)
    inp = ProblemAnalystInput(concept="Automated PRD framework", problem_statement="Writing PRDs manually is slow.")
    res = await analyst.analyze(inp)
    assert res.problem_domain is not None
    assert len(res.root_pain_points) > 0
    assert len(res.desired_outcomes) > 0

@pytest.mark.asyncio
async def test_stakeholder_analyst():
    ai = OfflineMockAdapter()
    analyst = StakeholderAnalyst(ai)
    inp = StakeholderAnalystInput(
        product_category="DevTools",
        intended_users=["Lead Engineer", "Product Manager"],
        domain="Software"
    )
    res = await analyst.analyze(inp)
    assert len(res.personas) >= 2
    assert len(res.user_journeys) >= 3

@pytest.mark.asyncio
async def test_business_rules_analyst():
    ai = OfflineMockAdapter()
    analyst = BusinessRulesAnalyst(ai)
    inp = BusinessRulesInput(
        domain="Software",
        objectives=["Ensure version auditability"],
        constraints=["Local execution only"]
    )
    res = await analyst.extract_rules(inp)
    assert len(res.business_rules) >= 3
    assert any(r.id == "BR-001" for r in res.business_rules)

@pytest.mark.asyncio
async def test_risk_analyst():
    ai = OfflineMockAdapter()
    analyst = RiskAnalyst(ai)
    inp = RiskAnalystInput(
        problem_domain="Requirements Automation",
        capabilities=["AI inference", "Document export"],
        constraints=["Offline local execution"]
    )
    res = await analyst.analyze_risks(inp)
    assert len(res.risks) >= 3
    assert any(r.id == "RSK-001" for r in res.risks)
