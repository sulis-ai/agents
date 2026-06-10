---
id: WP-008
title: Build the UC-flow-coverage gate
status: pending
sequence_id: WP-008
dependsOn: [WP-007]
blocks: [WP-010]
estimated_token_cost:
  input: 7k
  output: 5k
tdd_section: 7.4 (_verify_uc_flow_coverage.py) + 7.5 (three-gate composition)
adrs: [ADR-004]
primitive: create
group: expand
kind: backend
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_verify_uc_flow_coverage.py::test_uncovered_flow_yields_gaps
---

## Context

`_verify_scenario_coverage.py` (#86) classifies per-*scenario* within a journey
but has no UC-flow dimension and no surface dimension — it cannot tell that an
exception flow has no covering scenario. ADR-004 adds a *third companion* gate
(not a rewrite): `_verify_uc_flow_coverage.py` enumerates every UC flow
(main + alternate + exception), maps each to scenarios via the brain (NFR-D01),
and returns a fail-closed `covered`/`gaps` verdict (NFR-S04). It composes with
#103 and #86 (FR-13) — three distinct verdicts, none subsuming the other
(GLOSSARY "NOT the Same As"). This script is BOTH the production gate AND the
driver SC-12/SC-13/SC-14 invoke.

Advances DESIGN.md §6.5 hop T7 (GAP → WP), the §7.4 `_verify_uc_flow_coverage.py`
"Create" row, and the §7.5 three-gate table (the NEW row).

## Contract

```python
# plugins/sulis/scripts/_verify_uc_flow_coverage.py (this WP creates)
def verify_uc_flow_coverage(
    uc_flows: list,            # every flow: main + alternate + exception
    journey_workflow_id: str,
    *, base_dir, planned: set, out_of_scope: set,
) -> Result:                   # verdict: "covered" | "gaps"; uncovered_flows: []
    # For each flow: is there a covering scenario in the brain, OR a planned WP,
    # OR a recorded out-of-scope decision? Absence ⇒ gaps (fail-closed).
# CLI mirrors _verify_scenario_coverage's invocation shape.
```

Invariants:
- Fail-closed: a flow with no covering scenario and no out-of-scope record ⇒
  `gaps` (NFR-S04) — absence is never silently passed.
- Brain-sourced: coverage derives from `_brain_query.find_scenarios_for_journey`
  + the surface-tagged scenarios (WP-007), not an agent claim (NFR-D01).
- It is a *superset check* of #86, not a replacement: #86 checks hops within a
  scenario's journey; this checks a scenario exists per flow at all. Both run.
- Completes < 3 s combined with #103/#86 for ≤ 20 flows (NFR-03).

## Definition of Done

### Red — Failing tests written
- [ ] `test_verify_uc_flow_coverage.py::test_uncovered_flow_yields_gaps` — a journey with one uncovered exception flow ⇒ `gaps` (SC-13, SC-14).
- [ ] `test_verify_uc_flow_coverage.py::test_all_flows_covered_passes` — every flow has a covering scenario ⇒ `covered` (SC-12).
- [ ] `test_verify_uc_flow_coverage.py::test_out_of_scope_flow_not_a_gap` — an uncovered flow with a recorded out-of-scope ⇒ `covered`.
- [ ] `test_verify_uc_flow_coverage.py::test_brain_unreadable_yields_error` — brain unreadable ⇒ `error`, never silent pass.

### Green — Implementation makes tests pass
- [ ] `_verify_uc_flow_coverage.py` exists, enumerates flows, maps via brain, fail-closed verdict.
- [ ] Reads the WP-007 surface tag.
- [ ] #103 and #86 remain unchanged and still pass (FR-13 — companion, not rewrite).
- [ ] Follows `references/boring-code.md`.

### Blue — Refactor complete
- [ ] Brain-query helper shared with `_verify_scenario_coverage.py` (no duplicated `find_scenarios_for_journey` call shape).
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** WP-007 (surface tag the gate reads)
- **blocks:** WP-010 (`scenarios/SKILL.md` surfaces this gate's verdict)
- **Parallelisable with:** WP-009 (different file scope — walk vs gate)

## Estimated Token Cost

- **Input:** ~7k (this WP + #86's existing shape + the brain-query surface)
- **Output:** ~5k (gate script + test file)
- **Total:** ~12k

## Notes

- ADR-004: third companion, not a rewrite. Do not fold the UC-flow logic into
  `_verify_scenario_coverage.py` — they are distinct verdicts (BDR-002).
- SC-12/SC-13/SC-14 invoke this script directly; its CLI is the scenario driver.
