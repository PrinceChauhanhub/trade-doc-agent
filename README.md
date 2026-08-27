# Trade Document Compliance Agent

Cross-checks the documents that travel with an international shipment and reports
where they disagree — with a citation to the exact source of every finding.

When a container moves between countries, four to six documents accompany it:
commercial invoice, packing list, bill of lading, certificate of origin, and
treatment certificates. Each is produced by a **different party, at a different
time, in a different system**. Nobody sees all of them together until a customs
broker opens five PDFs side by side and starts copying values into a declaration.

That is where errors enter — and where this system operates.

```
SHIPMENT SYD-2026-0847 · India → Australia · LCL

[CRITICAL] Origin mismatch
   Invoice p1:  "Country of Origin: India"
   CoO field 3: "Bangladesh"
   -> AI-ECTA preferential claim will be rejected

[CRITICAL] HS code contradicts goods description
   Invoice HS 6109.10 = T-shirts, cotton, knitted
   BL p1: "Polyester sportswear, 500 pcs"
   -> Material conflict. Verify before declaring.

[WARNING] Weight declared three ways
   Packing List 500 kg · BL 480 kg · VGM 512 kg
   -> VGM is authoritative under SOLAS.

[PASSED] 11 checks
```

## Why this is not a PDF chatbot

Retrieval answers questions about *one* document. This system asks no questions —
it decides for itself what to check, and reasons **across five documents at once**.
Three things make that harder than retrieval:

- **Structured extraction** — pulling `{"hs_code": "6109.10", "gross_weight_kg": 500.0}`
  out of a layout that differs for every exporter, with schema validation and retries
- **Cross-document reasoning** — comparing values that live in separate files, and
  knowing when a difference is tolerable and when it is a problem
- **Deterministic vs semantic split** — a container check digit is arithmetic and an
  LLM should never touch it; whether "cotton knitted shirts" matches "garments,
  knitted" is judgment that rules cannot express

## Status

| Week | Focus | Status |
| --- | --- | --- |
| 1 | Synthetic document generator + ground truth | Done |
| 2 | Extraction pipeline (PDF to structured JSON) | In progress |
| 3 | All document types + normalisation | |
| 4 | Deterministic checks + golden dataset | |
| 5 | Semantic checks + LangGraph orchestration | |
| 6 | Eval harness + CI + baseline metrics | |
| 7 | FastAPI + Docker + deploy + tracing | |
| 8 | Optimisation round + writeup | |

## Documentation

- [The problem](docs/00-problem.md) — shipment lifecycle, parties, where errors originate
- [Architecture](docs/01-architecture.md) — system design and the reasoning behind it
- [Data generation](docs/02-data-generation.md) — how synthetic documents and ground truth are built
- [Decision records](docs/decisions/) — why things are built the way they are

## Quickstart

```bash
uv venv
uv pip install -r requirements-dev.txt

# generate 50 shipment document sets with ground truth
uv run python -m generator.main --count 50 --seed 1 --fresh
```

Output per shipment:

```
data/generated/AUSYD-2026-0001/
├── commercial_invoice.pdf
├── packing_list.pdf
├── bill_of_lading.pdf
├── certificate_of_origin.pdf
├── vgm_certificate.pdf
├── fumigation_certificate.pdf   # only when wooden packaging is declared
└── ground_truth.json
```

## Data

Every document in this repository is **synthetic**. No proprietary or employer data
is used anywhere in the project. Documents are generated from a single internally
consistent shipment, after which known defects are injected — which is what makes
the ground truth exact rather than hand-labelled.

## Licence

MIT