# Data Generation

Every document in this project is synthetic. No proprietary or employer data is
used anywhere.

That is not only a privacy constraint — it is what makes evaluation possible.
Because the generator knows exactly which defects it injected, the ground truth is
**exact rather than hand-labelled**, and it scales to any number of sets at no
labelling cost.

## The core idea

```
ShipmentTruth          one internally consistent shipment
      |
      v
DocumentSet            six independent copies, one per document
      |
      v
defect injection       break specific copies in specific ways
      |
      v
PDFs + ground_truth.json
```

A shipment is first built so that every value reconciles: line items sum to the
invoice total, package weights sum to the packing list total, the VGM equals cargo
plus tare, the container check digit is valid.

Only then are defects applied — and never to the shipment itself. Each document
receives its own `deepcopy`, and a defect mutates one copy. `ShipmentTruth` stays
correct for the life of the run, so ground truth can always be derived from it.

```python
@dataclass
class DocumentSet:
    truth: ShipmentTruth          # never mutated
    invoice: ShipmentTruth        # deepcopy
    packing_list: ShipmentTruth   # deepcopy
    bill_of_lading: ShipmentTruth # deepcopy
    ...
```

## Documents produced

| Document | Always present | Condition |
| --- | --- | --- |
| Commercial invoice | Yes | |
| Packing list | Yes | |
| Bill of lading | Yes | House B/L variant for LCL |
| Certificate of origin | Yes | Preferential (AI-ECTA) or non-preferential |
| VGM certificate | Yes | |
| Fumigation certificate | No | Only when wooden packaging is declared |

## Layout variation

Each document type renders through **two or more distinct layouts** — different
field order, different labels, different table structure.

This matters more than it looks. If every invoice rendered identically, an
extractor could learn positions instead of meaning, and the evaluation would report
a number that collapses on the first real document. Variation is the test.

The same field appears as `Gross Weight`, `G.W.`, and `Total Weight` across
layouts. Dates appear as `19 May 2026` and `19/05/2026`. Some layouts box the
shipper and consignee; others run them as inline label/value pairs.

## Defect catalogue

Eleven defect types, each producing an `ExpectedFinding` that states what a correct
system should report and which sources it should cite.

| Defect | Severity | What breaks |
| --- | --- | --- |
| `ORIGIN_MISMATCH` | CRITICAL | Certificate of origin names a different country than the invoice |
| `HS_CODE_MISMATCH` | CRITICAL | HS code differs between invoice and certificate of origin |
| `HS_DESCRIPTION_CONFLICT` | CRITICAL | B/L describes a material inconsistent with the declared HS code |
| `INVOICE_ARITHMETIC_ERROR` | CRITICAL | Printed total does not equal the sum of line items |
| `CONTAINER_CHECK_DIGIT_INVALID` | CRITICAL | Container number fails ISO 6346 |
| `MISSING_FUMIGATION_CERT` | CRITICAL | Wooden packaging declared, no ISPM-15 evidence |
| `WEIGHT_VARIANCE` | WARNING | Gross weight differs between packing list and B/L |
| `PACKAGE_COUNT_MISMATCH` | WARNING | Package count differs between packing list and B/L |
| `CONSIGNEE_MISMATCH` | WARNING | Consignee name differs between invoice and B/L |
| `DATE_SEQUENCE_INVALID` | WARNING | Certificate of origin dated after the bill of lading |
| `MISSING_HOUSE_BL` | WARNING | LCL shipment without a house bill of lading |

Two defects are conditional: `MISSING_FUMIGATION_CERT` only applies when wooden
packaging exists, and `MISSING_HOUSE_BL` only to LCL shipments. Applying them
otherwise would produce ground truth describing an impossible shipment.

## Defects are calibrated to be findable, not obvious

An early version drifted the invoice total by up to 8%. On a USD 470,000 invoice
that is a USD 38,000 gap — a defect nobody would ever miss, and therefore one that
measures nothing.

Real clerical errors are small. The drift is now 0.2% to 1.5%, which on the same
invoice is roughly USD 1,100: wrong, consequential, and easy to read past.

The same reasoning applies to consignee mismatches, which are generated as
plausible name variations (`Pty Ltd` becoming `Pty. Limited`, a subsidiary form)
rather than unrelated company names. Distinguishing a rename from a mismatch is
the actual difficulty.

## Clean sets

Roughly 30% of generated sets carry no defects at all.

Without them only recall would be measurable. Clean sets are what make **precision**
measurable — they reveal whether the system invents findings where none exist, which
is the failure mode that destroys operator trust fastest.

## Reproducibility

Generation is seeded end to end. The same `--seed` produces the same shipments,
the same defects, and the same layout choices.

```bash
uv run python -m generator.main --count 50 --seed 1 --fresh
```

This is a prerequisite for evaluation, not a convenience. When a prompt change
moves recall from 71% to 89%, the improvement is only attributable if the documents
were identical across both runs.

One implementation note: `Faker.seed()` sets class-level global state and leaks
across instances. `fake.seed_instance(seed)` is used instead.

## Ground truth format

```json
{
  "shipment_id": "AUBNE-2026-0003",
  "documents": ["bill_of_lading.pdf", "commercial_invoice.pdf", "..."],
  "expected_findings": [
    {
      "type": "WEIGHT_VARIANCE",
      "severity": "WARNING",
      "summary": "Gross weight differs between packing list and bill of lading",
      "sources": [
        "packing_list.total_gross_weight_kg",
        "bill_of_lading.gross_weight_kg"
      ],
      "details": {
        "packing_list_kg": 13694.0,
        "bill_of_lading_kg": 13040.796,
        "variance_pct": 4.77
      }
    }
  ],
  "is_clean": false,
  "true_values": { }
}
```

`expected_findings` scores detection. `true_values` scores extraction — every
field the documents should have yielded, so accuracy can be measured
independently of whether any discrepancy was found.

## Realism constraints

Several details exist purely so the data does not teach the wrong thing:

- **Weights are per package.** Totals multiply by count. An earlier version stored
  the full line weight in a single package row, producing 480 cartons at 0.4 kg each.
- **FCL and LCL carry different volumes.** FCL quantities run 2,000–10,000 units;
  LCL runs 400–2,000. A 40HC container holding 200 kg of cargo is not a shipment.
- **Freight and insurance scale with goods value.** Flat charges produced
  USD 1,980 of freight on a USD 470,000 invoice.
- **VGM is a third weight source.** Cargo plus tare, so packing list, B/L, and VGM
  legitimately disagree — which is exactly the reconciliation problem in the field.
- **Container numbers carry valid ISO 6346 check digits**, computed rather than
  faked, so the check-digit defect is genuinely detectable and clean sets genuinely
  pass.

## Module layout

```
generator/
├── models.py       ShipmentTruth and its components
├── data.py         ports, vessels, products, companies
├── iso6346.py      container check digit computation
├── shipment.py     builds one consistent shipment
├── defects.py      defect catalogue and injection
├── main.py         CLI and ground truth writer
└── renderers/
    ├── base.py     shared PDF primitives
    ├── invoice.py
    ├── packing_list.py
    ├── bill_of_lading.py
    ├── certificate_of_origin.py
    ├── vgm.py
    └── fumigation.py
```