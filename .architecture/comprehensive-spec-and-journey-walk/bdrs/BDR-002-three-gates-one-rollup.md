---
title: Three distinct gates, one founder-facing verdict rollup
status: accepted
kind: bdr
---

# BDR-002 — Three distinct gates, one founder-facing verdict rollup

## Context

FR-13 requires three companion gates — scenario-required (#103),
journey-coverage (#86), UC-flow-coverage (new) — that each independently block.
MISUSE_CASES.md pre-mortem 3 ("gate fatigue") warns that three overlapping
gates producing confusing multi-block verdicts will erode founder trust and
push founders to skip the discipline (a STRIDE-DoS bypass). This is a product
decision about how the founder *experiences* the gate layer, not a technical
decision about gate logic.

## Decision

Keep the three gates **distinct in logic** (each can independently block, each
has its own auditable verdict — ADR-004) but **report through one
founder-facing rollup**. The founder sees a single plain-English result
("ready to ship" / "not yet — here's the one thing missing"), not three
separate technical verdicts. Internally the three verdicts are preserved (for
the agent, the brain, and downstream tooling); the rollup is a presentation
layer over them, applying founder English (C-06, FE-01..10). When more than one
gate blocks, the rollup leads with the single most important gap, not a list of
three.

## Options Considered

- **Three distinct gates, one rollup (CHOSEN).** Preserves independent blocking
  + auditability; spares the founder the three-verdict cognitive load;
  consistent with the AAF "three lists, not N questions" discipline.
- **Merge the three into one gate** — rejected: violates FR-13; collapses three
  independently-meaningful checks; loses which discipline failed (ADR-004
  rejected this on the logic side).
- **Three separate founder-facing verdicts** — rejected: this IS the gate-
  fatigue failure mode (pre-mortem 3); a non-technical founder can't triage
  three overlapping technical verdicts.

## Consequences

- **Positive:** gate fatigue is mitigated; the founder gets one clear result;
  the three gates stay independently auditable for the agent/brain.
- **Negative:** the rollup is a small presentation layer to build + maintain;
  it must be kept in sync if a fourth gate is ever added.
- **Neutral:** the rollup is founder-facing only; the technical layer keeps the
  three verdicts verbatim for downstream tooling.
