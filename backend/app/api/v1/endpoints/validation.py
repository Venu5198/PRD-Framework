from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.validation import ValidationReport
from app.models.prd import PRDVersion
from app.services.validation_service import ValidationService
from app.db.repository import PRDRepository, PRDVersionRepository, ValidationRepository, ProjectRepository
from app.api.deps import (
    get_validation_service,
    get_validation_repo,
    get_prd_repo,
    get_version_repo,
    get_project_repo,
    get_current_user
)

router = APIRouter()

@router.post("/{project_id}/validate", response_model=ValidationReport)
async def validate_active_prd(
    project_id: str,
    version_id: Optional[str] = Query(None, description="Optional PRDVersion ID to validate. If omitted, validates current active version."),
    project_repo: ProjectRepository = Depends(get_project_repo),
    prd_repo: PRDRepository = Depends(get_prd_repo),
    version_repo: PRDVersionRepository = Depends(get_version_repo),
    validation_service: ValidationService = Depends(get_validation_service),
    current_user: dict = Depends(get_current_user)
):
    project = await project_repo.get_by_id(project_id)
    if not project or project.get("owner_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Project not found.")

    prd_doc = await prd_repo.get_by_project(project_id)
    if not prd_doc:
        raise HTTPException(status_code=404, detail="No PRD available for this project.")

    if version_id:
        ver_doc = await version_repo.get_by_id(version_id)
        if not ver_doc:
            raise HTTPException(status_code=404, detail=f"PRD version '{version_id}' not found.")
        if ver_doc.get("project_id") != project_id or ver_doc.get("prd_id") != prd_doc["id"]:
            raise HTTPException(status_code=404, detail=f"PRD version '{version_id}' does not belong to this project.")
    else:
        if not prd_doc.get("current_version_id"):
            raise HTTPException(status_code=404, detail="No active PRD version to validate.")
        ver_doc = await version_repo.get_by_id(prd_doc["current_version_id"])
        if not ver_doc:
            raise HTTPException(status_code=404, detail="Active version record not found.")

    prd_version = PRDVersion(**ver_doc)
    return await validation_service.validate_version(prd_version)

@router.get("/{project_id}/report", response_model=Optional[ValidationReport])
async def get_latest_report(
    project_id: str,
    version_id: Optional[str] = Query(None, description="Optional PRDVersion ID to retrieve report for. If omitted, retrieves for current version."),
    project_repo: ProjectRepository = Depends(get_project_repo),
    prd_repo: PRDRepository = Depends(get_prd_repo),
    version_repo: PRDVersionRepository = Depends(get_version_repo),
    validation_repo: ValidationRepository = Depends(get_validation_repo),
    validation_service: ValidationService = Depends(get_validation_service),
    current_user: dict = Depends(get_current_user)
):
    project = await project_repo.get_by_id(project_id)
    if not project or project.get("owner_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Project not found.")
    prd_doc = await prd_repo.get_by_project(project_id)
    if not prd_doc:
        return None

    if version_id:
        ver_doc = await version_repo.get_by_id(version_id)
        if not ver_doc:
            raise HTTPException(status_code=404, detail=f"PRD version '{version_id}' not found.")
        if ver_doc.get("project_id") != project_id or ver_doc.get("prd_id") != prd_doc["id"]:
            raise HTTPException(status_code=404, detail=f"PRD version '{version_id}' does not belong to this project.")
        target_version_id = version_id
    else:
        target_version_id = prd_doc.get("current_version_id")
        if not target_version_id:
            return None
        ver_doc = await version_repo.get_by_id(target_version_id)

    report = await validation_repo.get_latest_by_version(target_version_id)
    if not report and ver_doc:
        # Validate on demand if report is not yet persisted
        prd_version = PRDVersion(**ver_doc)
        return await validation_service.validate_version(prd_version)

    return ValidationReport(**report) if report else None

