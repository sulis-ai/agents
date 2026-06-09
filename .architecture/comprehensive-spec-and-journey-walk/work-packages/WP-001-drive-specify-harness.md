---
id: WP-001
title: Build the drive-specify fixture harness
status: pending
sequence_id: WP-001
dependsOn: []
blocks: [WP-006, WP-011, WP-012]
estimated_token_cost:
  input: 6k
  output: 4k
tdd_section: 7.4 (Component Model — fixture harness scripts) + Verification Plan (methodology adapter)
adrs: [ADR-002]
primitive: create
group: expand
kind: backend
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_drive_specify.py::test_drive_specify_emits_document_at_lite
---

## Context

The methodology verification adapter for this change drives `/sulis:specify`
on a fixture behavioural change and asserts the produced artifacts. Seven
scenarios (SC-01, SC-02, SC-03, SC-05, SC-15, SC-16, SC-18) invoke
`plugins/sulis/scripts/_drive_specify.py` as their first step — it is the
single most-shared harness primitive in the scenario set, so it is hoisted
into its own foundational WP (EP-03: extract the shared primitive before any
consumer depends on it). This WP creates the driver and its fixtures only; it
does not change any production specify behaviour.

Advances the DESIGN.md §7.4 "Fixture harness scripts" row and the Verification
Plan's `methodology-fixture-change` deferred need (it builds the reusable
fixture spin-up the plan names).

## Contract

```python
# plugins/sulis/scripts/_drive_specify.py (this WP creates)
# CLI: python3 _drive_specify.py --fixture <name> --depth <lite|standard|deep> --out <path>
#   --fixture: one of the named fixtures this WP ships
#               (sample-user-facing, no-dependencies, sample-tool-surface)
#   --depth:   forces the specify depth (bypasses the proposal so the driver
#              is deterministic — the depth is an input, not negotiated)
#   --out:     path the produced design document is written to
# exit 0 on a produced document; non-zero on a stage failure.
```

Fixtures this WP ships (under `plugins/sulis/scripts/tests/fixtures/methodology/`):
- `sample-user-facing` — a change manifest with one user-facing path so the
  surface heuristic fires.
- `no-dependencies` — a change whose intake cannot populate the dependencies
  section (drives the n/a-marking path for SC-03).
- `sample-tool-surface` — a change exposing tool operations (for SC-18).

Invariants the contract must preserve:
- The driver is deterministic — same fixture + depth ⇒ identical output
  (NFR-04).
- `--depth` is an explicit input; the driver does NOT consult the founder
  proposal flow (keeps the harness non-interactive).
- The driver reuses the real specify stage path; it does not re-implement
  document emission (it is a harness, not a fork).

## Definition of Done

### Red — Failing tests written
- [ ] `plugins/sulis/scripts/tests/test_drive_specify.py::test_drive_specify_emits_document_at_lite` — drives `sample-user-facing` at lite, asserts a file at `--out`.
- [ ] `plugins/sulis/scripts/tests/test_drive_specify.py::test_drive_specify_deterministic_same_fixture_same_depth` — two runs ⇒ byte-identical section set (NFR-04).
- [ ] `plugins/sulis/scripts/tests/test_drive_specify.py::test_drive_specify_nonzero_on_stage_failure` — a broken fixture ⇒ non-zero exit.

### Green — Implementation makes tests pass
- [ ] `_drive_specify.py` exists, parses `--fixture/--depth/--out`, drives the real specify path, writes the document.
- [ ] The three fixtures exist and are minimal.
- [ ] Follows `references/boring-code.md` — explicit args, no module-level state, no metaprogramming.

### Blue — Refactor complete
- [ ] Fixture-loading logic shared with `_drive_journey_walk.py` (WP-002) extracted to a common helper if both read the same manifest shape.
- [ ] No new behaviour introduced in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** none (foundational harness)
- **blocks:** WP-006 (doc emitter is verified via this driver), WP-011 (STRIDE/C4/contract sub-templates verified via this driver), WP-012 (decision emission verified via a sibling driver that reuses this fixture shape)
- **Parallelisable with:** WP-002, WP-003, WP-004 (independent file scope)

## Estimated Token Cost

- **Input:** ~6k (this WP + the specify SKILL path + fixture shape)
- **Output:** ~4k (driver + three fixtures + test file)
- **Total:** ~10k

## Notes

- This is the harness the SC-01/02/03/05/15/16/18 scenarios assume. Building it
  first means every doc-emission WP downstream has a green/red driver from day
  one.
- The `methodology-fixture-change` deferred infra need (DESIGN.md Verification
  Plan) is partially satisfied here — the reusable fixture spin-up lands with
  this WP.
