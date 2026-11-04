from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.security import decode_access_token
from app.db.repository import (
    UserRepository,
    ProjectRepository,
    SubmissionRepository,
    AnalysisRepository,
    ClarificationRepository,
    PRDRepository,
    PRDVersionRepository,
    ValidationRepository,
    GenerationRunRepository
)
from app.services.prd_service import PRDService
from app.services.validation_service import ValidationService
from app.services.export_service import ExportService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_user_repo() -> UserRepository:
    return UserRepository()

def get_project_repo() -> ProjectRepository:
    return ProjectRepository()

def get_submission_repo() -> SubmissionRepository:
    return SubmissionRepository()

def get_analysis_repo() -> AnalysisRepository:
    return AnalysisRepository()

def get_clarification_repo() -> ClarificationRepository:
    return ClarificationRepository()

def get_prd_repo() -> PRDRepository:
    return PRDRepository()

def get_version_repo() -> PRDVersionRepository:
    return PRDVersionRepository()

def get_validation_repo() -> ValidationRepository:
    return ValidationRepository()

def get_gen_run_repo() -> GenerationRunRepository:
    return GenerationRunRepository()

def get_prd_service(
    prd_repo: PRDRepository = Depends(get_prd_repo),
    version_repo: PRDVersionRepository = Depends(get_version_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    submission_repo: SubmissionRepository = Depends(get_submission_repo),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repo),
    clarification_repo: ClarificationRepository = Depends(get_clarification_repo),
    gen_run_repo: GenerationRunRepository = Depends(get_gen_run_repo)
) -> PRDService:
    return PRDService(
        prd_repo, version_repo, project_repo,
        submission_repo, analysis_repo, clarification_repo, gen_run_repo
    )

def get_validation_service(
    validation_repo: ValidationRepository = Depends(get_validation_repo)
) -> ValidationService:
    return ValidationService(validation_repo)

def get_export_service() -> ExportService:
    return ExportService()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repo)
) -> dict:
    # If no token provided, allow default local developer session
    if not token:
        dev_user = await user_repo.get_by_username("local_engineer")
        if not dev_user:
            dev_user = await user_repo.create({
                "username": "local_engineer",
                "email": "engineer@local.dev",
                "full_name": "Local Lead Engineer",
                "role": "lead_engineer",
                "hashed_password": "local_dev_user"
            })
        return dev_user

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await user_repo.get_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
