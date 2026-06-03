---
id: WP-015
title: Refactor minter to canonical repo.save + write_project_mirror, and update discover-project Mint prose
status: pending
kind: backend
primitive: refactor
group: REORGANISE
change_id: CH-01KT61
sequence_id: WP-015
dependsOn: [WP-014]
blocks: []
characterisation_test: tests/characterisation/test_minter_reconcile_baseline.py
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: Form #9, #10; Armor §Path-safety preserved on reconcile, §Graceful degradation; Proof §Project reconcile
adrs: [ADR-006]
verification:
  adapter: backend
  artifact: tests/unit/test_minter_reconcile.py::test_canonical_save_then_mirror
---

## Context

ADR-006's reconcile: the brain store becomes the **canonical** Project home;
`.sulis/projects/<slug>.jsonld` becomes a **human-facing mirror**. `_discovery/minter.py`
changes from writing the entity to `.sulis/projects` only, to:
1. canonical `repo.save("project", …)` (the brain store — central home via the
   port WP-013 wired), then
2. `write_project_mirror(…)` (the human mirror, canonical-first / mirror-second).

**REORGANISE-Refactor on internal code**, gated by WP-014's characterisation test
(EP-07 MUST). The path-safety discipline (`_assert_path_safety`, `_atomic_write`,
`_assert_not_exists` MUC-003, stale-tmp sweep, SIGINT handler) is preserved
**verbatim**, now guarding the mirror write. Graceful degradation: a failed
canonical write writes no mirror; a failed mirror after a good canonical save is
a logged best-effort degradation. This is **not a wrap** over `write_project_entity`
— the function is edited in place.

The discover-project skill's Mint-phase prose is updated to match (canonical-first,
mirror-second) and a canonical Workflow Step is updated where the prose references
it (Path-A drift parity, covered by the existing detector).

# canonical-source: TDD.md §Form #9, #10 — Project reconcile in minter

## Contract

### Files modified

```
plugins/sulis/scripts/_discovery/minter.py        # write_project_entity → canonical save + mirror
plugins/sulis/skills/discover-project/SKILL.md     # Mint-phase prose: canonical-first / mirror-second
```

### Surface

```python
def write_project_entity(...):
    """Canonical-first / mirror-second.
    1. repo.save("project", project_dict)   # brain store (central home, WP-013)
    2. write_project_mirror(project_dict, mirror_path)  # human mirror, path-safe
    A failed canonical save writes no mirror; a failed mirror after a good save
    is a logged best-effort degradation (graceful)."""
```

Project is a living entity by now (WP-012) — a re-discovery of an existing Project
is an `evolve_entity` call, not a fresh `save` (MUC-003 still refuses a duplicate
*mint*; re-discovery evolves the existing one).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_minter_reconcile.py::test_canonical_save_then_mirror` — brain store written first, then the mirror
- [ ] `::test_path_safety_preserved` — the four safety properties from WP-014 still hold on the mirror write (verbatim discipline)
- [ ] `::test_muc003_refuses` — duplicate mint refused; re-discovery evolves instead
- [ ] `::test_failed_canonical_writes_no_mirror` — canonical failure → no mirror file
- [ ] `::test_failed_mirror_after_good_save_degrades` — mirror failure after good save is logged, not raised
- [ ] WP-014 characterisation baseline still green (safety unchanged) or updated with documented diff
- [ ] `tests/unit/test_check_canonical_drift_lifecycle_steps.py` (or the discover-project drift test) green for the updated Mint prose

### Green — Implementation makes tests pass

- [ ] `write_project_entity` does canonical `repo.save` then `write_project_mirror`
- [ ] Path-safety helpers preserved verbatim, now guarding the mirror
- [ ] discover-project SKILL.md Mint prose updated to canonical-first / mirror-second; Path-A drift detector green

### Blue — Refactor complete

- [ ] No wrap over `write_project_entity` — the function is edited in place (REORGANISE, not SUBSTITUTE)
- [ ] One canonical writer, one derived mirror (ADR-006 — no sync job, no dual-source)
- [ ] Mirror write reuses the existing `_atomic_write` + `_assert_path_safety` — no second safety implementation

## Sequence

- **dependsOn:** WP-014 (characterisation baseline — MUST be green first)
- **blocks:** — (the join completes here; build-order piece 6 is terminal)

## Estimated Token Cost

- **Input:** ~4k (`minter.py` + discover-project SKILL.md + ADR-006)
- **Output:** ~4k
- **Total:** ~8k

## Notes

- The second REORGANISE-Refactor; characterisation-test-first via WP-014.
- Transitively depends on WP-012 + WP-013 through WP-014 — this is the join of
  build-order pieces 3+4+5 (per TDD §Build Order: piece 6 dependsOn 3, 4, 5).
- discover-project SKILL.md prose edit + minter edit ship together: the prose
  describes exactly what the minter now does (one reconcile contract); splitting
  would let prose and code drift mid-slice.
