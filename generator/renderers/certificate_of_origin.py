"""Certificate of origin — preferential (AI-ECTA) and non-preferential variants."""

from __future__ import annotations

import random
from pathlib import Path

from reportlab.platypus import Paragraph, Spacer, Table

from generator.defects import DocumentSet
from generator.renderers.base import (
    BOX_STYLE,
    GRID_STYLE,
    STYLES,
    build_pdf,
    content_width,
    field,
    header,
)

CHAMBERS = [
    "Bombay Chamber of Commerce and Industry",
    "Federation of Indian Export Organisations",
    "Madras Chamber of Commerce and Industry",
    "PHD Chamber of Commerce and Industry",
]


def _goods_table(docs: DocumentSet) -> Table:
    coo = docs.certificate_of_origin
    width = content_width()

    head = [
        "Item No.",
        "Marks & Numbers",
        "Description of Goods",
        "HS Code",
        "Quantity",
        "Invoice No. & Date",
    ]
    rows = [[Paragraph(h, STYLES["cell_header"]) for h in head]]

    for index, item in enumerate(coo.line_items, start=1):
        marks = coo.packages[index - 1].marks if index <= len(coo.packages) else "-"
        rows.append(
            [
                Paragraph(str(index), STYLES["cell"]),
                Paragraph(marks, STYLES["cell"]),
                Paragraph(item.description, STYLES["cell"]),
                Paragraph(item.hs_code, STYLES["cell"]),
                Paragraph(f"{item.quantity:,} {item.unit}", STYLES["cell"]),
                Paragraph(
                    f"{coo.invoice_number}<br/>{coo.dates.invoice_date.strftime('%d %b %Y')}",
                    STYLES["cell"],
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[width * w for w in (0.08, 0.14, 0.32, 0.12, 0.14, 0.20)],
        repeatRows=1,
    )
    table.setStyle(GRID_STYLE)
    return table


def _variant_preferential(docs: DocumentSet, rng: random.Random) -> list:
    coo = docs.certificate_of_origin
    width = content_width()

    flow = header(
        "CERTIFICATE OF ORIGIN",
        "INDIA–AUSTRALIA ECONOMIC COOPERATION AND TRADE AGREEMENT (AI-ECTA)",
    )

    top = Table(
        [
            [
                field("1. Exporter (Name, Address, Country)", coo.exporter.as_block()),
                field("Reference No.", coo.coo_number),
            ],
            [
                field("2. Consignee (Name, Address, Country)", coo.importer.as_block()),
                field("3. Country of Origin", coo.origin_country.upper()),
            ],
        ],
        colWidths=[width * 0.64, width * 0.36],
    )
    top.setStyle(BOX_STYLE)
    flow.append(top)
    flow.append(Spacer(1, 6))

    transport = Table(
        [
            [
                field(
                    "4. Means of Transport and Route",
                    f"By sea — {coo.vessel.name} V.{coo.vessel.voyage_number}<br/>"
                    f"From {coo.port_of_loading_name} to {coo.port_of_discharge_name}",
                ),
                field("5. Date of Departure", coo.dates.etd.strftime("%d %b %Y")),
            ]
        ],
        colWidths=[width * 0.64, width * 0.36],
    )
    transport.setStyle(BOX_STYLE)
    flow.append(transport)
    flow.append(Spacer(1, 6))

    flow.append(_goods_table(docs))
    flow.append(Spacer(1, 8))

    flow.append(
        Paragraph(
            "<b>Declaration by the Exporter</b><br/>"
            "The undersigned hereby declares that the above details and statements are "
            "correct, that all the goods were produced in "
            f"{coo.origin_country.upper()} and that they comply with the origin "
            "requirements specified for these goods under the AI-ECTA.",
            STYLES["value"],
        )
    )
    flow.append(Spacer(1, 12))

    certify = Table(
        [
            [
                field(
                    "Place and Date, Signature of Authorised Signatory",
                    f"{coo.exporter.city}, {coo.dates.coo_issue_date.strftime('%d %b %Y')}",
                ),
                field(
                    "Certification",
                    f"{rng.choice(CHAMBERS)}<br/>"
                    f"Issued on {coo.dates.coo_issue_date.strftime('%d %b %Y')}",
                ),
            ]
        ],
        colWidths=[width * 0.5, width * 0.5],
    )
    certify.setStyle(BOX_STYLE)
    flow.append(certify)

    return flow


def _variant_general(docs: DocumentSet, rng: random.Random) -> list:
    """Non-preferential chamber-issued certificate, simpler layout."""
    coo = docs.certificate_of_origin
    width = content_width()
    chamber = rng.choice(CHAMBERS)

    flow = [
        Paragraph(chamber.upper(), STYLES["title"]),
        Paragraph("NON-PREFERENTIAL CERTIFICATE OF ORIGIN", STYLES["subtitle"]),
        Spacer(1, 6),
    ]

    meta = Table(
        [
            [
                field("Certificate No.", coo.coo_number),
                field("Date of Issue", coo.dates.coo_issue_date.strftime("%d/%m/%Y")),
                field("Country of Origin", coo.origin_country.upper()),
            ]
        ],
        colWidths=[width / 3] * 3,
    )
    meta.setStyle(BOX_STYLE)
    flow.append(meta)
    flow.append(Spacer(1, 6))

    parties = Table(
        [
            [
                field("Exporter", coo.exporter.as_block()),
                field("Consignee", coo.importer.as_block()),
            ]
        ],
        colWidths=[width * 0.5, width * 0.5],
    )
    parties.setStyle(BOX_STYLE)
    flow.append(parties)
    flow.append(Spacer(1, 6))

    flow.append(_goods_table(docs))
    flow.append(Spacer(1, 10))

    flow.append(
        Paragraph(
            "It is hereby certified, on the basis of control carried out, that the goods "
            f"described above originate in {coo.origin_country.upper()}.",
            STYLES["value"],
        )
    )
    flow.append(Spacer(1, 20))
    flow.append(Paragraph(f"For {chamber}", STYLES["bold"]))
    flow.append(Spacer(1, 16))
    flow.append(Paragraph("Authorised Signatory &amp; Seal", STYLES["footer"]))

    return flow


def render(docs: DocumentSet, out_dir: Path, rng: random.Random) -> Path:
    path = out_dir / "certificate_of_origin.pdf"
    variant = rng.choice([_variant_preferential, _variant_general])
    build_pdf(path, variant(docs, rng), title="Certificate of Origin")
    return path