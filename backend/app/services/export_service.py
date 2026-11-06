import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.prd import PRDVersion, CANONICAL_SECTIONS, SECTION_TITLES
from app.core.config import settings
from app.services.document_model import (
    Document,
    DocumentMetadata,
    DocumentParser,
    SectionNode,
    HeadingNode,
    ParagraphNode,
    TableNode,
    ListNode,
    CodeBlockNode,
    CalloutNode,
    DiagramNode
)

logger = logging.getLogger(__name__)


def clean_xml_text(text: str) -> str:
    """Safely escapes text for ReportLab XML/HTML-like paragraph formatting."""
    if not text:
        return ""
    # Escape literal XML characters first so < and > and & don't break ReportLab's parser
    cleaned = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Convert markdown **bold** to <b>bold</b>
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', cleaned)
    # Convert markdown *italic* to <i>italic</i>
    cleaned = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', cleaned)
    # Convert markdown `code` to <font face="Courier">code</font>
    cleaned = re.sub(r'`([^`]+)`', r'<font face="Courier">\1</font>', cleaned)
    return cleaned


def ensure_vera_fonts_registered() -> str:
    """Registers Bitstream Vera TrueType fonts bundled with ReportLab for full UTF-8 Unicode fidelity."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab

    registered = pdfmetrics.getRegisteredFontNames()
    if "Vera" in registered and "VeraBd" in registered:
        return "Vera"

    fonts_dir = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    vera_regular = os.path.join(fonts_dir, "Vera.ttf")
    vera_bold = os.path.join(fonts_dir, "VeraBd.ttf")
    vera_italic = os.path.join(fonts_dir, "VeraIt.ttf")
    vera_bold_italic = os.path.join(fonts_dir, "VeraBI.ttf")

    if os.path.exists(vera_regular):
        pdfmetrics.registerFont(TTFont("Vera", vera_regular))
        pdfmetrics.registerFont(TTFont("VeraBd", vera_bold))
        pdfmetrics.registerFont(TTFont("VeraIt", vera_italic))
        pdfmetrics.registerFont(TTFont("VeraBI", vera_bold_italic))
        pdfmetrics.registerFontFamily(
            "Vera",
            normal="Vera",
            bold="VeraBd",
            italic="VeraIt",
            boldItalic="VeraBI"
        )
        return "Vera"
    return "Helvetica"


def compute_pdf_table_col_widths(
    headers: List[str],
    rows: List[List[str]],
    avail_width: float = 451.28
) -> List[float]:
    """Computes intelligent, content-aware column widths for PDF tables.
    
    Prevents narrow columns (IDs, Priorities) from consuming disproportionate space
    while allocating narrative text columns (Descriptions, Criteria) the majority of printable width.
    """
    num_cols = len(headers)
    if num_cols == 0:
        return []
    if num_cols == 1:
        return [avail_width]

    id_headers = {'id', 'fr id', 'ac id', 'story id', 'risk id', 'linked fr'}
    short_headers = {
        'priority', 'likelihood', 'impact', 'category', 'status', 
        'classification', 'owner', 'confirmation required', 
        'traceable ac', 'associated requirement', 'provenance'
    }

    is_wide = num_cols >= 7
    char_coeff = 4.0 if is_wide else 4.6
    pad_extra = 5.0 if is_wide else 8.0

    min_widths = []
    narrative_indices = []

    for c_idx, h in enumerate(headers):
        h_lower = h.lower().strip()
        cell_texts = [h] + [r[c_idx] for r in rows if c_idx < len(r)]
        words = [w.strip('*_`') for t in cell_texts for w in t.split()]
        max_word = max((len(w) for w in words), default=1)

        if h_lower in id_headers:
            min_w = 46.0 if is_wide else 50.0
        elif h_lower in short_headers:
            min_w = max(max_word * char_coeff + pad_extra, 32.0 if is_wide else 44.0)
        else:
            min_w = max(max_word * char_coeff + pad_extra, 38.0 if is_wide else 52.0)
            narrative_indices.append(c_idx)

        min_widths.append(min_w)

    sum_min = sum(min_widths)
    if sum_min >= avail_width:
        # Scale to avail_width while protecting ID headers
        final_widths = [avail_width * (w / sum_min) for w in min_widths]
        for i, h in enumerate(headers):
            if h.lower().strip() in id_headers and final_widths[i] < 45.0:
                deficit = 45.0 - final_widths[i]
                final_widths[i] = 45.0
                max_idx = max(range(num_cols), key=lambda k: final_widths[k])
                final_widths[max_idx] -= deficit
    else:
        surplus = avail_width - sum_min
        if narrative_indices:
            narrative_weights = []
            for idx in narrative_indices:
                cell_texts = [headers[idx]] + [r[idx] for r in rows if idx < len(r)]
                c_len = max((len(t) for t in cell_texts), default=1)
                narrative_weights.append(c_len ** 0.55)
            sum_nw = sum(narrative_weights)
            final_widths = list(min_widths)
            for i, idx in enumerate(narrative_indices):
                final_widths[idx] += surplus * (narrative_weights[i] / sum_nw)
        else:
            final_widths = [w + surplus / num_cols for w in min_widths]

    return [round(w, 2) for w in final_widths]


class ExportService:
    def __init__(self, exports_dir: Optional[Path] = None):
        self.exports_dir = exports_dir or settings.EXPORTS_DIR
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def export_document_to_markdown(self, doc: Document, filename: str) -> Path:
        """Renders Document IR to a standardized, clean Markdown document."""
        filepath = self.exports_dir / filename
        lines: List[str] = []

        # Document Header
        lines.append(f"# Product Requirements Document: {doc.metadata.title}")
        meta_parts = [
            f"**Version:** {doc.metadata.version_number}",
            f"**Status:** {doc.metadata.status.upper()}",
            f"**Date:** {doc.metadata.created_at.strftime('%Y-%m-%d')}"
        ]
        if doc.metadata.job_id:
            meta_parts.append(f"**Job ID:** {doc.metadata.job_id}")
        if doc.metadata.content_hash:
            meta_parts.append(f"**SHA-256:** `{doc.metadata.content_hash}`")
        lines.append(" | ".join(meta_parts))

        if doc.metadata.created_by or doc.metadata.changelog:
            lines.append(f"**Generated by:** {doc.metadata.created_by} | **Changelog:** {doc.metadata.changelog}")

        lines.append("\n---\n")

        # Sections
        for sec in doc.sections:
            lines.append(f"\n## {sec.title}\n")
            if sec.is_na:
                lines.append(f"> *Section marked Not Applicable: {sec.na_rationale or 'Omitted from baseline product scope'}*\n")
                continue

            for block in sec.blocks:
                if isinstance(block, HeadingNode):
                    prefix = "#" * min(block.level + 1, 4)
                    lines.append(f"\n{prefix} {block.text}\n")
                elif isinstance(block, ParagraphNode):
                    lines.append(f"\n{block.text}\n")
                elif isinstance(block, TableNode):
                    lines.append("")
                    # Header
                    lines.append("| " + " | ".join(block.headers) + " |")
                    # Separators
                    seps = []
                    for align in (block.column_alignments or ["left"] * len(block.headers)):
                        if align == "center":
                            seps.append(":---:")
                        elif align == "right":
                            seps.append("---:")
                        else:
                            seps.append("---")
                    while len(seps) < len(block.headers):
                        seps.append("---")
                    lines.append("| " + " | ".join(seps) + " |")
                    # Rows
                    for row in block.rows:
                        # Clean cell pipes
                        clean_row = [c.replace("|", "\\|") for c in row]
                        lines.append("| " + " | ".join(clean_row) + " |")
                    lines.append("")
                elif isinstance(block, ListNode):
                    lines.append("")
                    for idx, item in enumerate(block.items):
                        if block.ordered:
                            lines.append(f"{idx + 1}. {item}")
                        else:
                            lines.append(f"- {item}")
                    lines.append("")
                elif isinstance(block, CodeBlockNode):
                    lines.append(f"\n```{block.language}\n{block.code}\n```\n")
                elif isinstance(block, DiagramNode):
                    lines.append(f"\n```{block.diagram_type}\n{block.code}\n```\n")
                elif isinstance(block, CalloutNode):
                    lines.append(f"\n> {block.text}\n")

        content = "\n".join(lines).strip() + "\n"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def export_markdown(self, prd_version: PRDVersion, project_title: str) -> Path:
        """Export PRD version to clean Markdown file via Document IR."""
        filename = f"PRD_{prd_version.project_id[:8]}_{prd_version.version_number}.md"
        doc = DocumentParser.parse_prd(prd_version, project_title)
        return self.export_document_to_markdown(doc, filename)

    def export_document_to_docx(self, doc: Document, filename: str) -> Path:
        """Renders Document IR to Microsoft Word DOCX with professional Word styles and tables."""
        from docx import Document as WordDocument
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml import parse_xml, OxmlElement
        from docx.oxml.ns import nsdecls, qn

        filepath = self.exports_dir / filename
        word_doc = WordDocument()

        # 1. Page Margins & Running Header/Footer
        for section in word_doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

            # Running Header (top right)
            header_p = section.header.paragraphs[0]
            header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            hrun = header_p.add_run(f"Product Requirements Document | {doc.metadata.title}")
            hrun.font.size = Pt(8.5)
            hrun.font.color.rgb = RGBColor(100, 116, 139)

            # Running Footer (bottom right)
            footer_p = section.footer.paragraphs[0]
            footer_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            frun = footer_p.add_run(
                f"Version {doc.metadata.version_number} | {doc.metadata.status.upper()} | Date: {doc.metadata.created_at.strftime('%Y-%m-%d')}"
            )
            frun.font.size = Pt(8.5)
            frun.font.color.rgb = RGBColor(100, 116, 139)

        # 2. Document Title Block
        title_p = word_doc.add_paragraph()
        title_p.paragraph_format.space_before = Pt(8)
        title_p.paragraph_format.space_after = Pt(2)
        title_run = title_p.add_run("Product Requirements Document")
        title_run.font.size = Pt(13)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(14, 165, 233)  # Sky-500

        sub_p = word_doc.add_paragraph()
        sub_p.paragraph_format.space_after = Pt(6)
        sub_run = sub_p.add_run(doc.metadata.title)
        sub_run.font.size = Pt(24)
        sub_run.font.bold = True
        sub_run.font.color.rgb = RGBColor(15, 23, 42)  # Slate-900

        meta_p = word_doc.add_paragraph()
        meta_p.paragraph_format.space_after = Pt(18)
        meta_text = f"Version: {doc.metadata.version_number}   |   Status: {doc.metadata.status.upper()}   |   Date: {doc.metadata.created_at.strftime('%Y-%m-%d')}"
        if doc.metadata.content_hash:
            meta_text += f"\nSHA-256: {doc.metadata.content_hash}"
        meta_run = meta_p.add_run(meta_text)
        meta_run.font.size = Pt(9.5)
        meta_run.font.color.rgb = RGBColor(71, 85, 105)

        # 3. Render Sections from Document IR
        for sec in doc.sections:
            h1 = word_doc.add_heading(sec.title, level=1)
            h1.paragraph_format.space_before = Pt(18)
            h1.paragraph_format.space_after = Pt(6)
            h1.paragraph_format.keep_with_next = True
            for r in h1.runs:
                r.font.size = Pt(14)
                r.font.bold = True
                r.font.color.rgb = RGBColor(15, 23, 42)

            if sec.is_na:
                p = word_doc.add_paragraph()
                p.paragraph_format.space_after = Pt(8)
                p.italic = True
                p_run = p.add_run(f"[Not Applicable: {sec.na_rationale or 'Omitted from baseline product scope'}]")
                p_run.font.size = Pt(10)
                p_run.font.color.rgb = RGBColor(100, 116, 139)
                continue

            for block in sec.blocks:
                if isinstance(block, HeadingNode):
                    h_level = min(max(block.level, 1), 3)
                    h = word_doc.add_heading(block.text, level=h_level + 1)
                    h.paragraph_format.space_before = Pt(12)
                    h.paragraph_format.space_after = Pt(4)
                    h.paragraph_format.keep_with_next = True
                    for r in h.runs:
                        r.font.size = Pt(12 if h_level == 1 else 10.5)
                        r.font.bold = True
                        r.font.color.rgb = RGBColor(30, 41, 59)

                elif isinstance(block, ParagraphNode):
                    p = word_doc.add_paragraph()
                    p.paragraph_format.space_after = Pt(6)
                    p.paragraph_format.line_spacing = 1.15
                    # Simple inline formatting
                    raw = block.text
                    # Split on requirement badges or bold
                    parts = re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', raw)
                    for pt in parts:
                        if pt.startswith("**") and pt.endswith("**"):
                            run = p.add_run(pt[2:-2])
                            run.bold = True
                            run.font.size = Pt(10)
                            run.font.color.rgb = RGBColor(15, 23, 42)
                        elif pt.startswith("`") and pt.endswith("`"):
                            run = p.add_run(pt[1:-1])
                            run.font.name = "Consolas"
                            run.font.size = Pt(9)
                            run.font.color.rgb = RGBColor(15, 23, 42)
                        else:
                            run = p.add_run(pt)
                            run.font.size = Pt(10)
                            run.font.color.rgb = RGBColor(30, 41, 59)

                elif isinstance(block, TableNode):
                    if not block.headers:
                        continue
                    table = word_doc.add_table(rows=1 + len(block.rows), cols=len(block.headers))
                    table.alignment = WD_TABLE_ALIGNMENT.CENTER
                    table.autofit = True

                    # Style Header Row
                    hdr_cells = table.rows[0].cells
                    for col_idx, header_text in enumerate(block.headers):
                        cell = hdr_cells[col_idx]
                        cell.text = header_text
                        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="0F172A"/>')
                        cell._tc.get_or_add_tcPr().append(shading)
                        p = cell.paragraphs[0]
                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        for r in p.runs:
                            r.font.bold = True
                            r.font.size = Pt(9)
                            r.font.color.rgb = RGBColor(255, 255, 255)

                    # Repeat header row on every page
                    trPr = table.rows[0]._tr.get_or_add_trPr()
                    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
                    trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

                    # Populate Data Rows
                    for row_idx, row_data in enumerate(block.rows):
                        row = table.rows[row_idx + 1]
                        # Disallow row splitting across pages
                        r_trPr = row._tr.get_or_add_trPr()
                        r_trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

                        bg_hex = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
                        for col_idx, cell_value in enumerate(row_data):
                            if col_idx < len(row.cells):
                                cell = row.cells[col_idx]
                                cell.text = cell_value
                                if bg_hex != "FFFFFF":
                                    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_hex}"/>')
                                    cell._tc.get_or_add_tcPr().append(shading)
                                p = cell.paragraphs[0]
                                for r in p.runs:
                                    r.font.size = Pt(8.5)
                                    r.font.color.rgb = RGBColor(30, 41, 59)

                    # Space after table
                    sp = word_doc.add_paragraph()
                    sp.paragraph_format.space_before = Pt(4)
                    sp.paragraph_format.space_after = Pt(6)

                elif isinstance(block, ListNode):
                    for item in block.items:
                        p = word_doc.add_paragraph(style='List Number' if block.ordered else 'List Bullet')
                        p.paragraph_format.space_after = Pt(2)
                        p.paragraph_format.line_spacing = 1.15
                        run = p.add_run(item)
                        run.font.size = Pt(10)
                        run.font.color.rgb = RGBColor(30, 41, 59)

                elif isinstance(block, (CodeBlockNode, DiagramNode)):
                    p = word_doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(6)
                    p.paragraph_format.space_after = Pt(6)
                    p.paragraph_format.left_indent = Inches(0.25)
                    code_text = block.code
                    run = p.add_run(code_text)
                    run.font.name = "Consolas"
                    run.font.size = Pt(8.5)
                    run.font.color.rgb = RGBColor(15, 23, 42)

                elif isinstance(block, CalloutNode):
                    p = word_doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(4)
                    p.paragraph_format.space_after = Pt(6)
                    p.paragraph_format.left_indent = Inches(0.25)
                    run = p.add_run(f"> {block.text}")
                    run.italic = True
                    run.font.size = Pt(9.5)
                    run.font.color.rgb = RGBColor(71, 85, 105)

        word_doc.save(str(filepath))
        return filepath

    def export_docx(self, prd_version: PRDVersion, project_title: str) -> Path:
        """Export PRD version to Microsoft Word DOCX via Document IR."""
        filename = f"PRD_{prd_version.project_id[:8]}_{prd_version.version_number}.docx"
        doc = DocumentParser.parse_prd(prd_version, project_title)
        return self.export_document_to_docx(doc, filename)

    def export_document_to_pdf(self, doc: Document, filename: str) -> Path:
        """Renders Document IR to PDF with professional technical specification layout on A4 paper with 1-inch margins."""
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            KeepTogether
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas

        filepath = self.exports_dir / filename
        base_font = ensure_vera_fonts_registered()
        bold_font = f"{base_font}Bd" if base_font == "Vera" else "Helvetica-Bold"
        italic_font = f"{base_font}It" if base_font == "Vera" else "Helvetica-Oblique"

        # A4: 595.27559 x 841.88976 pt. Margins: 72 pt (1 inch) on all sides.
        # Printable width: 451.28 pt. Printable height: 697.89 pt.
        page_width, page_height = A4
        margin = 72.0
        avail_width = page_width - (margin * 2)  # 451.27559 pt

        class NumberedCanvas(canvas.Canvas):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._saved_page_states = []

            def showPage(self):
                self._saved_page_states.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                num_pages = len(self._saved_page_states)
                for state in self._saved_page_states:
                    self.__dict__.update(state)
                    self.draw_page_decorations(num_pages)
                    canvas.Canvas.showPage(self)
                canvas.Canvas.save(self)

            def draw_page_decorations(self, page_count):
                self.saveState()
                self.setFont(base_font, 8)
                self.setFillColor(colors.HexColor("#64748b"))

                # Running Header (pages 2+) - safely inside the 72pt top margin zone
                if self._pageNumber > 1:
                    header_y = page_height - margin + 26  # y ~ 795.89 pt
                    line_y = page_height - margin + 14    # y ~ 783.89 pt
                    header_title = f"Product Requirements Document | {doc.metadata.title}"
                    if len(header_title) > 65:
                        header_title = header_title[:62] + "..."
                    v_str = doc.metadata.version_number if str(doc.metadata.version_number).startswith('v') else f"v{doc.metadata.version_number}"
                    self.drawString(margin, header_y, header_title)
                    self.drawRightString(page_width - margin, header_y, v_str)
                    self.setStrokeColor(colors.HexColor("#cbd5e1"))
                    self.setLineWidth(0.5)
                    self.line(margin, line_y, page_width - margin, line_y)

                # Running Footer (all pages) - safely inside the 72pt bottom margin zone
                footer_line_y = margin - 16   # y = 56 pt
                footer_text_y = margin - 30   # y = 42 pt
                self.setStrokeColor(colors.HexColor("#cbd5e1"))
                self.setLineWidth(0.5)
                self.line(margin, footer_line_y, page_width - margin, footer_line_y)

                status_str = f"Version {doc.metadata.version_number} | {doc.metadata.status.upper()}"
                self.drawString(margin, footer_text_y, status_str)
                self.drawRightString(page_width - margin, footer_text_y, f"Page {self._pageNumber} of {page_count}")
                self.restoreState()

        doc_template = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin
        )
        styles = getSampleStyleSheet()

        # Professional Technical Specification Typography Scale
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName=bold_font,
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#0f172a"),
            alignment=0,
            spaceAfter=6
        )
        category_style = ParagraphStyle(
            'DocCategory',
            parent=styles['Normal'],
            fontName=bold_font,
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#0284c7"),
            spaceAfter=4
        )
        meta_style = ParagraphStyle(
            'DocMeta',
            parent=styles['Normal'],
            fontName=base_font,
            fontSize=8.5,
            leading=12.5,
            textColor=colors.HexColor("#475569"),
            spaceAfter=14
        )
        h1_style = ParagraphStyle(
            'SectionH1',
            parent=styles['Heading2'],
            fontName=bold_font,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=16,
            spaceAfter=8,
            keepWithNext=True
        )
        h1_table_style = ParagraphStyle(
            'SectionH1Table',
            parent=h1_style,
            keepWithNext=False
        )
        h2_style = ParagraphStyle(
            'SectionH2',
            parent=styles['Heading3'],
            fontName=bold_font,
            fontSize=14,
            leading=17,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=5,
            keepWithNext=True
        )
        h2_table_style = ParagraphStyle(
            'SectionH2Table',
            parent=h2_style,
            keepWithNext=False
        )
        h3_style = ParagraphStyle(
            'SectionH3',
            parent=styles['Heading3'],
            fontName=bold_font,
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#334155"),
            spaceBefore=9,
            spaceAfter=4,
            keepWithNext=True
        )
        h3_table_style = ParagraphStyle(
            'SectionH3Table',
            parent=h3_style,
            keepWithNext=False
        )
        h4_style = ParagraphStyle(
            'SectionH4',
            parent=styles['Normal'],
            fontName=bold_font,
            fontSize=10.5,
            leading=13.5,
            textColor=colors.HexColor("#475569"),
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName=base_font,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=6
        )
        bullet_style = ParagraphStyle(
            'Bullet',
            parent=styles['Normal'],
            fontName=base_font,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            leftIndent=16,
            firstLineIndent=-12,
            spaceAfter=3
        )
        callout_style = ParagraphStyle(
            'Callout',
            parent=styles['Normal'],
            fontName=italic_font,
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#475569"),
            leftIndent=12,
            spaceAfter=6
        )
        code_style = ParagraphStyle(
            'Code',
            parent=styles['Normal'],
            fontName="Courier",
            fontSize=8.0,
            leading=10.5,
            textColor=colors.HexColor("#0f172a")
        )
        table_hdr_style = ParagraphStyle(
            'TableHdr',
            parent=styles['Normal'],
            fontName=bold_font,
            fontSize=8.5,
            leading=11,
            textColor=colors.white
        )
        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName=base_font,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1e293b")
        )
        table_hdr_compact_style = ParagraphStyle(
            'TableHdrCompact',
            parent=styles['Normal'],
            fontName=bold_font,
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white
        )
        table_cell_compact_style = ParagraphStyle(
            'TableCellCompact',
            parent=styles['Normal'],
            fontName=base_font,
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1e293b")
        )

        story = []

        # Document Opening Header (Title Section)
        story.append(Paragraph("PRODUCT REQUIREMENTS DOCUMENT", category_style))
        story.append(Paragraph(doc.metadata.title, title_style))

        meta_items = [
            f"<b>Version:</b> {doc.metadata.version_number}",
            f"<b>Status:</b> {doc.metadata.status.upper()}",
            f"<b>Date:</b> {doc.metadata.created_at.strftime('%Y-%m-%d')}"
        ]
        if doc.metadata.job_id:
            meta_items.append(f"<b>Job ID:</b> <font face='Courier'>{doc.metadata.job_id[:18]}...</font>")
        meta_html = " &nbsp;|&nbsp; ".join(meta_items)
        if doc.metadata.content_hash:
            meta_html += f"<br/><b>SHA-256 Digest:</b> <font face='Courier'>{doc.metadata.content_hash}</font>"
        story.append(Paragraph(meta_html, meta_style))
        story.append(Spacer(1, 8))

        # Render Sections
        for sec in doc.sections:
            first_block = sec.blocks[0] if sec.blocks else None
            sec_h_style = h1_table_style if isinstance(first_block, TableNode) else h1_style
            story.append(Paragraph(sec.title, sec_h_style))

            if sec.is_na:
                na_txt = f"<i>[Section marked Not Applicable: {sec.na_rationale or 'Omitted from baseline product scope'}]</i>"
                story.append(Paragraph(na_txt, callout_style))
                story.append(Spacer(1, 6))
                continue

            for b_idx, block in enumerate(sec.blocks):
                next_block = sec.blocks[b_idx + 1] if b_idx + 1 < len(sec.blocks) else None
                follow_table = isinstance(next_block, TableNode)

                if isinstance(block, HeadingNode):
                    if block.level <= 2:
                        h_st = h2_table_style if follow_table else h2_style
                    elif block.level == 3:
                        h_st = h3_table_style if follow_table else h3_style
                    else:
                        h_st = h4_style
                    story.append(Paragraph(clean_xml_text(block.text), h_st))

                elif isinstance(block, ParagraphNode):
                    clean_p = clean_xml_text(block.text)
                    story.append(Paragraph(clean_p, body_style))

                elif isinstance(block, TableNode):
                    if not block.headers:
                        continue
                    num_cols = len(block.headers)
                    col_widths = compute_pdf_table_col_widths(block.headers, block.rows, avail_width)

                    is_wide = num_cols >= 7
                    hdr_style = table_hdr_compact_style if is_wide else table_hdr_style
                    cell_style = table_cell_compact_style if is_wide else table_cell_style
                    pad_h = 2.0 if is_wide else 4.5
                    pad_v = 2.5 if is_wide else 3.5

                    table_flow_data = []
                    # Header row
                    hdr_cells = [Paragraph(clean_xml_text(h), hdr_style) for h in block.headers]
                    table_flow_data.append(hdr_cells)

                    # Data rows
                    for r in block.rows:
                        row_cells = []
                        for cell_str in r:
                            cell_p = Paragraph(clean_xml_text(cell_str), cell_style)
                            row_cells.append(cell_p)
                        while len(row_cells) < num_cols:
                            row_cells.append(Paragraph("", cell_style))
                        table_flow_data.append(row_cells[:num_cols])

                    ts = [
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), pad_v),
                        ('TOPPADDING', (0, 0), (-1, -1), pad_v),
                        ('LEFTPADDING', (0, 0), (-1, -1), pad_h),
                        ('RIGHTPADDING', (0, 0), (-1, -1), pad_h),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ]
                    for r_idx in range(len(block.rows)):
                        bg_c = colors.HexColor("#f8fafc") if r_idx % 2 == 1 else colors.white
                        ts.append(('BACKGROUND', (0, r_idx + 1), (-1, r_idx + 1), bg_c))

                    pdf_table = Table(
                        table_flow_data,
                        colWidths=col_widths,
                        repeatRows=1,
                        splitByRow=1
                    )
                    pdf_table.setStyle(TableStyle(ts))
                    story.append(pdf_table)
                    story.append(Spacer(1, 8))

                elif isinstance(block, ListNode):
                    for idx, itm in enumerate(block.items):
                        bullet_prefix = f"{idx + 1}. " if block.ordered else "&bull; "
                        p_txt = f"{bullet_prefix}{clean_xml_text(itm)}"
                        story.append(Paragraph(p_txt, bullet_style))

                elif isinstance(block, (CodeBlockNode, DiagramNode)):
                    lines = block.code.splitlines()
                    formatted_lines = []
                    for l in lines:
                        escaped = l.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        num_leading = len(l) - len(l.lstrip(' '))
                        if num_leading > 0:
                            escaped = ('&nbsp;' * num_leading) + escaped[num_leading:]
                        formatted_lines.append(escaped)
                    code_html = '<br/>'.join(formatted_lines)
                    code_p = Paragraph(code_html, code_style)
                    code_box = Table([[code_p]], colWidths=[avail_width])
                    code_box.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ]))
                    story.append(code_box)
                    story.append(Spacer(1, 6))

                elif isinstance(block, CalloutNode):
                    story.append(Paragraph(f"<i>&gt; {clean_xml_text(block.text)}</i>", callout_style))

        doc_template.build(story, canvasmaker=NumberedCanvas)
        return filepath

        doc_template.build(story, canvasmaker=NumberedCanvas)
        return filepath

    def export_pdf(self, prd_version: PRDVersion, project_title: str) -> Path:
        """Export PRD version to PDF via Document IR."""
        filename = f"PRD_{prd_version.project_id[:8]}_{prd_version.version_number}.pdf"
        doc = DocumentParser.parse_prd(prd_version, project_title)
        return self.export_document_to_pdf(doc, filename)
