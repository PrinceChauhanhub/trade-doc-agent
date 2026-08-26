"""Bill of lading — two layout variants (ocean B/L style)."""

from __future__ import annotations

import random
from pathlib import Path

from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from generator.defects import DocumentSet
from generator.models import CargoType
from generator.renderers.base import (
    BOX_STYLE,
    STYLES,
    build_pdf,
    content_width,
    field,
    header,
)


def _bl_values(docs: DocumentSet) -> dict:
    """Resolve printed values, applying any document-level overrides."""
    bl = docs.bill_of_lading

    gross = (
        docs.bl_gross_weight_override
        if docs.bl_gross_weight_override is not None
        else bl.total_gross_weight_kg
    )
    packages = (
        docs.bl_package_count_override
        if docs.bl_package_count_override is not None
        else bl.total_packages
    )
    description = (
        docs.bl_goods_description_override
        if docs.bl_goods_description_override is not None
        else bl.goods_summary.upper()
    )
    return {
        "gross": gross,
        "packages": packages,
        "description": description,
    }


def _cargo_table(docs: DocumentSet, terse_labels: bool) -> Table:
    bl = docs.bill_of_lading
    values = _bl_values(docs)
    width = content_width()

    if terse_labels:
        head = ["Marks & Nos", "Pkgs", "Description of Goods", "Gross Wt", "Measurement"]
    else:
        head = [
            "Container / Seal Numbers, Marks & Numbers",
            "No. of Pkgs",
            "Description of Packages and Goods",
            "Gross Weight (KG)",
            "Measurement (CBM)",
        ]

    marks = (
        f"{bl.container.number}<br/>Seal: {bl.container.seal_number}<br/>"
        f"{bl.container.size_type}"
    )
    package_types = ", ".join(sorted({p.package_type for p in bl.packages}))

    rows = [
        [Paragraph(h, STYLES["cell_header"]) for h in head],
        [
            Paragraph(marks, STYLES["cell"]),
            Paragraph(f"{values['packages']}<br/>{package_types}", STYLES["cell"]),
            Paragraph(
                f"{values['description']}<br/><br/>"
                f"SHIPPER'S LOAD, STOW, WEIGHT AND COUNT<br/>"
                f"FREIGHT {'PREPAID' if bl.incoterms.value in ('CIF', 'CFR') else 'COLLECT'}",
                STYLES["cell"],
            ),
            Paragraph(f"{values['gross']:,.3f}", STYLES["cell"]),
            Paragraph(f"{bl.total_cbm:,.3f}", STYLES["cell"]),
        ],
    ]

    table = Table(
        rows,
        colWidths=[width * w for w in (0.22, 0.12, 0.36, 0.15, 0.15)],
        rowHeights=[None, 90],
    )
    style = TableStyle(
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
    table.setStyle(style)
    return table


def _variant_a(docs: DocumentSet) -> list:
    """Classic boxed ocean bill of lading."""
    bl = docs.bill_of_lading
    width = content_width()

    is_house = bl.cargo_type == CargoType.LCL and docs.include_house_bl
    doc_title = "HOUSE BILL OF LADING" if is_house else "BILL OF LADING"
    bl_number = (
        bl.house_bl_number if is_house and bl.house_bl_number else bl.master_bl_number
    )

    flow = header(doc_title, "FOR COMBINED TRANSPORT OR PORT TO PORT SHIPMENT")

    top = Table(
        [
            [
                field("Shipper", bl.exporter.as_block()),
                field("B/L No.", bl_number),
            ],
            [
                field("Consignee", bl.importer.as_block()),
                field("Date of Issue", bl.dates.bl_date.strftime("%d %b %Y")),
            ],
            [
                field(
                    "Notify Party",
                    (bl.notify_party.as_block() if bl.notify_party else "SAME AS CONSIGNEE"),
                ),
                field("Place of Receipt", f"{bl.port_of_loading_name}, {bl.origin_country}"),
            ],
        ],
        colWidths=[width * 0.62, width * 0.38],
    )
    top.setStyle(BOX_STYLE)
    flow.append(top)
    flow.append(Spacer(1, 6))

    voyage = Table(
        [
            [
                field("Vessel", bl.vessel.name),
                field("Voyage No.", bl.vessel.voyage_number),
                field("IMO No.", bl.vessel.imo),
            ],
            [
                field("Port of Loading", f"{bl.port_of_loading_name} ({bl.port_of_loading})"),
                field("Port of Discharge", f"{bl.port_of_discharge_name} ({bl.port_of_discharge})"),
                field("Place of Delivery", bl.port_of_discharge_name),
            ],
        ],
        colWidths=[width / 3] * 3,
    )
    voyage.setStyle(BOX_STYLE)
    flow.append(voyage)
    flow.append(Spacer(1, 6))

    flow.append(_cargo_table(docs, terse_labels=False))
    flow.append(Spacer(1, 8))

    flow.append(
        Paragraph(
            "RECEIVED by the Carrier the goods specified above in apparent good order "
            "and condition unless otherwise stated, to be transported to such place as "
            "agreed, authorised or permitted herein.",
            STYLES["footer"],
        )
    )
    flow.append(Spacer(1, 10))

    footer_row = Table(
        [
            [
                field("Place and Date of Issue", f"{bl.port_of_loading_name}, {bl.dates.bl_date.strftime('%d %b %Y')}"),
                field("Number of Original B/L", "THREE (3)"),
            ]
        ],
        colWidths=[width * 0.6, width * 0.4],
    )
    footer_row.setStyle(BOX_STYLE)
    flow.append(footer_row)
    flow.append(Spacer(1, 16))
    flow.append(Paragraph("As Agent for the Carrier", STYLES["footer"]))

    return flow


def _variant_b(docs: DocumentSet) -> list:
    """Compact carrier-style layout with terse labels."""
    bl = docs.bill_of_lading
    values = _bl_values(docs)
    width = content_width()

    is_house = bl.cargo_type == CargoType.LCL and docs.include_house_bl
    bl_number = (
        bl.house_bl_number if is_house and bl.house_bl_number else bl.master_bl_number
    )

    flow = [
        Paragraph("SEA WAYBILL / BILL OF LADING", STYLES["title"]),
        Paragraph(f"B/L No. {bl_number}", STYLES["subtitle"]),
        Spacer(1, 4),
    ]

    grid = Table(
        [
            [field("Shipper", bl.exporter.as_block()), field("Consignee", bl.importer.as_block())],
            [
                field("Vessel / Voy", f"{bl.vessel.name} / {bl.vessel.voyage_number}"),
                field("IMO", bl.vessel.imo),
            ],
            [
                field("POL", f"{bl.port_of_loading} — {bl.port_of_loading_name}"),
                field("POD", f"{bl.port_of_discharge} — {bl.port_of_discharge_name}"),
            ],
            [
                field("Shipped on Board", bl.dates.bl_date.strftime("%d/%m/%Y")),
                field("ETA", bl.dates.eta.strftime("%d/%m/%Y")),
            ],
        ],
        colWidths=[width * 0.5, width * 0.5],
    )
    grid.setStyle(BOX_STYLE)
    flow.append(grid)
    flow.append(Spacer(1, 6))

    flow.append(_cargo_table(docs, terse_labels=True))
    flow.append(Spacer(1, 8))

    totals = Table(
        [
            [
                Paragraph("<b>Total Pkgs</b>", STYLES["cell"]),
                Paragraph(str(values["packages"]), STYLES["cell"]),
                Paragraph("<b>Total G.W.</b>", STYLES["cell"]),
                Paragraph(f"{values['gross']:,.3f} KG", STYLES["cell"]),
                Paragraph("<b>Total Meas.</b>", STYLES["cell"]),
                Paragraph(f"{bl.total_cbm:,.3f} CBM", STYLES["cell"]),
            ]
        ],
        colWidths=[width / 6] * 6,
    )
    totals.setStyle(BOX_STYLE)
    flow.append(totals)
    flow.append(Spacer(1, 14))

    flow.append(
        Paragraph(
            "Carrier's liability limited as per terms and conditions on the reverse hereof. "
            "Particulars furnished by shipper.",
            STYLES["footer"],
        )
    )
    flow.append(Spacer(1, 18))
    flow.append(Paragraph("Signed for the Carrier", STYLES["footer"]))

    return flow


VARIANTS = [_variant_a, _variant_b]


def render(docs: DocumentSet, out_dir: Path, rng: random.Random) -> Path:
    path = out_dir / "bill_of_lading.pdf"
    variant = rng.choice(VARIANTS)
    build_pdf(path, variant(docs), title="Bill of Lading")
    return path