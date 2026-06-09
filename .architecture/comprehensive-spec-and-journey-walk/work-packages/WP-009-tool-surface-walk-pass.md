---
id: WP-009
title: Extend step 8.5 to a two-surface walk with the tool-surface binding bar
status: pending
sequence_id: WP-009
dependsOn: [WP-002, WP-006, WP-007]
blocks: [WP-013]
estimated_token_cost:
  input: 9k
  output: 6k
tdd_section: 7.4 (draft-architecture/SKILL.md step 8.5) + 6.5 (Surface B)
adrs: [ADR-003]
primitive: extend
group: expand
kind: docs
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_drive_journey_walk.py::test_tool_surface_second_table_present
---

## Context

`draft-architecture/SKILL.md` step 8.5 walks one surface (UI). ADR-003 adds a
second walk pass over the tool surface, reusing step 8.5's procedure and the
binding bar already proven for host-rendered hops. FR-08 needs a second table
covering every tool operation; FR-09 needs the EXISTS-requires-BOTH-handler-AND-
ServiceSpec-binding bar; NFR-D02 needs both tables persisted. The tool operations
are drawn from the interface-contract section (the skeleton stub from WP-006;
filled in WP-011). This WP also ships the walk-table assertion scripts the
SC-06/08 + SC-10/11 scenarios invoke (`_assert_walk_table.py`,
`_assert_flow_scenario_map.py`, `_drive_scenario.py`).

Advances DESIGN.md §6.5 hop T4 (GAP → WP) + Surface B, and the §7.4
`draft-architecture/SKILL.md` "Modify" row.

## Contract

```text
# plugins/sulis/skills/draft-architecture/SKILL.md (this WP extends step 8.5)
#   Add a second walk pass: for each tool operation drawn from the interface-
#   contract section, classify EXISTS (handler AND binding cited) | planned-WP |
#   GAP. EXISTS requires BOTH a handler cite AND a ServiceSpec binding cite
#   (FR-09); a serving handler with no binding is a GAP (NFR-S02). Emit a SECOND
#   `## Journey Walk` table alongside the UI table (NFR-D02).

# plugins/sulis/scripts/_assert_walk_table.py (this WP creates)
#   --surface <ui|tool> [--no-bare-gap] [--require-two-tables] ⇒ exit 0 iff the
#   named table classifies every hop and (when --require-two-tables) both tables
#   are present.
# plugins/sulis/scripts/_assert_flow_scenario_map.py (this WP creates)
#   ⇒ exit 0 iff every UC flow maps to ≥1 scenario (SC-10).
# plugins/sulis/scripts/_drive_scenario.py (this WP creates)
#   drives a single authored scenario; an undrivable tool scenario ⇒ recorded
#   deferred, never silent skip (SC-11, NFR-R02).
```

Invariants:
- A tool hop is EXISTS only if BOTH handler AND binding are cited (FR-09,
  NFR-S02) — the generalisation of the host-rendered bar, not a new rule
  (DESIGN.md §7.7).
- Both tables persist in the Journey Walk section (NFR-D02).
- A bare GAP in either surface blocks design completion (SC-07, SC-09 — driven
  via WP-002's `_drive_journey_walk`).
- The two-surface walk adds ≤ 1 agent turn over single-surface (NFR-S01).
- Every walked tool operation appears in the contract section (FR-19) — enforced
  mechanically by WP-013's subset assertion (this WP draws from the contract;
  WP-013 proves the subset).

## Definition of Done

### Red — Failing tests written
- [ ] `test_drive_journey_walk.py::test_tool_surface_second_table_present` — `sample-tool-surface` ⇒ `_assert_walk_table --surface tool --require-two-tables` exits 0 (SC-08).
- [ ] `test_drive_journey_walk.py::test_ui_walk_classifies_all_hops` — `_assert_walk_table --surface ui --no-bare-gap` exits 0 (SC-06).
- [ ] `test_drive_journey_walk.py::test_serving_no_binding_is_gap` — `tool-serving-no-binding` ⇒ exit 1, operation classified GAP not EXISTS (SC-09).
- [ ] `test_flow_scenario_map.py::test_every_flow_has_a_scenario` — `_assert_flow_scenario_map` exits 0 when each flow has ≥1 scenario (SC-10).
- [ ] `test_drive_scenario.py::test_undrivable_tool_recorded_deferred` — an undrivable tool scenario ⇒ recorded deferred, non-silent (SC-11).

### Green — Implementation makes tests pass
- [ ] Step 8.5 carries the tool-surface walk pass + the FR-09 binding bar + the second-table emission.
- [ ] `_assert_walk_table.py`, `_assert_flow_scenario_map.py`, `_drive_scenario.py` exist and pass.
- [ ] Tool operations are drawn from the WP-006 contract-section skeleton.
- [ ] All five scenario assertions pass through WP-002's driver + these scripts.

### Blue — Refactor complete
- [ ] UI-walk and tool-walk share the hop-classification helper (one classifier, two surfaces) — no duplicated EXISTS/GAP logic.
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** WP-002 (the walk driver), WP-006 (the contract-section skeleton the tool walk draws operations from), WP-007 (the surface tag scenarios carry)
- **blocks:** WP-013 (the walk-⊆-contract assertion checks this walk's operations)
- **Parallelisable with:** WP-008 (gate vs walk, different file scope)

## Estimated Token Cost

- **Input:** ~9k (this WP + step 8.5 + the host-rendered bar reference)
- **Output:** ~6k (step 8.5 extension + three scripts + tests)
- **Total:** ~15k

## Notes

- ADR-003: a second pass with the generalised binding bar — not a new walk
  mechanism. Reuse step 8.5's procedure.
- The contract operations this walk reads come from §7.6; WP-013 enforces
  walk ⊆ contract. This WP is the *producer-consumer consumer* side of the
  contract-first seam (CF-05); WP-006's skeleton is the producer the walk reads.
