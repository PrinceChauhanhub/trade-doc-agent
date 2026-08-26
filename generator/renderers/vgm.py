"""VGM (Verified Gross Mass) certificate — SOLAS Chapter VI Regulation 2."""

from __future__ import annotations

import random
from decimal import Decimal
from pathlib import Path

from reportlab.platypus import Paragraph, Spacer, Table

from generator.defects import DocumentSet
from generator.renderers.base import (
    BOX_STYLE,
    STYLES,
    build_pdf,
    content_width,
    field,
    header,
)

WEIGHBRIDGES = [
    ("Nhava Sheva Weighbridge Services", "WB/MH/0284"),
    ("Adani Mundra Terminal Weighbridge", "WB/GJ/0117"),
    ("Chennai Port Trust Weighbridge", "WB/TN/0339"),
    ("Cochin Container Terminal", "WB/KL/0092"),
]


def _body(docs: DocumentSet, rng: random.Random) -> list:
    vgm_doc = docs.vgm
    width = content_width()
    facility, licence = rng.choice(WEIGHBRIDGES)

    cargo_weight = vgm_doc.total_gross_weight_kg
    tare = vgm_doc.container.tare_weight_kg
    verified = vgm_doc.container.vgm_kg

    flow = header(
        "VERIFIED GROSS MASS (VGM) CERTIFICATE",
        "SOLAS CHAPTER VI, REGULATION 2 — SHIPPER'S DECLARATION",
    )

    top = Table(
        [
            [
                field("Shipper (Responsible Party)", vgm_doc.exporter.as_block()),
                field(
                    "Booking / B/L Reference",
                    f"{vgm_doc.booking_number}<br/>{vgm_doc.master_bl_number}",
                ),
            ]
        ],
        colWidths=[width * 0.62, width * 0.38],
    )
    top.setStyle(BOX_STYLE)
    flow.append(top)
    flow.append(Spacer(1, 6))

    container = Table(
        [
            [
                field("Container No.", vgm_doc.container.number),
                field("Container Type", vgm_doc.container.size_type),
                field("Seal No.", vgm_doc.container.seal_number),
            ],
            [
                field("Vessel / Voyage", f"{vgm_doc.vessel.name} / {vgm_doc.vessel.voyage_number}"),
                field("Port of Loading", vgm_doc.port_of_loading_name),
                field("Port of Discharge", vgm_doc.port_of_discharge_name),
            ],
        ],
        colWidths=[width / 3] * 3,
    )
    container.setStyle(BOX_STYLE)
    flow.append(container)
    flow.append(Spacer(1, 6))

    weights = Table(
        [
            [
                field("Cargo Gross Weight (KG)", f"{cargo_weight:,.3f}"),
                field("Container Tare Weight (KG)", f"{tare:,.3f}"),
                field("VERIFIED GROSS MASS (KG)", f"{verified:,.3f}"),
            ]
        ],
        colWidths=[width / 3] * 3,
    )
    weights.setStyle(BOX_STYLE)
    flow.append(weights)
    flow.append(Spacer(1, 6))

    method = Table(
        [
            [
                field(
                    "Method of Determination",
                    "Method 1 — Weighing the packed container at a calibrated weighbridge",
                ),
                field("Weighing Facility", f"{facility}<br/>Licence: {licence}"),
            ],
            [
                field("Date of Weighing", vgm_doc.dates.cargo_received_date.strftime("%d %b %Y")),
                field("Weighbridge Ticket No.", f"WT{rng.randint(1000000, 9999999)}"),
            ],
        ],
        colWidths=[width * 0.55, width * 0.45],
    )
    method.setStyle(BOX_STYLE)
    flow.append(method)
    flow.append(Spacer(1, 10))

    flow.append(
        Paragraph(
            "I, the undersigned, being duly authorised by the shipper named above, hereby "
            "declare that the verified gross mass stated herein has been obtained using an "
            "approved method and is accurate to the best of my knowledge, as required under "
            "SOLAS Chapter VI Regulation 2, paragraphs 4 to 6.",
            STYLES["value"],
        )
    )
    flow.append(Spacer(1, 20))

    sign = Table(
        [
            [
                field("Name of Authorised Person", vgm_doc.exporter.contact_name or "Authorised Signatory"),
                field("Date", vgm_doc.dates.cargo_received_date.strftime("%d/%m/%Y")),
            ]
        ],
        colWidths=[width * 0.6, width * 0.4],
    )
    sign.setStyle(BOX_STYLE)
    flow.append(sign)

    return flow


def render(docs: DocumentSet, out_dir: Path, rng: random.Random) -> Path:
    path = out_dir / "vgm_certificate.pdf"
    build_pdf(path, _body(docs, rng), title="VGM Certificate")
    return path