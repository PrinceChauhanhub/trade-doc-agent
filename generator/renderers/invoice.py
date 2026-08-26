"""Commercial invoice — two layout variants."""

from __future__ import annotations

import random
from pathlib import Path

from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from generator.defects import DocumentSet
from generator.renderers.base import (
    BOX_STYLE,
    GRID_STYLE,
    STYLES,
    build_pdf,
    content_width,
    field,
    header,
    money,
    two_column,
)


def _line_item_table(docs: DocumentSet, compact: bool) -> Table:
    inv = docs.invoice
    width = content_width()

    if compact:
        head = ["#", "Description of Goods", "HS Code", "Qty", "Rate", "Amount"]
        widths = [0.05, 0.42, 0.13, 0.10, 0.13, 0.17]
    else:
        head = ["Sr", "Goods Description", "H.S. Code", "Quantity", "Unit Price", "Total Value"]
        widths = [0.05, 0.38, 0.13, 0.12, 0.14, 0.18]

    rows = [[Paragraph(h, STYLES["cell_header"]) for h in head]]

    for index, item in enumerate(inv.line_items, start=1):
        rows.append(
            [
                Paragraph(str(index), STYLES["cell"]),
                Paragraph(item.description, STYLES["cell"]),
                Paragraph(item.hs_code, STYLES["cell"]),
                Paragraph(f"{item.quantity:,} {item.unit}", STYLES["cell"]),
                Paragraph(money(item.unit_price), STYLES["cell"]),
                Paragraph(money(item.line_total), STYLES["cell"]),
            ]
        )

    table = Table(rows, colWidths=[width * w for w in widths], repeatRows=1)
    table.setStyle(GRID_STYLE)
    return table


def _totals_block(docs: DocumentSet) -> Table:
    inv = docs.invoice
    printed_total = (
        docs.invoice_total_override
        if docs.invoice_total_override is not None
        else inv.invoice_total
    )

    rows = [["Goods Value", money(inv.goods_value, inv.currency)]]

    if inv.incoterms.value in ("CIF", "CFR"):
        rows.append(["Freight", money(inv.freight_charge, inv.currency)])
    if inv.incoterms.value == "CIF":
        rows.append(["Insurance", money(inv.insurance_charge, inv.currency)])

    rows.append([f"TOTAL ({inv.incoterms.value})", money(printed_total, inv.currency)])

    width = content_width()
    table = Table(
        [[Paragraph(a, STYLES["cell"]), Paragraph(b, STYLES["cell"])] for a, b in rows],
        colWidths=[width * 0.30, width * 0.22],
        hAlign="RIGHT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eeeeee")),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _variant_a(docs: DocumentSet) -> list:
    """Boxed shipper/consignee blocks, table below."""
    inv = docs.invoice
    width = content_width()

    flow = header("COMMERCIAL INVOICE", inv.exporter.name.upper())

    parties = Table(
        [
            [
                field("Shipper / Exporter", inv.exporter.as_block()),
                field("Consignee", inv.importer.as_block()),
            ]
        ],
        colWidths=[width * 0.5, width * 0.5],
    )
    parties.setStyle(BOX_STYLE)
    flow.append(parties)
    flow.append(Spacer(1, 6))

    meta = Table(
        [
            [
                field("Invoice No.", inv.invoice_number),
                field("Invoice Date", inv.dates.invoice_date.strftime("%d %b %Y")),
                field("Country of Origin", inv.origin_country),
            ],
            [
                field("Port of Loading", f"{inv.port_of_loading_name} ({inv.port_of_loading})"),
                field("Port of Discharge", f"{inv.port_of_discharge_name} ({inv.port_of_discharge})"),
                field("Terms of Delivery", inv.incoterms.value),
            ],
        ],
        colWidths=[width / 3] * 3,
    )
    meta.setStyle(BOX_STYLE)
    flow.append(meta)
    flow.append(Spacer(1, 8))

    flow.append(_line_item_table(docs, compact=True))
    flow.append(Spacer(1, 6))
    flow.append(_totals_block(docs))
    flow.append(Spacer(1, 14))

    flow.append(
        Paragraph(
            "We declare that this invoice shows the actual price of the goods "
            "described and that all particulars are true and correct.",
            STYLES["footer"],
        )
    )
    flow.append(Spacer(1, 18))
    flow.append(Paragraph(f"For {inv.exporter.name}", STYLES["bold"]))
    flow.append(Spacer(1, 20))
    flow.append(Paragraph("Authorised Signatory", STYLES["footer"]))

    return flow


def _variant_b(docs: DocumentSet) -> list:
    """Letterhead style, inline label/value pairs, abbreviated labels."""
    inv = docs.invoice

    flow = [
        Paragraph(inv.exporter.name.upper(), STYLES["title"]),
        Paragraph(
            f"{inv.exporter.address_line1}, {inv.exporter.city} {inv.exporter.postcode}, "
            f"{inv.exporter.country} &nbsp;|&nbsp; {inv.exporter.email or ''}",
            STYLES["subtitle"],
        ),
        Paragraph("COMMERCIAL INVOICE", STYLES["title"]),
        Spacer(1, 8),
    ]

    left = [
        Paragraph("<b>Buyer:</b>", STYLES["value"]),
        Paragraph(inv.importer.as_block().replace("\n", "<br/>"), STYLES["value"]),
    ]
    right = [
        Paragraph(f"<b>Inv. No:</b> {inv.invoice_number}", STYLES["value"]),
        Paragraph(f"<b>Dated:</b> {inv.dates.invoice_date.strftime('%d/%m/%Y')}", STYLES["value"]),
        Paragraph(f"<b>Origin:</b> {inv.origin_country}", STYLES["value"]),
        Paragraph(f"<b>POL:</b> {inv.port_of_loading_name}", STYLES["value"]),
        Paragraph(f"<b>POD:</b> {inv.port_of_discharge_name}", STYLES["value"]),
        Paragraph(f"<b>Terms:</b> {inv.incoterms.value}", STYLES["value"]),
        Paragraph(f"<b>Vessel:</b> {inv.vessel.name} V.{inv.vessel.voyage_number}", STYLES["value"]),
    ]

    flow.append(two_column(left, right, widths=(0.52, 0.48)))
    flow.append(Spacer(1, 10))
    flow.append(_line_item_table(docs, compact=False))
    flow.append(Spacer(1, 6))
    flow.append(_totals_block(docs))
    flow.append(Spacer(1, 16))

    flow.append(
        Paragraph(
            f"Amount chargeable in {inv.currency}. Payment against documents through bank.",
            STYLES["footer"],
        )
    )
    flow.append(Spacer(1, 22))
    flow.append(Paragraph("____________________________", STYLES["value"]))
    flow.append(Paragraph("Signature &amp; Company Stamp", STYLES["footer"]))

    return flow


VARIANTS = [_variant_a, _variant_b]


def render(docs: DocumentSet, out_dir: Path, rng: random.Random) -> Path:
    path = out_dir / "commercial_invoice.pdf"
    variant = rng.choice(VARIANTS)
    build_pdf(path, variant(docs), title="Commercial Invoice")
    return path