"""
Report Generation.

Accepts a list of already-generated interpretation blocks (the frontend
accumulates these as the user runs each module) and compiles them into
either a DOCX or a PDF. A section can optionally carry:
  - a `chart` spec — a real chart image, rendered server-side (chart_service)
  - one or more `tables` — real formatted tables (e.g. descriptive statistics,
    a correlation matrix), not just narrative text
"""
from io import BytesIO
from typing import Optional
import logging

from docx import Document
from docx.shared import Inches, Pt
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus import Table as RLTable
from reportlab.platypus import TableStyle

from app.routers.auth import require_verified_user
from app.services import chart_service

logger = logging.getLogger(__name__)


class ChartSpec(BaseModel):
    dataset_id: str
    chart_type: str  # "line" | "scatter" | "bar" | "heatmap"
    columns: list[str]
    title: str = ""


class TableSpec(BaseModel):
    title: str = ""
    headers: list[str]
    rows: list[list[str]]


class ReportSection(BaseModel):
    title: str
    text: str
    chart: Optional[ChartSpec] = None
    tables: Optional[list[TableSpec]] = None


class ReportRequest(BaseModel):
    project_title: str = "StatScholar Report"
    sections: list[ReportSection]


router = APIRouter(prefix="/report", tags=["Report Generation"])


def _render_chart_safe(chart: ChartSpec, owner_id: int) -> Optional[bytes]:
    """Never let a bad/stale chart spec take down the whole export — if the
    dataset was cleared, doesn't belong to this user, or the columns no
    longer match, skip the image rather than fail the report the user is
    trying to download. The failure is still logged (not just swallowed),
    so a silently-dropped chart shows up in the backend's terminal output
    instead of vanishing without a trace."""
    if chart is None:
        return None
    try:
        return chart_service.render_chart(chart.dataset_id, chart.chart_type, chart.columns, owner_id, chart.title)
    except Exception:
        logger.exception(
            "Chart rendering failed for report export — dataset_id=%s chart_type=%s columns=%s title=%r",
            chart.dataset_id, chart.chart_type, chart.columns, chart.title,
        )
        return None


@router.post("/export/docx")
async def export_docx(req: ReportRequest, current_user: dict = Depends(require_verified_user)):
    doc = Document()
    doc.add_heading(req.project_title, level=1)
    for section in req.sections:
        doc.add_heading(section.title, level=2)
        doc.add_paragraph(section.text)

        image_bytes = _render_chart_safe(section.chart, current_user["id"])
        if image_bytes:
            doc.add_picture(BytesIO(image_bytes), width=Inches(5.5))

        for table_spec in (section.tables or []):
            if table_spec.title:
                p = doc.add_paragraph()
                run = p.add_run(table_spec.title)
                run.bold = True
                run.font.size = Pt(11)

            table = doc.add_table(rows=1 + len(table_spec.rows), cols=len(table_spec.headers))
            table.style = "Light Grid Accent 1"
            for j, h in enumerate(table_spec.headers):
                cell = table.rows[0].cells[j]
                cell.text = str(h)
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.bold = True
            for i, row in enumerate(table_spec.rows, start=1):
                for j, val in enumerate(row):
                    table.rows[i].cells[j].text = str(val)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=statscholar_report.docx"},
    )


# ReportLab's built-in fonts (Helvetica/Times, cp1252-based) don't include
# Greek letters or subscript digits, and render them as solid black boxes
# instead of erroring — silent corruption rather than a crash, so this needs
# handling explicitly rather than hoping the font copes. The interpretation
# engine's text uses R\u00b2 (\u00b2), \u03c4 (\u03c4), \u03c7\u00b2 (chi-square, \u03c7) and
# subscripts like r\u2081 (\u2081) — all mapped to plain-text equivalents below.
_PDF_CHAR_MAP = {
    "\u00b2": "^2",   # R² -> R^2
    "\u03c4": "tau",  # τ  -> tau
    "\u03c7": "chi",  # χ  -> chi
    "\u2080": "0", "\u2081": "1", "\u2082": "2", "\u2083": "3", "\u2084": "4",
    "\u2085": "5", "\u2086": "6", "\u2087": "7", "\u2088": "8", "\u2089": "9",
}


def sanitize_for_pdf(text: str) -> str:
    for bad, good in _PDF_CHAR_MAP.items():
        text = text.replace(bad, good)
    # Safety net for any other character outside the built-in font's
    # encoding that might show up later (e.g. a new stat symbol added to
    # the interpretation engine and not yet mapped above).
    try:
        text.encode("cp1252")
    except UnicodeEncodeError:
        text = text.encode("cp1252", errors="replace").decode("cp1252")
    return text


def _pdf_table(table_spec: TableSpec) -> RLTable:
    data = [[sanitize_for_pdf(h) for h in table_spec.headers]]
    for row in table_spec.rows:
        data.append([sanitize_for_pdf(str(v)) for v in row])

    table = RLTable(data, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E1D8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F7F2")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


@router.post("/export/pdf")
async def export_pdf(req: ReportRequest, current_user: dict = Depends(require_verified_user)):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(sanitize_for_pdf(req.project_title), styles["Title"]), Spacer(1, 16)]

    for section in req.sections:
        story.append(Paragraph(sanitize_for_pdf(section.title), styles["Heading2"]))
        story.append(Paragraph(sanitize_for_pdf(section.text), styles["Normal"]))

        image_bytes = _render_chart_safe(section.chart, current_user["id"])
        if image_bytes:
            story.append(Spacer(1, 8))
            story.append(RLImage(BytesIO(image_bytes), width=380, height=190))

        for table_spec in (section.tables or []):
            story.append(Spacer(1, 10))
            if table_spec.title:
                story.append(Paragraph(sanitize_for_pdf(table_spec.title), styles["Heading3"]))
            story.append(_pdf_table(table_spec))

        story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=statscholar_report.pdf"},
    )
