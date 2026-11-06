# Phase 2.4.7: Baseline Engineering & Semantic Audit Report

## 1. Executive Summary

Phase 2.4.7 addresses semantic integrity, claim-level validation, responsive web viewer UX, and export artifact fidelity in the Local-First PRD Engineering Framework. 

Prior releases successfully repaired PDF geometry, typography, and table cell wrapping (Phase 2.4.6). However, baseline inspection of the framework identified three remaining structural challenges:
1. **Frontend Responsive Layout Limitations**: On narrower viewports (<1024px, 768px, 430px, 390px), horizontal workflow navigation tabs (steps 1–8) experienced horizontal clipping, hiding tab 8 ("8. Export") without explicit scroll affordances or auto-scroll tracking. Secondary actions crowded the document toolbar on mobile viewports.
2. **Validation Granularity & Claim Grounding**: The validation engine evaluated documents primarily at section granularity, lacking fine-grained atomic claim extraction, deterministic entailment adjudication, cross-section negative conflict detection, and policy governance across numerical targets.
3. **Lifecycle State Transition Integrity**: The generator self-approved generated documents upon completion rather than requiring independent human review, permitting approval even when quality gates detected unresolved defects.

---

## 2. Baseline Architecture & Technology Inspection

- **Backend**: FastAPI, Pydantic v2, Python 3.14 / 3.12, ReportLab 4.4.10, PyPDFium2, python-docx, pdfplumber.
- **Frontend**: React 18, Vite 5.4, Tailwind CSS, Lucide icons, Vitest.
- **Database / Store**: MongoDB Motor async driver with in-memory local fallback.
- **AI Gateway**: Local-first Ollama adapter with optional Groq fallback; strict local mock deterministic pipeline for CI/CD test automation.

---

## 3. Defect Taxonomy & Remediation Baseline

| Defect Class | Root Cause | Phase 2.4.7 Resolution |
| :--- | :--- | :--- |
| **Workflow Navigation Clipping** | `overflow-x-auto` without scroll controls or active tab auto-centering | Added touch-friendly scroll container with `ChevronLeft`/`ChevronRight` scroll buttons and `scrollIntoView` on active tab change |
| **Toolbar Mobile Overflow** | 6 individual export/print/validate buttons horizontally stacked | Implemented responsive collapsing into an overflow menu (`MoreVertical`) on screens < 768px, preserving primary PDF action and 44px touch targets |
| **Generator Self-Approval** | `worker.py` set `status: "approved"` upon generation completion | Set initial generation status to `under_review` (or `blocked`); enforced `approve_version` gate checking validation pass |
| **Validation Granularity** | Regex checks without atomic claim breakdown | Implemented `_extract_atomic_claims` across all 27 canonical sections with entailment adjudication (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONTRADICTED`, `AMBIGUOUS`, `NOT_SUPPORTED`) |
| **Export Manifest Hash Ambiguity** | Hash embedded inside raw content caused circular reference | Enforced separate SHA-256 calculation per artifact (MD, DOCX, PDF) tracked in authoritative external manifest |

