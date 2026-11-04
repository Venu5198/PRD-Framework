import re
import logging
from typing import Dict, Any, List
from app.models.prd import PRDVersion, CANONICAL_SECTIONS, SECTION_TITLES
from app.models.validation import ValidationIssue, ValidationReport
from app.db.repository import ValidationRepository

logger = logging.getLogger(__name__)

AMBIGUOUS_TERMS = [
    r"\bfast\b",
    r"\beasy to use\b",
    r"\brobust\b",
    r"\buser-friendly\b",
    r"\bseamless\b",
    r"\bscalable enough\b",
    r"\betc\b",
    r"\band so on\b",
    r"\befficient\b",
    r"\boptimal\b"
]

class ValidationService:
    def __init__(self, validation_repo: ValidationRepository):
        self.repo = validation_repo

    async def validate_version(self, prd_version: PRDVersion) -> ValidationReport:
        issues: List[ValidationIssue] = []
        score = 100

        # Check 1: Section Completeness (Canonical 27 sections)
        missing_sections = []
        empty_sections = []
        for sec_key in CANONICAL_SECTIONS:
            if sec_key not in prd_version.sections:
                missing_sections.append(sec_key)
            else:
                sec = prd_version.sections[sec_key]
                if not sec.is_na and (not sec.content or len(sec.content.strip()) < 15):
                    empty_sections.append(sec_key)

        for sec_key in missing_sections:
            issues.append(ValidationIssue(
                rule_id="VAL-SEC-001",
                severity="error",
                section_key=sec_key,
                title=f"Missing Canonical Section: {SECTION_TITLES.get(sec_key, sec_key)}",
                description=f"The required section '{sec_key}' is completely absent from the PRD version.",
                recommendation="Regenerate or supply content for this required section."
            ))
            score -= 10

        for sec_key in empty_sections:
            issues.append(ValidationIssue(
                rule_id="VAL-SEC-002",
                severity="warning",
                section_key=sec_key,
                title=f"Empty or Insufficient Section: {SECTION_TITLES.get(sec_key, sec_key)}",
                description=f"Section '{sec_key}' has less than 15 characters of content and is not marked as N/A.",
                recommendation="Provide detailed technical content or mark section as N/A with rationale."
            ))
            score -= 5

        # Check 2: Requirement IDs & Duplicates
        fr_section = prd_version.sections.get("functional_requirements")
        fr_content = fr_section.content if fr_section else ""
        fr_ids = re.findall(r"\b(FR-\d{3,4})\b", fr_content)
        
        seen_frs = set()
        duplicate_frs = set()
        for fid in fr_ids:
            if fid in seen_frs:
                duplicate_frs.add(fid)
            seen_frs.add(fid)

        for dup in duplicate_frs:
            issues.append(ValidationIssue(
                rule_id="VAL-REQ-001",
                severity="error",
                section_key="functional_requirements",
                title=f"Duplicate Functional Requirement Identifier: {dup}",
                description=f"Identifier {dup} appears multiple times in functional requirements.",
                recommendation="Assign unique, stable identifiers to each requirement."
            ))
            score -= 8

        # Check 3: Acceptance Criteria Mapping
        ac_section = prd_version.sections.get("acceptance_criteria")
        ac_content = ac_section.content if ac_section else ""
        ac_ids = set(re.findall(r"\b(AC-\d{3,4})\b", ac_content))

        # Check if FRs link to ACs
        for fid in seen_frs:
            # Check if AC section or FR table mentions this FR linked to an AC
            if fid not in ac_content:
                issues.append(ValidationIssue(
                    rule_id="VAL-AC-001",
                    severity="warning",
                    section_key="functional_requirements",
                    title=f"Unmapped Acceptance Criteria for {fid}",
                    description=f"Functional Requirement {fid} has no corresponding acceptance criteria in the Acceptance Criteria section.",
                    recommendation=f"Add testable Given-When-Then acceptance criteria linked to {fid}."
                ))
                score -= 4

        # Check 4: Ambiguous Wording Detection
        for sec_key, sec in prd_version.sections.items():
            if sec.is_na:
                continue
            for pattern in AMBIGUOUS_TERMS:
                matches = re.findall(pattern, sec.content, re.IGNORECASE)
                if matches:
                    matched_word = matches[0]
                    issues.append(ValidationIssue(
                        rule_id="VAL-AMB-001",
                        severity="info",
                        section_key=sec_key,
                        title=f"Potentially Ambiguous Term: '{matched_word}' in {SECTION_TITLES.get(sec_key, sec_key)}",
                        description=f"Found subjective word '{matched_word}'. Requirements must be measurable and objective.",
                        recommendation=f"Replace '{matched_word}' with explicit numerical metrics or deterministic criteria."
                    ))
                    score -= 1
                    break  # report at most one per section to avoid flooding

        # Check 5: Scope & Non-Goals verification
        scope_sec = prd_version.sections.get("product_scope")
        out_scope_sec = prd_version.sections.get("out_of_scope")
        if not scope_sec or len(scope_sec.content.strip()) < 20:
            issues.append(ValidationIssue(
                rule_id="VAL-SCP-001",
                severity="error",
                section_key="product_scope",
                title="Missing Product Scope Boundaries",
                description="Product Scope section is either missing or too brief to define MVP boundaries.",
                recommendation="Document clear in-scope capabilities for the target release."
            ))
            score -= 5

        if not out_scope_sec or len(out_scope_sec.content.strip()) < 20:
            issues.append(ValidationIssue(
                rule_id="VAL-SCP-002",
                severity="warning",
                section_key="out_of_scope",
                title="Missing Non-Goals (Out of Scope)",
                description="Out of Scope section lacks explicit non-goals, which risks scope creep.",
                recommendation="Explicitly list features that will NOT be included in this version."
            ))
            score -= 3

        # Compute summary
        score = max(0, min(100, score))
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        info_count = sum(1 for i in issues if i.severity == "info")
        is_valid = error_count == 0

        report = ValidationReport(
            prd_version_id=str(prd_version.id or "draft"),
            project_id=prd_version.project_id,
            is_valid=is_valid,
            score=score,
            total_issues=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            issues=issues
        )

        # Persist report
        report_dict = report.dict(exclude={"id"})
        saved = await self.repo.create(report_dict)
        report.id = saved["id"]

        return report
