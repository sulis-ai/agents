---
id: WP-007
title: Add a first-class surface tag to scenario authoring
status: pending
sequence_id: WP-007
dependsOn: []
blocks: [WP-008, WP-009]
estimated_token_cost:
  input: 5k
  output: 3k
tdd_section: 7.4 (_scenario_authoring.py)
adrs: [ADR-005]
primitive: extend
group: expand
kind: backend
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_scenario_authoring.py::test_assemble_scenario_graph_tags_surface
---

## Context

`assemble_scenario_graph` (`_scenario_authoring.py` lines 51–60) carries
`name/verifies/exercises/tenant/seed/steps` but no `surface` parameter — a
scenario cannot be tagged UI vs tool as a first-class property (FR-10, UC-05 2a).
ADR-005 adds only a `surface` tag; no new driver mechanism (FR-14 forbids it).
This extends an existing extension point (the function signature) and preserves
`seed` stability (NFR-05). Additive-optional: absent reads as `ui` (the current
single-surface default), so existing scenarios are unaffected (DESIGN.md §9.1).

Advances DESIGN.md §6.5 hop T5 (GAP → WP) and the §7.4 `_scenario_authoring.py`
row.

## Contract

```python
# plugins/sulis/scripts/_scenario_authoring.py (this WP modifies)
def assemble_scenario_graph(
    *, name, verifies, exercises, tenant, seed, steps,
    surface: str = "ui",   # NEW — "ui" | "tool"; absent reads as "ui"
):
    # surface is persisted as a first-class property on the Scenario brain node.
    ...
```

Invariants:
- `surface` defaults to `"ui"` so existing scenarios + their `seed`-derived IDs
  are unchanged (NFR-05, additive-optional migration §9.1).
- The tag is persisted on the Scenario node and readable via `_brain_query`
  (NFR-D01 — brain is truth).
- No new driver mechanism introduced (FR-14); per-step `mechanism`/`tool_ref`
  unchanged.

## Definition of Done

### Red — Failing tests written
- [ ] `test_scenario_authoring.py::test_assemble_scenario_graph_tags_surface` — assemble with `surface="tool"` ⇒ the brain bundle carries `surface: tool`.
- [ ] `test_scenario_authoring.py::test_surface_defaults_to_ui` — omit `surface` ⇒ reads `ui` (back-compat).
- [ ] `test_scenario_authoring.py::test_seed_stability_preserved` — same seed ⇒ identical scenario id with or without surface (NFR-05).

### Green — Implementation makes tests pass
- [ ] `surface` param added with `"ui"` default; persisted on the Scenario node.
- [ ] Round-trips via `_brain_query`.
- [ ] Follows `references/boring-code.md` — explicit param, no kwargs magic.

### Blue — Refactor complete
- [ ] No duplicated surface-validation logic; one enum check.
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** none (additive param on an existing function)
- **blocks:** WP-008 (UC-flow gate reads the surface tag), WP-009 (the tool walk authors tool-surface scenarios)
- **Parallelisable with:** WP-006 (P1 doc side), WP-004

## Estimated Token Cost

- **Input:** ~5k
- **Output:** ~3k
- **Total:** ~8k

## Notes

- ADR-005: reuse the #98 substrate, add only the tag. Resist adding a tool-only
  driver — the substrate already resolves drivers per step.
