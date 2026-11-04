from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    projects,
    analysis,
    prd,
    validation,
    export,
    system
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects & Submissions"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis & Clarification"])
api_router.include_router(prd.router, prefix="/prd", tags=["PRD Generation & Editing"])
api_router.include_router(validation.router, prefix="/validation", tags=["Quality & Validation"])
api_router.include_router(export.router, prefix="/export", tags=["Document Export"])
api_router.include_router(system.router, prefix="/system", tags=["System & Local Models"])

