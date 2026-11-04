import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.db.repository import (
    PRDRepository,
    PRDVersionRepository,
    ProjectRepository,
    SubmissionRepository,
    AnalysisRepository,
    ClarificationRepository,
    GenerationRunRepository
)
from app.models.prd import (
    PRDDocument,
    PRDVersion,
    PRDSectionContent,
    SectionUpdatePayload,
    SectionRegeneratePayload,
    SECTION_TITLES
)
from app.models.submission import IdeaSubmissionResponse
from app.models.analysis import AnalysisRecord
from app.ai.factory import get_ai_gateway
from app.ai.pipeline.input_analyzer import InputAnalyzer
from app.ai.pipeline.clarification_engine import ClarificationEngine
from app.ai.pipeline.requirement_engineer import RequirementEngineer
from app.ai.pipeline.prd_generator import PRDGenerator

logger = logging.getLogger(__name__)

class PRDService:
    def __init__(
        self,
        prd_repo: PRDRepository,
        version_repo: PRDVersionRepository,
        project_repo: ProjectRepository,
        submission_repo: SubmissionRepository,
        analysis_repo: AnalysisRepository,
        clarification_repo: ClarificationRepository,
        gen_run_repo: GenerationRunRepository
    ):
        self.prd_repo = prd_repo
        self.version_repo = version_repo
        self.project_repo = project_repo
        self.submission_repo = submission_repo
        self.analysis_repo = analysis_repo
        self.clarification_repo = clarification_repo
        self.gen_run_repo = gen_run_repo

    async def analyze_submission(self, project_id: str) -> AnalysisRecord:
        """Run stage 1: Input Analysis."""
        submissions = await self.submission_repo.get_by_project(project_id)
        if not submissions:
            raise ValueError("No idea submission found for this project.")
        
        latest_sub = IdeaSubmissionResponse(**submissions[0])
        ai_gw = await get_ai_gateway()
        analyzer = InputAnalyzer(ai_gw)
        
        start_t = time.time()
        analysis = await analyzer.analyze(latest_sub)
        duration = time.time() - start_t

        # Persist analysis
        analysis_data = analysis.dict(exclude={"id"})
        saved = await self.analysis_repo.create(analysis_data)
        analysis.id = saved["id"]

        # Track telemetry
        await self.gen_run_repo.create({
            "project_id": project_id,
            "stage": "input_analysis",
            "duration_seconds": round(duration, 3),
            "created_at": datetime.utcnow()
        })

        return analysis

    async def generate_clarifications(self, project_id: str):
        """Run stage 2: Clarification Questions."""
        analysis_doc = await self.analysis_repo.get_latest_by_project(project_id)
        if not analysis_doc:
            raise ValueError("Project has not been analyzed yet.")
        
        analysis = AnalysisRecord(**analysis_doc)
        ai_gw = await get_ai_gateway()
        engine = ClarificationEngine(ai_gw)

        session = await engine.generate_questions(analysis)
        session_data = session.dict(exclude={"id"})
        saved = await self.clarification_repo.create(session_data)
        session.id = saved["id"]
        return session

    async def answer_clarification(self, project_id: str, question_id: str, answer: Optional[str], proceed_with_assumption: bool):
        """Record user response to a question or flag as assumed."""
        session_doc = await self.clarification_repo.get_latest_by_project(project_id)
        if not session_doc:
            raise ValueError("No active clarification session found.")

        questions = session_doc.get("questions", [])
        updated = False
        for q in questions:
            if q.get("id") == question_id:
                if proceed_with_assumption:
                    q["resolved_as_assumption"] = True
                    q["documented_assumption"] = answer or "Accepted system recommendation"
                else:
                    q["user_answer"] = answer
                updated = True
                break

        if not updated:
            raise ValueError(f"Question with ID {question_id} not found.")

        await self.clarification_repo.update(session_doc["id"], {"questions": questions})
        return session_doc

    async def generate_full_prd(self, project_id: str, user_id: str) -> PRDVersion:
        """Run stages 3, 4 & 5: Requirements, Business Rules, and 27-Section Assembly."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError("Project not found.")

        analysis_doc = await self.analysis_repo.get_latest_by_project(project_id)
        if not analysis_doc:
            analysis = await self.analyze_submission(project_id)
        else:
            analysis = AnalysisRecord(**analysis_doc)

        clarification_doc = await self.clarification_repo.get_latest_by_project(project_id)
        from app.models.clarification import ClarificationSession
        clarification_session = ClarificationSession(**clarification_doc) if clarification_doc else None

        ai_gw = await get_ai_gateway()
        req_engineer = RequirementEngineer(ai_gw)
        generator = PRDGenerator(ai_gw)

        start_time = time.time()
        requirements_data = await req_engineer.engineer(analysis, clarification_session)
        sections = await generator.generate_full_prd(
            project_title=project.get("title", "Project"),
            analysis=analysis,
            clarification_session=clarification_session,
            requirements_data=requirements_data
        )
        duration = time.time() - start_time

        # Check existing PRD document or create
        existing_prd = await self.prd_repo.get_by_project(project_id)
        if not existing_prd:
            prd_data = {
                "project_id": project_id,
                "title": f"PRD for {project.get('title')}",
                "current_version_number": "v1.0",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            prd_doc = await self.prd_repo.create(prd_data)
            prd_id = prd_doc["id"]
        else:
            prd_id = existing_prd["id"]

        # Calculate next version number
        prior_versions = await self.version_repo.get_by_prd(prd_id)
        next_ver = f"v{len(prior_versions) + 1}.0"

        # Create immutable version record
        version_data = {
            "prd_id": prd_id,
            "project_id": project_id,
            "version_number": next_ver,
            "status": "draft",
            "sections": {k: v.dict() for k, v in sections.items()},
            "changelog": "Initial full PRD generation",
            "created_at": datetime.utcnow(),
            "created_by": user_id
        }
        saved_version = await self.version_repo.create(version_data)
        version_id = saved_version["id"]

        # Update active version reference in PRD and Project
        await self.prd_repo.update(prd_id, {
            "current_version_id": version_id,
            "current_version_number": next_ver,
            "updated_at": datetime.utcnow()
        })
        await self.project_repo.update(project_id, {
            "active_prd_id": prd_id,
            "updated_at": datetime.utcnow()
        })

        # Telemetry record
        await self.gen_run_repo.create({
            "project_id": project_id,
            "prd_id": prd_id,
            "version_id": version_id,
            "stage": "full_prd_generation",
            "duration_seconds": round(duration, 3),
            "created_at": datetime.utcnow()
        })

        return PRDVersion(**saved_version)

    async def update_section(self, project_id: str, section_key: str, payload: SectionUpdatePayload, user_id: str) -> PRDVersion:
        """Section editing creates a new minor version (e.g. v1.1) to preserve immutability."""
        prd = await self.prd_repo.get_by_project(project_id)
        if not prd or not prd.get("current_version_id"):
            raise ValueError("No active PRD found to edit.")

        latest_ver_doc = await self.version_repo.get_by_id(prd["current_version_id"])
        if not latest_ver_doc:
            raise ValueError("Active PRD version record not found.")

        current_ver = PRDVersion(**latest_ver_doc)
        sections = current_ver.sections.copy()

        # Update specific section
        title = SECTION_TITLES.get(section_key, section_key.replace("_", " ").title())
        sections[section_key] = PRDSectionContent(
            key=section_key,
            title=title,
            content=payload.content,
            is_na=payload.is_na,
            na_rationale=payload.na_rationale,
            last_modified=datetime.utcnow()
        )

        # Increment minor version (v1.0 -> v1.1)
        cur_num = current_ver.version_number
        try:
            major, minor = cur_num.replace("v", "").split(".")
            next_num = f"v{major}.{int(minor) + 1}"
        except Exception:
            next_num = f"{cur_num}.1"

        new_version_data = {
            "prd_id": prd["id"],
            "project_id": project_id,
            "version_number": next_num,
            "status": "draft",
            "sections": {k: v.dict() for k, v in sections.items()},
            "changelog": f"Edited section: {title}",
            "created_at": datetime.utcnow(),
            "created_by": user_id
        }
        saved_ver = await self.version_repo.create(new_version_data)
        
        await self.prd_repo.update(prd["id"], {
            "current_version_id": saved_ver["id"],
            "current_version_number": next_num,
            "updated_at": datetime.utcnow()
        })

        return PRDVersion(**saved_ver)

    async def regenerate_section(self, project_id: str, section_key: str, payload: SectionRegeneratePayload, user_id: str) -> PRDVersion:
        """Regenerates a single section using local AI and user guidance."""
        prd = await self.prd_repo.get_by_project(project_id)
        if not prd or not prd.get("current_version_id"):
            raise ValueError("No active PRD found.")

        latest_ver_doc = await self.version_repo.get_by_id(prd["current_version_id"])
        current_ver = PRDVersion(**latest_ver_doc)

        ai_gw = await get_ai_gateway()
        sec_title = SECTION_TITLES.get(section_key, section_key)
        
        prompt = (
            f"You are an expert Requirements Engineer.\n"
            f"Regenerate the content for PRD section: '{sec_title}'.\n"
            f"Current content:\n{current_ver.sections.get(section_key, PRDSectionContent(key=section_key, title=sec_title, content='')).content}\n\n"
            f"User Guidance / Adjustments:\n{payload.guidance or 'Improve technical precision and concrete criteria.'}\n\n"
            f"Return only the updated section content in professional Markdown."
        )

        new_content = await ai_gw.generate(
            prompt=prompt,
            system_instruction="You are a professional Product Requirements Engineer. Return markdown content only."
        )

        return await self.update_section(
            project_id=project_id,
            section_key=section_key,
            payload=SectionUpdatePayload(content=new_content.strip()),
            user_id=user_id
        )

    async def approve_version(self, project_id: str, version_id: str) -> PRDVersion:
        """Mark a version as Approved."""
        ver_doc = await self.version_repo.get_by_id(version_id)
        if not ver_doc:
            raise ValueError("PRD version not found.")

        updated = await self.version_repo.update(version_id, {
            "status": "approved",
            "changelog": f"{ver_doc.get('changelog', '')} [APPROVED]"
        })
        return PRDVersion(**updated)
