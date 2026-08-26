"""CLI entry point: generate shipment document sets with ground truth."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from generator.defects import DocumentSet, ExpectedFinding, apply_defects
from generator.models import ShipmentTruth
from generator.renderers import (
    bill_of_lading,
    certificate_of_origin,
    fumigation,
    invoice,
    packing_list,
    vgm,
)
from generator.shipment import build_shipment

DEFAULT_OUT = Path("data/generated")


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"cannot serialise {type(value)}")


def _true_values(truth: ShipmentTruth) -> dict:
    """Flat, extraction-comparable view of what the documents should say."""
    return {
        "shipment_id": truth.shipment_id,
        "cargo_type": truth.cargo_type.value,
        "invoice_number": truth.invoice_number,
        "invoice_date": truth.dates.invoice_date,
        "exporter_name": truth.exporter.name,
        "exporter_country": truth.exporter.country,
        "importer_name": truth.importer.name,
        "importer_country": truth.importer.country,
        "origin_country": truth.origin_country,
        "incoterms": truth.incoterms.value,
        "currency": truth.currency,
        "goods_value": truth.goods_value,
        "invoice_total": truth.invoice_total,
        "line_items": [
            {
                "description": item.description,
                "hs_code": item.hs_code,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
            }
            for item in truth.line_items
        ],
        "total_packages": truth.total_packages,
        "total_net_weight_kg": truth.total_net_weight_kg,
        "total_gross_weight_kg": truth.total_gross_weight_kg,
        "total_cbm": truth.total_cbm,
        "container_number": truth.container.number,
        "container_size_type": truth.container.size_type,
        "seal_number": truth.container.seal_number,
        "vgm_kg": truth.container.vgm_kg,
        "vessel_name": truth.vessel.name,
        "vessel_imo": truth.vessel.imo,
        "voyage_number": truth.vessel.voyage_number,
        "port_of_loading": truth.port_of_loading,
        "port_of_discharge": truth.port_of_discharge,
        "bl_date": truth.dates.bl_date,
        "etd": truth.dates.etd,
        "eta": truth.dates.eta,
        "master_bl_number": truth.master_bl_number,
        "house_bl_number": truth.house_bl_number,
        "coo_number": truth.coo_number,
        "coo_issue_date": truth.dates.coo_issue_date,
        "has_wooden_packaging": truth.has_wooden_packaging,
    }


def _finding_to_dict(finding: ExpectedFinding) -> dict:
    payload = asdict(finding)
    payload["type"] = finding.type.value
    payload["severity"] = finding.severity.value
    return payload


def _render_all(
    docs: DocumentSet,
    out_dir: Path,
    rng: random.Random,
) -> list[str]:
    """Render every document, returning the filenames actually written."""
    written: list[Path | None] = [
        invoice.render(docs, out_dir, rng),
        packing_list.render(docs, out_dir, rng),
        bill_of_lading.render(docs, out_dir, rng),
        certificate_of_origin.render(docs, out_dir, rng),
        vgm.render(docs, out_dir, rng),
        fumigation.render(docs, out_dir, rng),
    ]
    return sorted(path.name for path in written if path is not None)


def generate_set(
    rng: random.Random,
    sequence: int,
    out_root: Path,
    clean_probability: float,
) -> dict:
    truth = build_shipment(rng, sequence)
    docs, findings = apply_defects(truth, rng, clean_probability=clean_probability)

    set_dir = out_root / truth.shipment_id
    set_dir.mkdir(parents=True, exist_ok=True)

    documents = _render_all(docs, set_dir, rng)

    ground_truth = {
        "shipment_id": truth.shipment_id,
        "documents": documents,
        "expected_findings": [_finding_to_dict(f) for f in findings],
        "is_clean": not findings,
        "true_values": _true_values(truth),
    }

    (set_dir / "ground_truth.json").write_text(
        json.dumps(ground_truth, indent=2, default=_json_default),
        encoding="utf-8",
    )

    return {
        "shipment_id": truth.shipment_id,
        "cargo_type": truth.cargo_type.value,
        "documents": len(documents),
        "findings": [f.type.value for f in findings],
    }


def generate(
    count: int,
    seed: int,
    out_root: Path,
    clean_probability: float,
    fresh: bool,
) -> list[dict]:
    if fresh and out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    summaries = [
        generate_set(rng, index, out_root, clean_probability)
        for index in range(1, count + 1)
    ]

    manifest = {
        "seed": seed,
        "count": count,
        "clean_probability": clean_probability,
        "sets": summaries,
    }
    (out_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return summaries


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic trade document sets with ground truth."
    )
    parser.add_argument("--count", type=int, default=10, help="number of shipment sets")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    parser.add_argument(
        "--clean-probability",
        type=float,
        default=0.30,
        help="fraction of sets with no injected defects",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="delete the output directory before generating",
    )
    args = parser.parse_args()

    summaries = generate(
        count=args.count,
        seed=args.seed,
        out_root=args.out,
        clean_probability=args.clean_probability,
        fresh=args.fresh,
    )

    clean = sum(1 for s in summaries if not s["findings"])
    total_findings = sum(len(s["findings"]) for s in summaries)

    print(f"\nGenerated {len(summaries)} sets in {args.out} (seed={args.seed})\n")
    for summary in summaries:
        marker = "clean" if not summary["findings"] else ", ".join(summary["findings"])
        print(f"  {summary['shipment_id']:<20} {summary['cargo_type']:<4} "
              f"{summary['documents']} docs   {marker}")

    print(f"\n  {clean} clean · {len(summaries) - clean} defective · "
          f"{total_findings} findings total\n")


if __name__ == "__main__":
    cli()