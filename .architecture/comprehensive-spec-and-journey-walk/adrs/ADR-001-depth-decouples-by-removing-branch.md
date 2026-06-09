---
title: Depth decouples from doc-existence by removing the doc-shape branch
status: accepted
kind: adr
---

# ADR-001 — Depth decouples from doc-existence by removing the doc-shape branch

## Context

The current pipeline gates the *document shape* on depth: `specify/SKILL.md`
(lines 54–56) branches lite → 10-line SPEC / standard → 5-section SPEC / deep →
full doc via the requirements specialist. The `_specify_classifier`'s
`_DEPTH_PHRASE` reinforces this in founder prose ("a quick lite spec (three
lines)"). FR-01/02/03 require the comprehensive document to be produced for
EVERY behavioural change regardless of depth, with depth sizing only the
intake. The classifier must stay deterministic and pure (C-03).

The temptation is to add a new branch — "if always_comprehensive: emit full;
else: legacy". That keeps the coupling alive behind a flag and invites drift.

## Decision

**Decouple by removing the doc-shape branch, not by adding one.** The doc
emitter stops reading `classify_depth`'s output to decide *which* sections
exist; it reads it only to decide *how much detail* to populate. The Target
Structure (FR-11) is invariant; detail is `f(intake)`. `classify_depth` itself
is unchanged in signature and purity (C-03) — only its *callers'* wiring
changes (FR-03: no doc-section emission branches on its result). The
founder-facing `_DEPTH_PHRASE`/`_DEPTH_ALT` are reworded to describe interview
size, never document completeness (FR-04).

## Options Considered

- **Remove the branch; detail-only depth (CHOSEN).** One code path emits the
  full structure always; depth tunes detail. No flag, no second path to drift.
  Pure classifier untouched.
- **Feature-flag the comprehensive emitter** — rejected: keeps the legacy
  thin-doc path alive, so the bypass (MUC-01) survives behind the flag; two
  paths drift.
- **Make the classifier itself emit the structure** — rejected: violates C-03
  (the classifier would need to know the Target Structure, coupling a pure
  decision function to document concerns).

## Consequences

- **Positive:** the bypass is structurally impossible — there is no thin-doc
  code path to fall into under token pressure. The classifier stays pure and
  deterministic (NFR-01). Founder prose stops lying about doc thinness (FR-04).
- **Negative:** every change now pays the comprehensive-doc cost; bounded by
  NFR-02 (≤ 1.6× legacy lite) and NFR-R01 (degrade detail, not existence). The
  always-comprehensive emitter + template is net-new work (Phase 1).
- **Neutral:** the interview modes (lite/standard/deep) are unchanged in how
  they gather context — only their coupling to document shape is severed.
