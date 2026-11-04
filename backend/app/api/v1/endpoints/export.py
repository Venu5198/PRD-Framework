from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.models.prd import PRDVersion
from app.services.export_service import ExportService
from app.db.repository import PRDRepository, PRDVersionRepository, ProjectRepository
from app.api.deps import (
    get_export_service,
    get_prd_repo,
    get_version_repo,
    get_project_repo,
    get_current_user
)

router = APIRouter()

@router.get("/{project_id}/{export_format}")
async def export_prd(
    project_id: str,
    export_format: str,
    export_service: ExportService = Depends(get_export_service),
    prd_repo: PRDRepository = Depends(get_prd_repo),
    version_repo: PRDVersionRepository = Depends(get_version_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    current_user: dict = Depends(get_current_user)
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    prd_doc = await prd_repo.get_by_project(project_id)
    if not prd_doc or not prd_doc.get("current_version_id"):
        raise HTTPException(status_code=404, detail="No PRD version available to export.")

    ver_doc = await version_repo.get_by_id(prd_doc["current_version_id"])
    prd_version = PRDVersion(**ver_doc)
    proj_title = project.get("title", "Project")

    fmt = export_format.lower().strip()
    if fmt in ("md", "markdown"):
        file_path = export_service.export_markdown(prd_version, proj_title)
        return FileResponse(
            path=str(file_path),
            media_type="text/markdown",
            filename=file_path.name
        )
    elif fmt == "docx":
        file_path = export_service.export_docx(prd_version, proj_title)
        return FileResponse(
            path=str(file_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=file_path.name
        )
    elif fmt == "pdf":
        file_path = export_service.export_pdf(prd_version, proj_title)
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=file_path.name
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{export_format}'. Supported formats: markdown, docx, pdf"
        )

