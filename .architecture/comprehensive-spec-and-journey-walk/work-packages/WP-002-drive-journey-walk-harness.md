---
id: WP-002
title: Build the drive-journey-walk fixture harness
status: pending
sequence_id: WP-002
dependsOn: []
blocks: [WP-009, WP-013]
estimated_token_cost:
  input: 6k
  output: 4k
tdd_section: 7.4 (Component Model — fixture harness scripts) + Verification Plan (methodology adapter)
adrs: [ADR-003]
primitive: create
group: expand
kind: backend
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_drive_journey_walk.py::test_drive_journey_walk_emits_walk_section
---

## Context

Five scenarios (SC-06, SC-07, SC-08, SC-09, SC-19) drive the design-stage
journey walk through `plugins/sulis/scripts/_drive_journey_walk.py`. It is the
second most-shared harness primitive after `_drive_specify.py`, so it is
hoisted into its own foundational WP (EP-03). This WP builds the driver and the
walk fixtures only; it does not change the production step-8.5 walk (that is
WP-009).

Advances the DESIGN.md §7.4 "Fixture harness scripts" row and supports the
two-surface walk verification (NFR-D02).

## Contract

```python
# plugins/sulis/scripts/_drive_journey_walk.py (this WP creates)
# CLI: python3 _drive_journey_walk.py --fixture <name> --surface <ui|tool> --out <path>
#   --surface: which surface walk to drive (ui or tool)
#   --out:     path the produced design doc (with the Journey Walk section) lands
# exit 0 on a completed walk with no bare GAP; exit 1 when a bare GAP blocks
#   design completion (so SC-07 and SC-09 can assert the blocking behaviour).
```

Fixtures this WP ships (under `plugins/sulis/scripts/tests/fixtures/methodology/`):
- `ui-with-gap` — a UI journey with one hop that has neither a component nor a
  planned WP (drives SC-07 blocking).
- `sample-tool-surface` — reused from WP-001 if shape-compatible; otherwise a
  tool-operation fixture for SC-08.
- `tool-serving-no-binding` — a fixture where the handler serves but has no
  ServiceSpec binding (drives SC-09 GAP classification).

Invariants:
- Deterministic walk output for an unchanged worktree (NFR-04).
- A bare GAP ⇒ non-zero exit (fail-closed at the walk level, NFR-S04).
- The driver reuses the real step-8.5 walk procedure; it does not re-implement
  classification.

## Definition of Done

### Red — Failing tests written
- [ ] `plugins/sulis/scripts/tests/test_drive_journey_walk.py::test_drive_journey_walk_emits_walk_section` — drives a clean UI fixture, asserts a Journey Walk section in `--out`.
- [ ] `plugins/sulis/scripts/tests/test_drive_journey_walk.py::test_bare_gap_yields_nonzero_exit` — `ui-with-gap` ⇒ exit 1 (SC-07).
- [ ] `plugins/sulis/scripts/tests/test_drive_journey_walk.py::test_tool_serving_no_binding_is_gap` — `tool-serving-no-binding` ⇒ exit 1 (SC-09).

### Green — Implementation makes tests pass
- [ ] `_drive_journey_walk.py` exists, parses `--fixture/--surface/--out`, drives the real walk, writes the doc.
- [ ] The three walk fixtures exist.
- [ ] Follows `references/boring-code.md`.

### Blue — Refactor complete
- [ ] Fixture-loading shared with WP-001's helper if applicable.
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** none (foundational harness)
- **blocks:** WP-009 (tool-surface walk verified via this driver), WP-013 (walk-⊆-contract assertion verified via this driver)
- **Parallelisable with:** WP-001, WP-003, WP-004

## Estimated Token Cost

- **Input:** ~6k
- **Output:** ~4k (driver + fixtures + test file)
- **Total:** ~10k

## Notes

- Builds the green/red driver every P2 walk WP needs.
- The `--surface tool` path exercises the WP-009 second-table walk once that
  lands; until then it exercises the existing single-surface walk.
