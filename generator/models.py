"""Domain models for a shipment and its documents."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class CargoType(str, Enum):
    FCL = "FCL"
    LCL = "LCL"


class Incoterms(str, Enum):
    FOB = "FOB"
    CIF = "CIF"
    CFR = "CFR"
    EXW = "EXW"


class Party(BaseModel):
    """A company appearing on trade documents."""

    name: str
    address_line1: str
    address_line2: str | None = None
    city: str
    postcode: str
    country: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None

    def as_block(self) -> str:
        """Multi-line address block as printed on documents."""
        parts = [self.name, self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(f"{self.city} {self.postcode}")
        parts.append(self.country.upper())
        return "\n".join(parts)


class LineItem(BaseModel):
    """One row of goods on the commercial invoice."""

    description: str
    hs_code: str = Field(pattern=r"^\d{4}\.\d{2}(\.\d{2})?$")
    quantity: int
    unit: str = "PCS"
    unit_price: Decimal
    material: str          # "cotton", "polyester" — used for HS/description checks
    net_weight_kg: Decimal
    gross_weight_kg: Decimal

    @computed_field
    @property
    def line_total(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))


class Package(BaseModel):
    """One carton/pallet line on the packing list.

    Weights are PER PACKAGE. Totals multiply by count.
    """

    marks: str
    package_type: str      # "CARTON", "PALLET"
    count: int
    length_cm: Decimal
    width_cm: Decimal
    height_cm: Decimal
    net_weight_kg: Decimal
    gross_weight_kg: Decimal

    @computed_field
    @property
    def cbm(self) -> Decimal:
        volume = (self.length_cm * self.width_cm * self.height_cm * self.count)
        return (volume / Decimal("1000000")).quantize(Decimal("0.001"))

    @computed_field
    @property
    def total_net_weight_kg(self) -> Decimal:
        return (self.net_weight_kg * self.count).quantize(Decimal("0.001"))

    @computed_field
    @property
    def total_gross_weight_kg(self) -> Decimal:
        return (self.gross_weight_kg * self.count).quantize(Decimal("0.001"))


class Container(BaseModel):
    number: str            # ISO 6346, e.g. MSCU1234565
    seal_number: str
    size_type: str         # "20GP", "40HC"
    tare_weight_kg: Decimal
    vgm_kg: Decimal        # Verified Gross Mass (SOLAS)


class Vessel(BaseModel):
    name: str
    imo: str = Field(pattern=r"^\d{7}$")
    voyage_number: str


class ShipmentDates(BaseModel):
    invoice_date: date
    booking_date: date
    cargo_received_date: date
    bl_date: date
    etd: date
    eta: date
    coo_issue_date: date
    fumigation_date: date | None = None


class ShipmentTruth(BaseModel):
    """The single source of truth for one shipment.

    Every document is rendered from this object. Defects are applied to
    per-document copies, never here — this stays correct so ground truth
    can always be derived from it.
    """

    shipment_id: str
    cargo_type: CargoType

    exporter: Party
    importer: Party
    notify_party: Party | None = None

    line_items: list[LineItem]
    packages: list[Package]

    origin_country: str
    incoterms: Incoterms
    currency: str = "USD"
    freight_charge: Decimal = Decimal("0.00")
    insurance_charge: Decimal = Decimal("0.00")

    container: Container
    vessel: Vessel

    port_of_loading: str        # UN/LOCODE, e.g. INNSA
    port_of_loading_name: str
    port_of_discharge: str      # AUSYD
    port_of_discharge_name: str

    dates: ShipmentDates

    has_wooden_packaging: bool
    master_bl_number: str
    house_bl_number: str | None = None   # LCL only

    coo_number: str
    invoice_number: str
    booking_number: str

    @computed_field
    @property
    def goods_value(self) -> Decimal:
        return sum(
            (item.line_total for item in self.line_items),
            Decimal("0.00"),
        )

    @computed_field
    @property
    def invoice_total(self) -> Decimal:
        total = self.goods_value
        if self.incoterms in (Incoterms.CIF, Incoterms.CFR):
            total += self.freight_charge
        if self.incoterms == Incoterms.CIF:
            total += self.insurance_charge
        return total.quantize(Decimal("0.01"))

    @computed_field
    @property
    def total_packages(self) -> int:
        return sum(p.count for p in self.packages)

    @computed_field
    @property
    def total_gross_weight_kg(self) -> Decimal:
        return sum(
            (p.gross_weight_kg * p.count for p in self.packages),
            Decimal("0.000"),
        ).quantize(Decimal("0.001"))

    @computed_field
    @property
    def total_net_weight_kg(self) -> Decimal:
        return sum(
            (p.net_weight_kg * p.count for p in self.packages),
            Decimal("0.000"),
        ).quantize(Decimal("0.001"))

    @computed_field
    @property
    def total_cbm(self) -> Decimal:
        return sum((p.cbm for p in self.packages), Decimal("0.000"))

    @computed_field
    @property
    def goods_summary(self) -> str:
        """Short description as it appears on the BL."""
        if len(self.line_items) == 1:
            return self.line_items[0].description
        return f"{len(self.line_items)} ITEMS AS PER INVOICE"