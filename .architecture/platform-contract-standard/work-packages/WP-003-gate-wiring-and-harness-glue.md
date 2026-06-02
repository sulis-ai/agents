---
id: WP-003
title: Wire the design-phase gate + harness-invocation glue into specify + draft-architecture skills
status: pending
change_id: "01KT3X2M0JHFN583DKKV77W83C"
kind: methodology
primitive: extend
group: REINFORCE
sequence_id: WP-003
dependsOn: [WP-001]
blocks: [WP-006]
estimated_token_cost:
  input: 5k
  output: 4k
tdd_section: "Form §component 3 gate-wiring (line 79); Form §component 4 harness-glue (line 80); Armor A-7 (line 140); FR-002, FR-003, FR-014; NFR-005, NFR-007; OAQ-1"
adrs: [ADR-001, ADR-004]
verification:
  adapter: methodology
  artifact: tests/methodology/test_gate_wiring.py::test_skills_reference_platform_contract
---

## Context

Wires the **design-stage gate** (the friendly front leg of the
defence-in-depth pair; the rubric P-PLAT is the enforcement leg) **and** the
**harness-invocation glue** into the two design-phase skills:
`plugins/sulis/skills/specify/SKILL.md` and
`plugins/sulis/skills/draft-architecture/SKILL.md`.

This WP **owns both skill files outright** — gate-detection prose *and* the
harness-invocation step both land here. The TDD flagged (Form line 80;
Decomposition signal lines 326-327) that the harness-glue and the gate-wiring
both touch `draft-architecture/SKILL.md`. **Bundling both edits to the design
skills into one WP eliminates the shared-file collision** the discover-project
lesson warns about — there is exactly one owner of `draft-architecture/SKILL.md`
and one owner of `specify/SKILL.md` across this WP set.

**TDD reference:** Form component 3 (line 79) — prose detects a gated
third-party touch and asks for a Platform Contract. Form component 4 (line 80)
— how the design phase runs the harness via `execute-workflow` and lands the
bound-claim table as the contract body (ADR-004). Armor A-7 (line 140) — the
gate is defence-in-depth; the prose is the early ask, the rubric the hard leg.

**Why this depends on WP-001.** Both the gate prose and the harness-glue
reference `PLATFORM_CONTRACT_STANDARD.md` by path (the gate points the founder
at the standard; the glue produces an artifact conforming to its schema).
Until the standard exists, the references dangle.

**Why this blocks WP-006.** WP-006 *runs* the harness to produce the GitHub
Actions contract — it executes the invocation step authored here. The glue
must exist before the first instance is produced through it.

**Pre-Work Prior-Art Check:** `specify/SKILL.md` and
`draft-architecture/SKILL.md` already gate on the sibling contracts (the Data
contract structural check, the Visual contract gate — tasks #45, #48). This
WP **extends** the existing gate-prose pattern with a fourth contract; it does
not invent a new gate mechanism. Respect-don't-restate: the glue **references**
the harness step→artifact mapping in ADR-004; it does not restate the harness's
internal step semantics.

## Contract

### Files modified

- `plugins/sulis/skills/specify/SKILL.md` — EXTEND (gate-detection prose).
- `plugins/sulis/skills/draft-architecture/SKILL.md` — EXTEND (gate-detection
  prose + harness-invocation step).

### Gate-detection prose (FR-002 / FR-014 / ADR-001)

Both skills gain a step that:
- Detects a **gated third-party touch** in the change's scope.
- For **write/deploy** touches: **hard-gate** — design does not proceed until
  a Platform Contract covering the platform exists (or is produced now via the
  harness-glue step below). The block emits an FE-readable message naming the
  contract to produce: *"This change writes to {platform}. A Platform Contract
  is required first — at `plugins/sulis/references/platform-contracts/{platform}.md`."*
- For **read-only** touches: **soft-recommend** — note that a lightweight
  contract is advisable; do not block (ADR-001).
- Records the escalation override path (a read-only touch that informs a
  write/deploy decision may be escalated to hard-gated with a one-line note;
  de-escalation requires a superseding ADR — ADR-001).

### Harness-invocation step (FR-003 / ADR-004) — `draft-architecture` only

A step that:
- Dispatches the faithful-generation-harness via `/sulis-brain:execute-workflow`
  against the platform's official documentation as the closed manifest.
- Lands the harness's committed claim→source binding table **as the contract
  body** (each binding → one claim entry; flagged inferences →
  `inferred: true` entries) — per the step→artifact mapping **referenced** from
  ADR-004.
- Records the harness-run reference (`LifecycleRun.run_id`) in the produced
  contract's front matter (the provenance P-PLAT checks; NFR-007 / A-8).
- **OAQ-1 / ADR-004 cross-repo handling:** classify the harness integration
  `existing`; if the sibling repo is unresolvable, **emit a BLOCKER** — do
  **not** fall back to hand-authoring a contract.

> The gate prose lives in **both** skills; the harness-invocation step lives in
> **`draft-architecture` only** (the architect runs the harness — ADR-004).
> `specify` only detects-and-asks; it does not run the harness.

## Definition of Done

### Red — Failing test written first

- [ ] `tests/methodology/test_gate_wiring.py::test_skills_reference_platform_contract`
  asserts:
  - Both `specify/SKILL.md` and `draft-architecture/SKILL.md` reference
    `PLATFORM_CONTRACT_STANDARD.md` (or `platform-contracts/`).
  - Both contain the write/deploy hard-gate vs read-only soft-recommend
    distinction (regex for "write", "deploy", "read-only" in the gate step).
  - `draft-architecture/SKILL.md` references `/sulis-brain:execute-workflow`
    (the harness dispatch) **and** the BLOCKER-on-unresolvable path.
- [ ] Initial run FAILS (the prose is not present yet).

### Green — Implementation makes the test pass

- [ ] Extend `specify/SKILL.md` with the gate-detection step (detect + ask,
  no harness run).
- [ ] Extend `draft-architecture/SKILL.md` with the gate-detection step + the
  harness-invocation step (run harness, land binding table, record run-ref,
  BLOCKER on unresolvable).
- [ ] Hard-gate write/deploy, soft-recommend read-only, escalation override
  per ADR-001.
- [ ] Red-phase test passes.

### Blue — Refactor + polish

- [ ] Gate messages are FE-readable (FE-01..11): name the platform, name the
  file to produce, no internal IDs in founder-facing block text.
- [ ] Harness-glue references ADR-004's step→artifact mapping — does not
  restate the harness's internal step semantics (respect-don't-restate).
- [ ] The gate-detection step sits alongside the existing sibling-contract
  gates (Data/Visual) so the four contracts read as one coherent family.

## Sequence

- **Sequence ID:** WP-003
- **dependsOn:** WP-001 (gate + glue reference the standard).
- **blocks:** WP-006 (the n=1 contract is produced by running the harness
  through the glue authored here).
- **Parallelisable with:** WP-002, WP-004 (disjoint file surface — this WP
  owns the two skill files; WP-002 owns `platform-contracts/`; WP-004 owns the
  rubric).

## Estimated Token Cost

- **Input:** ~5k (both SKILL.md files read for the existing gate pattern +
  ADR-001 + ADR-004).
- **Output:** ~4k (gate step in two files + harness-invocation step).
- **Total:** ~9k.

## Notes

- **Single-owner discipline (collision avoidance):** this WP is the *sole*
  editor of both design-skill files across the WP set. The gate prose and the
  harness-glue are bundled here precisely because both touch
  `draft-architecture/SKILL.md` — splitting them would create the shared-file
  collision the discover-project lesson identifies. The two clauses
  (gate-detection, harness-invocation) are one cohesive change to the design
  phase's third-party-touch handling.
- The harness-invocation step is **prose** — it tells the architect agent
  *how* to dispatch the harness; the harness itself is the existing sibling-repo
  Workflow (ADR-004), not built here.

## Verification Plan (per-WP)

- **Adapter:** `methodology` — **Shape 1 (concrete).**
- **Artifact:** `tests/methodology/test_gate_wiring.py::test_skills_reference_platform_contract`.
- **Observable:** a design dispatch naming a write/deploy third-party touch
  stops and asks for a Platform Contract; a read-only touch only recommends.
  The structural test asserts the prose is present; the end-to-end behaviour
  is exercised by WP-008.
- **Resilience:** the harness dispatch's only failure mode (sibling repo
  unresolvable) is handled by the BLOCKER path (ADR-004), not a retry/CB — a
  missing dependency is a hard stop, not a transient fault.
