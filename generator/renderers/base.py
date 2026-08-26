"""Shared PDF building blocks (ReportLab)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_SIZE = A4
MARGIN = 15 * mm

_base = getSampleStyleSheet()

STYLES = {
    "title": ParagraphStyle(
        "DocTitle",
        parent=_base["Title"],
        fontSize=16,
        spaceAfter=4,
        alignment=TA_CENTER,
    ),
    "subtitle": ParagraphStyle(
        "DocSubtitle",
        parent=_base["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor("#555555"),
        alignment=TA_CENTER,
        spaceAfter=10,
    ),
    "label": ParagraphStyle(
        "Label",
        parent=_base["Normal"],
        fontSize=7,
        textColor=colors.HexColor("#666666"),
        spaceAfter=1,
    ),
    "value": ParagraphStyle(
        "Value",
        parent=_base["Normal"],
        fontSize=8.5,
        leading=11,
    ),
    "bold": ParagraphStyle(
        "BoldValue",
        parent=_base["Normal"],
        fontSize=8.5,
        leading=11,
        fontName="Helvetica-Bold",
    ),
    "cell": ParagraphStyle(
        "Cell",
        parent=_base["Normal"],
        fontSize=7.5,
        leading=9.5,
        alignment=TA_LEFT,
    ),
    "cell_header": ParagraphStyle(
        "CellHeader",
        parent=_base["Normal"],
        fontSize=7.5,
        leading=9.5,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    ),
    "footer": ParagraphStyle(
        "Footer",
        parent=_base["Normal"],
        fontSize=6.5,
        textColor=colors.HexColor("#888888"),
    ),
}

GRID_STYLE = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
)

BOX_STYLE = TableStyle(
    [
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
)


def money(value: Decimal, currency: str = "") -> str:
    formatted = f"{value:,.2f}"
    return f"{currency} {formatted}".strip()


def weight(value: Decimal, unit: str = "KG") -> str:
    return f"{value:,.3f} {unit}"


def field(label: str, value: str) -> list:
    """A stacked label + value pair for use inside a layout table."""
    return [
        Paragraph(label.upper(), STYLES["label"]),
        Paragraph(value.replace("\n", "<br/>"), STYLES["value"]),
    ]


def build_pdf(path: Path, flowables: list, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=title,
        author="trade-doc-agent",
    )
    doc.build(flowables)


def header(title: str, subtitle: str = "") -> list:
    items = [Paragraph(title, STYLES["title"])]
    if subtitle:
        items.append(Paragraph(subtitle, STYLES["subtitle"]))
    items.append(Spacer(1, 4))
    return items


def two_column(left: list, right: list, widths: tuple[float, float] = (0.5, 0.5)) -> Table:
    """Place two stacks of flowables side by side."""
    available = PAGE_SIZE[0] - 2 * MARGIN
    table = Table(
        [[left, right]],
        colWidths=[available * widths[0], available * widths[1]],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def content_width() -> float:
    return PAGE_SIZE[0] - 2 * MARGIN