# ADR-002: Split checks between deterministic code and the LLM

**Status:** Accepted
**Date:** 2026-08

## Context

The system performs around a dozen distinct checks across a shipment's document
set. They are not alike.

Some are arithmetic or standards conformance: a container number either satisfies
the ISO 6346 check digit or it does not; invoice line items either sum to the
printed total or they do not; a certificate is either dated before the bill of
lading or after it.

Others require understanding. Do "Men's T-Shirts, 100% Cotton, Knitted" and
"Cotton knitwear, mens" describe the same goods? Is "Southern Cross Homewares Pty.
Limited" the same legal entity as "Southern Cross Homewares", or a different one?
Does a bill of lading reading "Polyester sportswear" contradict HS code 6109.10?

The obvious path is to route everything through an LLM, since one of the two
categories requires it anyway and a single path is simpler to build.

## Decision

Every check is assigned to exactly one engine, and the assignment is fixed:

- **Deterministic checks execute in Python.** No LLM involvement at any stage.
- **Semantic checks execute through an LLM**, with the result validated against a
  schema before it can produce a finding.

Where a check has both components, it is split. The HS code check is a worked
example: comparing the HS code on the invoice against the one on the certificate of
origin is string equality and runs in Python. Deciding whether the goods
description contradicts the material implied by that HS code is judgment and runs
through the LLM.

## Rationale

**Determinism where determinism is available.** A check digit computation has one
correct answer, obtainable in microseconds at zero cost with no possibility of
variance between runs. Routing it through a language model replaces a guarantee
with a probability — and pays for the downgrade.

**Cost and evaluation frequency.** Fifty document sets at five documents each is
250 extraction calls per evaluation run, before any checking. Adding a dozen
LLM checks per set makes evaluation expensive enough that it stops being run
routinely. An eval harness that is too costly to run on every push has already
failed at its purpose.

**Failure modes stay separable.** When recall drops after a change, the first
question is where. If arithmetic and semantics share a path, a regression could
originate in either, and both are suspects. Separated, an arithmetic check that
fails is a code bug with a stack trace, and a semantic check that fails is a
prompt or model problem. The split makes debugging tractable.

**Rules cannot express semantics either.** The inverse error is equally real.
String matching on goods descriptions produces false positives on every legitimate
paraphrase and false negatives on every deliberate obfuscation. A rules engine that
tries to handle "cotton knitwear" versus "knitted cotton garments" ends up as an
unmaintainable pile of special cases.

## Consequences

### Accepted costs

**Two engines to maintain.** Deterministic checks need unit tests; semantic checks
need eval cases. Neither substitutes for the other.

**Routing is a judgement call at the boundary.** Some checks are not obviously in
one camp. Weight variance is arithmetic, but the tolerance is not: 4% variance on
an LCL consolidation may be routine while the same variance on FCL is not. The
current approach computes the variance deterministically and treats the tolerance
as configuration rather than inference — but the boundary needs deliberate thought
per check rather than a default.

**Adding a check requires deciding its category first.** This is friction, and it
is intentional. The alternative is defaulting everything to the LLM, which is how
the split erodes.

### Benefits realised

- Deterministic checks are unit-testable in isolation, with no API calls
- Evaluation cost stays bounded and dominated by extraction, not checking
- Arithmetic results are identical across runs, so any variance in eval output is
  attributable to the semantic path
- Deterministic checks run first and can short-circuit expensive semantic work

### Interview-facing note

The routing decision is the question most worth being asked about this project.
"Why not just send everything to the model?" has a real answer, and it is the same
answer that separates a working system from a demo.