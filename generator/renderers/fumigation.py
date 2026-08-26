"""ISPM-15 fumigation / phytosanitary treatment certificate."""

from __future__ import annotations

import random
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

FUMIGATORS = [
    ("Pest Control (India) Pvt Ltd", "NSPM/AC/0142"),
    ("Bharat Fumigation Services", "NSPM/AC/0387"),
    ("Anchor Pest Solutions", "NSPM/AC/0511"),
    ("Coastal Fumigation Co", "NSPM/AC/0263"),
]


def _body(docs: DocumentSet, rng: random.Random) -> list:
    truth = docs.truth
    width = content_width()
    company, accreditation = rng.choice(FUMIGATORS)
    treatment_date = truth.dates.fumigation_date or truth.dates.cargo_received_date

    flow = header(
        "FUMIGATION CERTIFICATE",
        "TREATMENT OF WOOD PACKAGING MATERIAL — ISPM-15",
    )

    issuer = Table(
        [
            [
                field("Treatment Provider", f"{company}<br/>Accreditation: {accreditation}"),
                field("Certificate No.", f"FUM/{rng.randint(100000, 999999)}/2026"),
            ]
        ],
        colWidths=[width * 0.62, width * 0.38],
    )
    issuer.setStyle(BOX_STYLE)
    flow.append(issuer)
    flow.append(Spacer(1, 6))

    parties = Table(
        [
            [
                field("Exporter", truth.exporter.as_block()),
                field("Consignee", truth.importer.as_block()),
            ]
        ],
        colWidths=[width * 0.5, width * 0.5],
    )
    parties.setStyle(BOX_STYLE)
    flow.append(parties)
    flow.append(Spacer(1, 6))

    treatment = Table(
        [
            [
                field(
                    "Treatment Type",
                    rng.choice(["Methyl Bromide Fumigation", "Heat Treatment (HT)"]),
                ),
                field("Date of Treatment", treatment_date.strftime("%d %b %Y")),
                field("Duration", "24 hours"),
            ],
            [
                field(
                    "Dosage / Temperature",
                    rng.choice(["48 g/m³", "56°C core for 30 min"]),
                ),
                field("Place of Treatment", truth.exporter.city),
                field("Container No.", truth.container.number),
            ],
        ],
        colWidths=[width / 3] * 3,
    )
    treatment.setStyle(BOX_STYLE)
    flow.append(treatment)
    flow.append(Spacer(1, 6))

    package_types = ", ".join(sorted({p.package_type for p in truth.packages}))
    goods = Table(
        [
            [
                field(
                    "Description of Wood Packaging Material Treated",
                    f"{truth.total_packages} × {package_types.lower()} including wooden "
                    f"pallets, shipped under invoice {truth.invoice_number}",
                ),
            ]
        ],
        colWidths=[width],
    )
    goods.setStyle(BOX_STYLE)
    flow.append(goods)
    flow.append(Spacer(1, 10))

    flow.append(
        Paragraph(
            "This is to certify that the wood packaging material described above has been "
            "treated in accordance with ISPM-15 and bears the approved IPPC mark. The "
            "treatment was carried out under the supervision of the undersigned.",
            STYLES["value"],
        )
    )
    flow.append(Spacer(1, 22))
    flow.append(Paragraph(f"For {company}", STYLES["bold"]))
    flow.append(Spacer(1, 16))
    flow.append(Paragraph("Accredited Fumigation Operator", STYLES["footer"]))

    return flow


def render(docs: DocumentSet, out_dir: Path, rng: random.Random) -> Path | None:
    """Returns None when the certificate is deliberately absent."""
    if not docs.include_fumigation_cert:
        return None

    path = out_dir / "fumigation_certificate.pdf"
    build_pdf(path, _body(docs, rng), title="Fumigation Certificate")
    return path