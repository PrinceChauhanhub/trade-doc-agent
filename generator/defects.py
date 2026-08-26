"""Inject discrepancies into per-document views of a shipment.

The ShipmentTruth object is never mutated. Each defect returns an
ExpectedFinding describing what a correct system should detect.
"""

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Callable

from generator.models import CargoType, ShipmentTruth


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"


class DefectType(str, Enum):
    ORIGIN_MISMATCH = "ORIGIN_MISMATCH"
    HS_DESCRIPTION_CONFLICT = "HS_DESCRIPTION_CONFLICT"
    WEIGHT_VARIANCE = "WEIGHT_VARIANCE"
    PACKAGE_COUNT_MISMATCH = "PACKAGE_COUNT_MISMATCH"
    INVOICE_ARITHMETIC_ERROR = "INVOICE_ARITHMETIC_ERROR"
    CONSIGNEE_MISMATCH = "CONSIGNEE_MISMATCH"
    CONTAINER_CHECK_DIGIT_INVALID = "CONTAINER_CHECK_DIGIT_INVALID"
    DATE_SEQUENCE_INVALID = "DATE_SEQUENCE_INVALID"
    MISSING_FUMIGATION_CERT = "MISSING_FUMIGATION_CERT"
    MISSING_HOUSE_BL = "MISSING_HOUSE_BL"
    HS_CODE_MISMATCH = "HS_CODE_MISMATCH"


@dataclass
class ExpectedFinding:
    """Ground truth: what the system should report for this document set."""

    type: DefectType
    severity: Severity
    summary: str
    sources: list[str]
    details: dict = field(default_factory=dict)


@dataclass
class DocumentSet:
    """Per-document views. Each may drift from the truth."""

    truth: ShipmentTruth
    invoice: ShipmentTruth
    packing_list: ShipmentTruth
    bill_of_lading: ShipmentTruth
    certificate_of_origin: ShipmentTruth
    vgm: ShipmentTruth

    include_fumigation_cert: bool = True
    include_house_bl: bool = True
    invoice_total_override: Decimal | None = None
    bl_gross_weight_override: Decimal | None = None
    bl_package_count_override: int | None = None
    bl_goods_description_override: str | None = None

    @classmethod
    def from_truth(cls, truth: ShipmentTruth) -> DocumentSet:
        return cls(
            truth=truth,
            invoice=deepcopy(truth),
            packing_list=deepcopy(truth),
            bill_of_lading=deepcopy(truth),
            certificate_of_origin=deepcopy(truth),
            vgm=deepcopy(truth),
            include_fumigation_cert=truth.has_wooden_packaging,
            include_house_bl=truth.cargo_type == CargoType.LCL,
        )


# --- individual defects ------------------------------------------------

OTHER_ORIGINS = ["Bangladesh", "Vietnam", "Sri Lanka", "Pakistan", "China"]

CONFLICTING_MATERIALS = {
    "cotton": "polyester",
    "polyester": "cotton",
    "leather": "synthetic PU",
    "steel": "aluminium",
    "ceramic": "melamine",
    "wood": "MDF composite",
    "rubber": "PVC",
    "brass": "zinc alloy",
}


def origin_mismatch(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    wrong = rng.choice(OTHER_ORIGINS)
    docs.certificate_of_origin.origin_country = wrong
    return ExpectedFinding(
        type=DefectType.ORIGIN_MISMATCH,
        severity=Severity.CRITICAL,
        summary="Country of origin differs between invoice and certificate of origin",
        sources=["invoice.origin_country", "certificate_of_origin.origin_country"],
        details={"invoice": docs.invoice.origin_country, "coo": wrong},
    )


def hs_description_conflict(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    item = docs.bill_of_lading.line_items[0]
    original_material = item.material
    wrong_material = CONFLICTING_MATERIALS.get(original_material, "synthetic")

    new_description = item.description.replace(
        original_material.title(), wrong_material.title()
    )
    if new_description == item.description:
        new_description = f"{wrong_material.title()} goods, {item.quantity} PCS"

    docs.bl_goods_description_override = new_description.upper()

    return ExpectedFinding(
        type=DefectType.HS_DESCRIPTION_CONFLICT,
        severity=Severity.CRITICAL,
        summary="Bill of lading describes a material inconsistent with the declared HS code",
        sources=["invoice.line_items[0].hs_code", "bill_of_lading.goods_description"],
        details={
            "hs_code": item.hs_code,
            "hs_material": original_material,
            "bl_description": docs.bl_goods_description_override,
        },
    )


def weight_variance(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    true_gross = docs.truth.total_gross_weight_kg
    factor = Decimal(str(round(rng.uniform(0.90, 0.96), 4)))
    wrong = (true_gross * factor).quantize(Decimal("0.001"))
    docs.bl_gross_weight_override = wrong

    variance_pct = round(float((true_gross - wrong) / true_gross * 100), 2)

    return ExpectedFinding(
        type=DefectType.WEIGHT_VARIANCE,
        severity=Severity.WARNING,
        summary="Gross weight differs between packing list and bill of lading",
        sources=["packing_list.total_gross_weight_kg", "bill_of_lading.gross_weight_kg"],
        details={
            "packing_list_kg": float(true_gross),
            "bill_of_lading_kg": float(wrong),
            "variance_pct": variance_pct,
        },
    )


def package_count_mismatch(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    true_count = docs.truth.total_packages
    delta = rng.choice([-3, -2, -1, 1, 2, 3])
    wrong = max(1, true_count + delta)
    docs.bl_package_count_override = wrong

    return ExpectedFinding(
        type=DefectType.PACKAGE_COUNT_MISMATCH,
        severity=Severity.WARNING,
        summary="Package count differs between packing list and bill of lading",
        sources=["packing_list.total_packages", "bill_of_lading.package_count"],
        details={"packing_list": true_count, "bill_of_lading": wrong},
    )


def invoice_arithmetic_error(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    """A plausible clerical slip — small enough to survive a quick glance."""
    correct = docs.truth.invoice_total
    drift = Decimal(str(round(rng.uniform(-0.015, 0.015), 4)))
    if abs(drift) < Decimal("0.002"):
        drift = Decimal("0.004")
    wrong = (correct * (Decimal("1") + drift)).quantize(Decimal("0.01"))
    docs.invoice_total_override = wrong

    return ExpectedFinding(
        type=DefectType.INVOICE_ARITHMETIC_ERROR,
        severity=Severity.CRITICAL,
        summary="Invoice total does not equal the sum of its line items",
        sources=["invoice.line_items", "invoice.total"],
        details={
            "computed": float(correct),
            "printed": float(wrong),
            "difference": float(wrong - correct),
        },
    )


def consignee_mismatch(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    original = docs.bill_of_lading.importer.name
    variants = [
        original.replace("Pty Ltd", "Pty. Limited"),
        original.replace(" Group", " Holdings"),
        f"{original.split()[0]} International Pty Ltd",
    ]
    wrong = rng.choice([v for v in variants if v != original] or [f"{original} (AUS)"])
    docs.bill_of_lading.importer.name = wrong

    return ExpectedFinding(
        type=DefectType.CONSIGNEE_MISMATCH,
        severity=Severity.WARNING,
        summary="Consignee name differs between invoice and bill of lading",
        sources=["invoice.importer.name", "bill_of_lading.importer.name"],
        details={"invoice": original, "bill_of_lading": wrong},
    )


def container_check_digit_invalid(
    docs: DocumentSet, rng: random.Random
) -> ExpectedFinding:
    original = docs.truth.container.number
    current = int(original[10])
    wrong_digit = rng.choice([d for d in range(10) if d != current])
    wrong = f"{original[:10]}{wrong_digit}"

    docs.bill_of_lading.container.number = wrong
    docs.vgm.container.number = wrong

    return ExpectedFinding(
        type=DefectType.CONTAINER_CHECK_DIGIT_INVALID,
        severity=Severity.CRITICAL,
        summary="Container number fails the ISO 6346 check digit test",
        sources=["bill_of_lading.container.number"],
        details={"printed": wrong, "expected_check_digit": current},
    )


def date_sequence_invalid(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    from datetime import timedelta

    bl_date = docs.truth.dates.bl_date
    wrong = bl_date + timedelta(days=rng.randint(3, 21))
    docs.certificate_of_origin.dates.coo_issue_date = wrong

    return ExpectedFinding(
        type=DefectType.DATE_SEQUENCE_INVALID,
        severity=Severity.WARNING,
        summary="Certificate of origin is dated after the bill of lading",
        sources=["certificate_of_origin.issue_date", "bill_of_lading.date"],
        details={
            "coo_issue_date": str(wrong),
            "bl_date": str(bl_date),
        },
    )


def missing_fumigation_cert(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    docs.include_fumigation_cert = False
    return ExpectedFinding(
        type=DefectType.MISSING_FUMIGATION_CERT,
        severity=Severity.CRITICAL,
        summary="Wooden packaging declared but no ISPM-15 treatment evidence supplied",
        sources=["packing_list.package_types"],
        details={"package_types": [p.package_type for p in docs.truth.packages]},
    )


def missing_house_bl(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    docs.include_house_bl = False
    return ExpectedFinding(
        type=DefectType.MISSING_HOUSE_BL,
        severity=Severity.WARNING,
        summary="LCL shipment without a house bill of lading",
        sources=["bill_of_lading.house_bl_number"],
        details={"cargo_type": docs.truth.cargo_type.value},
    )


def hs_code_mismatch(docs: DocumentSet, rng: random.Random) -> ExpectedFinding:
    item = docs.certificate_of_origin.line_items[0]
    original = item.hs_code
    head, tail = original.split(".", 1)
    wrong_head = str(int(head) + rng.choice([-1, 1])).zfill(4)
    item.hs_code = f"{wrong_head}.{tail}"

    return ExpectedFinding(
        type=DefectType.HS_CODE_MISMATCH,
        severity=Severity.CRITICAL,
        summary="HS code differs between invoice and certificate of origin",
        sources=["invoice.line_items[0].hs_code", "certificate_of_origin.hs_code"],
        details={"invoice": original, "coo": item.hs_code},
    )


# --- selection ---------------------------------------------------------

DefectFn = Callable[[DocumentSet, random.Random], ExpectedFinding]

ALWAYS_APPLICABLE: list[DefectFn] = [
    origin_mismatch,
    hs_description_conflict,
    weight_variance,
    package_count_mismatch,
    invoice_arithmetic_error,
    consignee_mismatch,
    container_check_digit_invalid,
    date_sequence_invalid,
    hs_code_mismatch,
]


def _applicable_defects(truth: ShipmentTruth) -> list[DefectFn]:
    defects = list(ALWAYS_APPLICABLE)
    if truth.has_wooden_packaging:
        defects.append(missing_fumigation_cert)
    if truth.cargo_type == CargoType.LCL:
        defects.append(missing_house_bl)
    return defects


def apply_defects(
    truth: ShipmentTruth,
    rng: random.Random,
    clean_probability: float = 0.30,
    max_defects: int = 3,
) -> tuple[DocumentSet, list[ExpectedFinding]]:
    """Return per-document views plus the findings a correct system should report."""
    docs = DocumentSet.from_truth(truth)

    if rng.random() < clean_probability:
        return docs, []

    pool = _applicable_defects(truth)
    count = rng.choices([1, 2, 3], weights=[50, 33, 17])[0]
    count = min(count, max_defects, len(pool))

    chosen = rng.sample(pool, count)
    findings = [defect(docs, rng) for defect in chosen]
    return docs, findings