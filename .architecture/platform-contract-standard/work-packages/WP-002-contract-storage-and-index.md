---
id: WP-002
title: Create platform-contracts storage directory + derived INDEX.md
status: pending
change_id: "01KT3X2M0JHFN583DKKV77W83C"
kind: methodology
primitive: create
group: EXPAND
sequence_id: WP-002
dependsOn: [WP-001]
blocks: [WP-006, WP-007]
estimated_token_cost:
  input: 2k
  output: 2k
tdd_section: "Form §component 2 (line 78); Canonical Identifiers §storage-path (lines 46-50); FR-010, FR-011; NFR-006"
adrs: [ADR-002]
verification:
  adapter: methodology
  artifact: tests/methodology/test_platform_contract_standard.py::test_storage_and_index_present
---

## Context

Creates the durable store for Platform Contracts and its derived index:

- Contracts: `plugins/sulis/references/platform-contracts/<platform>.md`
  (`<platform>` = lowercase-hyphenated slug).
- Index: `plugins/sulis/references/platform-contracts/INDEX.md` — a derived
  view listing every contract, its platform, its harness-run reference, and
  its newest/oldest `retrieval-date` (the freshness column that the reuse
  path reads; FR-011 / FR-013).

**TDD reference:** Form pillar component 2 (line 78) names the directory +
derived INDEX as the durable store; ADR-002 fixes the storage layout and the
INDEX-as-derived-view decision. The storage-path convention is locked in
TDD §Canonical Identifiers lines 46-50.

**Why this depends on WP-001.** The claim-entry schema (which every stored
contract conforms to) is defined in the standard. The INDEX's freshness
column reads the `retrieval-date` field defined by that schema. Until the
standard exists, the storage convention has nothing to point at.

**Why this is a separate WP from the standard.** The standard *defines* the
schema (a spec); this WP *creates the directory and the index machinery* (a
store). Disjoint file surface: WP-001 touches only `standards/`, this WP
touches only `platform-contracts/`. No collision.

**Pre-Work Prior-Art Check:** no `platform-contracts/` directory exists yet
(this is the first design-stage contract with a *per-instance* store — the
sibling contracts are produced per-change, not stored centrally). The INDEX
shape mirrors other derived `INDEX.md` files in the repo (e.g.
`hardening-deltas/INDEX.md`, `work-packages/INDEX.md`).

## Contract

### Files created

- `plugins/sulis/references/platform-contracts/INDEX.md` — NEW (derived view).
- `plugins/sulis/references/platform-contracts/.gitkeep` or a `README` stub
  — NEW (so the directory exists in a fresh clone before the first contract
  lands).

> The first actual contract (`github-actions.md`) is created in WP-006, not
> here. This WP creates the **container + index**, not the content.

### INDEX.md shape (derived view — ADR-002)

```markdown
# Platform Contracts — Index

> Derived view. One row per contract in this directory.
> Reuse path (FR-011): a change touching a listed platform treats it as
> covered, subject to freshness (FR-013 — flag any claim past 180 days).

| Platform | Contract | Harness run | Oldest retrieval-date | Stale? (>180d) |
|---|---|---|---|---|
| (none yet — first contract lands in WP-006) | | | | |
```

The INDEX is **derived**, not hand-maintained as source of truth: the row
data is computable from each contract's front matter. ADR-002 records that a
later automation can regenerate it; for this change it is authored once and
updated by WP-006 when `github-actions.md` lands.

## Definition of Done

### Red — Failing test written first

- [ ] `tests/methodology/test_platform_contract_standard.py::test_storage_and_index_present`
  asserts:
  - `plugins/sulis/references/platform-contracts/` exists.
  - `platform-contracts/INDEX.md` exists with the column header row
    (`Platform | Contract | Harness run | Oldest retrieval-date | Stale?`).
- [ ] Initial run FAILS (directory + INDEX do not exist).

### Green — Implementation makes the test pass

- [ ] Create the directory with a tracked placeholder.
- [ ] Author `INDEX.md` with the derived-view header + the freshness column.
- [ ] Red-phase test passes.

### Blue — Refactor + polish

- [ ] INDEX header prose states the reuse + freshness semantics (FR-011 /
  FR-013) so a reader understands the table without the standard.
- [ ] No duplication of the claim-entry schema — INDEX references the
  standard for the schema (respect-don't-restate).

## Sequence

- **Sequence ID:** WP-002
- **dependsOn:** WP-001 (the stored artifacts conform to the schema the
  standard defines; the INDEX freshness column reads `retrieval-date`).
- **blocks:** WP-006 (the GitHub Actions contract lands in this directory and
  adds a row to this INDEX), WP-007 (conformance test reads the directory).
- **Parallelisable with:** WP-003, WP-004 (disjoint file surface — they touch
  skill files + the rubric, this touches `platform-contracts/`).

## Estimated Token Cost

- **Input:** ~2k (ADR-002 + storage-path canonical + one existing INDEX for
  shape).
- **Output:** ~2k (INDEX skeleton + placeholder).
- **Total:** ~4k.

## Notes

- The INDEX is a **derived view** (ADR-002) — it is not the source of truth;
  each contract's front matter is. For this change it is hand-authored; a
  regeneration script is out of scope.
- WP-006 is the WP that adds the first real row (when `github-actions.md`
  lands). This WP leaves the table with the explicit "none yet" placeholder.

## Verification Plan (per-WP)

- **Adapter:** `methodology` — **Shape 1 (concrete).**
- **Artifact:** `tests/methodology/test_platform_contract_standard.py::test_storage_and_index_present`.
- **Observable:** the directory + INDEX exist with the freshness column header.
- **No resilience primitive:** filesystem layout; no external call.
