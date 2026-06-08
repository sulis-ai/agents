---
id: WP-008
title: Add --open/--roadmap/--done/--by-type/--by-state to sulis-brain-query
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-008
dependsOn: [WP-007]
blocks: [WP-010, WP-012, WP-013]
estimated_token_cost:
  input: 7k
  output: 3k
tdd_section: Form — CLI modes; ADR-006 query-seam extension shape
adrs: [ADR-006]
primitive: extend
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_brain_query_cli_modes.py::test_open_done_roadmap_modes
---

## Context

Surfaces the WP-007 query extensions through the existing `sulis-brain-query`
CLI as new mutually-exclusive modes, in the plain founder-facing vocabulary
FR-07 mandates (`--open` / `--roadmap` / `--done`) plus the composable
`--by-type` / `--by-state` (FR-09's seam-level capability). Same
`{"ok":…,"data":{"count":N,"entities":[…]}}` envelope as the existing modes.
EXPAND-Extend: new branches in the existing `main()` mutually-exclusive
group, no new CLI.

## Contract

```text
sulis-brain-query  (new modes, mutually exclusive with existing --list/--by-id/--verifying/...)
  --open                         open = draft requirements + hypothesis opportunities
  --roadmap                      sidecar members resolved to entities
  --done                         implemented/verified requirements
  --by-type {opportunity,requirement}
  --by-state STATE               composable with --by-type
  (existing common args: --base-dir, --domain, --repo-root unchanged)

Output: {"ok": true, "data": {"count": N, "entities": [...]}}  (unchanged envelope)
```

Contract invariants:
- **Envelope unchanged** — identical `{"ok":…,"data":{"count":…,"entities":[…]}}` shape as the existing modes (no consumer breakage).
- **Mutually exclusive** — added to the existing `add_mutually_exclusive_group`; existing modes untouched.
- **`--open`** = `find_requirements(state="draft")` + `find_opportunities(state="hypothesis")` merged; **`--done`** = `find_requirements` filtered to `_DONE_REQUIREMENT_STATES`; **`--roadmap`** = `find_roadmap(...)`. The mapping is the WP-007 module constants — the CLI does not redefine open/done (ADR-006).
- **`--by-type` + `--by-state`** delegate to `find_opportunities` / `find_requirements` with the `state=` kwarg — the composable escape hatch.
- **Empty store → `count:0`**, exit 0 (NFR-01); never an error envelope for an empty result.
- `main()` never raises (existing CLI discipline preserved).

## Definition of Done

### Red — Failing tests written
- [ ] `tests/integration/test_brain_query_cli_modes.py::test_open_done_roadmap_modes` — seed a temp store; `--open` returns draft reqs + hypothesis opps; `--done` returns implemented/verified; `--roadmap` returns sidecar members. Exit 0, envelope shape correct.
- [ ] `tests/integration/test_brain_query_cli_modes.py::test_by_type_by_state_compose` — `--by-type requirement --by-state approved` returns only approved requirements.
- [ ] `tests/integration/test_brain_query_cli_modes.py::test_empty_store_count_zero` — empty temp dir; every new mode → `{"ok":true,"data":{"count":0,"entities":[]}}` exit 0.
- [ ] `tests/integration/test_brain_query_cli_modes.py::test_new_modes_mutually_exclusive_with_existing` — `--open --list requirement` together → argparse rejects (exit 2).
- [ ] `tests/integration/test_brain_query_cli_modes.py::test_existing_modes_unaffected` — `--list opportunity` and `--by-id` still behave as before (regression).

### Green — Implementation makes tests pass
- [ ] All Red tests pass against a temp `.brain/instances`.
- [ ] Calls WP-007 functions; does not re-implement state mapping (ADR-006 single-source).
- [ ] New `import` line adds `find_opportunities, find_roadmap` (and uses the new `state=` kwarg) — no copy of the predicate logic into the CLI.
- [ ] Boring code: explicit mode branches mirroring the existing ones.

### Blue — Refactor complete
- [ ] If `--open` merges two result lists, the merge is a single small helper (dedupe by id) — not inlined twice.
- [ ] No new behaviour in Blue.
- [ ] All tests green after refactor.

## Sequence
- **dependsOn:** WP-007 (the query functions + state constants)
- **blocks:** WP-010 (the backlog skill invokes these modes), WP-012 (the Sulis agent calls these modes), WP-013 (dogfood/scenario asks "what's open")
- **Parallelisable with:** WP-006 (the capture CLI)

## Estimated Token Cost
- **Input:** ~7k (this WP + the existing `sulis-brain-query` + WP-007 contract)
- **Output:** ~3k (CLI mode branches + integration test file)
- **Total:** ~10k

## Notes
- The `--open`/`--roadmap`/`--done` verbs are the vocabulary the founder-facing skill and agent speak; `--by-type`/`--by-state` is the escape hatch an agent drops to when a named view doesn't cover the question (ADR-006).
