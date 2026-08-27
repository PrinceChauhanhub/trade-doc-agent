# ADR-001: Synthetic documents instead of real ones

**Status:** Accepted
**Date:** 2026-08

## Context

The system needs trade documents to work on: commercial invoices, packing lists,
bills of lading, certificates of origin, treatment certificates. It also needs
ground truth — a statement of which discrepancies exist in each set — because
without that, no accuracy claim about the system is meaningful.

Three sources were available.

**Real documents from work.** Immediately available and maximally realistic. Also
proprietary: they contain client identities, commercial terms, and party details
that belong to an employer and its customers. Not usable in a public repository
under any framing.

**Public samples.** Templates and specimen documents exist online. They are few,
mostly single documents rather than complete shipment sets, and carry no ground
truth. Building a golden dataset from them would mean hand-labelling every
discrepancy — slow, error-prone, and capped at whatever quantity could be found.

**Generated documents.** Build a generator that produces internally consistent
shipments, then injects known defects.

## Decision

Generate all documents synthetically, with defects injected programmatically.

## Rationale

The decisive argument is not privacy — it is that **ground truth comes free**.

When the generator injects an origin mismatch, it knows the shipment is now
defective, which two documents disagree, what each of them says, and what a correct
system should cite. No labelling step exists, so no labelling errors exist either.

That single property unlocks the rest:

- **Scale.** 50 sets or 500 sets cost the same effort.
- **Reproducibility.** Seeded generation means an evaluation run can be repeated
  exactly, which is what makes a before/after comparison attributable to a code
  change rather than to different documents.
- **Controlled difficulty.** Defect frequency, severity mix, and subtlety are all
  tunable. A dataset can be built that is deliberately hard in a specific way.
- **Clean sets on demand.** Roughly 30% of sets carry no defects, making precision
  measurable. Real-world corpora rarely come with a verified "nothing wrong here"
  label.
- **Layout variation by construction.** Each document type renders through multiple
  layouts, so the extractor is forced to read meaning rather than position.

## Consequences

### Accepted costs

**The generator is itself a substantial component.** Roughly a week of work went
into producing documents realistic enough to be worth extracting from — and the
generator has to be right, because a bug in it silently corrupts every metric
downstream. Two such bugs were caught and fixed during Week 1 (per-package weights,
and defect magnitudes large enough to be trivially detectable).

**Synthetic realism has a ceiling.** Generated documents are cleaner than real ones.
They lack scanned pages, stamps overlapping text, handwritten annotations, multi-page
line item tables that break across pages, and the genuinely strange formats that
appear in practice. Reported accuracy is therefore an upper bound on real-world
accuracy, and the README says so.

**Defect distribution is chosen, not observed.** The eleven defect types reflect
domain judgement about what actually causes customs rejections. They are not
sampled from a real error distribution, so the relative frequencies are not
evidence of anything about the field.

### Mitigations

- Multiple layouts per document type, with differing labels, field order, and
  table structure
- Defect magnitudes calibrated to be plausible rather than obvious
- Realism constraints enforced in the generator: valid ISO 6346 check digits,
  weights that reconcile across three independent sources, freight and insurance
  scaled to goods value, FCL and LCL volumes that differ appropriately

### Deferred

A scanned-document path (rasterisation plus OCR, or a vision model) is a real
requirement for production use. It is deliberately out of scope until the text-based
pipeline has measured baselines, because adding an input modality before the core is
instrumented would make it impossible to attribute any change in the numbers.