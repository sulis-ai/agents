---
id: WP-010
title: Surface the tool scenarios and UC-flow coverage in the scenarios report
status: pending
sequence_id: WP-010
dependsOn: [WP-008]
blocks: []
estimated_token_cost:
  input: 5k
  output: 3k
tdd_section: 7.4 (scenarios/SKILL.md)
adrs: [ADR-004]
primitive: extend
group: expand
kind: docs
verification:
  adapter: methodology
  artifact: tests/methodology/test_scenarios_report_shows_surface_and_flow.py::test_report_shows_tool_scenarios_and_uc_flow_coverage
---

## Context

`scenarios/SKILL.md` produces a read-only report of the change's scenarios. It
lacks the UC-flow + surface view (DESIGN.md §6.5 hop A6). This WP extends the
report to surface the tool-surface scenarios, the surface tag (WP-007), and the
UC-flow-coverage verdict (WP-008) in plain English (C-06, FE-01..10) — the
founder-facing rollup of the three gates (BDR-002). Read-only: no behaviour
change to the gates themselves.

Advances DESIGN.md §6.5 hop A6 (GAP → WP, Phase 2) and the §7.4
`scenarios/SKILL.md` "Modify" row.

## Contract

```text
# plugins/sulis/skills/scenarios/SKILL.md (this WP extends)
#   The report adds, per scenario, its surface (ui|tool) and, for the change,
#   the UC-flow-coverage verdict (covered|gaps) alongside the existing #103/#86
#   verdicts — one founder-facing rollup, plain English, no scenario ids
#   (FE: surface plain titles, e.g. "3 flows nothing covers yet: <titles>").
```

Invariants:
- Read-only — surfaces existing brain + gate state; changes no verdict logic.
- Founder English (C-06): no internal IDs, no scenario ids in founder-facing
  prose; uncovered flows shown as plain titles.
- The three gate verdicts (#103, #86, UC-flow) roll up into one result
  (BDR-002) without collapsing their distinct logic.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/methodology/test_scenarios_report_shows_surface_and_flow.py::test_report_shows_tool_scenarios_and_uc_flow_coverage` — a change with tool scenarios + one uncovered flow ⇒ the report shows the surface tag and a plain-English `gaps` rollup.
- [ ] `tests/methodology/test_scenarios_report_shows_surface_and_flow.py::test_report_uses_plain_titles_not_ids` — no `SC-NN` ids in the founder-facing rollup text.

### Green — Implementation makes tests pass
- [ ] `scenarios/SKILL.md` surfaces surface tag + UC-flow verdict in the rollup.
- [ ] The rollup is plain-English, three verdicts unified.

### Blue — Refactor complete
- [ ] Verdict-rendering shares the founder-English translation helper used elsewhere (no per-gate jargon).
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** WP-008 (the UC-flow verdict it surfaces)
- **blocks:** none (terminal P2 reporting WP)
- **Parallelisable with:** WP-009 (different file scope)

## Estimated Token Cost

- **Input:** ~5k
- **Output:** ~3k
- **Total:** ~8k

## Notes

- BDR-002: three distinct gates, one founder-facing rollup. This WP is the
  rollup surface; it must not merge the gates' logic.
