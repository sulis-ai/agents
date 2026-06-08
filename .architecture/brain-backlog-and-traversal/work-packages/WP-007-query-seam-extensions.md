---
id: WP-007
title: Extend _brain_query with find_opportunities, state filters, find_roadmap
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-007
dependsOn: [WP-005]
blocks: [WP-008]
estimated_token_cost:
  input: 8k
  output: 3k
tdd_section: Form — query extension; ADR-006 query-seam extension shape
adrs: [ADR-006, ADR-001]
primitive: extend
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_brain_query_views.py::test_open_roadmap_done_views
---

## Context

Advances FR-09 (query-seam extension) and ADR-006. Extends `_brain_query.py`
with the three views the traverse path needs, built **on the existing
predicate combinators** (`where_field_equals`, `where_id_in`,
`find_entities`) — nothing bespoke. `find_opportunities` is the missing
sibling to the existing `find_requirements`; `state=` filtering reuses
`where_field_equals`; `find_roadmap` reuses `roadmap_members` (WP-005) +
`where_id_in`. The open/done state sets are defined **once** as module
constants so the skill (WP-010) and the agent (WP-012) share one definition
(ADR-006). EXPAND-Extend; pure additions preserve existing callers
(kwarg-default-preserving), so no characterisation test is needed (ADR-006
consequence) — but this WP adds the unit coverage for the new modes (Proof).

Reuse mandate (CP-01..05): no new walker, no query engine, no second read
module (all three rejected in ADR-006). Compose the primitives already in
the module.

## Contract

```python
# plugins/sulis/scripts/_brain_query.py  (this WP adds)

_OPEN_REQUIREMENT_STATES   = frozenset({"draft"})
_OPEN_OPPORTUNITY_STATES   = frozenset({"hypothesis"})
_DONE_REQUIREMENT_STATES   = frozenset({"implemented", "verified"})

def find_opportunities(base_dir, *, domain="product-development", state=None) -> list[dict]:
    """Sibling to find_requirements; optional state filter via where_field_equals."""

# find_requirements gains an optional state= kwarg (default None preserves behaviour):
def find_requirements(base_dir, *, domain="product-development", state=None) -> list[dict]: ...

def find_roadmap(base_dir, *, domain="product-development") -> list[dict]:
    """Resolve roadmap_members(base_dir) ids to entities via where_id_in.
    Empty/missing/malformed sidecar → [] (NFR-01)."""
```

Contract invariants:
- **`find_requirements` stays backward-compatible** — `state=None` default reproduces today's behaviour exactly (existing callers: the DoD verification flow, `find_testresults_verifying`, unaffected).
- **State sets defined once** — the skill and agent never re-define `open`/`done`; they call these functions or read these constants (ADR-006 — no duplication across FR-07/FR-08 consumers).
- **Empty store → empty, not error** — every view returns `[]` against a missing/empty base dir (the existing `iter_entities` returns early on a missing dir; NFR-01, Q3).
- **`find_roadmap` tolerates a malformed sidecar** — returns `[]`, never raises (NFR-01).
- Built on `where_field_equals` / `where_id_in` / `find_entities` — no new traversal primitive.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_brain_query_views.py::test_find_opportunities_returns_all_then_filtered` — seed 2 opportunities (hypothesis + validated) in a temp store; `find_opportunities()` → both; `state="hypothesis"` → one.
- [ ] `tests/unit/test_brain_query_views.py::test_find_requirements_state_kwarg_backward_compatible` — `find_requirements()` (no state) returns all; `state="draft"` filters; an existing-style call signature still works.
- [ ] `tests/unit/test_brain_query_views.py::test_open_roadmap_done_views` — seed a mix; assert the open set = draft reqs + hypothesis opps, done set = implemented/verified reqs, roadmap = sidecar members resolved to entities.
- [ ] `tests/unit/test_brain_query_views.py::test_empty_store_returns_empty_not_error` — all three views on an empty temp dir → `[]`, no exception.
- [ ] `tests/unit/test_brain_query_views.py::test_find_roadmap_tolerates_malformed_sidecar` — junk sidecar → `[]` (NFR-01).
- [ ] `tests/unit/test_brain_query_views.py::test_state_sets_are_single_source` — the open/done constants are the only definition (import them; assert membership).

### Green — Implementation makes tests pass
- [ ] All Red tests pass against a temp `.brain/instances` + real vendored schemas.
- [ ] New functions are compositions of existing predicates — no new walker, no SPARQL/RDF layer (ADR-006 rejections honoured).
- [ ] `find_roadmap` reuses `roadmap_members` (WP-005) — does not re-read the sidecar layout itself.
- [ ] Boring code: explicit `frozenset` constants, no string-keyed dispatch.

### Blue — Refactor complete
- [ ] `find_opportunities` and `find_requirements` share the enumerate-then-optionally-filter shape — extract a private `_find_typed(entity_type, state)` if it removes duplication without obscuring.
- [ ] No new behaviour in Blue.
- [ ] All tests green after refactor.

## Sequence
- **dependsOn:** WP-005 (`roadmap_members` reader)
- **blocks:** WP-008 (the CLI surfaces these functions)
- **Parallelisable with:** WP-001, WP-002, WP-003 (capture-side composes)

## Estimated Token Cost
- **Input:** ~8k (this WP + `_brain_query.py` head + WP-005 contract)
- **Output:** ~3k (three functions + constants + test file)
- **Total:** ~11k

## Notes
- Per ADR-006: "no characterisation test needed for a pure addition, but the REINFORCE-Test WP adds unit coverage." This WP *is* that coverage — the Red tests above are the unit net for the new modes.
