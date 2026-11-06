import time
import asyncio
import logging
import re
import hashlib
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
from app.ai.pipeline.assignment_parser import AssignmentParser, AssignmentParserInput
from app.ai.pipeline.problem_analyst import ProblemAnalyst, ProblemAnalystInput
from app.ai.pipeline.clarification_engine import ClarificationEngine
from app.ai.pipeline.stakeholder_analyst import StakeholderAnalyst, StakeholderAnalystInput
from app.ai.pipeline.requirement_engineer import RequirementEngineer
from app.ai.pipeline.business_rules_analyst import BusinessRulesAnalyst, BusinessRulesInput
from app.ai.pipeline.risk_analyst import RiskAnalyst, RiskAnalystInput
from app.ai.pipeline.prd_generator import PRDGenerator
from app.ai.pipeline.prd_validator import PRDValidator, PRDValidatorInput

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
        gen_run_repo: GenerationRunRepository,
        validation_repo: Optional[Any] = None
    ):
        self.prd_repo = prd_repo
        self.version_repo = version_repo
        self.project_repo = project_repo
        self.submission_repo = submission_repo
        self.analysis_repo = analysis_repo
        self.clarification_repo = clarification_repo
        self.gen_run_repo = gen_run_repo
        self.validation_repo = validation_repo

    async def analyze_submission(self, project_id: str, force_mock: bool = False) -> AnalysisRecord:
        """Run stage 1: Input Analysis."""
        submissions = await self.submission_repo.get_by_project(project_id)
        if not submissions:
            raise ValueError("No idea submission found for this project.")
        
        latest_sub = IdeaSubmissionResponse(**submissions[0])
        ai_gw = await get_ai_gateway(force_mock=force_mock)
        analyzer = InputAnalyzer(ai_gw)
        
        start_t = time.time()
        analysis = await analyzer.analyze(latest_sub)
        
        # Invoke AssignmentParser if assignment context is provided
        if latest_sub.assignment_context:
            asg_parser = AssignmentParser(ai_gw)
            asg_res = await asg_parser.parse(AssignmentParserInput(assignment_text=latest_sub.assignment_context))
            from app.models.analysis import AssignmentRequirement
            analysis.assignment_requirements = AssignmentRequirement(
                instruction=asg_res.instruction_summary,
                mandatory_sections=asg_res.mandatory_sections,
                deliverables=asg_res.deliverables,
                constraints=asg_res.constraints,
                expected_length=asg_res.expected_length
            )

        # Invoke ProblemAnalyst to deepen problem domain & root pain points
        prob_analyst = ProblemAnalyst(ai_gw)
        prob_res = await prob_analyst.analyze(ProblemAnalystInput(
            concept=latest_sub.raw_idea,
            problem_statement=latest_sub.problem_statement
        ))
        if prob_res.problem_domain and prob_res.problem_domain != "Software Architecture":
            analysis.problem_domain = prob_res.problem_domain
        analysis.root_pain_points = prob_res.root_pain_points or []
        analysis.current_limitations = prob_res.current_limitations or []
        analysis.desired_outcomes = prob_res.desired_outcomes or []
        if prob_res.desired_outcomes:
            for outcome in prob_res.desired_outcomes:
                if outcome not in analysis.core_objectives:
                    analysis.core_objectives.append(outcome)

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

    async def generate_clarifications(self, project_id: str, force_mock: bool = False):
        """Run stage 2: Clarification Questions."""
        analysis_doc = await self.analysis_repo.get_latest_by_project(project_id)
        if not analysis_doc:
            raise ValueError("Project has not been analyzed yet.")
        
        analysis = AnalysisRecord(**analysis_doc)
        ai_gw = await get_ai_gateway(force_mock=force_mock)
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

    async def generate_full_prd(
        self,
        project_id: str,
        user_id: str,
        force_mock: bool = False,
        on_progress: Optional[Any] = None,
        check_cancelled: Optional[Any] = None,
        job_id: Optional[str] = None,
        requested_version: Optional[str] = None
    ) -> PRDVersion:
        """Run stages 3, 4 & 5: Requirements, Business Rules, and 27-Section Assembly."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError("Project not found.")
        if user_id and project.get("owner_id") != user_id:
            raise ValueError("Access denied: Project does not belong to user.")

        # Stage 1: Input Analysis Check
        if on_progress:
            await on_progress("input_analysis", [], {"stage_name": "Input Analysis & Context Extraction", "step": 1, "total_steps": 6})
        if check_cancelled and await check_cancelled():
            raise asyncio.CancelledError("Job cancelled by user.")

        analysis_doc = await self.analysis_repo.get_latest_by_project(project_id)
        if not analysis_doc:
            analysis = await self.analyze_submission(project_id, force_mock=force_mock)
        else:
            analysis = AnalysisRecord(**analysis_doc)

        clarification_doc = await self.clarification_repo.get_latest_by_project(project_id)
        from app.models.clarification import ClarificationSession
        clarification_session = ClarificationSession(**clarification_doc) if clarification_doc else None

        ai_gw = await get_ai_gateway(force_mock=force_mock)
        req_engineer = RequirementEngineer(ai_gw)
        generator = PRDGenerator(ai_gw)

        start_time = time.time()

        # Stage 2: Requirement Engineering
        if on_progress:
            await on_progress("requirements_engineering", ["input_analysis"], {"stage_name": "Requirement Engineering", "step": 2, "total_steps": 6})
        if check_cancelled and await check_cancelled():
            raise asyncio.CancelledError("Job cancelled by user.")
        requirements_data = await req_engineer.engineer(analysis, clarification_session)

        # Stage 3: Stakeholder Analyst
        if on_progress:
            await on_progress("stakeholder_analysis", ["input_analysis", "requirements_engineering"], {"stage_name": "Stakeholder & Persona Analysis", "step": 3, "total_steps": 6})
        if check_cancelled and await check_cancelled():
            raise asyncio.CancelledError("Job cancelled by user.")
        stakeholder_analyst = StakeholderAnalyst(ai_gw)
        sh_res = await stakeholder_analyst.analyze(StakeholderAnalystInput(
            product_category=analysis.product_category,
            intended_users=analysis.intended_users,
            domain=analysis.problem_domain
        ))
        requirements_data["stakeholders"] = [p.dict() for p in sh_res.personas]
        requirements_data["user_journeys"] = [j.dict() for j in sh_res.user_journeys]

        # Stage 4: Business Rules Analyst
        if on_progress:
            await on_progress("business_rules", ["input_analysis", "requirements_engineering", "stakeholder_analysis"], {"stage_name": "Business Rules Extraction", "step": 4, "total_steps": 6})
        if check_cancelled and await check_cancelled():
            raise asyncio.CancelledError("Job cancelled by user.")
        clarif_confirmed = []
        clarif_answers = []
        if clarification_session and clarification_session.questions:
            for q in clarification_session.questions:
                if q.user_answer:
                    clarif_confirmed.append(f"{q.question}: {q.user_answer}")
                    clarif_answers.append(f"{q.question}: {q.user_answer}")
                elif q.resolved_as_assumption and q.documented_assumption:
                    clarif_answers.append(f"{q.question}: Assumed {q.documented_assumption}")

        asg_constraints = []
        if analysis.assignment_requirements and analysis.assignment_requirements.constraints:
            asg_constraints = analysis.assignment_requirements.constraints

        subs = await self.submission_repo.get_by_project(project_id)
        raw_idea = subs[0].get("raw_idea") if subs else None

        br_analyst = BusinessRulesAnalyst(ai_gw)
        br_res = await br_analyst.extract_rules(BusinessRulesInput(
            domain=analysis.problem_domain,
            objectives=analysis.core_objectives,
            constraints=analysis.explicit_constraints,
            confirmed_facts=analysis.facts,
            assignment_constraints=asg_constraints,
            confirmed_clarifications=clarif_confirmed,
            raw_idea=raw_idea,
            clarifications=clarif_answers
        ))
        # Merge or ensure business rules are fully populated with unique IDs
        current_rules = requirements_data.get("business_rules", [])
        existing_br_titles = {b.get("title", "").strip().lower() for b in current_rules}
        for br in br_res.business_rules:
            if br.title.strip().lower() not in existing_br_titles:
                current_rules.append(br.dict())
        for idx, br_item in enumerate(current_rules, 1):
            br_item["id"] = f"BR-{idx:03d}"
        requirements_data["business_rules"] = current_rules

        # Stage 5: Risk Analyst
        if on_progress:
            await on_progress("risk_analysis", ["input_analysis", "requirements_engineering", "stakeholder_analysis", "business_rules"], {"stage_name": "Risk & Mitigation Analysis", "step": 5, "total_steps": 6})
        if check_cancelled and await check_cancelled():
            raise asyncio.CancelledError("Job cancelled by user.")
        risk_analyst = RiskAnalyst(ai_gw)
        risk_res = await risk_analyst.analyze_risks(RiskAnalystInput(
            problem_domain=analysis.problem_domain,
            capabilities=analysis.expected_capabilities,
            constraints=analysis.explicit_constraints
        ))
        requirements_data["risks"] = [r.dict() for r in risk_res.risks]

        # Resolve target version and PRD ID before section generation
        existing_prd = await self.prd_repo.get_by_project(project_id)
        if not existing_prd:
            target_version = requested_version or "v1.0"
            prd_data = {
                "project_id": project_id,
                "title": f"PRD for {project.get('title')}",
                "current_version_number": target_version,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            prd_doc = await self.prd_repo.create(prd_data)
            prd_id = prd_doc["id"]
        else:
            prd_id = existing_prd["id"]
            if requested_version:
                target_version = requested_version
            else:
                prior_versions = await self.version_repo.get_by_prd(prd_id)
                target_version = f"v{len(prior_versions) + 1}.0"

        # Stage 6: Canonical 27-Section Assembly
        if on_progress:
            await on_progress("prd_assembly", ["input_analysis", "requirements_engineering", "stakeholder_analysis", "business_rules", "risk_analysis"], {"stage_name": "Synthesizing Canonical 27-Section PRD", "step": 6, "total_steps": 6})
        if check_cancelled and await check_cancelled():
            raise asyncio.CancelledError("Job cancelled by user.")
        sections = await generator.generate_full_prd(
            project_title=project.get("title", "Project"),
            analysis=analysis,
            clarification_session=clarification_session,
            requirements_data=requirements_data,
            version_number=target_version,
            job_id=job_id
        )
        duration = time.time() - start_time

        # Compute canonical content hash of the version's sections
        import hashlib
        # Synchronize Section 1 Content Hash with authoritative canonical content hash
        canonical_content = "".join(f"## {sections[k].title}\n\n{sections[k].content}\n\n" for k in sorted(sections.keys()) if k != "document_information")
        content_hash = hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()
        if "document_information" in sections:
            doc_info = sections["document_information"].content
            doc_info = re.sub(r"(\*\*Content Hash \(SHA-256\):\*\*)\s*`[^`]+`", f"\\1 `{content_hash}`", doc_info)
            sections["document_information"].content = doc_info

        # Create immutable version record
        version_data = {
            "prd_id": prd_id,
            "project_id": project_id,
            "job_id": job_id,
            "version_number": target_version,
            "content_hash": content_hash,
            "status": "draft",
            "sections": {k: v.dict() for k, v in sections.items()},
            "provenance_ledger": getattr(generator, "last_provenance_ledger", []),
            "changelog": f"Full PRD generation {target_version}",
            "created_at": datetime.utcnow(),
            "created_by": user_id
        }
        saved_version = await self.version_repo.create(version_data)
        version_id = saved_version["id"]

        # Update active version reference in PRD and Project
        await self.prd_repo.update(prd_id, {
            "current_version_id": version_id,
            "current_version_number": target_version,
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
        project = await self.project_repo.get_by_id(project_id)
        if not project or (user_id and project.get("owner_id") != user_id):
            raise ValueError("Access denied: Project does not belong to user.")

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

        # Synchronize Section 1 Document Information version header with new version number
        if "document_information" in sections and section_key != "document_information":
            doc_sec = sections["document_information"]
            new_doc_content = re.sub(
                r"(\*\*Version:\*\*)\s*[^\n]+",
                f"\\1 {next_num}",
                doc_sec.content
            )
            doc_sec.content = new_doc_content
            sections["document_information"] = doc_sec

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

    async def regenerate_section(self, project_id: str, section_key: str, payload: SectionRegeneratePayload, user_id: str, force_mock: bool = False) -> PRDVersion:
        """Regenerates a single section using local AI and user guidance."""
        prd = await self.prd_repo.get_by_project(project_id)
        if not prd or not prd.get("current_version_id"):
            raise ValueError("No active PRD found.")

        latest_ver_doc = await self.version_repo.get_by_id(prd["current_version_id"])
        current_ver = PRDVersion(**latest_ver_doc)

        ai_gw = await get_ai_gateway(force_mock=force_mock)
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
        """Mark a version as Approved strictly after quality and semantic validation passes."""
        ver_doc = await self.version_repo.get_by_id(version_id)
        if not ver_doc:
            raise ValueError("PRD version not found.")

        # Ensure validation is run and passing before approval
        from app.services.validation_service import ValidationService
        validator = ValidationService(validation_repo=self.validation_repo, analysis_repo=self.analysis_repo)
        temp_version = PRDVersion(**ver_doc)
        val_report = await validator.validate_version(temp_version)
        if not val_report.is_valid or val_report.error_count > 0 or val_report.verdict != "APPROVED":
            # Transition status to blocked if critical validation failures exist
            await self.version_repo.update(version_id, {"status": "blocked"})
            raise ValueError(
                f"Cannot approve PRD version: Document has {val_report.error_count} blocking validation error(s) "
                f"and verdict is '{val_report.verdict}'."
            )

        # Update Section 1 Document Information to Status: Approved
        sections = ver_doc.get("sections", {})
        if "document_information" in sections:
            doc_info = sections["document_information"]
            content = doc_info.get("content", "")
            content = re.sub(r"(\*\*Status:\*\*)\s*[^\n]+", r"\1 Approved", content)
            doc_info["content"] = content
            sections["document_information"] = doc_info

        updated = await self.version_repo.update(version_id, {
            "status": "approved",
            "sections": sections,
            "changelog": f"{ver_doc.get('changelog', '')} [APPROVED]"
        })
        return PRDVersion(**updated)

