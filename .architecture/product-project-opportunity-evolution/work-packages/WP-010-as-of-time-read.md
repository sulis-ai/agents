---
id: WP-010
title: Add as-of-time window read to _brain_query — (type, id, as_of) → containing window
status: pending
kind: backend
primitive: extend
group: EXPAND
change_id: CH-01KT61
sequence_id: WP-010
dependsOn: [WP-009]
blocks: [WP-013]
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form #6; Proof §As-of-time read test
adrs: [ADR-003]
verification:
  adapter: backend
  artifact: tests/unit/test_brain_query_as_of.py::test_returns_window_containing_as_of
---

## Context

The read side of the bitemporal window chain (ADR-003). Adds a function to the
existing `_brain_query.py` read seam that, given `(type, id, as_of)`, returns the
window whose `[valid_from, valid_to)` half-open interval contains `as_of`. This
is the query that makes the windows WP-009 writes observable as-of any point in
time. `EXPAND-Extend` through the existing read seam — same flat-file walk,
new signature.

# canonical-source: TDD.md §Form #6 — As-of-time read

## Contract

### Files modified

```
plugins/sulis/scripts/_brain_query.py
```

### Signature

```python
def read_as_of(
    *,
    entity_type: str,
    entity_id: str,
    as_of: str,            # ISO-8601 timestamp
    base_dir: Path,        # repo-local OR central Tenant home (ADR-005)
) -> dict | None:
    """Return the window whose [valid_from, valid_to) contains as_of.
    as_of after the latest open window → the open window.
    as_of before the first window → None."""
```

Half-open interval semantics: `valid_from <= as_of < valid_to`; an open window
has `valid_to == None` (treated as +∞). Reuses the existing `iter_entities`
flat-file walk — no new traversal code.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_brain_query_as_of.py::test_returns_window_containing_as_of` — given 3 windows, returns the right one
- [ ] `tests/unit/test_brain_query_as_of.py::test_as_of_in_open_window_returns_open` — `as_of` after the latest closes → the open window
- [ ] `tests/unit/test_brain_query_as_of.py::test_as_of_before_first_returns_none`
- [ ] `tests/unit/test_brain_query_as_of.py::test_boundary_is_half_open` — `as_of == valid_to` of window N returns window N+1, not N
- [ ] `tests/unit/test_brain_query_as_of.py::test_runs_against_real_temp_dir` — real temp dir, no mock (MEA-09)

### Green — Implementation makes tests pass

- [ ] `read_as_of` added to `_brain_query.py` per Contract
- [ ] Reuses `iter_entities` for the walk; window selection is half-open interval logic

### Blue — Refactor complete

- [ ] No duplicate flat-file walk — extends the existing seam
- [ ] Half-open boundary logic in one place; documented in the docstring
- [ ] `base_dir` parameter lets the same function serve repo-local and central home (ADR-005)

## Sequence

- **dependsOn:** WP-009 (reads the windows evolve writes; the window shape must exist)
- **blocks:** WP-013 (peer-collision serialisation — WP-013's `find_current_for_tenant` edit to `_brain_query.py` lands after this WP's `read_as_of` edit to the same file)

## Estimated Token Cost

- **Input:** ~3k (existing `_brain_query` + ADR-003)
- **Output:** ~3k
- **Total:** ~6k

## Notes

- `extend` not `create`: the read seam exists; this adds a new signature behind
  it (EXPAND-Extend through the extension point), matching the seam's
  impl-swappable design.
