"""Build a consistent, defect-free shipment."""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from faker import Faker

from generator import data
from generator.iso6346 import make_container_number
from generator.models import (
    CargoType,
    Container,
    Incoterms,
    LineItem,
    Package,
    Party,
    ShipmentDates,
    ShipmentTruth,
    Vessel,
)


def _money(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def _weight(value: float) -> Decimal:
    return Decimal(str(round(value, 3)))


def _build_exporter(rng: random.Random, fake: Faker) -> Party:
    name, addr, city, postcode = rng.choice(data.INDIAN_EXPORTERS)
    return Party(
        name=name,
        address_line1=addr,
        address_line2=f"Plot {rng.randint(1, 240)}",
        city=city,
        postcode=postcode,
        country="India",
        contact_name=fake.name(),
        email=f"exports@{name.split()[0].lower()}.co.in",
        phone=f"+91-{rng.randint(70, 99)}{rng.randint(10000000, 99999999)}",
    )


def _build_importer(rng: random.Random, fake: Faker) -> Party:
    name, addr, city, postcode = rng.choice(data.AUSTRALIAN_IMPORTERS)
    return Party(
        name=name,
        address_line1=addr,
        city=city,
        postcode=postcode,
        country="Australia",
        contact_name=fake.name(),
        email=f"imports@{name.split()[0].lower()}.com.au",
        phone=f"+61-{rng.randint(2, 8)}-{rng.randint(10000000, 99999999)}",
    )


def _build_line_items(rng: random.Random, cargo_type: CargoType) -> list[LineItem]:
    count = rng.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]
    chosen = rng.sample(data.PRODUCTS, count)

    # FCL shipments carry far more volume than LCL consolidations.
    if cargo_type == CargoType.FCL:
        quantities = [2000, 3000, 4000, 5000, 6000, 8000, 10000]
    else:
        quantities = [400, 600, 800, 1000, 1500, 2000]

    items = []
    for description, hs_code, material, price_range, unit_weight in chosen:
        quantity = rng.choice(quantities)
        unit_price = _money(rng.uniform(*price_range))
        net = _weight(quantity * unit_weight)
        gross = _weight(float(net) * rng.uniform(1.06, 1.14))

        items.append(
            LineItem(
                description=description,
                hs_code=hs_code,
                quantity=quantity,
                unit="PCS",
                unit_price=unit_price,
                material=material,
                net_weight_kg=net,
                gross_weight_kg=gross,
            )
        )
    return items


def _build_packages(
    rng: random.Random,
    line_items: list[LineItem],
    wooden: bool,
) -> list[Package]:
    """Split each line item into physical packages.

    Package weights are per unit, so the packing list totals reconcile
    with the invoice line items.
    """
    packages = []
    for index, item in enumerate(line_items, start=1):
        target = Decimal(str(rng.uniform(15, 30)))
        count = max(4, int(item.gross_weight_kg / target))
        count = min(count, 400)

        package_type = "PALLET" if wooden and index == 1 else rng.choice(
            ["CARTON", "CARTON", "CARTON", "CRATE"]
        )

        per_net = (item.net_weight_kg / count).quantize(Decimal("0.001"))
        per_gross = (item.gross_weight_kg / count).quantize(Decimal("0.001"))

        packages.append(
            Package(
                marks=f"{item.hs_code.replace('.', '')}/{index:02d}",
                package_type=package_type,
                count=count,
                length_cm=Decimal(str(rng.choice([40, 45, 50, 60, 80]))),
                width_cm=Decimal(str(rng.choice([30, 35, 40, 50, 60]))),
                height_cm=Decimal(str(rng.choice([25, 30, 35, 40, 45]))),
                net_weight_kg=per_net,
                gross_weight_kg=per_gross,
            )
        )
    return packages


def _build_dates(rng: random.Random) -> ShipmentDates:
    invoice_date = date(2026, 1, 1) + timedelta(days=rng.randint(0, 200))
    booking_date = invoice_date + timedelta(days=rng.randint(1, 5))
    cargo_received = booking_date + timedelta(days=rng.randint(2, 8))
    bl_date = cargo_received + timedelta(days=rng.randint(1, 4))
    etd = bl_date
    eta = etd + timedelta(days=rng.randint(14, 24))
    coo_issue = invoice_date + timedelta(days=rng.randint(1, 6))

    return ShipmentDates(
        invoice_date=invoice_date,
        booking_date=booking_date,
        cargo_received_date=cargo_received,
        bl_date=bl_date,
        etd=etd,
        eta=eta,
        coo_issue_date=coo_issue,
        fumigation_date=cargo_received - timedelta(days=rng.randint(1, 3)),
    )


def build_shipment(rng: random.Random, sequence: int) -> ShipmentTruth:
    """Create one internally consistent shipment."""
    seed = rng.randint(0, 10**9)
    fake = Faker()
    fake.seed_instance(seed)

    cargo_type = rng.choices([CargoType.FCL, CargoType.LCL], weights=[55, 45])[0]
    wooden = rng.random() < 0.45

    line_items = _build_line_items(rng, cargo_type)
    packages = _build_packages(rng, line_items, wooden)

    pol_code, pol_name = rng.choice(data.INDIAN_PORTS)
    pod_code, pod_name = rng.choice(data.AUSTRALIAN_PORTS)
    vessel_name, imo = rng.choice(data.VESSELS)

    size_type, tare = rng.choice(data.CONTAINER_SIZES)
    container_number = make_container_number(
        rng.choice(data.CONTAINER_PREFIXES),
        rng.randint(100000, 999999),
    )

    gross_total = sum(
        (p.gross_weight_kg * p.count for p in packages), Decimal("0")
    )
    vgm = _weight(float(gross_total) + tare + rng.uniform(8, 40))

    goods_value = float(sum(item.line_total for item in line_items))
    incoterms = rng.choice(list(Incoterms))
    dates = _build_dates(rng)

    return ShipmentTruth(
        shipment_id=f"{pod_code}-2026-{sequence:04d}",
        cargo_type=cargo_type,
        exporter=_build_exporter(rng, fake),
        importer=_build_importer(rng, fake),
        line_items=line_items,
        packages=packages,
        origin_country="India",
        incoterms=incoterms,
        currency="USD",
        freight_charge=_money(goods_value * rng.uniform(0.010, 0.030)),
        insurance_charge=_money(goods_value * rng.uniform(0.002, 0.006)),
        container=Container(
            number=container_number,
            seal_number=f"SL{rng.randint(1000000, 9999999)}",
            size_type=size_type,
            tare_weight_kg=Decimal(str(tare)),
            vgm_kg=vgm,
        ),
        vessel=Vessel(
            name=vessel_name,
            imo=imo,
            voyage_number=f"{rng.randint(100, 499)}{rng.choice('NSEW')}",
        ),
        port_of_loading=pol_code,
        port_of_loading_name=pol_name,
        port_of_discharge=pod_code,
        port_of_discharge_name=pod_name,
        dates=dates,
        has_wooden_packaging=wooden,
        master_bl_number=f"{rng.choice(['MAEU', 'MSCU', 'CMDU'])}{rng.randint(100000000, 999999999)}",
        house_bl_number=(
            f"HBL{rng.randint(1000000, 9999999)}"
            if cargo_type == CargoType.LCL
            else None
        ),
        coo_number=f"CO/{rng.randint(2026000, 2026999)}/{rng.randint(100, 999)}",
        invoice_number=f"INV/{rng.randint(1000, 9999)}/2026",
        booking_number=f"BK{rng.randint(10000000, 99999999)}",
    )