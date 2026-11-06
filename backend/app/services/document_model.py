"""
Unified PRD Document Intermediate Representation (IR) and Parser.

This module provides a format-agnostic document model that normalizes
canonical PRD sections into structured nodes (Headings, Paragraphs,
Tables, Lists, Code Blocks, Callouts, Diagrams).

It guarantees content preservation, consistent typography hierarchy,
and structural integrity across Web, Markdown, PDF, and DOCX renderers.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Regex patterns for markdown element recognition
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
TABLE_ROW_RE = re.compile(r'^\|(.+)\|$')
LIST_ITEM_RE = re.compile(r'^(\s*)([-*]|\d+\.)\s+(.+)$')
BLOCKQUOTE_RE = re.compile(r'^>\s*(.*)$')
FENCE_RE = re.compile(r'^```(\w*)\s*$')
REQ_ID_RE = re.compile(r'\b(FR-\d+|NFR-\d+|BR-\d+|AC-\d+|RSK-\d+|CLM-\d+)\b')


@dataclass
class DocumentMetadata:
    title: str
    version_number: str
    status: str
    created_at: datetime
    created_by: str = "PRD Engineering Framework"
    changelog: str = ""
    job_id: Optional[str] = None
    content_hash: Optional[str] = None
    project_id: Optional[str] = None


@dataclass
class BlockNode:
    """Base class for intermediate document blocks."""
    pass


@dataclass
class HeadingNode(BlockNode):
    level: int  # 1 for Document/Major Section, 2 for Subheading, 3 for Nested
    text: str
    anchor_id: str = ""


@dataclass
class ParagraphNode(BlockNode):
    text: str
    raw_markdown: str = ""


@dataclass
class TableNode(BlockNode):
    headers: List[str]
    rows: List[List[str]]
    column_alignments: List[str] = field(default_factory=list)


@dataclass
class ListNode(BlockNode):
    ordered: bool
    items: List[str]


@dataclass
class CodeBlockNode(BlockNode):
    language: str
    code: str


@dataclass
class CalloutNode(BlockNode):
    kind: str  # 'info', 'note', 'warning', 'not_applicable'
    text: str


@dataclass
class DiagramNode(BlockNode):
    diagram_type: str  # 'mermaid', etc.
    code: str


@dataclass
class SectionNode:
    key: str
    title: str
    is_na: bool = False
    na_rationale: Optional[str] = None
    blocks: List[BlockNode] = field(default_factory=list)


@dataclass
class Document:
    metadata: DocumentMetadata
    sections: List[SectionNode] = field(default_factory=list)

    def total_sections(self) -> int:
        return len(self.sections)

    def active_sections_count(self) -> int:
        return sum(1 for s in self.sections if not s.is_na)

    def all_headings(self) -> List[HeadingNode]:
        headings: List[HeadingNode] = []
        for s in self.sections:
            headings.append(HeadingNode(level=1, text=s.title, anchor_id=f"section-{s.key}"))
            for b in s.blocks:
                if isinstance(b, HeadingNode):
                    headings.append(b)
        return headings


class DocumentParser:
    """Parses canonical PRD sections and raw markdown into a typed Document IR."""

    @staticmethod
    def parse_markdown_blocks(raw_text: str, section_key: str = "") -> List[BlockNode]:
        if not raw_text or not raw_text.strip():
            return []

        blocks: List[BlockNode] = []
        lines = raw_text.splitlines()
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            trimmed = line.strip()

            if not trimmed:
                i += 1
                continue

            # 1. Code Fence (including Mermaid)
            fence_match = FENCE_RE.match(trimmed)
            if fence_match:
                lang = fence_match.group(1).lower().strip()
                code_lines = []
                i += 1
                while i < n and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # consume closing fence
                code_text = "\n".join(code_lines)
                if lang == "mermaid":
                    blocks.append(DiagramNode(diagram_type="mermaid", code=code_text))
                else:
                    blocks.append(CodeBlockNode(language=lang or "text", code=code_text))
                continue

            # 2. Markdown Table
            if TABLE_ROW_RE.match(trimmed):
                table_lines = []
                while i < n and TABLE_ROW_RE.match(lines[i].strip()):
                    table_lines.append(lines[i].strip())
                    i += 1

                if len(table_lines) >= 2:
                    # Line 0: Header
                    headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
                    # Line 1: Separator
                    seps = [c.strip() for c in table_lines[1].strip("|").split("|")]
                    aligns = []
                    for s in seps:
                        if s.startswith(":") and s.endswith(":"):
                            aligns.append("center")
                        elif s.endswith(":"):
                            aligns.append("right")
                        else:
                            aligns.append("left")

                    # Rows
                    rows = []
                    for row_line in table_lines[2:]:
                        cells = [c.strip() for c in row_line.strip("|").split("|")]
                        # Pad or trim to match header length
                        if len(cells) < len(headers):
                            cells.extend([""] * (len(headers) - len(cells)))
                        rows.append(cells[:len(headers)])

                    blocks.append(TableNode(headers=headers, rows=rows, column_alignments=aligns))
                elif len(table_lines) == 1:
                    blocks.append(ParagraphNode(text=table_lines[0], raw_markdown=table_lines[0]))
                continue

            # 3. Blockquote / Callout Note
            if trimmed.startswith(">"):
                quote_lines = []
                while i < n and lines[i].strip().startswith(">"):
                    quote_lines.append(lines[i].strip().lstrip(">").strip())
                    i += 1
                full_quote = " ".join(quote_lines)
                is_na = "not applicable" in full_quote.lower() or "[not applicable" in full_quote.lower()
                kind = "not_applicable" if is_na else "note"
                blocks.append(CalloutNode(kind=kind, text=full_quote))
                continue

            # 4. Heading (H1-H6)
            heading_match = HEADING_RE.match(trimmed)
            if heading_match:
                hashes, heading_text = heading_match.groups()
                level = len(hashes)
                anchor = re.sub(r'[^a-zA-Z0-9_-]', '-', heading_text.lower()).strip('-')
                blocks.append(HeadingNode(level=min(level, 3), text=heading_text.strip(), anchor_id=anchor))
                i += 1
                continue

            # 5. List Items (bullet or numbered)
            list_match = LIST_ITEM_RE.match(line)
            if list_match:
                marker = list_match.group(2)
                is_ordered = marker.endswith(".")
                items = [list_match.group(3).strip()]
                i += 1
                while i < n:
                    sub_match = LIST_ITEM_RE.match(lines[i])
                    if sub_match and (sub_match.group(2).endswith(".") == is_ordered):
                        items.append(sub_match.group(3).strip())
                        i += 1
                    elif lines[i].strip() == "":
                        # Lookahead to see if next line is also a list item
                        if i + 1 < n and LIST_ITEM_RE.match(lines[i + 1]):
                            i += 1
                        else:
                            break
                    else:
                        break
                blocks.append(ListNode(ordered=is_ordered, items=items))
                continue

            # 6. Paragraph (accumulate consecutive non-empty lines)
            para_lines = []
            while i < n:
                cur = lines[i].strip()
                if not cur:
                    break
                # Stop if starting another block construct
                if (FENCE_RE.match(cur) or
                    TABLE_ROW_RE.match(cur) or
                    cur.startswith(">") or
                    HEADING_RE.match(cur) or
                    LIST_ITEM_RE.match(lines[i])):
                    break
                para_lines.append(cur)
                i += 1

            if para_lines:
                para_text = " ".join(para_lines)
                blocks.append(ParagraphNode(text=para_text, raw_markdown="\n".join(para_lines)))

        return blocks

    @classmethod
    def parse_prd(cls, prd_version: Any, project_title: str) -> Document:
        """Constructs a canonical Document IR from a PRDVersion model or dict."""
        from app.models.prd import CANONICAL_SECTIONS, SECTION_TITLES

        # Extract metadata
        ver_num = getattr(prd_version, "version_number", "v1.0")
        status = getattr(prd_version, "status", "draft")
        created_at = getattr(prd_version, "created_at", datetime.utcnow())
        created_by = getattr(prd_version, "created_by", "Automated Requirements Engine")
        changelog = getattr(prd_version, "changelog", "Baseline release")
        job_id = getattr(prd_version, "job_id", None)
        content_hash = getattr(prd_version, "content_hash", None)
        project_id = str(getattr(prd_version, "project_id", "project"))

        metadata = DocumentMetadata(
            title=project_title,
            version_number=ver_num,
            status=status,
            created_at=created_at if isinstance(created_at, datetime) else datetime.utcnow(),
            created_by=created_by,
            changelog=changelog,
            job_id=job_id,
            content_hash=content_hash,
            project_id=project_id
        )

        doc = Document(metadata=metadata)

        # Get sections map
        sections_map = getattr(prd_version, "sections", {})
        if not isinstance(sections_map, dict):
            sections_map = {}

        for sec_key in CANONICAL_SECTIONS:
            sec_obj = sections_map.get(sec_key)
            title = SECTION_TITLES.get(sec_key, sec_key.replace('_', ' ').title())

            is_na = False
            na_rationale = None
            raw_content = ""

            if sec_obj:
                if isinstance(sec_obj, dict):
                    is_na = sec_obj.get("is_na", False)
                    na_rationale = sec_obj.get("na_rationale")
                    raw_content = sec_obj.get("content", "")
                    title = sec_obj.get("title", title)
                else:
                    is_na = getattr(sec_obj, "is_na", False)
                    na_rationale = getattr(sec_obj, "na_rationale", None)
                    raw_content = getattr(sec_obj, "content", "")
                    title = getattr(sec_obj, "title", title)

            sec_node = SectionNode(
                key=sec_key,
                title=title,
                is_na=is_na,
                na_rationale=na_rationale
            )

            if not is_na and raw_content:
                sec_node.blocks = cls.parse_markdown_blocks(raw_content, section_key=sec_key)

            doc.sections.append(sec_node)

        return doc

    @classmethod
    def parse_from_markdown_file(cls, filepath: str, project_title: str) -> Document:
        """Parses a full flat Markdown PRD file into a Document IR."""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract title and metadata if present
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            project_title = title_match.group(1).replace("Product Requirements Document:", "").strip()

        ver_match = re.search(r'\*\*Version:\*\*\s*([^\s|]+)', content)
        version_num = ver_match.group(1) if ver_match else "v2.3"

        status_match = re.search(r'\*\*Status:\*\*\s*([^\s|]+)', content)
        status = status_match.group(1).lower() if status_match else "draft"

        metadata = DocumentMetadata(
            title=project_title,
            version_number=version_num,
            status=status,
            created_at=datetime.utcnow()
        )

        doc = Document(metadata=metadata)

        # Split on section headings (## )
        parts = re.split(r'\n##\s+', content)
        for idx, part in enumerate(parts):
            if idx == 0:
                # Preamble / Document title section
                continue
            lines = part.splitlines()
            sec_title = lines[0].strip()
            sec_body = "\n".join(lines[1:])
            sec_key = re.sub(r'[^a-zA-Z0-9_]', '_', sec_title.lower()).strip('_')

            is_na = "> *Section marked Not Applicable" in sec_body or "[Not Applicable" in sec_body

            sec_node = SectionNode(
                key=sec_key,
                title=sec_title,
                is_na=is_na
            )
            if not is_na:
                sec_node.blocks = cls.parse_markdown_blocks(sec_body, section_key=sec_key)

            doc.sections.append(sec_node)

        return doc
