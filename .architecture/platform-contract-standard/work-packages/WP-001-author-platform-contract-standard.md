---
id: WP-001
title: Author PLATFORM_CONTRACT_STANDARD.md (schema + harness-binding + relationship-to-siblings)
status: pending
change_id: "01KT3X2M0JHFN583DKKV77W83C"
kind: methodology
primitive: create
group: EXPAND
sequence_id: WP-001
dependsOn: []
blocks: [WP-002, WP-003, WP-004, WP-006, WP-007]
estimated_token_cost:
  input: 5k
  output: 6k
tdd_section: "Form §component 1 (line 77); Form §dependency-direction (lines 84-111); Armor §controls A-1..A-8 (lines 132-141); FR-001, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-013, FR-016; NFR-001, NFR-002, NFR-003"
adrs: [ADR-001, ADR-003, ADR-004, ADR-005]
verification:
  adapter: methodology
  artifact: tests/methodology/test_platform_contract_standard.py::test_standard_exists
---

## Context

This WP authors the keystone artifact: the **fourth design-stage contract
standard** at
`plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md`. It is the
foundational WP — it **defines the claim-entry schema everything else
conforms to**, the harness-binding discipline, the gate posture, and the
relationship axis distinguishing this contract from its three siblings. Every
other WP in this set cites this file by path; until it exists, nothing else
can reference it.

**TDD reference:** Form pillar component 1 (line 77) names this file and
mandates it mirror the sibling-standard shape
(`CONTRACT_FIRST_STANDARD.md` / `UX_VISUAL_DESIGN_STANDARD.md`). The
canonical claim-entry schema is locked in TDD §Canonical Identifiers
(lines 24-44). The Armor controls table (lines 132-141) is the source for
the standard's per-requirement hardening rationale.

**Why this depends on nothing.** It is the schema author. The contract
storage convention (WP-002), the gate wiring (WP-003), the rubric phase
(WP-004), and the first instance (WP-006) all conform to or enforce the
schema defined here.

**Pre-Work Prior-Art Check (EP-03, MUST):** the three sibling standards
(`CONTRACT_FIRST_STANDARD.md`, `UX_VISUAL_DESIGN_STANDARD.md`,
`architecture/SERVICE_SPECIFICATION.md`) already exist and establish the
standard-document shape (severity convention, model, numbered requirements,
tiers, how-used, provenance, version history). This WP **mirrors** that
shape — it does not invent a new one. Respect-don't-restate: the standard
**references** the faithful-generation-harness's grounding discipline (the
five steps, the failure modes, the terminal verdicts) by pointing at it;
it does not re-derive the faithful-by-construction theory.

## Contract

### Files created

- `plugins/sulis/references/standards/PLATFORM_CONTRACT_STANDARD.md` — NEW.

### Document shape (mirrors the three siblings)

The standard MUST carry, in this order:

1. **Front matter** — `id`, `version` (`0.1.0`), severity-convention pointer.
2. **Severity convention** — MUST / SHOULD / MAY (per repo CLAUDE.md).
3. **Model** — what a Platform Contract *is*: a faithful capture of a
   third-party platform's behaviour at a seam **we do not control**
   (GLOSSARY four-contracts table; TDD line 110).
4. **Relationship to existing standards (FR-016, MUST)** — names the Data
   contract (`CONTRACT_FIRST_STANDARD.md`), the Visual contract
   (`UX_VISUAL_DESIGN_STANDARD.md`), the ServiceSpec
   (`architecture/SERVICE_SPECIFICATION.md`), and states the distinguishing
   axis: the Platform Contract is a *faithful capture*, not a design
   decision.
5. **The claim-entry schema (FR-004)** — reproduced **verbatim** from TDD
   §Canonical Identifiers lines 28-38 (the YAML block) plus the four
   conformance invariants (lines 41-44). This is the single source of the
   schema; WP-002, WP-006, WP-007 all point here.
6. **Numbered requirements `PC-NN`** — one per the Armor control table rows
   A-1..A-8 (TDD lines 132-141), each at MUST/SHOULD, each naming its closed
   MUC + NFR. Maps:
   - `PC-01` ← A-1 (no uncited factual claim; NFR-001/MUC-001).
   - `PC-02` ← A-2 (refusal on ungrounded load-bearing claim; FR-006/MUC-001).
   - `PC-03` ← A-3 (meaning-check not shape-check; NFR-003/MUC-002, FR-007).
   - `PC-04` ← A-4 (honest inference; NFR-002/MUC-006).
   - `PC-05` ← A-5 (freshness via retrieval-date, 180-day reuse flag;
     NFR-006/MUC-003; ADR-003).
   - `PC-06` ← A-6 (probe integrity; NFR-004/MUC-005; ADR-005).
   - `PC-07` ← A-7 (gate not prose-only; NFR-005/MUC-004 — references P-PLAT,
     authored in WP-004).
   - `PC-08` ← A-8 (harness provenance; NFR-007/MUC-007 — the run-reference
     front-matter field; ADR-004).
7. **Harness-invocation discipline (FR-003; ADR-004)** — prose stating a
   Platform Contract is produced by running the faithful-generation-harness
   via `/sulis-brain:execute-workflow`, with the step→artifact mapping
   **referenced** from ADR-004 (not restated). States the harness lives in a
   sibling repo (cross-repo boundary, load-bearing) and that if unresolvable
   the gate emits a BLOCKER (never falls back to hand-authoring; ADR-004 /
   OAQ-1).
8. **Probe-recipe section (FR-008; ADR-005)** — references the probe
   mechanism; `load_bearing:true` ⇒ probe + probe-result.
9. **Gate posture (FR-014; ADR-001)** — hard-gate write/deploy,
   soft-recommend read-only; the escalation/de-escalation override path.
10. **Freshness (FR-013; ADR-003)** — `retrieval-date` per claim; reuse
    surfaces claims past the 180-day named constant; automated re-probe
    deferred (`platform-contract-staleness-reprobe`).
11. **Tiers / how-used** — when a change author produces a contract; reuse
    not regeneration (FR-011).
12. **Provenance + version history** — the GitHub issue #137 need, the
    triggering reusable-workflow incident.

### Reviewability (NFR-003)

Each `PC-NN` requirement carries a plain-language one-line summary at
Flesch-Kincaid Grade ≤ 10 (the founder-facing Armor; TDD lines 143-150).
The standard mandates the `quote` field, not just the URL: "source exists vs
source supports the claim" (GLOSSARY).

## Definition of Done

### Red — Failing test written first

- [ ] `tests/methodology/test_platform_contract_standard.py::test_standard_exists`
  exists and asserts:
  - `PLATFORM_CONTRACT_STANDARD.md` exists at the canonical path.
  - It declares the severity convention (regex for MUST/SHOULD/MAY block).
  - It cites all three siblings by filename (FR-016): `CONTRACT_FIRST_STANDARD.md`,
    `UX_VISUAL_DESIGN_STANDARD.md`, `SERVICE_SPECIFICATION.md`.
  - It contains the claim-entry schema (regex: `inferred:`, `load_bearing:`,
    `probe-result:` keys present).
  - It contains requirement IDs `PC-01`..`PC-08`.
- [ ] Initial run FAILS (the file does not exist yet).

### Green — Implementation makes the test pass

- [ ] Author the standard per the Contract section shape.
- [ ] All twelve document sections present, in order.
- [ ] Claim-entry schema reproduced verbatim from TDD §Canonical Identifiers.
- [ ] `PC-01`..`PC-08` present, each mapped to its A-NN control + MUC + NFR.
- [ ] Harness-invocation discipline references ADR-004 (does not restate the
  step→artifact mapping).
- [ ] Red-phase test passes.

### Blue — Refactor + polish

- [ ] Each `PC-NN` carries an FK ≤ 10 plain-language summary (NFR-003).
- [ ] No restating of harness theory, P-VER mechanism, or sibling-standard
  bodies — citation only (respect-don't-restate).
- [ ] Cross-reference links: each `PC-NN` → its source ADR + MUC.
- [ ] Section ordering matches the sibling standards (a reviewer who knows
  `CONTRACT_FIRST_STANDARD.md` can navigate this one).

## Sequence

- **Sequence ID:** WP-001
- **dependsOn:** — (foundational keystone)
- **blocks:** WP-002 (storage conforms to schema), WP-003 (gate wiring
  references the standard), WP-004 (P-PLAT enforces the schema), WP-006
  (the n=1 contract conforms), WP-007 (tests assert the schema).
- **Parallelisable with:** — (nothing precedes it; everything follows)

## Estimated Token Cost

- **Input:** ~5k (TDD + 4 ADRs + GLOSSARY four-contracts table + one sibling
  standard read for shape).
- **Output:** ~6k (≈ 300-line standard).
- **Total:** ~11k.

## Notes

- This WP is **prose, not code.** The schema it defines is enforced
  mechanically by the `contract` adapter (WP-007) and P-PLAT (WP-004); this
  WP authors the spec they read.
- The harness lives in a **sibling repo**
  (`plugins/sulis-brain/instances/faithful-generation-harness/`) — the
  standard references it; it does not vendor or copy it (ADR-004 cross-repo
  boundary).
- The 180-day staleness threshold is a named constant (OAQ-3 calibration
  item); the standard names it but does not defend the exact number.

## Verification Plan (per-WP)

- **Adapter:** `methodology` — **Shape 1 (concrete).**
- **Artifact:** `tests/methodology/test_platform_contract_standard.py::test_standard_exists`
  (authored in WP-007; this WP's Red writes the assertion stub).
- **Observable:** the standard file exists, carries the severity convention,
  cites the three siblings, and contains the claim-entry schema + `PC-01..08`.
- **No resilience primitive:** methodology prose; no HTTP/RPC hot path.
