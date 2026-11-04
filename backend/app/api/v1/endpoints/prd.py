from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.models.prd import (
    PRDDocument,
    PRDVersion,
    SectionUpdatePayload,
    SectionRegeneratePayload
)
from app.services.prd_service import PRDService
from app.db.repository import PRDRepository, PRDVersionRepository
from app.api.deps import (
    get_prd_service,
    get_prd_repo,
    get_version_repo,
    get_current_user
)

router = APIRouter()

@router.post("/{project_id}/generate", response_model=PRDVersion)
async def generate_prd(
    project_id: str,
    prd_service: PRDService = Depends(get_prd_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        return await prd_service.generate_full_prd(project_id, current_user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}", response_model=dict)
async def get_active_prd(
    project_id: str,
    prd_repo: PRDRepository = Depends(get_prd_repo),
    version_repo: PRDVersionRepository = Depends(get_version_repo),
    current_user: dict = Depends(get_current_user)
):
    prd_doc = await prd_repo.get_by_project(project_id)
    if not prd_doc:
        raise HTTPException(status_code=404, detail="No PRD document generated yet.")

    current_ver = None
    if prd_doc.get("current_version_id"):
        current_ver = await version_repo.get_by_id(prd_doc["current_version_id"])

    return {
        "document": PRDDocument(**prd_doc),
        "active_version": PRDVersion(**current_ver) if current_ver else None
    }

@router.get("/{project_id}/versions", response_model=List[PRDVersion])
async def list_prd_versions(
    project_id: str,
    prd_repo: PRDRepository = Depends(get_prd_repo),
    version_repo: PRDVersionRepository = Depends(get_version_repo),
    current_user: dict = Depends(get_current_user)
):
    prd_doc = await prd_repo.get_by_project(project_id)
    if not prd_doc:
        return []
    versions = await version_repo.get_by_prd(prd_doc["id"])
    return [PRDVersion(**v) for v in versions]

@router.get("/{project_id}/versions/{version_id}", response_model=PRDVersion)
async def get_prd_version(
    project_id: str,
    version_id: str,
    version_repo: PRDVersionRepository = Depends(get_version_repo),
    current_user: dict = Depends(get_current_user)
):
    ver = await version_repo.get_by_id(version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="PRD version not found.")
    return PRDVersion(**ver)

@router.patch("/{project_id}/sections/{section_key}", response_model=PRDVersion)
async def update_section(
    project_id: str,
    section_key: str,
    payload: SectionUpdatePayload,
    prd_service: PRDService = Depends(get_prd_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        return await prd_service.update_section(project_id, section_key, payload, current_user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{project_id}/sections/{section_key}/regenerate", response_model=PRDVersion)
async def regenerate_section(
    project_id: str,
    section_key: str,
    payload: SectionRegeneratePayload,
    prd_service: PRDService = Depends(get_prd_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        return await prd_service.regenerate_section(project_id, section_key, payload, current_user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{project_id}/versions/{version_id}/approve", response_model=PRDVersion)
async def approve_version(
    project_id: str,
    version_id: str,
    prd_service: PRDService = Depends(get_prd_service),
    current_user: dict = Depends(get_current_user)
):
    try:
        return await prd_service.approve_version(project_id, version_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

