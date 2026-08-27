# The Problem

## A container, end to end

Take one shipment: 500 cotton t-shirts from Mumbai to Sydney, LCL, sea freight.

**Day 1 — Mumbai.** The exporter's accounts team raises a commercial invoice.
HS code `6109.10`, origin India, USD 12,000.

**Day 3 — Bhiwandi warehouse, 40 km away.** A different person counts the goods
and produces a packing list. Twelve cartons, 500 kg gross, 2.4 CBM. He also types
a line he types on every packing list: *"Packing: wooden pallets x 12."* He has
not seen the invoice. He does not need to.

**Day 4 — Chamber of commerce.** A junior copies last month's certificate of
origin template and edits the fields. The origin field still reads *Bangladesh*.
The clerk stamps it. Nobody cross-checks.

**Day 10 — Nhava Sheva.** The container is weighed for VGM under SOLAS. This
shipment's share comes to 512 kg — the pallet weight was never counted in the
packing list.

**Day 12 — Bill of lading.** The shipping line issues the B/L. The goods
description came from a booking form filled in by a clerk who wrote *"Polyester
sportswear."* The weight field says 480 kg, copied from an earlier draft.

Four documents. Four parties. Four different days. **Nobody lied.** Nobody saw
another party's document.

**Day 30 — Sydney.** A customs broker has twenty shipments to clear today and
ten minutes for this one. He opens five PDFs, copies values into a declaration,
and submits.

He does not notice that the B/L says polyester while the HS code says cotton.
He does not notice the certificate of origin says Bangladesh. He takes the weight
from the invoice because it was the first tab he opened. He never reaches page 2
of the packing list, where the wooden packaging is declared.

## What that costs

| Day | Event |
| --- | --- |
| 1 | Preferential duty claim rejected — certificate names the wrong country |
| 2 | Biosecurity hold — wooden packaging declared, no ISPM-15 certificate attached |
| 4 | Terminal demurrage begins |
| 6 | Inspection finds cartons marked *100% Cotton* against a polyester declaration — now a misdeclaration, not a clerical slip |
| 11 | Container released |

Extra duty, eleven days of demurrage, fumigation charges, and a compliance record
attached to the importer's name. The next several shipments get closer scrutiny.

## This is not an edge case

Manual customs data entry carries a **1–4% error rate per field**, and a typical
customs entry form contains 15–25 independently transcribed values. Roughly **32%
of customs delays** trace back to documentation errors.

The failure mode is not one careless person. It is structural: the more parties
involved, the more inconsistency, and no party is positioned to see the whole set.

## The parties

| Party | Produces |
| --- | --- |
| Exporter | Commercial invoice |
| Warehouse | Packing list |
| Chamber of commerce | Certificate of origin |
| Fumigation operator | ISPM-15 treatment certificate |
| Weighbridge / shipper | VGM certificate |
| Shipping line | Master bill of lading |
| NVOCC / consolidator | House bill of lading (LCL) |
| Customs broker | The declaration that must reconcile all of the above |

## Where this project sits

```
Phase 1-3          Phase 5            Phase 6
(documents)        (customs filing)   (clearance)
    |                   |                  |
    v                   v                  v
 +------+          +---------+        +---------+
 | PDFs |--------->| EDIFACT |------->| Cleared |
 +------+          +---------+        +---------+
    ^
    |
 THIS PROJECT
```

Customs reporting systems catch these problems at submission, when rejection is
already expensive. This system operates one step earlier — on the source documents,
before the declaration is built.

## What "checking" actually means

**Deterministic** — arithmetic, formats, and standards. No judgment required.

- ISO 6346 container check digit
- Invoice line items sum to the stated total
- Date sequence: invoice <= booking <= B/L <= ETA
- Vessel IMO format, UN/LOCODE port codes
- Package counts reconcile across packing list and B/L

**Semantic** — requires understanding, not rules.

- Does the goods description on the B/L match the material implied by the HS code?
- Are two differently worded descriptions the same goods?
- Is a consignee name variation a rename, a subsidiary, or a genuine mismatch?

**Conditional** — depends on shipment attributes.

- Wooden packaging declared, so an ISPM-15 certificate is required
- LCL shipment, so a house bill of lading is expected
- Preferential duty claimed, so a valid certificate of origin is required
- Value below the low-value threshold, so a simplified declaration path applies

## Jurisdiction

Roughly 70% of these checks are country-independent, because they concern whether
documents agree **with each other**. The remaining 30% are jurisdiction-specific:
which documents are mandatory, value thresholds, HS code digit depth, permit
requirements.

The system is built as a country-independent core with pluggable rule packs.
Australia is the first pack. Adding another jurisdiction should mean adding a
rules file, not changing the engine.