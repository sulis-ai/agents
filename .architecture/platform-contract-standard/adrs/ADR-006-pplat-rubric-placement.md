---
id: ADR-006
title: Rubric P-PLAT placement — append after P-VER (Phase 9) as Phase 10; minor version bump, no re-versioning
status: accepted
date: 2026-06-02
change: platform-contract-standard
relates-to: [FR-015, NFR-005, MUC-004, "PRIMITIVE_TREE:node:rubric-check"]
---

# ADR-006 — P-PLAT rubric placement

## Decision

The Platform Contract gate is enforced mechanically by a **new phase appended to
`plugins/sulis/references/decompose-validation-rubric.md` after Phase 9 (P-VER),
as Phase 10 (P-PLAT)**. P-PLAT mirrors P-VER's structure exactly:

- A **grandfather sub-phase** that reads a `platform_contract_required_from:`
  date constant from the rubric's front matter and the candidate change's
  `started_at` — grandfathering changes started before the standard merges
  (NFR-005), identically to P-VER's mechanism.
- A **failure-mode table** (P-PLAT.01..) — one row per the contract-integrity
  controls (see TDD Armor pillar), each MUST, each with a deterministic
  pass criterion.
- **Verdict semantics:** a P-PLAT MUST failure collapses the overall verdict to
  GAPS_FOUND and emits an FE-readable remediation string naming the exact file to
  produce: *"Platform Contract required at
  `plugins/sulis/references/platform-contracts/<platform>.md`."*

The rubric receives a **minor version bump**; no re-versioning of existing phases.

## Why

- **Defence-in-depth against MUC-004.** The gate is wired in skill prose
  (`/sulis:specify`, `/sulis:draft-architecture`) *and* in the rubric. A prose
  edit that weakens the gate cannot bypass the rubric phase — the rubric runs
  mechanically at decompose time regardless of prose. P-PLAT is the load-bearing
  enforcement leg; the prose is the early, friendly ask.
- **Mirror P-VER, don't invent.** P-VER already solved every structural problem
  P-PLAT faces: grandfathering by change `started_at`, a failure-mode table with
  deterministic criteria, GAPS_FOUND collapse, FE-readable remediation. Mirroring
  it (CP-01 internal prior art) means a reviewer who understands P-VER understands
  P-PLAT for free, and the grandfather mechanism is battle-tested.
- **Append, don't renumber.** Inserting P-PLAT mid-sequence would renumber P-VER
  and break every existing citation to "Phase 9". Appending as Phase 10 is the
  boring, non-breaking placement. (P-PLAT is the *name*; Phase 10 is the
  *position* — the name is what other artifacts cite, exactly as P-VER is cited by
  name not by "Phase 9".)

## Alternatives considered

- **Fold the check into P-VER (Phase 9).** Rejected: P-VER is about the
  Verification Plan's presence and shape; the Platform Contract gate is a distinct
  concern (does a *contract* exist for a gated platform). Conflating them muddies
  both failure messages and couples two independently-calibrated checks.
- **Enforce only in skill prose, no rubric phase.** Rejected: this is exactly
  MUC-004 — a prose-only gate is bypassable by a prose edit. The SRD (FR-015) and
  the misuse analysis both require a mechanical phase. Prose alone is not a gate.
- **A standalone new rubric file.** Rejected: a second rubric file is a second
  thing to invoke and keep in sync; the decompose-validation-rubric is *the* place
  decomposition gates live (Phase 7 ServiceSpec, Phase 9 P-VER are the siblings the
  dispatch names). P-PLAT belongs beside them.
