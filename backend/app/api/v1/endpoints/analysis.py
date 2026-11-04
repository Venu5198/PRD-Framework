from fastapi import APIRouter, Depends, HTTPException
from app.models.analysis import AnalysisRecord
from app.models.clarification import ClarificationSession, ClarificationAnswerRequest
from app.services.prd_service import PRDService
from app.db.repository import AnalysisRepository, ClarificationRepository
from app.api.deps import (
    get_prd_service,
    get_analysis_repo,
    get_clarification_repo,
    get_current_user
)

router = APIRouter()

@router.post("/{project_id}/analyze", response_model=AnalysisRecord)
async def analyze_project_input(
    project_id: str,
    prd_service: PRDService = Depends(get_prd_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        return await prd_service.analyze_submission(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/analysis", response_model=AnalysisRecord)
async def get_project_analysis(
    project_id: str,
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
    current_user: dict = Depends(get_current_user)
):
    record = await analysis_repo.get_latest_by_project(project_id)
    if not record:
        raise HTTPException(status_code=404, detail="No analysis record found for this project.")
    return AnalysisRecord(**record)

@router.post("/{project_id}/clarifications/generate", response_model=ClarificationSession)
async def generate_clarifications(
    project_id: str,
    prd_service: PRDService = Depends(get_prd_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        return await prd_service.generate_clarifications(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/clarifications", response_model=ClarificationSession)
async def get_clarifications(
    project_id: str,
    clarification_repo: ClarificationRepository = Depends(get_clarification_repo),
    current_user: dict = Depends(get_current_user)
):
    session = await clarification_repo.get_latest_by_project(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="No clarification session exists.")
    return ClarificationSession(**session)

@router.post("/{project_id}/clarifications/answer")
async def answer_clarification(
    project_id: str,
    answer_in: ClarificationAnswerRequest,
    prd_service: PRDService = Depends(get_prd_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        session = await prd_service.answer_clarification(
            project_id=project_id,
            question_id=answer_in.question_id,
            answer=answer_in.answer,
            proceed_with_assumption=answer_in.proceed_with_assumption
        )
        return {"status": "success", "session": session}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

