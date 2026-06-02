---
id: ADR-001
title: Canonical-as-spec for discover-project — Path A n=2 dogfood
status: accepted
date: 2026-06-01
deciders: [iain]
extends: ../../release-train-as-entities/adrs/ADR-001-path-a-as-v1-execution-strategy.md
---

## Context

`release-train-as-entities` (CH-01KSZ4) established Path A: canonical
JSON-LD entities are the specification of truth; the imperative
implementation (a YAML workflow there; a Markdown skill here) is the
executable; a drift detector at PR time enforces conformance.

The drift detector has since become blocking
(`7d666df extend: tighten-drift-gate`) — any divergence between
canonical and imperative fails branch-CI.

This change is the **n=2 dogfood**. If Path A holds for a second
non-trivial workflow whose imperative side is a different shape (a
Markdown skill rather than a YAML workflow), the pattern proves out
beyond its first encoded instance.

The alternative for v1 of discover-project would be:

- **Author the skill directly without canonical entities.** The skill
  works in isolation; no drift gate; no audit trail; no queryability;
  no way to express FailureMode coverage as data.

That alternative would be a regression on what we just shipped, and
would mean the marketplace has one Workflow under Path A discipline
and one outside it — a worse state than uniformly applying the
discipline.

## Decision

**Apply Path A to discover-project unchanged.** The canonical entity
files at `plugins/sulis/instances/discover-project/` are the
specification; the skill at `plugins/sulis/skills/discover-project/SKILL.md`
is the imperative; the drift detector validates them.

Skill conformance annotations use HTML comments (`<!-- canonical:step:<name> -->`)
because the imperative is Markdown rather than YAML. The drift detector
gains a small extension (WP-009) to parse HTML-comment annotations in
addition to YAML comment annotations. The matching logic is unchanged —
only the annotation parser's input format differs.

## Options Considered

- **Path A (CHOSEN).** Reuses the discipline + tooling already shipped.
  n=2 evidence for the pattern. Drift detector catches skill/canonical
  divergence at PR time exactly as it does for release-train.
- **Author skill directly, no canonical entities** — rejected.
  Inconsistent with release-train; loses gap-detection, queryability,
  audit-traceability. No FailureMode coverage as data.
- **Wait for n=3 before generalising Path A** — rejected. The
  generalisation already happened when Path A was named in
  release-train's ADR-001. n=2 either confirms the pattern or surfaces
  a defect; either outcome is information we need.

## Consequences

- **Positive:** Path A pattern hardened by the second instance.
  Drift detector exercised on a Markdown imperative — confirms the
  parser extension is the only delta. Discovery becomes audit-able and
  query-able the same way release-train is.
- **Negative:** Drift detector needs a small extension (WP-009) for
  HTML-comment annotation parsing. Two annotation formats coexist
  (`#` for YAML, `<!--` for Markdown). The detector's parser becomes
  multi-format — a small complexity cost.
- **Neutral:** Skill prose is unchanged in shape — same front matter,
  same section structure, just with annotations as the binding mechanism
  to canonical Steps.

## Composition

This ADR **extends** `release-train-as-entities` ADR-001. It does not
supersede or contradict; it confirms Path A for a second use case.
