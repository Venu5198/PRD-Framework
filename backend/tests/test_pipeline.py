import pytest
from app.ai.offline_adapter import OfflineMockAdapter
from app.ai.pipeline.input_analyzer import InputAnalyzer
from app.ai.pipeline.clarification_engine import ClarificationEngine
from app.ai.pipeline.requirement_engineer import RequirementEngineer
from app.ai.pipeline.prd_generator import PRDGenerator
from app.models.submission import IdeaSubmissionResponse
from datetime import datetime

@pytest.mark.asyncio
async def test_input_analyzer():
    adapter = OfflineMockAdapter()
    analyzer = InputAnalyzer(adapter)
    
    sub = IdeaSubmissionResponse(
        id="sub-1",
        project_id="proj-1",
        submission_type="idea",
        raw_idea="A local offline automated tool for generating PRD documents from unstructured developer ideas.",
        problem_statement="Creating PRDs takes too much time and missing requirements cause costly delays.",
        created_at=datetime.utcnow()
    )
    
    analysis = await analyzer.analyze(sub)
    assert analysis.project_id == "proj-1"
    assert len(analysis.intended_users) > 0
    assert len(analysis.core_objectives) > 0
    assert len(analysis.facts) > 0
    assert len(analysis.assumptions) > 0

@pytest.mark.asyncio
async def test_clarification_engine():
    adapter = OfflineMockAdapter()
    analyzer = InputAnalyzer(adapter)
    clarifier = ClarificationEngine(adapter)

    sub = IdeaSubmissionResponse(
        id="sub-1",
        project_id="proj-1",
        submission_type="assignment",
        raw_idea="Build an automated requirement framework for our senior capstone course.",
        assignment_context="Must follow IEEE 830-1998 format and contain at least 5 functional requirements.",
        created_at=datetime.utcnow()
    )
    analysis = await analyzer.analyze(sub)
    session = await clarifier.generate_questions(analysis)
    
    assert session.project_id == "proj-1"
    assert len(session.questions) > 0
    assert session.questions[0].priority in ("critical", "medium", "low")
    assert len(session.questions[0].suggested_options) > 0

@pytest.mark.asyncio
async def test_requirement_engineer_and_prd_assembly():
    adapter = OfflineMockAdapter()
    analyzer = InputAnalyzer(adapter)
    req_eng = RequirementEngineer(adapter)
    generator = PRDGenerator(adapter)

    sub = IdeaSubmissionResponse(
        id="sub-1",
        project_id="proj-1",
        submission_type="idea",
        raw_idea="Local PRD Engineering framework for offline development",
        created_at=datetime.utcnow()
    )
    analysis = await analyzer.analyze(sub)
    req_data = await req_eng.engineer(analysis, None)

    assert "functional_requirements" in req_data
    assert "acceptance_criteria" in req_data
    assert len(req_data["functional_requirements"]) > 0

    sections = await generator.generate_full_prd(
        project_title="Local PRD Engine",
        analysis=analysis,
        clarification_session=None,
        requirements_data=req_data
    )

    # Verify all 27 canonical sections exist
    from app.models.prd import CANONICAL_SECTIONS
    assert len(sections) == 27
    for key in CANONICAL_SECTIONS:
        assert key in sections
        assert len(sections[key].content) > 10

