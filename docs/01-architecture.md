# Architecture

## Pipeline

```
PDFs (4-6 per shipment)
  |
  v
[Classifier]   which document type is this?
  |
  v
[Extractor]    per-type Pydantic schema, LLM structured fill
  |            retry on validation failure
  |            flag fields that cannot be read
  v
[Normalizer]   units, currencies, date formats, address forms
  |
  v
[Checks]
  |-- Deterministic (Python)  check digits, arithmetic, date order, formats
  |-- Semantic (LLM)          description match, HS code vs goods description
  |-- Conditional             required documents given shipment attributes
  |
  v
[Report]       severity, evidence, source citation per finding
```

## The central decision: deterministic vs semantic

Every check is routed to exactly one of two engines, and the routing is not
negotiable.

**Deterministic checks run in Python.** A container check digit is modulo
arithmetic defined by ISO 6346. An invoice total either equals the sum of its line
items or it does not. A date is either before another date or it is not. An LLM
adds nothing here except cost, latency, and the possibility of being wrong about
arithmetic.

**Semantic checks run through an LLM.** Whether "Men's T-Shirts, 100% Cotton,
Knitted" and "Cotton knitwear, mens" describe the same goods is not expressible as
a rule. Neither is whether "Southern Cross Homewares" and "Southern Cross
Homewares Pty. Limited" are the same legal entity or two different ones.

Getting this split wrong in either direction is a design failure:

- LLM doing arithmetic: unreliable, expensive, and unnecessary
- Rules doing semantics: brittle string matching that breaks on the first
  legitimate paraphrase

## Extraction is separate from truth

The extraction schemas in `extractor/schemas.py` are deliberately **not** the
domain models in `generator/models.py`.

The generator knows the truth. The extractor must not. If both used the same
model, it would be easy to accidentally leak generator state into the extraction
path and produce an evaluation that measures nothing.

Extraction schemas also carry fields the domain model has no reason to hold:

```python
class ExtractedInvoice(BaseModel):
    invoice_number: str | None
    invoice_date: date | None
    total_amount: Decimal | None
    ...
    confidence: dict[str, float]
    extraction_notes: list[str]
```

Every field is nullable. An extractor that says "this field was not present"
is more useful than one that guesses, because a guessed value silently becomes a
false finding downstream.

## Citations are load-bearing

Every finding carries the document, page, and field it came from.

This is not a presentation detail. It is what makes the output usable by someone
who does not trust the system. A broker reading "origin mismatch" has to
re-open both documents to act on it. A broker reading:

```
Invoice p1, line 8:  Country of Origin: India
CoO p1, field 3:     Bangladesh
```

can verify it in ten seconds. The design goal is **verifiability, not trust** —
the system does not need to be believed, only checked quickly.

A hallucinated citation is therefore the most serious failure the system can
produce, worse than a missed finding, and citation accuracy is measured as its own
metric.

## Evaluation is part of the system

The evaluation harness is not a testing afterthought. It is the component that
makes every other decision measurable.

Golden dataset: 50 document sets with exact ground truth, roughly 30% of them
defect-free so that false positives are measurable.

| Metric | Question it answers |
| --- | --- |
| Extraction accuracy | Field-level. How many of ~40 fields were read correctly? |
| Precision | Of the findings raised, how many were real? |
| Recall | Of the real discrepancies, how many were caught? |
| Citation accuracy | Does the cited source actually contain the cited value? |
| Cost / latency | What does one document set cost, and how long does it take? |

The precision/recall trade-off is a deliberate product decision, not a tuning
accident. A missed discrepancy stops a container. A false alarm costs a phone call.
The system is tuned toward recall, and the resulting precision loss is stated
rather than hidden.

Evaluation runs in CI on every push, so a prompt change that improves one document
type and quietly degrades another is visible immediately.

## Model routing

Two tiers, chosen by task:

| Task | Tier | Reason |
| --- | --- | --- |
| Field extraction | Cheap, fast (Gemini Flash / Groq) | High volume, structurally constrained, schema-validated |
| Semantic judgment | Stronger (Claude / GPT) | Low volume, genuinely hard, wrong answers are expensive |

At 50 sets x 5 documents, one evaluation run is 250 extraction calls. Routing all
of them to a frontier model would make evaluation too expensive to run often,
which would defeat the purpose of having evaluation at all.

## Why LangGraph

The flow is not linear:

- Extraction can fail validation and needs bounded retries
- An ambiguous HS code may require a lookup before the check can complete
- Some checks only become applicable once other fields are resolved
- Missing documents change which checks apply

That is a graph with conditional edges and shared state, not a chain.

## Storage

Postgres holds documents, extraction runs, and results. Every run is persisted so
that two runs can be compared field by field after a prompt or model change.

pgvector is present for HS code semantic lookup, not for document retrieval —
there is no retrieval step in this system, which is the point.

## Deliberate non-choices

**No RAG over the documents.** Retrieval answers questions about one document.
This system asks no questions and must see every field of every document.

**No Streamlit backend.** The API is FastAPI. Streamlit exists only as a thin demo
client, so the system remains deployable and callable without it.

**No fine-tuning.** The task is structured extraction against a schema and
reasoning over the result. Prompting plus validation plus retries reaches the
useful range far more cheaply, and the eval harness is what proves it.

**No OCR path yet.** Generated documents are digital PDFs with a text layer. Scanned
input is a real-world requirement but a separate problem, and adding it before the
core is measured would confuse the metrics.