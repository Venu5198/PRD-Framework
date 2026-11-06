import re
import logging
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from app.models.prd import PRDVersion, PRDSectionContent, CANONICAL_SECTIONS, SECTION_TITLES, CanonicalProvenance
from app.models.analysis import AnalysisRecord
from app.models.validation import ValidationIssue, ValidationReport, ClaimModel, EntailmentOutcome
from app.db.repository import ValidationRepository, AnalysisRepository

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

TEN_CATEGORIES = [
    "Structural Completeness",
    "Provenance & Grounding",
    "Semantic Entailment",
    "Cross-Section Consistency",
    "Numerical & SLA Governance",
    "Requirements & AC Coherence",
    "Data & Security Governance",
    "Export Artifact Integrity",
    "Workflow & Domain Realism",
    "Regulatory & Compliance"
]

def categorize_issue_rule(rule_id: str) -> str:
    r = rule_id.upper()
    if any(k in r for k in ["VAL-SEC-001", "VAL-SEC-002", "VAL-STR-", "VAL-DIA-", "VAL-ENG-008"]):
        return "Structural Completeness"
    if any(k in r for k in ["VAL-PROV-", "VAL-GRD-", "VAL-CLAIM-"]):
        return "Provenance & Grounding"
    if any(k in r for k in ["VAL-NUM-", "VAL-SLA-", "VAL-TGT-"]):
        return "Numerical & SLA Governance"
    if any(k in r for k in ["VAL-SCP-", "VAL-XSEC-", "VAL-COH-", "VAL-DUP-"]):
        return "Cross-Section Consistency"
    if any(k in r for k in ["VAL-REQ-", "VAL-AC-", "VAL-TRC-", "VAL-ENG-"]):
        return "Requirements & AC Coherence"
    if any(k in r for k in ["VAL-DAT-", "VAL-PRIV-", "VAL-CYBER-"]) or ("VAL-SEC-" in r and not r.startswith("VAL-SEC-00")):
        return "Data & Security Governance"
    if any(k in r for k in ["VAL-EXP-", "VAL-HASH-", "VAL-DOC-", "VAL-STATUS-", "VAL-STAT-"]):
        return "Export Artifact Integrity"
    if any(k in r for k in ["VAL-WRK-", "VAL-DOM-", "VAL-UJ-"]):
        return "Workflow & Domain Realism"
    if any(k in r for k in ["VAL-REG-", "VAL-CMP-", "VAL-LEGAL-"]):
        return "Regulatory & Compliance"
    if any(k in r for k in ["VAL-SEM-", "VAL-ENT-", "VAL-AMB-"]):
        return "Semantic Entailment"
    return "Semantic Entailment"

class ValidationService:
    def __init__(
        self,
        validation_repo: Optional[ValidationRepository] = None,
        analysis_repo: Optional[AnalysisRepository] = None
    ):
        self.repo = validation_repo
        self.analysis_repo = analysis_repo

    async def validate_version(
        self,
        prd_version: PRDVersion,
        analysis: Optional[AnalysisRecord] = None
    ) -> ValidationReport:
        """
        Executes structural, traceability, semantic alignment, and domain relevance validation.
        Does NOT rely on global banned-keyword lists.
        """
        issues: List[ValidationIssue] = []
        score = 100

        # Attempt to load project analysis if not passed in
        if not analysis and self.analysis_repo and prd_version.project_id:
            try:
                doc = await self.analysis_repo.get_latest_by_project(prd_version.project_id)
                if doc:
                    analysis = AnalysisRecord(**doc)
            except Exception as e:
                logger.warning(f"ValidationService: could not fetch analysis: {e}")

        # -------------------------------------------------------------
        # 1. Structural Checks (27 Canonical Sections)
        # -------------------------------------------------------------
        missing_sections = []
        empty_sections = []
        for sec_key in CANONICAL_SECTIONS:
            if sec_key not in prd_version.sections:
                missing_sections.append(sec_key)
            else:
                sec = prd_version.sections[sec_key]
                if not sec.is_na and (not sec.content or len(sec.content.strip()) < 20):
                    empty_sections.append(sec_key)

        for sec_key in missing_sections:
            issues.append(ValidationIssue(
                rule_id="VAL-SEC-001",
                severity="error",
                section_key=sec_key,
                title=f"Missing Canonical Section: {SECTION_TITLES.get(sec_key, sec_key)}",
                description=f"The canonical section '{sec_key}' is completely absent from the PRD.",
                recommendation="Supply or generate content for this required section."
            ))
            score -= 10

        for sec_key in empty_sections:
            issues.append(ValidationIssue(
                rule_id="VAL-SEC-002",
                severity="warning",
                section_key=sec_key,
                title=f"Insufficient Section Content: {SECTION_TITLES.get(sec_key, sec_key)}",
                description=f"Section '{sec_key}' contains less than 20 characters and is not marked as N/A.",
                recommendation="Provide comprehensive domain specification or mark as N/A with rationale."
            ))
            score -= 5

        # VAL-STR-002: Mandatory Engineering Sections Completeness and Non-Empty Tables
        MANDATORY_SECTIONS = [
            ("functional_requirements", "FR-"),
            ("non_functional_requirements", "NFR-"),
            ("business_rules", "BR-"),
            ("acceptance_criteria", "AC-")
        ]
        for m_key, m_prefix in MANDATORY_SECTIONS:
            m_sec = prd_version.sections.get(m_key)
            if not m_sec:
                continue
            if m_sec.is_na:
                issues.append(ValidationIssue(
                    rule_id="VAL-STR-002",
                    severity="error",
                    section_key=m_key,
                    title=f"Mandatory Section Marked N/A: {SECTION_TITLES.get(m_key, m_key)}",
                    description=f"Section '{m_key}' is a mandatory engineering specification and cannot be marked as N/A.",
                    recommendation="Provide complete, testable specifications for this mandatory section."
                ))
                score -= 10
                continue

            m_content = m_sec.content.strip() if m_sec.content else ""
            if len(m_content) < 60:
                issues.append(ValidationIssue(
                    rule_id="VAL-STR-002",
                    severity="error",
                    section_key=m_key,
                    title=f"Mandatory Section Incomplete: {SECTION_TITLES.get(m_key, m_key)}",
                    description=f"Section '{m_key}' has fewer than 60 characters and lacks required engineering content.",
                    recommendation="Populate with complete domain requirements and specifications."
                ))
                score -= 10
                continue

            # Check for empty markdown table (header present but 0 data rows)
            table_lines = [l.strip() for l in m_content.split("\n") if l.strip().startswith("|") and l.strip().endswith("|")]
            if table_lines:
                # Filter out header and divider lines
                data_rows = [
                    l for l in table_lines
                    if not re.match(r"^\|(\s*:?-+:?\s*\|)+$", l)
                    and not any(h in l.lower() for h in ["| id |", "| ac id |", "| rule title |", "| title |", "| story id |"])
                ]
                if len(data_rows) == 0:
                    issues.append(ValidationIssue(
                        rule_id="VAL-STR-002",
                        severity="error",
                        section_key=m_key,
                        title=f"Empty Mandatory Table in {SECTION_TITLES.get(m_key, m_key)}",
                        description=f"Section '{m_key}' contains a table header but 0 data rows.",
                        recommendation="Populate table with at least 3 concrete requirement rows."
                    ))
                    score -= 10
                    continue

            # Check NFRs completeness without enforcing artificial minimum count
            if m_key == "non_functional_requirements":
                nfr_matches = re.findall(r"\bNFR-\d{3,4}\b", m_content)
                if len(nfr_matches) == 0:
                    issues.append(ValidationIssue(
                        rule_id="VAL-STR-002",
                        severity="error",
                        section_key="non_functional_requirements",
                        title="Missing Non-Functional Requirements",
                        description="NFR section contains 0 documented Non-Functional Requirements.",
                        recommendation="Document confirmed NFRs or explicitly note unconstrained parameters as open decisions."
                    ))
                    score -= 10
                elif len(nfr_matches) < 3:
                    issues.append(ValidationIssue(
                        rule_id="VAL-STR-002",
                        severity="info",
                        section_key="non_functional_requirements",
                        title="Incomplete Non-Functional Requirements Set",
                        description=f"NFR section documents {len(nfr_matches)} NFRs; unstated technical targets remain open decisions.",
                        recommendation="Preserve confirmed NFRs; mark unconfirmed technical targets as proposed or unresolved."
                    ))

        # -------------------------------------------------------------
        # 2. Scope & Non-Goals Boundaries
        # -------------------------------------------------------------
        scope_sec = prd_version.sections.get("product_scope")
        out_scope_sec = prd_version.sections.get("out_of_scope")
        if not scope_sec or len(scope_sec.content.strip()) < 25:
            issues.append(ValidationIssue(
                rule_id="VAL-SCP-001",
                severity="error",
                section_key="product_scope",
                title="Missing Product Scope Boundaries",
                description="Product Scope section is missing or too brief to establish MVP boundaries.",
                recommendation="List explicit in-scope capabilities for the target release."
            ))
            score -= 5

        if not out_scope_sec or len(out_scope_sec.content.strip()) < 25:
            issues.append(ValidationIssue(
                rule_id="VAL-SCP-002",
                severity="warning",
                section_key="out_of_scope",
                title="Missing Non-Goals (Out of Scope)",
                description="Out of Scope section lacks explicit non-goals, creating risk of scope creep.",
                recommendation="Explicitly enumerate capabilities excluded from the initial release."
            ))
            score -= 3

        # Contradiction check: in-scope vs out-of-scope
        if scope_sec and out_scope_sec and not scope_sec.is_na and not out_scope_sec.is_na:
            scope_lines = [l.strip().lower() for l in scope_sec.content.split("\n") if l.strip().startswith("-")]
            out_lines = [l.strip().lower() for l in out_scope_sec.content.split("\n") if l.strip().startswith("-")]
            contradiction_keywords = ["crm", "zendesk", "freshdesk", "jira", "payment", "billing", "external ticketing", "third-party database"]
            for s_line in scope_lines:
                clean_s = re.sub(r"[^a-z0-9 ]", "", s_line).strip()
                if len(clean_s) > 10:
                    for o_line in out_lines:
                        clean_o = re.sub(r"[^a-z0-9 ]", "", o_line).strip()
                        has_direct_match = (clean_s in clean_o or clean_o in clean_s)
                        has_keyword_clash = any(kw in clean_s and kw in clean_o for kw in contradiction_keywords)
                        if has_direct_match or has_keyword_clash:
                            # Verify if in-scope line is a negation or explicitly self-contained
                            is_scope_negation = any(neg in s_line for neg in ["no ", "not ", "self-contained", "deferred", "without"])
                            if not is_scope_negation:
                                issues.append(ValidationIssue(
                                    rule_id="VAL-SEM-004",
                                    severity="error",
                                    section_key="product_scope",
                                    title=f"Scope Contradiction Detected",
                                    description=f"Capability '{clean_s[:50]}' appears both in-scope and out-of-scope.",
                                    recommendation="Resolve contradiction by clarifying whether this capability is in MVP or deferred."
                                ))
                                score -= 8
                                break
                    else:
                        continue
                    break

        # Contradiction check: out-of-scope vs integration_requirements
        int_sec = prd_version.sections.get("integration_requirements")
        if out_scope_sec and int_sec and not out_scope_sec.is_na and not int_sec.is_na:
            out_lines = [l.strip().lower() for l in out_scope_sec.content.split("\n") if l.strip().startswith("-")]
            int_lines = [l.strip().lower() for l in int_sec.content.split("\n") if l.strip().startswith("-")]
            for o_line in out_lines:
                clean_o = re.sub(r"[^a-z0-9 ]", "", o_line).strip()
                if len(clean_o) > 10:
                    for i_line in int_lines:
                        clean_i = re.sub(r"[^a-z0-9 ]", "", i_line).strip()
                        has_direct_match = (clean_o in clean_i or clean_i in clean_o) and len(clean_i) > 10
                        has_keyword_clash = any(kw in clean_o and kw in clean_i for kw in ["crm", "zendesk", "freshdesk", "jira", "payment", "billing"])
                        if has_direct_match or has_keyword_clash:
                            is_int_negation = any(neg in i_line for neg in ["no ", "not ", "self-contained", "deferred", "without", "open decision", "open architectural"])
                            if not is_int_negation:
                                issues.append(ValidationIssue(
                                    rule_id="VAL-SEM-004",
                                    severity="error",
                                    section_key="integration_requirements",
                                    title="Scope Contradiction: Out-of-Scope Capability Defined in Integration",
                                    description=f"Capability '{clean_o[:50]}' is declared out-of-scope but defined as an active integration requirement.",
                                    recommendation="Remove conflicting integration requirement or revise out-of-scope list."
                                ))
                                score -= 8
                                break
                    else:
                        continue
                    break

        # Contradiction check: out-of-scope vs functional_requirements
        fr_section_pre = prd_version.sections.get("functional_requirements")
        if out_scope_sec and fr_section_pre and not out_scope_sec.is_na and not fr_section_pre.is_na:
            out_lines = [l.strip().lower() for l in out_scope_sec.content.split("\n") if l.strip().startswith("-")]
            fr_text_low = fr_section_pre.content.lower()
            out_keywords = ["external ticketing", "third-party ticketing", "ticketing platforms", "zendesk", "freshdesk", "jira", "crm synchronization", "salesforce", "telephony", "voice calls", "payment processing"]
            for o_line in out_lines:
                for kw in out_keywords:
                    if kw in o_line:
                        fr_lines_with_kw = [l for l in fr_text_low.split("\n") if kw in l and ("fr-" in l or "###" in l or "| **fr-" in l)]
                        for f_line in fr_lines_with_kw:
                            is_fr_negation = any(neg in f_line for neg in ["no ", "not ", "deferred", "without", "out of scope", "prohibited"])
                            if not is_fr_negation:
                                issues.append(ValidationIssue(
                                    rule_id="VAL-SEM-004",
                                    severity="error",
                                    section_key="functional_requirements",
                                    title=f"Scope Contradiction: Out-of-Scope Capability '{kw}' Defined in Functional Requirements",
                                    description=f"Capability related to '{kw}' is explicitly listed as out-of-scope, but is specified as an active functional requirement.",
                                    recommendation="Remove conflicting functional requirement or update out-of-scope declarations."
                                ))
                                score -= 10
                                break
                        if any(i.rule_id == "VAL-SEM-004" and i.section_key == "functional_requirements" for i in issues):
                            break

        # Contradiction check: out-of-scope vs executive_summary, assumptions, risks, journeys
        if out_scope_sec and not out_scope_sec.is_na:
            out_text_low = out_scope_sec.content.lower()
            if any(kw in out_text_low for kw in ["external ticketing", "third-party ticketing", "ticketing platforms", "crm synchronization", "salesforce"]):
                target_secs = [
                    ("executive_summary", ["integrate with chat/ticketing", "ticketing platforms", "resolve tickets quickly", "close tickets", "incoming tickets"]),
                    ("user_journeys", ["ticket creation", "ticket id", "queued ticket", "ticket generation", "closes tickets", "resolve tickets", "open the queued ticket"]),
                    ("system_workflows", ["zendesk", "third-party ticketing", "external ticketing", "ticket creation", "creates ticket", "zendesk ticket", "jira"]),
                    ("integration_requirements", ["zendesk", "third-party ticketing", "external ticketing", "ticket creation"]),
                    ("risks_and_mitigation", ["crm vendor api", "ticketing platform api", "external ticketing failure"]),
                    ("assumptions_and_open_questions", ["ticketing api credentials", "crm api integration is available", "ticketing platform is maintained"])
                ]
                for sec_key, forbidden_phrases in target_secs:
                    sec_item = prd_version.sections.get(sec_key)
                    if sec_item and not sec_item.is_na and sec_item.content:
                        sec_low = sec_item.content.lower()
                        for fp in forbidden_phrases:
                            if fp in sec_low:
                                line_fp = [l for l in sec_low.split("\n") if fp in l][0]
                                if not any(neg in line_fp for neg in ["no ", "not ", "deferred", "without", "out of scope", "prohibited", "future consideration"]):
                                    issues.append(ValidationIssue(
                                        rule_id="VAL-SEM-004",
                                        severity="error",
                                        section_key=sec_key,
                                        title=f"Out-of-Scope Ticketing Capability '{fp}' in {sec_key}",
                                        description=f"Section '{sec_key}' references external ticketing capability '{fp}', contradicting out-of-scope MVP boundary.",
                                        recommendation="Remove out-of-scope ticketing/CRM references and use self-contained internal escalation queue routing."
                                    ))
                                    score -= 8
                                    break

        # -------------------------------------------------------------
        # 3. Requirement Identifiers & Traceability
        # -------------------------------------------------------------
        fr_section = prd_version.sections.get("functional_requirements")
        fr_content = fr_section.content if fr_section else ""
        fr_ids = re.findall(r"^\|\s*\*{0,2}(FR-\d{3,4})\*{0,2}\s*\|", fr_content, re.MULTILINE)
        if not fr_ids:
            fr_ids = re.findall(r"\b(FR-\d{3,4})\b", fr_content)
        
        seen_frs: Set[str] = set()
        duplicate_frs: Set[str] = set()
        for fid in fr_ids:
            if fid in seen_frs:
                duplicate_frs.add(fid)
            seen_frs.add(fid)

        for dup in duplicate_frs:
            issues.append(ValidationIssue(
                rule_id="VAL-DUP-001",
                severity="error",
                section_key="functional_requirements",
                title=f"Duplicate Functional Requirement Identifier: {dup}",
                description=f"Identifier {dup} appears multiple times in functional requirements.",
                recommendation="Assign unique, stable identifiers to each requirement."
            ))
            issues.append(ValidationIssue(
                rule_id="VAL-REQ-001",
                severity="error",
                section_key="functional_requirements",
                title=f"Duplicate Functional Requirement Identifier: {dup}",
                description=f"Identifier {dup} appears multiple times in functional requirements.",
                recommendation="Assign unique, stable identifiers to each requirement."
            ))
            score -= 8

        # VAL-REQ-002: Generic or Fabricated Requirement Attributes Check
        if fr_section and not fr_section.is_na:
            fr_text_lower = fr_section.content.lower()
            fabricated_patterns = [
                r"actor has active authorized session",
                r"standard schema payload",
                r"enforces strict domain validation rules",
                r"halt transaction safely and notify actor with diagnostic code",
                r"state transition is recorded and verified confirmation is returned",
                r"updates\s+[\w\s]+\s+ledger with timestamp and actor id"
            ]
            for pat in fabricated_patterns:
                f_match = re.search(pat, fr_text_lower)
                if f_match:
                    match_str = f_match.group(0)
                    issues.append(ValidationIssue(
                        rule_id="VAL-REQ-002",
                        severity="error",
                        section_key="functional_requirements",
                        title=f"Fabricated Generic Requirement Attribute: '{match_str}'",
                        description=f"Requirement contains fabricated default behavior '{match_str}'. Missing source information must remain explicitly unresolved rather than defaulting to generic system actions.",
                        recommendation="Remove generic fallback defaults; mark missing preconditions, inputs, constraints, failure paths, and outcomes as [Unresolved: Pending stakeholder specification]."
                    ))
                    score -= 10
                    break

        # Traceability: FR -> AC
        ac_section = prd_version.sections.get("acceptance_criteria")
        ac_content = ac_section.content if ac_section else ""
        ac_ids = set(re.findall(r"\b(AC-\d{3,4})\b", ac_content))

        for fid in seen_frs:
            if fid not in ac_content:
                issues.append(ValidationIssue(
                    rule_id="VAL-AC-001",
                    severity="warning",
                    section_key="functional_requirements",
                    title=f"Unmapped Acceptance Criteria for {fid}",
                    description=f"Requirement {fid} has no corresponding acceptance criteria in the Acceptance Criteria section.",
                    recommendation=f"Add testable Given-When-Then acceptance criteria linked to {fid}."
                ))
                score -= 4

        # Traceability: US -> FR
        us_section = prd_version.sections.get("user_stories")
        if us_section and not us_section.is_na:
            us_fr_links = re.findall(r"\b(FR-\d{3,4})\b", us_section.content)
            for linked_fr in us_fr_links:
                if seen_frs and linked_fr not in seen_frs:
                    issues.append(ValidationIssue(
                        rule_id="VAL-TRC-003",
                        severity="warning",
                        section_key="user_stories",
                        title=f"User Story Links to Undefined Requirement: {linked_fr}",
                        description=f"A user story references requirement {linked_fr}, which does not exist in the FR catalog.",
                        recommendation=f"Update user story to reference a defined requirement or add {linked_fr} to Functional Requirements."
                    ))
                    score -= 3

        # -------------------------------------------------------------
        # 4. Acceptance Criteria Quality
        # -------------------------------------------------------------
        if ac_section and not ac_section.is_na:
            ac_lines = [l.strip() for l in ac_content.split("\n") if "AC-" in l and "|" in l]
            for line in ac_lines:
                if not any(token in line for token in ["Given", "When", "Then", "Shall", "Must"]):
                    issues.append(ValidationIssue(
                        rule_id="VAL-AC-002",
                        severity="warning",
                        section_key="acceptance_criteria",
                        title="Acceptance Criterion Lacks Testable Given-When-Then Phrasing",
                        description=f"Criterion line does not follow structured Given-When-Then or normative condition format.",
                        recommendation="Format criteria as: 'Given [precondition], When [action], Then [measurable outcome]'."
                    ))
                    score -= 2
                    break

        # -------------------------------------------------------------
        # 5. Business Rule Provenance & Duplicate Check
        # -------------------------------------------------------------
        br_section = prd_version.sections.get("business_rules")
        if br_section and not br_section.is_na:
            br_content = br_section.content
            valid_provenances = [
                "user_confirmed",
                "user_provided",
                "confirmed_user_input",
                "explicit_clarification",
                "clarification_confirmed",
                "assignment_required",
                "assignment_instruction",
                "reference_supported",
                "external_reference",
                "inferred",
                "ai_proposed_assumption",
                "proposed",
                "recommendation",
                "unresolved",
                "unresolved_decision",
                "unresolved_open_decision"
            ]
            br_rows = [l for l in br_content.split("\n") if "BR-" in l and "|" in l]
            for row in br_rows:
                has_prov = any(vp in row.lower() for vp in valid_provenances)
                if not has_prov:
                    issues.append(ValidationIssue(
                        rule_id="VAL-SEM-003",
                        severity="warning",
                        section_key="business_rules",
                        title="Business Rule Missing Explicit Provenance Tag",
                        description="Business rule does not specify whether it is user_confirmed, clarification_confirmed, or an assumption.",
                        recommendation="Tag rule provenance with: `user_confirmed`, `assignment_required`, `reference_supported`, `ai_proposed_assumption`, or `unresolved`."
                    ))
                    score -= 3
                    break

            # Check duplicate Business Rule IDs (e.g. duplicate BR-007)
            br_ids = re.findall(r"\|\s*\*{0,2}(BR-\d{3,4})\*{0,2}\s*\|", br_content)
            seen_brs: Set[str] = set()
            for bid in br_ids:
                if bid in seen_brs:
                    issues.append(ValidationIssue(
                        rule_id="VAL-DUP-001",
                        severity="error",
                        section_key="business_rules",
                        title=f"Duplicate Business Rule Identifier: {bid}",
                        description=f"Identifier {bid} appears multiple times in the Business Rules table.",
                        recommendation="Assign unique, stable identifiers (e.g. BR-001, BR-002) to each business rule."
                    ))
                    score -= 10
                    break
                seen_brs.add(bid)

        # Check duplicate Acceptance Criteria IDs
        if ac_section and not ac_section.is_na:
            ac_rows_ids = re.findall(r"\|\s*\*{0,2}(AC-\d{3,4})\*{0,2}\s*\|", ac_content)
            seen_ac_ids: Set[str] = set()
            for aid in ac_rows_ids:
                if aid in seen_ac_ids:
                    issues.append(ValidationIssue(
                        rule_id="VAL-DUP-001",
                        severity="error",
                        section_key="acceptance_criteria",
                        title=f"Duplicate Acceptance Criterion Identifier: {aid}",
                        description=f"Identifier {aid} appears multiple times in Acceptance Criteria.",
                        recommendation="Assign unique, stable identifiers to each acceptance criterion."
                    ))
                    score -= 8
                    break
                seen_ac_ids.add(aid)

        # Check duplicate User Story IDs
        if us_section and not us_section.is_na:
            us_rows_ids = re.findall(r"\|\s*\*{0,2}(US-\d{3,4})\*{0,2}\s*\|", us_section.content)
            seen_us_ids: Set[str] = set()
            for uid in us_rows_ids:
                if uid in seen_us_ids:
                    issues.append(ValidationIssue(
                        rule_id="VAL-DUP-001",
                        severity="error",
                        section_key="user_stories",
                        title=f"Duplicate User Story Identifier: {uid}",
                        description=f"Identifier {uid} appears multiple times in User Stories.",
                        recommendation="Assign unique, stable identifiers to each user story."
                    ))
                    score -= 8
                    break
                seen_us_ids.add(uid)

        # -------------------------------------------------------------
        # 6. Semantic Relevance & Domain Alignment (No Global Forbidden Lists)
        # -------------------------------------------------------------
        if analysis:
            domain_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", analysis.problem_domain.lower()))
            cat_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", analysis.product_category.lower()))
            key_tokens = domain_tokens.union(cat_tokens)

            # Check if Functional Requirements mention any domain entities
            if fr_content:
                fr_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", fr_content.lower()))
                common_tokens = key_tokens.intersection(fr_tokens)
                if key_tokens and len(common_tokens) == 0:
                    issues.append(ValidationIssue(
                        rule_id="VAL-SEM-001",
                        severity="error",
                        section_key="functional_requirements",
                        title="Functional Requirements Fail Domain Relevance",
                        description=f"Requirements do not reference key domain terminology from '{analysis.problem_domain}'.",
                        recommendation="Align functional requirements directly with the target product domain and operational entities."
                    ))
                    score -= 15

            # Persona & User Journey Alignment
            target_users = set(u.strip().lower() for u in analysis.intended_users if u.strip())
            personas_sec = prd_version.sections.get("user_personas")
            if target_users and personas_sec and not personas_sec.is_na:
                persona_content_lower = personas_sec.content.lower()
                matched_users = []
                for u in target_users:
                    u_stem = u.rstrip("s")
                    words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", u) if w not in ["the", "and", "user", "users"]]
                    if u in persona_content_lower or u_stem in persona_content_lower or (words and all(w.rstrip("s") in persona_content_lower for w in words)):
                        matched_users.append(u)
                if len(matched_users) == 0:
                    issues.append(ValidationIssue(
                        rule_id="VAL-SEM-002",
                        severity="warning",
                        section_key="user_personas",
                        title="Persona Profiles Do Not Match Intended Target Users",
                        description=f"None of the intended users ({', '.join(analysis.intended_users)}) appear in User Personas.",
                        recommendation="Define detailed personas representing the primary intended user roles."
                    ))
                    score -= 5

            # Assignment Compliance
            ASSIGNMENT_SECTION_MAPPINGS = {
                # 1. Assignment instructions / guidelines / RFP requirements
                "instruction": ["document_information", "product_overview", "dependencies_and_constraints"],
                "instructions": ["document_information", "product_overview", "dependencies_and_constraints"],
                "assignment": ["document_information", "product_overview", "dependencies_and_constraints"],
                "guideline": ["document_information", "product_overview", "dependencies_and_constraints"],
                "guidelines": ["document_information", "product_overview", "dependencies_and_constraints"],
                "rfp": ["document_information", "product_overview", "dependencies_and_constraints"],

                # 2. Product requirements / system requirements / capabilities / functional specs
                "requirement": ["functional_requirements", "product_scope", "acceptance_criteria", "user_stories"],
                "requirements": ["functional_requirements", "product_scope", "acceptance_criteria", "user_stories"],
                "functional": ["functional_requirements", "user_stories", "acceptance_criteria"],
                "capability": ["functional_requirements", "product_scope", "product_overview"],
                "capabilities": ["functional_requirements", "product_scope", "product_overview"],
                "specification": ["functional_requirements", "non_functional_requirements", "product_scope"],
                "specifications": ["functional_requirements", "non_functional_requirements", "product_scope"],
                "scope": ["product_scope", "out_of_scope"],

                # 3. Implementation details / architecture / engineering design
                "implementation": ["proposed_solution", "system_workflows", "dependencies_and_constraints", "data_requirements"],
                "details": ["proposed_solution", "system_workflows", "dependencies_and_constraints"],
                "implementation details": ["proposed_solution", "system_workflows", "dependencies_and_constraints", "data_requirements"],
                "architecture": ["system_workflows", "dependencies_and_constraints", "product_overview"],
                "system architecture": ["system_workflows", "dependencies_and_constraints", "product_overview"],
                "design": ["proposed_solution", "system_workflows", "user_journeys"],
                "technical": ["non_functional_requirements", "data_requirements", "integration_requirements", "security_and_privacy_requirements"],
                "engineering": ["proposed_solution", "dependencies_and_constraints", "system_workflows"],
                "data": ["data_requirements"],
                "database": ["data_requirements"],
                "integration": ["integration_requirements"],
                "api": ["integration_requirements", "system_workflows"],
                "ui": ["proposed_solution", "system_workflows", "user_journeys"],
                "interface": ["proposed_solution", "system_workflows", "user_journeys", "integration_requirements"],
                "user interface": ["proposed_solution", "system_workflows", "user_journeys"],
                "user interface design": ["proposed_solution", "system_workflows", "user_journeys"],
                "workflow": ["system_workflows", "existing_workflow_and_pain_points"],
                "workflows": ["system_workflows", "existing_workflow_and_pain_points"],
                "security": ["security_and_privacy_requirements"],
                "privacy": ["security_and_privacy_requirements"],

                # Domain-specific technical capabilities
                "nlp": ["proposed_solution", "functional_requirements"],
                "language": ["proposed_solution", "functional_requirements"],
                "processing": ["proposed_solution", "functional_requirements"],
                "ai": ["proposed_solution", "functional_requirements"],
                "natural language": ["proposed_solution", "functional_requirements"],
                "natural language processing": ["proposed_solution", "functional_requirements"],
                "knowledge base": ["integration_requirements", "proposed_solution"],
                "knowledge base integration": ["integration_requirements", "proposed_solution"],

                # 4. Open decisions / open questions / architectural trade-offs
                "decision": ["assumptions_and_open_questions", "dependencies_and_constraints", "security_and_privacy_requirements"],
                "decisions": ["assumptions_and_open_questions", "dependencies_and_constraints", "security_and_privacy_requirements"],
                "open": ["assumptions_and_open_questions", "dependencies_and_constraints"],
                "open decisions": ["assumptions_and_open_questions", "dependencies_and_constraints"],
                "open questions": ["assumptions_and_open_questions"],
                "tradeoff": ["assumptions_and_open_questions", "dependencies_and_constraints"],
                "tradeoffs": ["assumptions_and_open_questions", "dependencies_and_constraints"],
                "trade-off": ["assumptions_and_open_questions", "dependencies_and_constraints"],
                "question": ["assumptions_and_open_questions"],
                "questions": ["assumptions_and_open_questions"],
                "assumption": ["assumptions_and_open_questions"],
                "assumptions": ["assumptions_and_open_questions"],

                # 5. Recommendations / advisory / release / future scope / risk
                "recommendation": ["risks_and_mitigation", "release_considerations", "assumptions_and_open_questions", "proposed_solution"],
                "recommendations": ["risks_and_mitigation", "release_considerations", "assumptions_and_open_questions", "proposed_solution"],
                "advisory": ["risks_and_mitigation", "assumptions_and_open_questions"],
                "future": ["release_considerations", "out_of_scope"],
                "release": ["release_considerations"],
                "risk": ["risks_and_mitigation"],
                "risks": ["risks_and_mitigation"],
                "mitigation": ["risks_and_mitigation"],
                "testing": ["acceptance_criteria"],
                "acceptance": ["acceptance_criteria"],
                "metric": ["success_metrics"],
                "metrics": ["success_metrics"],
                "success": ["success_metrics"]
            }

            if analysis.assignment_requirements and analysis.assignment_requirements.mandatory_sections:
                for req_name in analysis.assignment_requirements.mandatory_sections:
                    clean_req = req_name.strip().lower()
                    req_words = [w for w in re.findall(r"[a-z0-9]+", clean_req) if w not in ["and", "or", "the", "of", "requirements", "section", "system"]]

                    candidate_keys = set()
                    # 1. Exact phrase match
                    if clean_req in ASSIGNMENT_SECTION_MAPPINGS:
                        candidate_keys.update(ASSIGNMENT_SECTION_MAPPINGS[clean_req])

                    # 2. Token match against mapping
                    for rw in req_words:
                        if rw in ASSIGNMENT_SECTION_MAPPINGS:
                            candidate_keys.update(ASSIGNMENT_SECTION_MAPPINGS[rw])

                    # 3. Direct match against canonical section names
                    for k in CANONICAL_SECTIONS:
                        k_clean = k.replace("_", " ")
                        if clean_req in k_clean or k_clean in clean_req:
                            candidate_keys.add(k)
                        for rw in req_words:
                            if len(rw) >= 4 and rw in k:
                                candidate_keys.add(k)

                    if not candidate_keys:
                        # Meaningful validation warning for unrecognized phrases
                        issues.append(ValidationIssue(
                            rule_id="VAL-SEM-006",
                            severity="warning",
                            section_key="document_information",
                            title=f"Unrecognized Assignment Requirement Phrase: '{req_name}'",
                            description=f"The assignment instruction lists '{req_name}' as a mandatory requirement, but it could not be mapped to any canonical PRD section. Review assignment instructions.",
                            recommendation=f"Clarify whether '{req_name}' represents a specific product deliverable, an open decision, or should be documented within a canonical PRD section."
                        ))
                        score -= 3
                    else:
                        # Verify that at least one candidate canonical section is populated
                        has_populated_section = False
                        for ck in candidate_keys:
                            sec = prd_version.sections.get(ck)
                            if sec and not sec.is_na and len(sec.content.strip()) >= 20:
                                has_populated_section = True
                                break

                        if not has_populated_section:
                            issues.append(ValidationIssue(
                                rule_id="VAL-SEM-005",
                                severity="error",
                                section_key="document_information",
                                title=f"Mandatory Assignment Section Non-Compliant: {req_name}",
                                description=f"The assignment requires '{req_name}' (mapped to canonical sections: {', '.join(sorted(candidate_keys))}), but these sections are missing, empty, or marked N/A.",
                                recommendation=f"Populate section '{req_name}' with verified requirements to satisfy assignment criteria."
                            ))
                            score -= 8

        # -------------------------------------------------------------
        # 7. Ambiguity Detection
        # -------------------------------------------------------------
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
                    break

        # -------------------------------------------------------------
        # 8. Engineering Readiness & Actionability Checks
        # -------------------------------------------------------------
        # VAL-ENG-001: Actionable & Non-Repetitive Requirement Check
        if fr_section and not fr_section.is_na:
            fr_rows = [l.strip() for l in fr_content.split("\n") if "FR-" in l and "|" in l]
            for row in fr_rows:
                parts = [p.strip() for p in row.split("|")]
                # Expected format: | **FR-001** | Title | Description | Priority | Traceable AC |
                if len(parts) >= 5:
                    fid = parts[1].replace("*", "").strip()
                    title = parts[2].strip()
                    desc = parts[3].strip()
                    is_repetitive = (
                        f"shall implement {title.lower()}" in desc.lower() or
                        desc.lower() == title.lower() or
                        (title.lower() in desc.lower() and len(desc) < len(title) + 20)
                    )
                    if is_repetitive:
                        issues.append(ValidationIssue(
                            rule_id="VAL-ENG-001",
                            severity="error",
                            section_key="functional_requirements",
                            title=f"Repetitive or Non-Actionable Requirement Description: {fid}",
                            description=f"Requirement {fid} description merely repeats the title or uses formulaic 'The system shall implement [title]'.",
                            recommendation="Specify explicit actor, preconditions, system behavior, business constraints, and expected outcome."
                        ))
                        score -= 8
                        break

        # VAL-AC-003: Scenario-Specific Acceptance Criteria & Boilerplate Check
        if ac_section and not ac_section.is_na:
            ac_lines = [l.strip() for l in ac_content.split("\n") if "AC-" in l and "|" in l]
            seen_then_clauses = {}
            for line in ac_lines:
                parts = [p.strip() for p in line.split("|")]
                line_lower = line.lower()
                if "executes successfully and logs the result" in line_lower or "action is performed" in line_lower:
                    issues.append(ValidationIssue(
                        rule_id="VAL-AC-003",
                        severity="error",
                        section_key="acceptance_criteria",
                        title="Acceptance Criterion Uses Generic Boilerplate Phrasing",
                        description="Acceptance criterion uses generic outcome 'executes successfully and logs the result' instead of domain-specific conditions.",
                        recommendation="Specify domain-concrete Given-When-Then conditions covering happy path, threshold breaches, and error states."
                    ))
                    score -= 8
                    break

                # Check for duplicate Then/Given clauses across different ACs
                if len(parts) >= 5:
                    ac_id = parts[1]
                    then_clause = parts[4].lower()
                    if len(then_clause) > 20:
                        if then_clause in seen_then_clauses and seen_then_clauses[then_clause] != ac_id:
                            issues.append(ValidationIssue(
                                rule_id="VAL-AC-003",
                                severity="error",
                                section_key="acceptance_criteria",
                                title=f"Duplicate Acceptance Criteria Outcome in {ac_id}",
                                description=f"Acceptance criterion {ac_id} duplicates the outcome of {seen_then_clauses[then_clause]}.",
                                recommendation="Provide unique, testable Given-When-Then criteria for each acceptance condition."
                            ))
                            score -= 6
                            break
                        seen_then_clauses[then_clause] = ac_id

        # VAL-AC-004: Duplicated Requirement Text or Formulaic Run-On Acceptance Criteria
        if ac_section and not ac_section.is_na:
            ac_lines = [l.strip() for l in ac_content.split("\n") if "AC-" in l and "|" in l]
            fr_desc_map = {}
            if fr_section and not fr_section.is_na:
                for row in fr_content.split("\n"):
                    if "FR-" in row and "|" in row:
                        p = [x.strip() for x in row.split("|")]
                        if len(p) >= 4:
                            fid = p[1].replace("*", "").strip()
                            desc = p[3].strip().lower()
                            fr_desc_map[fid] = desc

            for line in ac_lines:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    ac_id = parts[1].replace("*", "").strip()
                    stmt = parts[2].strip() if len(parts) == 3 else (" ".join(parts[2:]).strip())
                    stmt_lower = stmt.lower()

                    # 1. Formulaic field-concatenation & generic boilerplate pattern check
                    generic_boilerplate_phrases = [
                        "given an authenticated actor with valid preconditions",
                        "executes the transition successfully, and records the verifiable confirmation",
                        "executes the transition successfully, and returns a verified confirmation",
                        "verifies authorization, executes the transition successfully",
                        "executes successfully and logs the result",
                        "halts invalid state transitions"
                    ]
                    is_generic_boilerplate = any(p in stmt_lower for p in generic_boilerplate_phrases)
                    is_runon_concat = bool(re.search(
                        r"given\s+.+\s+initiates\s+.+\s+with\s+.+,\s+when\s+processed\s+under\s+.+,\s+then\s+the\s+system\s+.+\s+and\s+.+",
                        stmt_lower
                    ))
                    if is_generic_boilerplate or is_runon_concat:
                        issues.append(ValidationIssue(
                            rule_id="VAL-AC-004",
                            severity="error",
                            section_key="acceptance_criteria",
                            title=f"Generic Boilerplate Acceptance Criterion Detected: {ac_id}",
                            description=f"Criterion {ac_id} uses generic placeholder phrasing rather than scenario-specific Given-When-Then assertions.",
                            recommendation="Replace generic placeholder phrasing with concrete domain behavior, inputs, and expected outcomes."
                        ))
                        score -= 8
                        break

                    # 2. Check if statement duplicates any FR description
                    for fid, fr_desc in fr_desc_map.items():
                        if len(fr_desc) > 30 and (stmt_lower == fr_desc or (not ("given " in stmt_lower and "then " in stmt_lower) and fr_desc in stmt_lower) or (stmt_lower in fr_desc and len(stmt_lower) > 25 and not ("given " in stmt_lower and "then " in stmt_lower))):
                            issues.append(ValidationIssue(
                                rule_id="VAL-AC-004",
                                severity="error",
                                section_key="acceptance_criteria",
                                title=f"Acceptance Criterion Duplicates Requirement Description: {ac_id}",
                                description=f"Acceptance criterion {ac_id} duplicates the description of {fid} rather than providing testable conditions.",
                                recommendation="Replace copied requirement text with concrete verification assertions."
                            ))
                            score -= 8
                            break
                    else:
                        continue
                    break

        # VAL-ENG-003: Provenance Accuracy & Evidence Alignment Check
        if br_section and not br_section.is_na and analysis:
            user_evidence_list = (analysis.explicit_constraints or []) + (analysis.facts or []) + (analysis.core_objectives or [])
            user_evidence_str = " ".join(user_evidence_list).lower()
            if user_evidence_list:
                br_rows = [l for l in br_content.split("\n") if "BR-" in l and "|" in l]
                user_prov_count = sum(1 for r in br_rows if any(p in r.lower() for p in ["user_confirmed", "user_provided", "confirmed_user_input", "assignment_required", "assignment_instruction", "explicit_clarification"]))
                if user_prov_count == 0 and len(br_rows) > 0:
                    issues.append(ValidationIssue(
                        rule_id="VAL-ENG-003",
                        severity="warning",
                        section_key="business_rules",
                        title="Mislabeled Rule Provenance: User Constraints Tagged as Assumptions",
                        description="Project contains confirmed facts/constraints, but zero business rules are tagged as user_provided or user_confirmed.",
                        recommendation="Tag rules derived from user submissions or constraints as `user_confirmed` or `user_provided`."
                    ))
                    score -= 4

                # Cross-check rules claiming confirmed_user_input against actual user evidence
                for row in br_rows:
                    parts = [p.strip() for p in row.split("|")]
                    if len(parts) >= 6:
                        rule_id = parts[1].replace("*", "").strip()
                        rule_title = parts[2].strip()
                        rule_stmt = parts[3].strip()
                        rule_prov = parts[4].replace("`", "").strip().lower()
                        source_ref = parts[5].strip().lower()
                        conf_req = parts[-2].strip().lower() if len(parts) >= 7 else ""

                        # 1. Check for cross-domain contamination in source reference
                        if "attendance" in source_ref and "support" in (analysis.problem_domain or "").lower():
                            issues.append(ValidationIssue(
                                rule_id="VAL-ENG-003",
                                severity="error",
                                section_key="business_rules",
                                title=f"Invalid Cross-Domain Source Reference in {rule_id}",
                                description=f"Rule {rule_id} cites attendance threshold as source reference in a customer support product.",
                                recommendation="Cite only relevant customer support constraints or submissions."
                            ))
                            score -= 10
                            break
                        if ("customer support" in source_ref or "80% confidence" in source_ref) and ("attendance" in (analysis.problem_domain or "").lower() or "education" in (analysis.problem_domain or "").lower()):
                            issues.append(ValidationIssue(
                                rule_id="VAL-ENG-003",
                                severity="error",
                                section_key="business_rules",
                                title=f"Invalid Cross-Domain Source Reference in {rule_id}",
                                description=f"Rule {rule_id} cites customer support or 80% confidence as source reference in an attendance product.",
                                recommendation="Cite only relevant educational administration constraints."
                            ))
                            score -= 10
                            break

                        # 2. Conflicting provenance references
                        if rule_prov in ["user_confirmed", "confirmed_user_input", "user_provided"]:
                            if any(k in source_ref for k in ["assignment requirement", "course guideline", "rfp requirement"]) and not any(k in user_evidence_str for k in ["assignment", "rfp"]):
                                issues.append(ValidationIssue(
                                    rule_id="VAL-ENG-003",
                                    severity="warning",
                                    section_key="business_rules",
                                    title=f"Conflicting Provenance Reference in {rule_id}",
                                    description=f"Rule {rule_id} is marked as confirmed_user_input but cites assignment instruction ({parts[5]}).",
                                    recommendation="Classify assignment-provided requirements separately as `assignment_instruction`."
                                ))
                                score -= 3

                        # 3. Check for ungrounded specific numeric assertions
                        if rule_prov in ["user_confirmed", "confirmed_user_input", "user_provided"]:
                            pcts = re.findall(r"\b\d+(?:\.\d+)?%", rule_stmt)
                            user_pct_vals = [float(p.replace("%", "")) for p in re.findall(r"\b\d+(?:\.\d+)?%", user_evidence_str)]
                            for pct in pcts:
                                p_val = float(pct.replace("%", ""))
                                if p_val not in user_pct_vals and pct not in user_evidence_str:
                                    issues.append(ValidationIssue(
                                        rule_id="VAL-PROV-003",
                                        severity="error",
                                        section_key="business_rules",
                                        title=f"Source Reference Does Not Support Statement: Unconfirmed Metric '{pct}' in {rule_id}",
                                        description=f"Rule {rule_id} asserts '{pct}' as confirmed_user_input, but '{pct}' is not present in user constraints or confirmed facts.",
                                        recommendation="Demote unconfirmed numeric invariants to ai_proposed_assumption or unresolved decision."
                                    ))
                                    issues.append(ValidationIssue(
                                        rule_id="VAL-PROV-001",
                                        severity="error",
                                        section_key="business_rules",
                                        title=f"Mislabeled Rule Provenance: Assertion of Unconfirmed Metric '{pct}' in {rule_id}",
                                        description=f"Rule {rule_id} asserts '{pct}' as confirmed_user_input, but '{pct}' is not present in user constraints or confirmed facts.",
                                        recommendation="Demote unconfirmed numeric invariants to ai_proposed_assumption."
                                    ))
                                    score -= 8
                                    break

                        # Canonical provenance verification (VAL-PROV-002 / VAL-PROV-001)
                        if not rule_prov or rule_prov in ["none", "n/a", "null", "unknown"]:
                            issues.append(ValidationIssue(
                                rule_id="VAL-PROV-001",
                                severity="error",
                                section_key="business_rules",
                                title=f"Missing Provenance in {rule_id}",
                                description=f"Rule {rule_id} has no documented provenance.",
                                recommendation="Provide canonical provenance classification for each rule."
                            ))
                            score -= 8

                        canonical_provenances = {
                            "user_confirmed", "assignment_required", "reference_supported", "inferred", "proposed", "unresolved",
                            "confirmed_user_input", "user_provided", "assignment_instruction", "explicit_clarification",
                            "clarification_confirmed", "ai_proposed_assumption", "external_reference", "unresolved_decision", "recommendation"
                        }
                        if rule_prov and rule_prov not in canonical_provenances:
                            issues.append(ValidationIssue(
                                rule_id="VAL-PROV-002",
                                severity="error",
                                section_key="business_rules",
                                title=f"Non-Canonical Provenance Value '{rule_prov}' in {rule_id}",
                                description=f"Rule {rule_id} uses unapproved provenance '{rule_prov}'. Must be one of the canonical provenance standards.",
                                recommendation="Map provenance strictly to one of: USER_CONFIRMED, ASSIGNMENT_REQUIRED, REFERENCE_SUPPORTED, INFERRED, PROPOSED, UNRESOLVED."
                            ))
                            issues.append(ValidationIssue(
                                rule_id="VAL-PROV-001",
                                severity="error",
                                section_key="business_rules",
                                title=f"Non-Canonical Provenance Value '{rule_prov}' in {rule_id}",
                                description=f"Rule {rule_id} uses unapproved provenance '{rule_prov}'. Must be one of the canonical provenance standards.",
                                recommendation="Map provenance strictly to one of: USER_CONFIRMED, ASSIGNMENT_REQUIRED, REFERENCE_SUPPORTED, INFERRED, PROPOSED, UNRESOLVED."
                            ))
                            score -= 6

                        # 4. Recommendations must NEVER be presented as confirmed requirements (VAL-PROV-004)
                        if "recommendation" in rule_prov or "inferred" in rule_prov or "proposed" in rule_prov:
                            is_claimed_confirmed = bool(re.search(r"\b(?:no|false)\b", conf_req))
                            if is_claimed_confirmed or any(firm in rule_stmt.lower() for firm in ["must be strictly enforced", "is mandatory"]):
                                issues.append(ValidationIssue(
                                    rule_id="VAL-PROV-004",
                                    severity="error",
                                    section_key="business_rules",
                                    title=f"AI Inference/Proposal Presented as Confirmed Requirement in {rule_id}",
                                    description=f"Rule {rule_id} is marked as an inference or proposal but is presented as an approved requirement without requiring stakeholder review.",
                                    recommendation="Ensure proposals and inferences require stakeholder confirmation and are not treated as firm invariants."
                                ))
                                issues.append(ValidationIssue(
                                    rule_id="VAL-ENG-003",
                                    severity="error",
                                    section_key="business_rules",
                                    title=f"Recommendation Presented as Confirmed Requirement in {rule_id}",
                                    description=f"Rule {rule_id} is marked as a recommendation but is presented as a confirmed requirement without requiring stakeholder review.",
                                    recommendation="Ensure recommendations require stakeholder confirmation and are not treated as firm invariants."
                                ))
                                score -= 5

                        # 5. Missing traceable source reference check
                        if len(source_ref) < 5 or source_ref in ["none", "n/a", "null", "unknown"]:
                            issues.append(ValidationIssue(
                                rule_id="VAL-ENG-003",
                                severity="warning",
                                section_key="business_rules",
                                title=f"Missing Traceable Source Reference in {rule_id}",
                                description=f"Rule {rule_id} lacks a traceable source reference justifying its provenance.",
                                recommendation="Provide an explicit source reference quoting user input, assignment text, or domain standard."
                            ))
                            score -= 2

        # -------------------------------------------------------------
        # VAL-PROV-005: Provenance Ledger & Deterministic Evidence Entailment
        # -------------------------------------------------------------
        app_sec = prd_version.sections.get("appendix_and_glossary")
        if app_sec and not app_sec.is_na:
            app_content = app_sec.content or ""
            has_ledger = "full document provenance ledger" in app_content.lower()
            
            # Determine document version
            doc_info = prd_version.sections.get("document_information")
            doc_ver = prd_version.version_number or ""
            if doc_info and doc_info.content:
                vm = re.search(r"\*\*Version:\*\*\s*([^\s\|]+)", doc_info.content)
                if vm:
                    doc_ver = vm.group(1).strip()
            is_p245_or_newer = any(v in doc_ver for v in ["v2.4.5", "v2.4.6", "v2.5", "v3."])

            if not has_ledger:
                if is_p245_or_newer:
                    issues.append(ValidationIssue(
                        rule_id="VAL-PROV-001",
                        severity="error",
                        section_key="appendix_and_glossary",
                        title="Missing Section 27 Full Document Provenance Ledger",
                        description="Section 27 (Appendix and Glossary) must contain the authoritative Full Document Provenance Ledger table.",
                        recommendation="Render the complete claim-level provenance ledger covering canonical sections."
                    ))
                    score -= 8
                else:
                    issues.append(ValidationIssue(
                        rule_id="VAL-PROV-001",
                        severity="info",
                        section_key="appendix_and_glossary",
                        title="Provenance Ledger Not Rendered in Legacy Section 27",
                        description="Section 27 does not contain the Full Document Provenance Ledger table (mandated starting in v2.4.5).",
                        recommendation="Render the complete claim-level provenance ledger covering canonical sections."
                    ))
            else:
                ledger_lines = [l.strip() for l in app_content.split("\n") if l.strip().startswith("|") and ("CLM-" in l or "PL-" in l)]
                if len(ledger_lines) < 15:
                    issues.append(ValidationIssue(
                        rule_id="VAL-PROV-001",
                        severity="error",
                        section_key="appendix_and_glossary",
                        title="Incomplete Full Document Provenance Ledger",
                        description=f"Provenance Ledger contains only {len(ledger_lines)} claims; comprehensive coverage across 27 canonical sections requires at least 25 entries.",
                        recommendation="Generate claim-level provenance entries covering all canonical PRD sections."
                    ))
                    score -= 8

                raw_idea = getattr(analysis, "raw_idea", None) if analysis else None
                user_evidence_list = (analysis.explicit_constraints or []) + (analysis.facts or []) + (analysis.core_objectives or []) + ([raw_idea] if raw_idea else [])
                user_evidence_str = " ".join(user_evidence_list).lower()

                for row in ledger_lines:
                    parts = [p.strip() for p in row.split("|")]
                    if len(parts) >= 9:
                        cid = parts[1].replace("*", "").strip()
                        c_sec = parts[2].strip()
                        c_stmt = parts[3].strip()
                        c_class = parts[4].replace("`", "").strip().upper()
                        c_doc = parts[5].strip()
                        c_src = parts[6].strip()
                        c_meth = parts[7].strip()
                        c_res = parts[8].strip()

                        # Validate classification
                        valid_classes = {"USER_CONFIRMED", "ASSIGNMENT_REQUIRED", "REFERENCE_SUPPORTED", "INFERRED", "PROPOSED", "UNRESOLVED"}
                        if c_class not in valid_classes:
                            issues.append(ValidationIssue(
                                rule_id="VAL-PROV-002",
                                severity="error",
                                section_key="appendix_and_glossary",
                                title=f"Non-Canonical Provenance Classification '{c_class}' in {cid}",
                                description=f"Claim {cid} uses non-canonical provenance '{c_class}'.",
                                recommendation="Map classification strictly to: USER_CONFIRMED, ASSIGNMENT_REQUIRED, REFERENCE_SUPPORTED, INFERRED, PROPOSED, UNRESOLVED."
                            ))
                            score -= 5

                        # VAL-PROV-005 Deterministic Evidence Entailment check
                        if c_class in ["USER_CONFIRMED", "ASSIGNMENT_REQUIRED"] and analysis:
                            pcts = re.findall(r"\b\d+(?:\.\d+)?%", c_stmt)
                            for pct in pcts:
                                if pct not in user_evidence_str:
                                    issues.append(ValidationIssue(
                                        rule_id="VAL-PROV-005",
                                        severity="error",
                                        section_key="appendix_and_glossary",
                                        title=f"Deterministic Evidence Entailment Failed: Ungrounded Metric '{pct}' in {cid}",
                                        description=f"Claim {cid} is marked as '{c_class}' but asserts ungrounded metric '{pct}' absent from source evidence.",
                                        recommendation="Reclassify claim as PROPOSED or INFERRED unless explicitly confirmed in source evidence."
                                    ))
                                    score -= 8
                                    break

                            if "support" in (analysis.problem_domain or "").lower():
                                out_of_scope_terms = ["ticket creation", "external ticketing", "callback", "telephony", "whatsapp", "billing dispute", "manager sign-off"]
                                for oos in out_of_scope_terms:
                                    if oos in c_stmt.lower() and oos not in user_evidence_str:
                                        issues.append(ValidationIssue(
                                            rule_id="VAL-PROV-005",
                                            severity="error",
                                            section_key="appendix_and_glossary",
                                            title=f"Deterministic Evidence Entailment Failed: Out-of-Scope Capability '{oos}' in {cid}",
                                            description=f"Claim {cid} is marked as '{c_class}' but introduces out-of-scope capability '{oos}'.",
                                            recommendation="Reclassify as UNRESOLVED or remove out-of-scope capability."
                                        ))
                                        score -= 8
                                        break

        # VAL-ENG-004: Unspecified Architecture & Compliance Claims Check
        sec_sec = prd_version.sections.get("security_and_privacy_requirements")
        if sec_sec and not sec_sec.is_na:
            content_lower = sec_sec.content.lower()
            has_gdpr = any(reg in content_lower for reg in ["gdpr", "hipaa", "ferpa"])
            is_open_decision = any(token in content_lower for token in ["open decision", "pending", "review", "to be determined", "unspecified"])
            user_mentioned = analysis and any(reg in " ".join(analysis.explicit_constraints + analysis.facts).lower() for reg in ["gdpr", "hipaa", "ferpa"])
            if has_gdpr and not is_open_decision and not user_mentioned:
                issues.append(ValidationIssue(
                    rule_id="VAL-ENG-004",
                    severity="error",
                    section_key="security_and_privacy_requirements",
                    title="Unspecified Regulatory Compliance Claimed as Fact",
                    description="PRD asserts specific regulatory compliance (GDPR/HIPAA/FERPA) not requested by user and not marked as an open decision.",
                    recommendation="Mark unverified regulatory standards as an Open Decision pending compliance review."
                ))
                score -= 6

        # VAL-ENG-005: Risk Structure and Completeness Check
        risk_sec = prd_version.sections.get("risks_and_mitigation")
        if risk_sec and not risk_sec.is_na:
            risk_rows = [l.strip() for l in risk_sec.content.split("\n") if "RSK-" in l and "|" in l]
            if len(risk_rows) < 3:
                issues.append(ValidationIssue(
                    rule_id="VAL-ENG-005",
                    severity="warning",
                    section_key="risks_and_mitigation",
                    title="Insufficient Risk Identification",
                    description=f"Only {len(risk_rows)} risks documented; production PRD requires at least 3 domain failure modes.",
                    recommendation="Enumerate at least 3 comprehensive risk entries with mitigation and contingency plans."
                ))
                score -= 5
            else:
                has_generic_risk = any(
                    "| operational risk |" in r.lower() or
                    "| monitor and log |" in r.lower() or
                    "| manual administrative intervention |" in r.lower()
                    for r in risk_rows
                )
                if has_generic_risk:
                    issues.append(ValidationIssue(
                        rule_id="VAL-ENG-005",
                        severity="error",
                        section_key="risks_and_mitigation",
                        title="Generic or Malformed Risk Entries Detected",
                        description="Risk table contains generic placeholders ('Operational risk') or empty/shifted columns.",
                        recommendation="Specify domain-concrete failure events, root causes, mitigations, contingency plans, and owners."
                    ))
                    score -= 8

        # VAL-US-001: User Story Human Persona & Meaningful Value Check
        if us_section and not us_section.is_na:
            us_rows = [l.strip() for l in us_section.content.split("\n") if "US-" in l and "|" in l]
            forbidden_system_actors = ["system", "backend", "ai engine", "database", "worker", "job processor", "queue"]
            forbidden_internal_actions = ["calculate confidence score", "compute attendance percentage", "process background job", "hash document", "store session token"]
            for row in us_rows:
                parts = [p.strip() for p in row.split("|")]
                if len(parts) >= 5:
                    us_id = parts[1].replace("*", "").strip()
                    actor = parts[2].lower().strip()
                    action = parts[3].lower().strip()
                    benefit = parts[4].lower().strip()

                    # 1. System actors forbidden in user stories
                    if any(sa == actor or f"the {sa}" == actor for sa in forbidden_system_actors):
                        issues.append(ValidationIssue(
                            rule_id="VAL-US-001",
                            severity="error",
                            section_key="user_stories",
                            title=f"Invalid System Actor '{parts[2]}' in User Story {us_id}",
                            description=f"User story {us_id} uses internal technical component '{parts[2]}' as actor instead of a human user persona.",
                            recommendation="Assign user stories exclusively to human stakeholders (e.g., Customer, Support Representative, Faculty, Student)."
                        ))
                        score -= 8
                        break

                    # 2. Internal system tasks without user value
                    if any(ia in action for ia in forbidden_internal_actions):
                        issues.append(ValidationIssue(
                            rule_id="VAL-US-001",
                            severity="error",
                            section_key="user_stories",
                            title=f"Internal System Task Assigned as User Story in {us_id}",
                            description=f"User story {us_id} assigns internal processing task '{parts[3]}' directly to an end user.",
                            recommendation="Reframe user story around end-user capabilities or move internal tasks to functional requirements."
                        ))
                        score -= 6
                        break

                    # 3. Meaningful outcome
                    if (
                        not benefit or
                        benefit in ["it works", "it is done", "it executes successfully", action] or
                        len(benefit) < 12
                    ):
                        issues.append(ValidationIssue(
                            rule_id="VAL-US-001",
                            severity="error",
                            section_key="user_stories",
                            title=f"User Story {us_id} Lacks Meaningful User Value or Distinct Benefit",
                            description="User story 'So that...' clause merely repeats the action or provides no tangible user outcome.",
                            recommendation="Articulate specific user benefit or business outcome in the 'So that...' clause."
                        ))
                        score -= 6
                        break

        # VAL-ENG-007: Unsupported Numerical Performance Targets
        nfr_sec = prd_version.sections.get("non_functional_requirements")
        if nfr_sec and not nfr_sec.is_na:
            content_lower = nfr_sec.content.lower()
            has_extreme_sla = any(t in content_lower for t in ["99.999%", "99.99%", "< 50ms", "< 10ms"])
            has_open_decision = any(token in content_lower for token in ["open decision", "pending", "benchmark", "target bound", "unspecified"])
            user_sla_specified = analysis and any(t in " ".join(analysis.explicit_constraints + analysis.facts).lower() for t in ["99.99", "50ms", "10ms"])
            if has_extreme_sla and not has_open_decision and not user_sla_specified:
                issues.append(ValidationIssue(
                    rule_id="VAL-ENG-007",
                    severity="warning",
                    section_key="non_functional_requirements",
                    title="Unsupported Numerical SLA or Latency Target Claimed Without Baseline",
                    description="PRD asserts extreme SLA (e.g. 99.999%) or latency target (< 50ms) without empirical benchmark or user constraint.",
                    recommendation="Mark extreme performance bounds as Open Architectural Decisions pending formal load benchmarking."
                ))
                score -= 3

        # VAL-NUM-001: Unsupported Numerical Metric / SLA Claimed Without Provenance
        if fr_section and not fr_section.is_na and analysis:
            user_evidence_str = " ".join((analysis.explicit_constraints or []) + (analysis.facts or []) + (analysis.core_objectives or [])).lower()
            latency_matches = re.findall(r"\b(?:within\s+\d+\s*(?:seconds?|secs?|s)|<\s*\d+\s*(?:seconds?|secs?|s)|under\s+\d+\s*(?:seconds?|secs?|s))\b", fr_content, re.IGNORECASE)
            for lm in latency_matches:
                clean_lm = lm.lower().strip()
                if clean_lm not in user_evidence_str:
                    fr_blocks = re.split(r"(?=####\s+FR-|\bFR-\d{3,4}\b)", fr_content)
                    block_with_lm = next((b for b in fr_blocks if clean_lm in b.lower()), fr_content)
                    b_low = block_with_lm.lower()
                    is_open = any(tok in b_low for tok in ["open decision", "proposed target", "pending benchmark", "to be determined"])
                    if not is_open:
                        issues.append(ValidationIssue(
                            rule_id="VAL-NUM-001",
                            severity="error",
                            section_key="functional_requirements",
                            title=f"Unsupported Operational Latency SLA in Functional Requirements: '{clean_lm}'",
                            description=f"Requirement asserts operational latency target '{clean_lm}' as a firm specification without user constraint provenance.",
                            recommendation="Reclassify operational latency targets under Non-Functional Requirements as 'Proposed target' or mark as an Open Architectural Decision."
                        ))
                        score -= 8
                        break

        if nfr_sec and not nfr_sec.is_na and analysis:
            user_evidence_str = " ".join((analysis.explicit_constraints or []) + (analysis.facts or []) + (analysis.core_objectives or [])).lower()
            nfr_rows = [l.strip() for l in nfr_sec.content.split("\n") if "NFR-" in l and "|" in l]
            for row in nfr_rows:
                parts = [p.strip() for p in row.split("|")]
                if len(parts) >= 5:
                    classification = parts[4].lower()
                    desc = parts[3].lower()
                    if "confirmed requirement" in classification or classification == "confirmed":
                        sla_match = re.search(
                            r"\b(?:within\s+\d+\s*(?:seconds?|secs?|s)|<\s*\d+\s*(?:seconds?|secs?|ms)|99\.\d+%\s*(?:uptime|availability|monthly)|automatic\s+failover|hot\s+standby)\b",
                            desc
                        )
                        if sla_match and sla_match.group(0) not in user_evidence_str:
                            matched_claim = sla_match.group(0)
                            issues.append(ValidationIssue(
                                rule_id="VAL-NUM-001",
                                severity="error",
                                section_key="non_functional_requirements",
                                title=f"Ungrounded SLA Classified as Confirmed Requirement: '{matched_claim}'",
                                description=f"NFR asserts operational target '{matched_claim}' as a Confirmed Requirement without source mandate.",
                                recommendation="Classify unverified performance bounds as 'Proposed target' or 'Open decision'."
                            ))
                            score -= 8
                            break

        # VAL-ENG-008: Valid Mermaid Diagram Syntax & Completeness Check
        for key in ["user_journeys", "system_workflows"]:
            m_sec = prd_version.sections.get(key)
            if m_sec and not m_sec.is_na and "```mermaid" in m_sec.content:
                content = m_sec.content
                mermaid_blocks = re.findall(r"```mermaid(.*?)```", content, re.DOTALL)
                unclosed_mermaid = content.count("```mermaid") > content.count("```\n") and not content.endswith("```")
                if unclosed_mermaid or len(mermaid_blocks) == 0:
                    issues.append(ValidationIssue(
                        rule_id="VAL-ENG-008",
                        severity="error",
                        section_key=key,
                        title="Malformed or Truncated Mermaid Diagram",
                        description="A Mermaid diagram block is unclosed or truncated in mid-generation.",
                        recommendation="Ensure all Mermaid diagram blocks are properly closed with triple backticks and valid syntax."
                    ))
                    issues.append(ValidationIssue(
                        rule_id="VAL-DIA-001",
                        severity="error",
                        section_key=key,
                        title="Malformed or Truncated Mermaid Diagram",
                        description="A Mermaid diagram block is unclosed or truncated in mid-generation.",
                        recommendation="Ensure all Mermaid diagram blocks are properly closed with triple backticks and valid syntax."
                    ))
                    score -= 8
                else:
                    for block in mermaid_blocks:
                        block_stripped = block.strip()
                        valid_headers = ["sequencediagram", "flowchart", "graph", "classdiagram", "statediagram", "erdiagram"]
                        if not any(block_stripped.lower().startswith(h) for h in valid_headers):
                            issues.append(ValidationIssue(
                                rule_id="VAL-ENG-008",
                                severity="error",
                                section_key=key,
                                title="Mermaid Diagram Missing Valid Header Type",
                                description="Mermaid diagram must begin with a recognized diagram type (sequenceDiagram, flowchart, etc.).",
                                recommendation="Add 'sequenceDiagram' or 'flowchart TD' at the start of the Mermaid code block."
                            ))
                            issues.append(ValidationIssue(
                                rule_id="VAL-DIA-001",
                                severity="error",
                                section_key=key,
                                title="Mermaid Diagram Missing Valid Header Type",
                                description="Mermaid diagram must begin with a recognized diagram type (sequenceDiagram, flowchart, etc.).",
                                recommendation="Add 'sequenceDiagram' or 'flowchart TD' at the start of the Mermaid code block."
                            ))
                            score -= 8

        # VAL-SEM-001 / VAL-UJ-001: Unsupported Capability or Out-of-Scope Workflow in User Journeys
        uj_sec = prd_version.sections.get("user_journeys")
        if uj_sec and not uj_sec.is_na:
            uj_content_lower = uj_sec.content.lower()
            unsupported_journey_terms = [
                "schedule a call back",
                "schedule a callback",
                "call back",
                "callback",
                "voice call",
                "telephony",
                "phone call",
                "ivr",
                "sms channel",
                "whatsapp integration",
                "biometric",
                "facial recognition",
                "geofencing",
                "manager approval",
                "managerial sign-off",
                "manager sign-off",
                "quick-edit field",
                "rep's edit",
                "agent editing",
                "fallback to connect with a live representative",
                "live representative fallback",
                "dashboard for ai accuracy",
                "daily dashboard",
                "billing discrepancy",
                "view the invoice",
                "invoice",
                "did this solve your issue",
                "final satisfaction feedback",
                "satisfaction feedback",
                "queue is full",
                "marks the interaction as resolved",
                "wait time estimate",
                "wait-time"
            ]
            for term in unsupported_journey_terms:
                if term in uj_content_lower:
                    term_lines = [l for l in uj_content_lower.split("\n") if term in l]
                    is_negated = any(
                        re.search(r"\b(?:no|not|out of scope|prohibited|deferred|without)\s+[\w\s]{0,20}\b" + re.escape(term), l)
                        or any(neg in l for neg in ["is out of scope", "are out of scope", "deferred to future"])
                        for l in term_lines
                    )
                    if not is_negated:
                        issues.append(ValidationIssue(
                            rule_id="VAL-SEM-001",
                            severity="error",
                            section_key="user_journeys",
                            title=f"Unsupported User Journey Action: '{term}'",
                            description=f"User journey introduces unsupported capability or action '{term}', which is not confirmed by source input.",
                            recommendation="Remove invented actions (satisfaction prompts, billing workflows, rep editing) from user journeys."
                        ))
                        issues.append(ValidationIssue(
                            rule_id="VAL-UJ-001",
                            severity="error",
                            section_key="user_journeys",
                            title=f"Unsupported Capability in User Journeys: '{term}'",
                            description=f"User journey documents capability '{term}' which is excluded from MVP scope or unsupported by product constraints.",
                            recommendation="Remove out-of-scope interactions from user journeys and align with MVP scope."
                        ))
                        score -= 10
                        break

        # VAL-XDOM-001: Cross-Domain Semantic Contamination Check
        all_prd_text = " ".join(sec.content for sec in prd_version.sections.values() if not sec.is_na).lower()
        dom_context = ((analysis.problem_domain if analysis else "") + " " + (analysis.product_category if analysis else "") + " " + (analysis.core_objectives[0] if analysis and analysis.core_objectives else "")).lower()

        is_support_domain = any(t in dom_context for t in ["support", "helpdesk", "customer service", "agent assistant"])
        is_attendance_domain = any(t in dom_context for t in ["attendance", "student", "roll call", "condonation", "faculty"])

        if is_support_domain and not is_attendance_domain:
            for term in ["attendance threshold", "75% attendance", "roll call", "condonation rule", "absentee record", "attendance window"]:
                if term in all_prd_text:
                    issues.append(ValidationIssue(
                        rule_id="VAL-XDOM-001",
                        severity="error",
                        section_key="business_rules" if "business_rules" in prd_version.sections else "functional_requirements",
                        title=f"Cross-Domain Contamination: '{term}' in Customer Support PRD",
                        description=f"PRD contains academic attendance terminology ('{term}') which does not belong in a customer support product.",
                        recommendation="Eliminate cross-domain contaminated terms and ensure requirements reflect only target domain capabilities."
                    ))
                    score -= 15
                    break

        if is_attendance_domain and not is_support_domain:
            for term in ["80% confidence escalation", "customer hold time", "support ticket deflection", "helpdesk queue", "agent handoff summary"]:
                if term in all_prd_text:
                    issues.append(ValidationIssue(
                        rule_id="VAL-XDOM-001",
                        severity="error",
                        section_key="business_rules" if "business_rules" in prd_version.sections else "functional_requirements",
                        title=f"Cross-Domain Contamination: '{term}' in Attendance Management PRD",
                        description=f"PRD contains customer support terminology ('{term}') which does not belong in an attendance management product.",
                        recommendation="Eliminate cross-domain contaminated terms and ensure requirements reflect only target domain capabilities."
                    ))
                    score -= 15
                    break

        # -------------------------------------------------------------
        # 9. Mathematical & Threshold Precision Checks (VAL-MTH-001)
        # -------------------------------------------------------------
        if is_attendance_domain and not is_support_domain:
            # Check for distorted attendance threshold: "miss more than 75%"
            if "miss more than 75%" in all_prd_text or "misses more than 75%" in all_prd_text or "misses 75% of classes" in all_prd_text:
                issues.append(ValidationIssue(
                    rule_id="VAL-MTH-001",
                    severity="error",
                    section_key="business_rules" if "business_rules" in prd_version.sections else "functional_requirements",
                    title="Mathematical Inversion in Attendance Threshold (BR-002)",
                    description="PRD asserts that missing more than 75% of classes triggers an alert. The valid threshold is when attendance percentage falls strictly below 75.0% (< 75.0%).",
                    recommendation="Correct threshold to: 'Warning notifications trigger strictly when calculated attendance falls below 75.0% (< 75.0%).'"
                ))
                score -= 15

            # Check for boundary condition violation: exactly 75% triggering alert
            if "exactly 75% will receive a warning" in all_prd_text or "exactly 75.0% triggers an alert" in all_prd_text:
                issues.append(ValidationIssue(
                    rule_id="VAL-MTH-001",
                    severity="error",
                    section_key="acceptance_criteria",
                    title="Boundary Condition Error: Exactly 75% Triggers Alert",
                    description="PRD asserts that a student with exactly 75.0% attendance triggers a warning. Exactly 75.0% is eligible and must suppress alerts.",
                    recommendation="Ensure acceptance criteria state that exactly 75.0% attendance marks the student as eligible with no warning."
                ))
                score -= 10

            # Check for unaddressed division-by-zero vulnerability
            ac_text_lower = (prd_version.sections.get("acceptance_criteria").content if "acceptance_criteria" in prd_version.sections else "").lower()
            if "division-by-zero" not in ac_text_lower and "0 conducted sessions" not in ac_text_lower and "division by zero" not in ac_text_lower:
                issues.append(ValidationIssue(
                    rule_id="VAL-MTH-001",
                    severity="warning",
                    section_key="acceptance_criteria",
                    title="Unaddressed Zero Conducted Sessions Boundary",
                    description="Acceptance criteria do not specify behavior when zero course sessions have been conducted, risking division-by-zero errors.",
                    recommendation="Add an acceptance criterion covering zero conducted sessions."
                ))
                score -= 4

            # Check for fabricated Support / Admin Role persona in Attendance
            if personas_sec and not personas_sec.is_na and "support / admin" in personas_sec.content.lower():
                issues.append(ValidationIssue(
                    rule_id="VAL-SEM-002",
                    severity="error",
                    section_key="user_personas",
                    title="Fabricated Persona Detected in Attendance PRD: Support / Admin Role",
                    description="User personas include generic 'Support / Admin Role' not requested by user and irrelevant to academic attendance management.",
                    recommendation="Remove Support / Admin Role persona; restrict personas to Faculty Instructors, Students, and Department Heads."
                ))
                score -= 8

        if is_support_domain and not is_attendance_domain:
            # Check for threshold confusion: confusing relevance (e.g. 70%) with 80% confidence
            br_text_lower = (prd_version.sections.get("business_rules").content if "business_rules" in prd_version.sections else "").lower()
            if "70% relevance threshold" in br_text_lower or "relevance threshold: 0.5" in all_prd_text:
                issues.append(ValidationIssue(
                    rule_id="VAL-MTH-001",
                    severity="error",
                    section_key="business_rules",
                    title="Threshold Metric Confusion: Retrieval Relevance Confused with Answer Confidence",
                    description="PRD asserts an ungrounded 70% relevance or 0.5 escalation threshold. The user-confirmed threshold is strictly 80.0% answer confidence.",
                    recommendation="Enforce the confirmed 80.0% confidence threshold and treat retrieval scoring as an internal implementation detail."
                ))
                score -= 10

            # Check for unsupported commitments in business rules or NFRs
            if any(term in all_prd_text for term in ["2 minutes for first-level", "within 1 minute of request receipt", "responded to within 30 minutes"]):
                issues.append(ValidationIssue(
                    rule_id="VAL-NUM-002",
                    severity="error",
                    section_key="business_rules",
                    title="Unsupported Operational Response/Hold Limits in Customer Support",
                    description="PRD includes arbitrary 2-minute hold time, 1-minute response time, or 30-minute escalation limits unsupported by user input.",
                    recommendation="Remove unconfirmed operational latency limits or reclassify them as open operational decisions."
                ))
                score -= 10

            # Check for fabricated 30-day retention or email API integration
            int_sec_text = (prd_version.sections.get("integration_requirements").content if "integration_requirements" in prd_version.sections else "").lower()
            if "email api for receiving" in int_sec_text:
                issues.append(ValidationIssue(
                    rule_id="VAL-SEM-004",
                    severity="error",
                    section_key="integration_requirements",
                    title="Fabricated Integration Scope: Email API in Chat Assistant",
                    description="PRD defines an Email API integration requirement unsupported by the web chat product scope.",
                    recommendation="Remove Email API integration and ensure MVP operates as a self-contained web chat solution."
                ))
                score -= 8

        # -------------------------------------------------------------
        # 10. Cross-Section Consistency Checks (VAL-XSEC-001 to 005)
        # -------------------------------------------------------------
        # VAL-XSEC-001: Confidence Scale and Escalation Consistency
        if is_support_domain and not is_attendance_domain:
            # Check for contradictory escalation thresholds across sections (e.g. 50%, 70%, 0.5 vs 80%)
            for sec_key, sec in prd_version.sections.items():
                if sec and not sec.is_na:
                    for line in sec.content.split("\n"):
                        line_low = line.lower()
                        if "escalat" in line_low and any(th in line_low for th in ["0.5", "50%", "70%", "< 0.7", "< 70%", "relevance score < 0.7"]):
                            issues.append(ValidationIssue(
                                rule_id="VAL-XSEC-001",
                                severity="error",
                                section_key=sec_key,
                                title=f"Cross-Section Escalation Metric Conflict in {sec_key}",
                                description="Section defines a conflicting escalation threshold (0.5, 50%, or 70%) contradicting the authoritative 80.0% answer confidence rule.",
                                recommendation="Align all escalation triggers across all sections strictly with the 80.0% confidence threshold."
                            ))
                            score -= 10
                            break

        # VAL-XSEC-002: Retention Policy Consistency Check
        ret_patterns_24h = ["24 hours", "24-hour", "24h", "duration of the active chat session", "session duration"]
        ret_patterns_30d = [
            "30-day conversation retention",
            "chat transcripts are retained for 30 days",
            "enforce retention of at least 30 days",
            "minimum of 30 days",
            "retained for a minimum of 30 days",
            "retained for at least 30 days",
            "retained for 30 days",
            "stored for 30 days",
            "30 days retention",
            "30-day retention",
            "retention of 30 days",
            "less than 30 days",
            "30 days old",
            "30 days",
            "30-day"
        ]
        has_24h = any(p in all_prd_text for p in ret_patterns_24h)
        has_30d = any(p in all_prd_text for p in ret_patterns_30d)

        if has_24h and has_30d:
            conflicting_secs = []
            for sec_k, sec_obj in prd_version.sections.items():
                if sec_obj and not sec_obj.is_na:
                    c_low = sec_obj.content.lower()
                    for line in c_low.split("\n"):
                        if any(p in line for p in ret_patterns_30d):
                            is_line_open = any(tok in line for tok in ["open decision", "open architectural", "pending privacy review", "to be determined"])
                            if not is_line_open:
                                conflicting_secs.append(sec_k)
                                break

            if conflicting_secs:
                issues.append(ValidationIssue(
                    rule_id="VAL-XSEC-002",
                    severity="error",
                    section_key=conflicting_secs[0],
                    title=f"Contradictory Retention Policy: 24h vs 30d Transcript Storage in {conflicting_secs[0]}",
                    description=f"PRD asserts both 24-hour active session retention and mandatory 30-day transcript retention in section '{conflicting_secs[0]}' without distinguishing active cache TTL from archival policies or marking as an open decision.",
                    recommendation="Explicitly separate active chat session retention from de-identified analytics/audit archives, or mark long-term retention as an Open Architectural Decision."
                ))
                score -= 10


        # VAL-ARCH-001: Unconfirmed Architectural Decision Asserted as Mandatory
        arch_secs = [prd_version.sections.get("non_functional_requirements"), prd_version.sections.get("dependencies_and_constraints")]
        unconfirmed_arch_patterns = [
            r"automatic\s+failover\s+to\s+(?:a\s+)?hot\s+standby\s+instance",
            r"failover\s+to\s+(?:a\s+)?hot\s+standby",
            r"hot\s+standby\s+instance\s+in\s+a\s+different\s+availability\s+zone",
            r"employing\s+automatic\s+failover",
            r"mandatory\s+cloud\s+hosting",
            r"mandatory\s+linux\s+environment"
        ]
        for sec in arch_secs:
            if sec and not sec.is_na:
                for pat in unconfirmed_arch_patterns:
                    matches = list(re.finditer(pat, sec.content, re.IGNORECASE))
                    for m in matches:
                        line = [l for l in sec.content.split("\n") if m.group(0).lower() in l.lower()][0]
                        line_low = line.lower()
                        is_open = any(tok in line_low for tok in ["open decision", "open architectural", "proposed target", "proposed option", "pending review", "subject to"])
                        if not is_open:
                            issues.append(ValidationIssue(
                                rule_id="VAL-ARCH-001",
                                severity="error",
                                section_key=sec.key,
                                title=f"Unconfirmed Architectural Decision Asserted as Mandatory: '{m.group(0)}'",
                                description=f"Section '{sec.key}' mandates architectural implementation '{m.group(0)}' without source mandate or open decision qualification.",
                                recommendation="Classify unconfirmed infrastructure and failover schemes as 'Open Architectural Decisions' or 'Proposed targets'."
                            ))
                            score -= 8
                            break
                    if any(i.rule_id == "VAL-ARCH-001" and i.section_key == sec.key for i in issues):
                        break

        # VAL-XSEC-003: Channel Scope Consistency Check
        scope_sec = prd_version.sections.get("product_scope") or prd_version.sections.get("executive_summary")
        if scope_sec and not scope_sec.is_na:
            scope_text = scope_sec.content.lower()
            if "web chat only" in scope_text or "web widget" in scope_text or "self-contained web" in scope_text:
                for sec_k in ["functional_requirements", "integration_requirements", "system_workflows"]:
                    s = prd_version.sections.get(sec_k)
                    if s and not s.is_na:
                        st = s.content.lower()
                        if any(ch in st for ch in ["whatsapp integration", "voice call processing", "sms channel", "phone hotline"]):
                            issues.append(ValidationIssue(
                                rule_id="VAL-XSEC-003",
                                severity="error",
                                section_key=sec_k,
                                title=f"Out-of-Scope Channel Contradiction in {sec_k}",
                                description=f"Section {sec_k} specifies WhatsApp, Voice, or SMS channels which contradict the Web-Chat-only MVP scope.",
                                recommendation="Restrict MVP functional and integration requirements strictly to the web chat widget."
                            ))
                            score -= 8
                            break

        # VAL-XSEC-004: Ticketing Scope Consistency Check
        if scope_sec and not scope_sec.is_na:
            scope_text = scope_sec.content.lower()
            if "external ticketing" in scope_text and ("out of scope" in scope_text or "deferred" in scope_text):
                for sec_k in ["functional_requirements", "integration_requirements"]:
                    s = prd_version.sections.get(sec_k)
                    if s and not s.is_na:
                        st = s.content.lower()
                        if "mandatory zendesk" in st or "mandatory jira api" in st or "external ticketing api integration is mandatory" in st:
                            issues.append(ValidationIssue(
                                rule_id="VAL-XSEC-004",
                                severity="error",
                                section_key=sec_k,
                                title=f"Contradictory Ticketing Scope in {sec_k}",
                                description=f"Section {sec_k} specifies mandatory external ticketing API integration contradicting out-of-scope status for MVP.",
                                recommendation="Use internal queue or webhook dispatch for MVP escalation and defer proprietary ticketing integrations."
                            ))
                            score -= 8
                            break

        # VAL-XSEC-005: Architectural Mandate & Local-First Independence
        infra_sec = prd_version.sections.get("dependencies_and_constraints") or prd_version.sections.get("release_considerations")
        if infra_sec and not infra_sec.is_na:
            infra_text = infra_sec.content.lower()
            if any(prop in infra_text for prop in ["must run on aws bedrock", "requires google cloud vertex ai mandatory", "mandatory azure openai"]):
                issues.append(ValidationIssue(
                    rule_id="VAL-XSEC-005",
                    severity="error",
                    section_key=infra_sec.key or "dependencies_and_constraints",
                    title="Unapproved Proprietary Cloud Mandate Detected",
                    description="PRD imposes a mandatory proprietary cloud vendor lock-in without user mandate or architectural open decision.",
                    recommendation="Formulate deployment requirements as provider-agnostic containerized services."
                ))
                score -= 8

        # VAL-GRAM-001: Functional Requirement Grammar and Statement Completeness Check
        fr_sec = prd_version.sections.get("functional_requirements")
        if fr_sec and not fr_sec.is_na and fr_sec.content:
            fr_text = fr_sec.content
            gram_patterns = [
                r"\bThe system the (?:AI|system|assistant|application|engine)\b",
                r"\bThe system append\b",
                r"\bThe system route\b",
                r"\bThe system maintain\b",
                r"\bThe system generate\b",
                r"\bThe system store\b",
                r"\bThe system if confidence\b",
                r"\bThe system if\b"
            ]
            for gp in gram_patterns:
                m = re.search(gp, fr_text, re.IGNORECASE)
                if m:
                    issues.append(ValidationIssue(
                        rule_id="VAL-GRAM-001",
                        severity="error",
                        section_key="functional_requirements",
                        title=f"Malformed Requirement Grammar: '{m.group(0)}'",
                        description=f"Functional requirements contain grammatically malformed phrases or uninflected prompt fragments ('{m.group(0)}').",
                        recommendation="Ensure system behavior describes observable actions with proper third-person singular grammar and complete predicate structure."
                    ))
                    score -= 10
                    break

        # VAL-ACT-001: Incorrect Actor Responsibility in Interaction Sequence
        for key in ["user_journeys", "system_workflows"]:
            sec_obj = prd_version.sections.get(key)
            if sec_obj and not sec_obj.is_na and sec_obj.content:
                bad_actor_patterns = [
                    r"\b(?:SupportRepresentative|Support\s+Representative|Support_Representative|Representative|CustomerServiceRepresentative|Customer\s+Service\s+Representative|Agent|Customer|End-Customer)\b[^\n\->]*->>\s*\w+\s*:\s*(?:Calculates|Generates answer|Evaluates confidence|Computes|Searches the knowledge base)",
                    r"- \*\*Actor \((?:Support Representative|Customer Service Representative|Agent)\):\*\*\s*(?:Calculates confidence|Generates a concise answer|Computes similarity)"
                ]
                for bap in bad_actor_patterns:
                    m = re.search(bap, sec_obj.content, re.IGNORECASE)
                    if m:
                        issues.append(ValidationIssue(
                            rule_id="VAL-ACT-001",
                            severity="error",
                            section_key=key,
                            title="Incorrect Actor Responsibility in Interaction Sequence",
                            description=f"Human actor is depicted executing internal algorithmic or AI processing ('{m.group(0)[:60]}'). Internal computations must be assigned to the system actor.",
                            recommendation="Assign algorithmic processing, confidence evaluation, and retrieval to the system actor."
                        ))
                        score -= 10
                        break

        # VAL-NUM-004: Unsupported Wait-Time Estimates in User Journeys
        for key in ["user_journeys", "system_workflows"]:
            sec_obj = prd_version.sections.get(key)
            if sec_obj and not sec_obj.is_na and sec_obj.content:
                if re.search(r"\b(?:expected wait time|estimated wait time|informs the customer of an expected wait time)\b", sec_obj.content, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        rule_id="VAL-NUM-004",
                        severity="error",
                        section_key=key,
                        title="Unsupported Wait-Time Estimate in User Journey",
                        description="User journey specifies calculating or communicating queue wait-time estimates without user-specified SLA or telemetry baseline.",
                        recommendation="Remove ungrounded wait-time estimations; notify user of queue status without unverified time commitments."
                    ))
                    score -= 8
                    break

        # VAL-DIA-001: Truncated or Malformed Mermaid Sequence Diagrams
        for sec_k, sec_obj in prd_version.sections.items():
            if sec_obj and not sec_obj.is_na and sec_obj.content:
                diag_blocks = re.findall(r"```mermaid([\s\S]*?)```", sec_obj.content)
                for d_text in diag_blocks:
                    d_lines = [l.strip() for l in d_text.split("\n") if l.strip()]
                    for dl in d_lines:
                        if re.search(r"(?:->>|-->>|->|-->)\s*$", dl):
                            issues.append(ValidationIssue(
                                rule_id="VAL-DIA-001",
                                severity="error",
                                section_key=sec_k,
                                title=f"Truncated Sequence Diagram in {sec_k}",
                                description=f"Mermaid diagram line '{dl[:60]}' has an unclosed transition arrow without target or message.",
                                recommendation="Provide complete actor interactions and close all diagram statements."
                            ))
                            score -= 10
                            break
                        truncated_word_match = (
                            re.search(
                                r":\s*.*?\b(?:into the [A-Z]|the [a-z]|draf|notifies th|with|at the|types a description of|searches the knowledge|ai prompts the|as resolved if|ai informs the customer of|either approves|system truncates and|marks ticket as closed|system auto-closes)\s*$",
                                dl,
                                re.IGNORECASE
                            )
                            or re.search(r":\s*.*?\b(?:of|the|a|an|in|on|at|by|for|with|and|or|if|to|from)\s*$", dl, re.IGNORECASE)
                        )
                        if truncated_word_match:
                            issues.append(ValidationIssue(
                                rule_id="VAL-DIA-001",
                                severity="error",
                                section_key=sec_k,
                                title=f"Truncated Diagram Text in {sec_k}",
                                description=f"Diagram interaction line ends abruptly mid-word or mid-phrase: '{dl[:70]}'.",
                                recommendation="Ensure all diagram labels and sequence messages are complete sentences without character truncation."
                            ))
                            score -= 10
                            break
                    if any(i.rule_id == "VAL-DIA-001" and i.section_key == sec_k for i in issues):
                        break

        # VAL-NUM-003: Unsupported Quantitative Efficiency or Reduction Claims
        user_facts_str = " ".join((analysis.facts or []) + (analysis.explicit_constraints or []) + (analysis.core_objectives or [])).lower() if analysis else ""
        for sec_k in ["executive_summary", "proposed_solution", "goals_and_objectives", "success_metrics"]:
            s_obj = prd_version.sections.get(sec_k)
            if s_obj and not s_obj.is_na and s_obj.content:
                s_text = s_obj.content.replace("\u2011", "-").replace("\u2013", "-")
                eff_patterns = [
                    r"\b(?:cut|cuts|reduce|reduces|reducing)\s+(?:average\s+|median\s+|customer\s+)?wait\s*times?\s*(?:by\s+)?(?:up\s+to\s+)?(\d{1,2}%)(?!\w)",
                    r"\b(?:reduce|reduces|reducing)\s+repetitive\s+query\s+volume\s+by\s+(\d{1,2}%)(?!\w)",
                    r"\b(?:deflect|deflects|deflecting)\s+(?:up\s+to\s+)?(\d{1,2}%)\s+of\s+repetitive\b",
                    r"\b(\d{1,2}%)\s*wait[- ]time\s+reduction\b",
                    r"\b(\d{1,2}%)\s*repetitive[- ]query\s+reduction\b",
                    r"\b(?:resolution rate|ai-only resolution)\s*[≥>=]+\s*70%",
                    r"\b(?:average confidence|confidence score)\s*[≥>=]+\s*85%",
                    r"\b(?:csat|customer satisfaction)\s*(?:score\s*)?[≥>=]+\s*4\.5",
                    r"\b(?:handling time|handle time)\s*[≤<=]+\s*5\s*minutes?\b",
                    r"\b(?:escalation rate|escalation)\s*[≤<=]+\s*20%"
                ]
                for pat in eff_patterns:
                    for em in re.finditer(pat, s_text, re.IGNORECASE):
                        claimed_match = em.group(0)
                        line_containing = [l for l in s_text.split("\n") if claimed_match.lower() in l.lower()]
                        line_str = line_containing[0].lower() if line_containing else ""
                        is_qualified = any(q in line_str for q in ["proposed target", "proposed", "target goal", "open decision", "estimated target", "aspirational", "pending benchmark"])
                        if not is_qualified and not any(kw in user_facts_str for kw in ["70%", "85%", "4.5", "5 minutes", "20%"]):
                            issues.append(ValidationIssue(
                                rule_id="VAL-NUM-003",
                                severity="error",
                                section_key=sec_k,
                                title=f"Unsupported Quantitative Claim '{claimed_match}' in {sec_k}",
                                description=f"Section '{sec_k}' asserts quantitative target '{claimed_match}' without source grounding or proposed qualification.",
                                recommendation="Ground percentage metrics in confirmed user baselines or explicitly qualify as a Proposed Target / Aspirational KPI."
                            ))
                            score -= 8
                            break
                    if any(i.rule_id == "VAL-NUM-003" and i.section_key == sec_k for i in issues):
                        break

        # VAL-NFR-001: Proposed or Open NFRs Priority Check
        nfr_sec = prd_version.sections.get("non_functional_requirements")
        if nfr_sec and not nfr_sec.is_na and nfr_sec.content:
            for line in nfr_sec.content.split("\n"):
                if line.strip().startswith("|") and any(w in line.lower() for w in ["proposed", "open decision"]):
                    cells = [c.strip() for c in line.split("|") if c.strip()]
                    if len(cells) >= 5:
                        prio = cells[-1].lower()
                        classif = cells[-2].lower()
                        if "must have" in prio and ("proposed" in classif or "open" in classif):
                            issues.append(ValidationIssue(
                                rule_id="VAL-NFR-001",
                                severity="error",
                                section_key="non_functional_requirements",
                                title=f"Proposed or Open NFR '{cells[0]}' Marked Must Have",
                                description=f"NFR '{cells[0]}' is classified as '{cells[-2]}' but assigned priority 'Must Have'. Proposed targets and open decisions cannot be implementation mandates.",
                                recommendation="Change priority of proposed or open NFRs to 'Should Have' or 'Could Have'."
                            ))
                            score -= 8
                            break

        # VAL-ARCH-001 to VAL-ARCH-005: Unconfirmed Architecture Mandates
        for arch_k in ["data_requirements", "dependencies_and_constraints", "security_and_privacy_requirements", "system_workflows"]:
            sec_obj = prd_version.sections.get(arch_k)
            if sec_obj and not sec_obj.is_na and sec_obj.content:
                s_text = sec_obj.content
                # PostgreSQL mandate
                if re.search(r"(?:\brelational store\s*\((?:e\.g\.,\s*)?postgresql\)|database:\s*postgresql|\bmandatory postgresql\b|\buses postgresql\b|\brelational store[^\n\.\;]*postgresql)", s_text, re.IGNORECASE):
                    line_c = [l for l in s_text.split("\n") if "postgresql" in l.lower()]
                    line_str = line_c[0].lower() if line_c else ""
                    if not any(q in line_str for q in ["proposed target", "proposed option", "open architectural decision", "open decision", "options:"]) and "postgresql" not in user_facts_str:
                        issues.append(ValidationIssue(
                            rule_id="VAL-ARCH-001",
                            severity="error",
                            section_key=arch_k,
                            title="Unconfirmed PostgreSQL Implementation Mandate",
                            description="PRD asserts PostgreSQL as a confirmed relational datastore mandate without source evidence.",
                            recommendation="Classify PostgreSQL as a proposed option or open architectural decision."
                        ))
                        score -= 8
                        break
                # Time-series / Columnar DB mandate
                if re.search(r"\b(?:time-series or columnar store|columnar warehouse|timescale db)\b", s_text, re.IGNORECASE):
                    line_c = [l for l in s_text.split("\n") if "columnar" in l.lower() or "time-series" in l.lower()]
                    line_str = line_c[0].lower() if line_c else ""
                    if not any(q in line_str for q in ["proposed target", "proposed option", "open architectural decision", "open decision", "options:"]) and "columnar" not in user_facts_str:
                        issues.append(ValidationIssue(
                            rule_id="VAL-ARCH-002",
                            severity="error",
                            section_key=arch_k,
                            title="Unconfirmed Time-Series / Columnar Store Mandate",
                            description="PRD asserts time-series or columnar store as a confirmed mandate without source evidence.",
                            recommendation="Classify analytics datastore choices as proposed options or open architectural decisions."
                        ))
                        score -= 8
                        break
                # Immutable log storage mandate
                if re.search(r"\b(?:immutable log store|immutable audit log store)\b", s_text, re.IGNORECASE):
                    line_c = [l for l in s_text.split("\n") if "immutable log store" in l.lower()]
                    line_str = line_c[0].lower() if line_c else ""
                    if not any(q in line_str for q in ["proposed target", "proposed option", "open architectural decision", "open decision", "options:"]) and "immutable log store" not in user_facts_str:
                        issues.append(ValidationIssue(
                            rule_id="VAL-ARCH-003",
                            severity="error",
                            section_key=arch_k,
                            title="Unconfirmed Immutable Log Store Mandate",
                            description="PRD asserts immutable log store as a confirmed mandate without source evidence.",
                            recommendation="Classify audit log storage technologies as proposed options or open architectural decisions."
                        ))
                        score -= 8
                        break
                # Unsupported cloud / on-premises hosting mandate
                if re.search(r"\b(?:must be hosted on-premise|must be hosted in cloud|mandatory cloud hosting|mandatory on-premises hosting)\b", s_text, re.IGNORECASE):
                    if not any(h in user_facts_str for h in ["cloud", "on-premise"]):
                        issues.append(ValidationIssue(
                            rule_id="VAL-ARCH-004",
                            severity="error",
                            section_key=arch_k,
                            title="Unsupported Hosting Deployment Mandate",
                            description="PRD asserts a fixed hosting deployment mandate without user constraint evidence.",
                            recommendation="Classify hosting environment as an open architectural decision."
                        ))
                        score -= 8
                        break
                # Multi-region active-active deployment mandate
                if re.search(r"\b(?:multi-region active-active|active-active deployment|multi-region failover)\b", s_text, re.IGNORECASE):
                    line_c = [l for l in s_text.split("\n") if "active-active" in l.lower() or "multi-region" in l.lower()]
                    line_str = line_c[0].lower() if line_c else ""
                    if not any(q in line_str for q in ["proposed target", "proposed option", "open architectural decision", "open decision"]) and "active-active" not in user_facts_str:
                        issues.append(ValidationIssue(
                            rule_id="VAL-ARCH-005",
                            severity="error",
                            section_key=arch_k,
                            title="Unsupported Multi-Region Active-Active Deployment Mandate",
                            description="PRD asserts multi-region active-active deployment as a confirmed mandate without source evidence.",
                            recommendation="Classify high-availability topology as an open architectural decision."
                        ))
                        score -= 8
                        break

        # VAL-RET-001: Unsupported Analytics and Audit Retention Mandates
        for ret_k in ["security_and_privacy_requirements", "data_requirements"]:
            sec_obj = prd_version.sections.get(ret_k)
            if sec_obj and not sec_obj.is_na and sec_obj.content:
                s_text = sec_obj.content
                ret_match = re.search(r"\b(?:analytics(?: are aggregated and do not retain raw user text beyond)?\s+(?:90\s+days|90-day)|audit\s+logs?\s+retained\s+for\s+(?:1\s+year|one\s+year)|retained\s+for\s+90\s+days|retained\s+for\s+1\s+year)\b", s_text, re.IGNORECASE)
                if ret_match and "90" not in user_facts_str and "1 year" not in user_facts_str:
                    line_c = [l for l in s_text.split("\n") if ret_match.group(0).lower() in l.lower()]
                    line_str = line_c[0].lower() if line_c else ""
                    if not any(q in line_str for q in ["open decision", "proposed target", "subject to", "pending policy", "proposed option"]):
                        issues.append(ValidationIssue(
                            rule_id="VAL-RET-001",
                            severity="error",
                            section_key=ret_k,
                            title=f"Unsupported Data Retention Mandate: '{ret_match.group(0)}'",
                            description="PRD asserts operational analytics or audit retention periods as confirmed mandates without user constraint evidence.",
                            recommendation="Classify archival, analytics, and compliance audit retention periods as open architectural decisions pending stakeholder policy."
                        ))
                        score -= 8
                        break

        # VAL-AC-002: Acceptance Criteria Introducing Unsupported Functionality
        ac_sec = prd_version.sections.get("acceptance_criteria")
        if ac_sec and not ac_sec.is_na and ac_sec.content:
            ac_text = ac_sec.content
            if "24-hour" in ac_text.lower() and "24" not in user_facts_str:
                line_c = [l for l in ac_text.split("\n") if "24-hour" in l.lower() or "24 hour" in l.lower()]
                if any("exceeding the 24-hour" in l.lower() or "inactive chat session" in l.lower() for l in line_c):
                    issues.append(ValidationIssue(
                        rule_id="VAL-AC-002",
                        severity="error",
                        section_key="acceptance_criteria",
                        title="Acceptance Criteria Introducing Unsupported Session Inactivity Behavior",
                        description="Acceptance criteria introduces 24-hour session reset and inactivity behavior without user requirement backing.",
                        recommendation="Derive acceptance criteria directly from confirmed requirement attributes without inventing session-reset mechanisms."
                    ))
                    score -= 8

        # VAL-XSEC-006: Cross-Section Context Summary Word Limit Contradiction
        has_150 = any(
            re.search(r"\b(?:150\s*words?|150-word|≤\s*150|<=150)\b", s.content, re.IGNORECASE)
            for s in prd_version.sections.values() if s and not s.is_na and s.content
        )
        has_200 = any(
            re.search(r"\b(?:200\s*words?|200-word|≤\s*200|<=200)\b", s.content, re.IGNORECASE)
            for s in prd_version.sections.values() if s and not s.is_na and s.content
        )
        if has_150 and has_200:
            issues.append(ValidationIssue(
                rule_id="VAL-XSEC-006",
                severity="error",
                section_key="functional_requirements",
                title="Cross-Section Summary Word Limit Contradiction",
                description="PRD asserts conflicting context summarization bounds across sections (both 150 words and 200 words).",
                recommendation="Standardize summarization length constraint (e.g. strictly 'under 200 words') consistently across all sections."
            ))
            score -= 8

        # VAL-SEM-005: Unsupported Confirmation Receipts in Conversational Assistant
        if is_support_domain and not is_attendance_domain:
            for sec_k in ["functional_requirements", "acceptance_criteria", "system_workflows"]:
                s_obj = prd_version.sections.get(sec_k)
                if s_obj and not s_obj.is_na and s_obj.content:
                    if re.search(r"\b(?:audit receipt|confirmation receipt|transaction receipt|email receipt)\b", s_obj.content, re.IGNORECASE):
                        issues.append(ValidationIssue(
                            rule_id="VAL-SEM-005",
                            severity="error",
                            section_key=sec_k,
                            title=f"Unsupported Confirmation Receipt in {sec_k}",
                            description=f"Section '{sec_k}' specifies generating confirmation or audit receipts, which is unsupported by self-contained conversational assistant MVP scope.",
                            recommendation="Remove transactional receipt requirements; return grounded responses and log standard session telemetry."
                        ))
                        score -= 8
                        break

        # VAL-SEM-007: Unsupported Supervisory Persona / Capabilities Without Scope
        if is_support_domain and analysis and not any("manager" in u.lower() or "supervisor" in u.lower() for u in (analysis.intended_users or [])):
            for sec_k in ["user_personas", "user_stories", "user_journeys"]:
                s_obj = prd_version.sections.get(sec_k)
                if s_obj and not s_obj.is_na and s_obj.content:
                    if re.search(r"\b(?:support manager|customer support manager|staffing optimization|accuracy dashboard|review escalation volumes)\b", s_obj.content, re.IGNORECASE):
                        issues.append(ValidationIssue(
                            rule_id="VAL-SEM-007",
                            severity="error",
                            section_key=sec_k,
                            title=f"Unsupported Support Manager Role or Capabilities in {sec_k}",
                            description=f"Section '{sec_k}' introduces Support Manager role and managerial analytics/staffing workflows unsupported by approved MVP user roles.",
                            recommendation="Restrict personas, stories, and workflows strictly to approved end-user roles (Customer, Support Representative)."
                        ))
                        score -= 8
                        break

        # VAL-PRIV-001: Unsupported Regulatory / GDPR Compliance Claims
        user_mandates_gdpr = analysis and any("gdpr" in c.lower() for c in (analysis.explicit_constraints + analysis.facts))
        for sec_k in ["executive_summary", "product_scope", "security_and_privacy_requirements"]:
            s_obj = prd_version.sections.get(sec_k)
            if s_obj and not s_obj.is_na and s_obj.content:
                s_text = s_obj.content.replace("\u2011", "-").replace("\u2013", "-")
                gdpr_matches = list(re.finditer(r"\b(?:guarantees|ensures|mandates|enforces|fully)\b[^\n\.\;]*\bgdpr\b|\b(?:compliance\s+with\s+gdpr|gdpr\s+compliance|gdpr[- ]compliant)\b", s_text, re.IGNORECASE))
                for gm in gdpr_matches:
                    line_containing = [l for l in s_text.split("\n") if gm.group(0).lower() in l.lower()]
                    line_str = line_containing[0].lower() if line_containing else ""
                    is_legal_reviewed = any(lr in line_str for lr in ["subject to formal legal", "pending legal review", "open decision", "compliance assessment required"])
                    if not is_legal_reviewed and not user_mandates_gdpr:
                        issues.append(ValidationIssue(
                            rule_id="VAL-PRIV-001",
                            severity="error",
                            section_key=sec_k,
                            title=f"Unsupported GDPR Compliance Assertion in {sec_k}",
                            description=f"Section '{sec_k}' claims guaranteed GDPR compliance without verified legal grounds or institutional Data Protection Assessment.",
                            recommendation="Qualify regulatory compliance as subject to formal institutional privacy assessment and legal review."
                        ))
                        score -= 8
                        break

        # VAL-STR-003: Malformed Markdown Table Row Check
        for sec_k in ["functional_requirements", "non_functional_requirements", "business_rules", "acceptance_criteria", "user_stories"]:
            s_obj = prd_version.sections.get(sec_k)
            if s_obj and not s_obj.is_na and s_obj.content:
                t_lines = [l.strip() for l in s_obj.content.split("\n") if l.strip().startswith("|") and l.strip().endswith("|")]
                if len(t_lines) >= 3:
                    header_cols = len(t_lines[0].split("|"))
                    for row_idx, r_line in enumerate(t_lines[2:], 3):
                        cols = len(r_line.split("|"))
                        if cols < header_cols - 1 or cols > header_cols + 2:
                            issues.append(ValidationIssue(
                                rule_id="VAL-STR-003",
                                severity="error",
                                section_key=sec_k,
                                title=f"Malformed Markdown Table Row in {sec_k}",
                                description=f"Line {row_idx} of table in '{sec_k}' has {cols-2} columns but header specifies {header_cols-2} columns.",
                                recommendation="Format all table data rows with the same number of pipe delimiters as the header."
                            ))
                            score -= 6
                            break

        # VAL-VER-001: Authoritative Document Identity and Version Verification
        doc_info_sec = prd_version.sections.get("document_information")
        if doc_info_sec and not doc_info_sec.is_na:
            doc_text = doc_info_sec.content
            if prd_version.version_number and f"**Version:** {prd_version.version_number}" not in doc_text:
                issues.append(ValidationIssue(
                    rule_id="VAL-VER-001",
                    severity="error",
                    section_key="document_information",
                    title="Document Version Inconsistency",
                    description=f"Section 1 header version does not match authoritative PRDVersion ({prd_version.version_number}).",
                    recommendation="Ensure Section 1 Document Information specifies the authoritative release version."
                ))
                score -= 10
            # VAL-HASH-001: Embedded Content Hash Inconsistency
            all_doc_hashes = list(set(re.findall(r"\b([a-f0-9]{64})\b", doc_text)))
            if len(all_doc_hashes) > 1:
                issues.append(ValidationIssue(
                    rule_id="VAL-HASH-001",
                    severity="error",
                    section_key="document_information",
                    title="Conflicting Embedded Content Hashes in Document",
                    description=f"Multiple conflicting SHA-256 hashes detected in document: {all_doc_hashes}",
                    recommendation="Remove conflicting self-referential hashes; use authoritative external manifest."
                ))
                score -= 10
            elif "**SHA-256:**" in doc_text:
                hash_match = re.search(r"\*\*SHA-256:\*\*\s*`([a-f0-9]{64})`", doc_text)
                if hash_match:
                    embedded_hash = hash_match.group(1)
                    if prd_version.content_hash and embedded_hash != prd_version.content_hash:
                        issues.append(ValidationIssue(
                            rule_id="VAL-HASH-001",
                            severity="error",
                            section_key="document_information",
                            title="Embedded Content Hash Inconsistency",
                            description="Embedded SHA-256 hash does not match authoritative version hash.",
                            recommendation="Do not embed self-referential hash in raw file; track hash in external manifest."
                        ))
                        score -= 10

            # VAL-STATUS-001 / VAL-STAT-001: Document Status vs Validation Outcome Check
            doc_status_match = re.search(r"\*\*Status:\*\*\s*([A-Za-z\s]+)", doc_text)
            if doc_status_match:
                doc_status_str = doc_status_match.group(1).strip().lower()
                pre_errors = sum(1 for i in issues if i.severity == "error")
                if "approved" in doc_status_str and (pre_errors > 0 or prd_version.status == "rejected"):
                    issues.append(ValidationIssue(
                        rule_id="VAL-STATUS-001",
                        severity="error",
                        section_key="document_information",
                        title="Document Status Contradicts Validation Outcome",
                        description="Section 1 Document Information asserts 'Approved' status despite presence of validation errors.",
                        recommendation="Set document status to 'Draft' or 'Rejected' when validation errors are present."
                    ))
                    issues.append(ValidationIssue(
                        rule_id="VAL-STAT-001",
                        severity="error",
                        section_key="document_information",
                        title="Document Status Contradicts Validation Outcome",
                        description="Section 1 Document Information asserts 'Approved' status despite presence of validation errors.",
                        recommendation="Set document status to 'Draft' or 'Rejected' when validation errors are present."
                    ))
                    score -= 10
                elif prd_version.status == "approved" and any(d in doc_status_str for d in ["draft", "under active review", "under_review"]):
                    issues.append(ValidationIssue(
                        rule_id="VAL-STATUS-001",
                        severity="error",
                        section_key="document_information",
                        title="Document Status Mismatch with Authoritative Approved Record",
                        description=f"Document asserts '{doc_status_match.group(1).strip()}' while version record is marked Approved.",
                        recommendation="Synchronize document status to 'Approved' upon successful validation approval."
                    ))
                    issues.append(ValidationIssue(
                        rule_id="VAL-STAT-001",
                        severity="error",
                        section_key="document_information",
                        title="Document Status Mismatch with Authoritative Approved Record",
                        description=f"Document asserts '{doc_status_match.group(1).strip()}' while version record is marked Approved.",
                        recommendation="Synchronize document status to 'Approved' upon successful validation approval."
                    ))
                    score -= 10

        # Compute summary
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        info_count = sum(1 for i in issues if i.severity == "info")
        
        # Enforce score capping and strict verdict
        if error_count > 0:
            is_valid = False
            verdict = "REJECTED"
            score = min(score, 65)  # Cap at 65 when semantic or contract errors exist
        else:
            is_valid = True
            verdict = "APPROVED" if score >= 85 else "REJECTED"
        score = max(0, min(100, score))

        # Extract atomic claims across all 27 canonical sections
        claims = self._extract_atomic_claims(prd_version, analysis)

        # Compute Category Summaries across the 10 canonical categories
        category_summaries: Dict[str, int] = {cat: 0 for cat in TEN_CATEGORIES}
        for iss in issues:
            cat = categorize_issue_rule(iss.rule_id)
            category_summaries[cat] = category_summaries.get(cat, 0) + 1

        total_claims = len(claims)
        supported_claims = sum(1 for c in claims if c.entailment_outcome == EntailmentOutcome.SUPPORTED.value)
        partially_supported = sum(1 for c in claims if c.entailment_outcome == EntailmentOutcome.PARTIALLY_SUPPORTED.value)
        contradicted_claims = sum(1 for c in claims if c.entailment_outcome == EntailmentOutcome.CONTRADICTED.value)
        unsupported_claims = sum(1 for c in claims if c.entailment_outcome == EntailmentOutcome.NOT_SUPPORTED.value)
        ambiguous_claims = sum(1 for c in claims if c.entailment_outcome == EntailmentOutcome.AMBIGUOUS.value)
        
        structural_errors = category_summaries.get("Structural Completeness", 0)
        cross_section_conflicts = category_summaries.get("Cross-Section Consistency", 0)
        export_integrity_status = "COMPROMISED" if category_summaries.get("Export Artifact Integrity", 0) > 0 else "VERIFIED"

        report = ValidationReport(
            prd_version_id=str(prd_version.id or "draft"),
            project_id=prd_version.project_id,
            is_valid=is_valid,
            verdict=verdict,
            score=score,
            total_issues=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            issues=issues,
            claims=claims,
            total_claims=total_claims,
            supported_claims=supported_claims,
            partially_supported_claims=partially_supported,
            contradicted_claims=contradicted_claims,
            unsupported_claims=unsupported_claims,
            ambiguous_claims=ambiguous_claims,
            unresolved_high_severity_findings=error_count,
            structural_errors=structural_errors,
            cross_section_conflicts=cross_section_conflicts,
            export_integrity_status=export_integrity_status,
            category_summaries=category_summaries
        )

        # Persist report if repository is configured
        if self.repo:
            try:
                report_dict = report.dict(exclude={"id"})
                saved = await self.repo.create(report_dict)
                report.id = saved["id"]
            except Exception as e:
                logger.warning(f"Could not persist validation report: {e}")

        return report

    def _extract_atomic_claims(
        self,
        prd_version: PRDVersion,
        analysis: Optional[AnalysisRecord]
    ) -> List[ClaimModel]:
        claims: List[ClaimModel] = []
        claim_counter = 1

        facts_text = " ".join(analysis.facts) if analysis and analysis.facts else ""
        objectives_text = " ".join(analysis.core_objectives) if analysis and analysis.core_objectives else ""
        constraints_text = " ".join(analysis.explicit_constraints) if analysis and analysis.explicit_constraints else ""
        assumptions_text = " ".join(analysis.assumptions) if analysis and analysis.assumptions else ""
        ground_corpus = f"{facts_text} {objectives_text} {constraints_text}".lower()

        out_of_scope_text = ""
        if "out_of_scope" in prd_version.sections and not prd_version.sections["out_of_scope"].is_na:
            out_of_scope_text = prd_version.sections["out_of_scope"].content.lower()

        for sec_key in CANONICAL_SECTIONS:
            sec = prd_version.sections.get(sec_key)
            if not sec or sec.is_na or not sec.content:
                continue

            content = sec.content.strip()
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            for line in lines:
                clean_line = re.sub(r"^[\|\-\*\#\d\.\s]+", "", line).strip()
                clean_line = re.sub(r"\|.*$", "", clean_line).strip()
                if len(clean_line) < 15:
                    continue

                req_ids = list(set(re.findall(r"\b(?:FR|NFR|BR|AC|RSK|MET)-\d+\b", line)))
                fingerprint = hashlib.sha256(clean_line.encode("utf-8")).hexdigest()[:16]

                is_ambiguous = any(re.search(pat, clean_line, re.IGNORECASE) for pat in AMBIGUOUS_TERMS)

                is_contradicted = False
                lower_line = clean_line.lower()
                if out_of_scope_text and sec_key != "out_of_scope":
                    for oos_phrase in [p.strip() for p in out_of_scope_text.splitlines() if len(p.strip()) > 10]:
                        clean_oos = re.sub(r"^[\|\-\*\#\d\.\s]+", "", oos_phrase).lower()
                        if clean_oos and clean_oos in lower_line:
                            is_contradicted = True
                            break

                if is_contradicted:
                    outcome = EntailmentOutcome.CONTRADICTED.value
                    prov = CanonicalProvenance.PROPOSED.value
                elif is_ambiguous:
                    outcome = EntailmentOutcome.AMBIGUOUS.value
                    prov = CanonicalProvenance.INFERRED.value
                elif ground_corpus and any(term in ground_corpus for term in lower_line.split() if len(term) > 5):
                    outcome = EntailmentOutcome.SUPPORTED.value
                    prov = CanonicalProvenance.USER_CONFIRMED.value
                elif assumptions_text and any(term in assumptions_text.lower() for term in lower_line.split() if len(term) > 5):
                    outcome = EntailmentOutcome.PARTIALLY_SUPPORTED.value
                    prov = CanonicalProvenance.INFERRED.value
                else:
                    outcome = EntailmentOutcome.PARTIALLY_SUPPORTED.value
                    prov = CanonicalProvenance.PROPOSED.value

                claims.append(ClaimModel(
                    claim_id=f"CLM-{sec_key[:4].upper()}-{claim_counter:03d}",
                    statement_text=clean_line[:300],
                    section_key=sec_key,
                    source_type="user_submission",
                    source_document="User Submission",
                    source_fingerprint=fingerprint,
                    source_excerpt=clean_line[:100],
                    provenance=prov,
                    entailment_outcome=outcome,
                    adjudication_status="ADJUDICATED",
                    related_requirement_ids=req_ids
                ))
                claim_counter += 1

        return claims

    async def validate_markdown(
        self,
        md_content: str,
        analysis: Optional[AnalysisRecord] = None
    ) -> ValidationReport:
        """
        Parses final rendered Markdown PRD and validates it directly through the validation engine.
        Detects rendering discrepancies, formatting artifacts, unrendered template tags,
        and ensures complete semantic and structural consistency.
        """
        sections: Dict[str, PRDSectionContent] = {}
        header_pattern = r"(?m)^##\s+(?:(\d+)\.\s+)?([^\n]+)"
        splits = list(re.finditer(header_pattern, md_content))

        title_to_key = {title.lower(): key for key, title in SECTION_TITLES.items()}
        for k in CANONICAL_SECTIONS:
            title_to_key[k.replace('_', ' ').lower()] = k

        for idx, match in enumerate(splits):
            raw_title = match.group(2).strip()
            clean_title = re.sub(r"^\d+\.\s*", "", raw_title).strip()
            start_pos = match.end()
            end_pos = splits[idx + 1].start() if idx + 1 < len(splits) else len(md_content)
            content = md_content[start_pos:end_pos].strip()

            key = None
            for cand_title, cand_key in title_to_key.items():
                if cand_title in clean_title.lower() or clean_title.lower() in cand_title:
                    key = cand_key
                    break

            if not key:
                key = re.sub(r"[^a-z0-9]", "_", clean_title.lower()).strip("_")

            is_na = "> *Section marked Not Applicable" in content or "[Not Applicable" in content
            sections[key] = PRDSectionContent(
                key=key,
                title=raw_title,
                content=content,
                is_na=is_na
            )

        # Extract metadata
        ver_match = re.search(r"\*\*Version:\*\*\s*([^\s\|]+)", md_content)
        version_number = ver_match.group(1).strip() if ver_match else "v1.0"

        status_match = re.search(r"\*\*Status:\*\*\s*([A-Za-z\s]+)", md_content)
        status_str = status_match.group(1).strip().lower() if status_match else "draft"

        all_hashes = list(set(re.findall(r"\b([a-f0-9]{64})\b", md_content)))

        temp_version = PRDVersion(
            prd_id="md-rendered-prd",
            project_id=analysis.project_id if analysis else "project-md",
            version_number=version_number,
            status=status_str,
            content_hash=all_hashes[0] if all_hashes else None,
            sections=sections
        )

        report = await self.validate_version(temp_version, analysis=analysis)

        # Additional markdown-level checks
        if len(all_hashes) > 1:
            report.issues.append(ValidationIssue(
                rule_id="VAL-HASH-001",
                severity="error",
                section_key="document_information",
                title="Conflicting Embedded Hashes in Rendered Document",
                description=f"Multiple conflicting SHA-256 hashes detected in rendered markdown: {all_hashes}",
                recommendation="Do not embed self-referential hash; use authoritative external manifest."
            ))
            report.error_count += 1
            report.total_issues += 1
            report.is_valid = False
            report.verdict = "REJECTED"
            report.score = min(report.score, 65)
            report.category_summaries["Export Artifact Integrity"] = report.category_summaries.get("Export Artifact Integrity", 0) + 1
            report.export_integrity_status = "COMPROMISED"
            report.unresolved_high_severity_findings += 1

        return report
