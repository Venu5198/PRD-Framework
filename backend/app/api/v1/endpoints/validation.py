from fastapi import APIRouter, Depends, HTTPException
from app.models.validation import ValidationReport
from app.models.prd import PRDVersion
from app.services.validation_service import ValidationService
from app.db.repository import PRDRepository, PRDVersionRepository, ValidationRepository
from app.api.deps import (
    get_validation_service,
    get_validation_repo,
    get_prd_repo,
    get_version_repo,
    get_current_user
)

router = APIRouter()

@router.post("/{project_id}/validate", response_model=ValidationReport)
async def validate_active_prd(
    project_id: str,
    prd_repo: PRDRepository = Depends(get_prd_repo),
    version_repo: PRDVersionRepository = Depends(get_version_repo),
    validation_service: ValidationService = Depends(get_validation_service),
    current_user: dict = Depends(get_current_user)
):
    prd_doc = await prd_repo.get_by_project(project_id)
    if not prd_doc or not prd_doc.get("current_version_id"):
        raise HTTPException(status_code=404, detail="No active PRD version to validate.")

    ver_doc = await version_repo.get_by_id(prd_doc["current_version_id"])
    if not ver_doc:
        raise HTTPException(status_code=404, detail="Version record not found.")

    prd_version = PRDVersion(**ver_doc)
    return await validation_service.validate_version(prd_version)

@router.get("/{project_id}/report", response_model=ValidationReport)
async def get_latest_report(
    project_id: str,
    prd_repo: PRDRepository = Depends(get_prd_repo),
    validation_repo: ValidationRepository = Depends(get_validation_repo),
    current_user: dict = Depends(get_current_user)
):
    prd_doc = await prd_repo.get_by_project(project_id)
    if not prd_doc or not prd_doc.get("current_version_id"):
        raise HTTPException(status_code=404, detail="No active PRD version exists.")

    report = await validation_repo.get_latest_by_version(prd_doc["current_version_id"])
    if not report:
        raise HTTPException(status_code=404, detail="No validation report generated for this version.")

    return ValidationReport(**report)

