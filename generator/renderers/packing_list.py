"""Packing list — two layout variants."""

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
    two_column,
    weight,
)


def _package_table(docs: DocumentSet, abbreviated: bool) -> Table:
    pl = docs.packing_list
    width = content_width()

    if abbreviated:
        head = ["Marks", "Type", "Pkgs", "Dims (cm)", "N.W./pkg", "G.W./pkg", "CBM"]
    else:
        head = [
            "Marks & Numbers",
            "Package Type",
            "No. of Packages",
            "Dimensions L×W×H (cm)",
            "Net Wt/Pkg (KG)",
            "Gross Wt/Pkg (KG)",
            "Volume (CBM)",
        ]

    widths = [0.15, 0.13, 0.11, 0.21, 0.13, 0.14, 0.13]
    rows = [[Paragraph(h, STYLES["cell_header"]) for h in head]]

    for pkg in pl.packages:
        rows.append(
            [
                Paragraph(pkg.marks, STYLES["cell"]),
                Paragraph(pkg.package_type, STYLES["cell"]),
                Paragraph(str(pkg.count), STYLES["cell"]),
                Paragraph(
                    f"{pkg.length_cm:g} × {pkg.width_cm:g} × {pkg.height_cm:g}",
                    STYLES["cell"],
                ),
                Paragraph(f"{pkg.net_weight_kg:,.3f}", STYLES["cell"]),
                Paragraph(f"{pkg.gross_weight_kg:,.3f}", STYLES["cell"]),
                Paragraph(f"{pkg.cbm:,.3f}", STYLES["cell"]),
            ]
        )

    rows.append(
        [
            Paragraph("<b>TOTAL</b>", STYLES["cell"]),
            Paragraph("", STYLES["cell"]),
            Paragraph(f"<b>{pl.total_packages}</b>", STYLES["cell"]),
            Paragraph("", STYLES["cell"]),
            Paragraph(f"<b>{pl.total_net_weight_kg:,.3f}</b>", STYLES["cell"]),
            Paragraph(f"<b>{pl.total_gross_weight_kg:,.3f}</b>", STYLES["cell"]),
            Paragraph(f"<b>{pl.total_cbm:,.3f}</b>", STYLES["cell"]),
        ]
    )

    table = Table(rows, colWidths=[width * w for w in widths], repeatRows=1)
    style = TableStyle(GRID_STYLE.getCommands())
    style.add("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eeeeee"))
    table.setStyle(style)
    return table


def _packing_note(docs: DocumentSet) -> Paragraph:
    pl = docs.packing_list
    types = {p.package_type for p in pl.packages}

    if pl.has_wooden_packaging:
        note = (
            f"Packing: {', '.join(sorted(types)).lower()} on wooden pallets. "
            "Wood packaging material as per ISPM-15."
        )
    else:
        note = (
            f"Packing: {', '.join(sorted(types)).lower()}. "
            "No wood packaging material used."
        )

    return Paragraph(note, STYLES["value"])


def _variant_a(docs: DocumentSet) -> list:
    pl = docs.packing_list
    width = content_width()

    flow = header("PACKING LIST", pl.exporter.name.upper())

    parties = Table(
        [
            [
                field("Shipper", pl.exporter.as_block()),
                field("Consignee", pl.importer.as_block()),
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
                field("Invoice No.", pl.invoice_number),
                field("Date", pl.dates.invoice_date.strftime("%d %b %Y")),
                field("Container No.", pl.container.number),
            ],
            [
                field("Vessel / Voyage", f"{pl.vessel.name} / {pl.vessel.voyage_number}"),
                field("Port of Loading", pl.port_of_loading_name),
                field("Port of Discharge", pl.port_of_discharge_name),
            ],
        ],
        colWidths=[width / 3] * 3,
    )
    meta.setStyle(BOX_STYLE)
    flow.append(meta)
    flow.append(Spacer(1, 8))

    flow.append(_package_table(docs, abbreviated=False))
    flow.append(Spacer(1, 8))
    flow.append(_packing_note(docs))
    flow.append(Spacer(1, 20))
    flow.append(Paragraph(f"For {pl.exporter.name}", STYLES["bold"]))
    flow.append(Spacer(1, 18))
    flow.append(Paragraph("Authorised Signatory", STYLES["footer"]))

    return flow


def _variant_b(docs: DocumentSet) -> list:
    """Summary-first layout with abbreviated column labels."""
    pl = docs.packing_list

    flow = [
        Paragraph(pl.exporter.name.upper(), STYLES["title"]),
        Paragraph("PACKING LIST", STYLES["subtitle"]),
        Spacer(1, 6),
    ]

    left = [
        Paragraph("<b>Consignee</b>", STYLES["value"]),
        Paragraph(pl.importer.as_block().replace("\n", "<br/>"), STYLES["value"]),
    ]
    right = [
        Paragraph(f"<b>Ref:</b> {pl.invoice_number}", STYLES["value"]),
        Paragraph(f"<b>Date:</b> {pl.dates.invoice_date.strftime('%d/%m/%Y')}", STYLES["value"]),
        Paragraph(
            f"<b>Container:</b> {pl.container.number} / {pl.container.size_type}",
            STYLES["value"],
        ),
        Paragraph(f"<b>Seal:</b> {pl.container.seal_number}", STYLES["value"]),
    ]
    flow.append(two_column(left, right, widths=(0.55, 0.45)))
    flow.append(Spacer(1, 10))

    flow.append(
        Paragraph(
            f"<b>Total Packages:</b> {pl.total_packages} &nbsp;&nbsp;·&nbsp;&nbsp; "
            f"<b>Total N.W.:</b> {weight(pl.total_net_weight_kg)} &nbsp;&nbsp;·&nbsp;&nbsp; "
            f"<b>Total G.W.:</b> {weight(pl.total_gross_weight_kg)} &nbsp;&nbsp;·&nbsp;&nbsp; "
            f"<b>Total CBM:</b> {pl.total_cbm:,.3f}",
            STYLES["value"],
        )
    )
    flow.append(Spacer(1, 10))

    flow.append(_package_table(docs, abbreviated=True))
    flow.append(Spacer(1, 8))
    flow.append(_packing_note(docs))
    flow.append(Spacer(1, 24))
    flow.append(Paragraph("____________________________", STYLES["value"]))
    flow.append(Paragraph("Signature &amp; Stamp", STYLES["footer"]))

    return flow


VARIANTS = [_variant_a, _variant_b]


def render(docs: DocumentSet, out_dir: Path, rng: random.Random) -> Path:
    path = out_dir / "packing_list.pdf"
    variant = rng.choice(VARIANTS)
    build_pdf(path, variant(docs), title="Packing List")
    return path