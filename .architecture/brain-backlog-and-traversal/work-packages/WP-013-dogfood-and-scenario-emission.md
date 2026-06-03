---
id: WP-013
title: Dogfood — capture this change's own ideas through the capture path + emit and run the two scenarios from-graph
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-013
dependsOn: [WP-006, WP-008, WP-009, WP-010, WP-011, WP-012]
blocks: []
estimated_token_cost:
  input: 14k
  output: 5k
tdd_section: Proof — Scenario coverage (run-from-graph); bootstrapping-circularity note; FR-10
adrs: [ADR-004, ADR-005, ADR-001]
primitive: create
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_scenarios_from_graph.py::test_capture_and_traverse_journeys_run_green
---

## Context

The **last** WP, deliberately. Per the TDD's bootstrapping-circularity note,
the two verification scenarios verify the capture/emit path — which does not
exist until WP-001..WP-012 are built. So the Requirement + scenario emission
is deferred to this dogfood step and emitted **through the new capture path
itself** (FR-10), never via the old `--from-srd` path. This proves the path
end-to-end and ensures this change's own ideas are not lost. EXPAND-Create
(authors scenario journeys + drives the dogfood).

Three acts:
1. **Mature the change's own opportunity (ADR-004 dogfood).** Run the
   opportunity-analyst (WP-011) against the why behind "brain as a living
   backlog" — the analyst is *exercised*, not merely shipped (FR-10).
2. **Capture the two pieces as Requirements (ADR-005).** Capture the
   capture-path idea and the backlog-command idea **through `sulis-capture`**
   (WP-006 / the `/sulis:capture` skill, WP-009), rooted in that matured
   opportunity, Roadmap-labelled (ADR-001). No `--from-srd`.
3. **Author + emit + run the two scenarios from-graph.** Author the capture
   journey and the traverse journey in plain English via
   `sulis-author-scenario`, emit them, and run them via
   `sulis-verify-acceptance --scenario` — both green.

## Contract

Artifacts this WP produces:
- A matured Opportunity (this change's why) in the store, advanced past `hypothesis` by the analyst.
- Two draft Requirements (capture-path, backlog-command) sourced from that Opportunity, Roadmap-labelled in `.brain/labels/roadmap.jsonld`.
- Two authored scenario bundles (capture journey, traverse journey) under the change's scenario location, emitted into the brain.
- An integration test that runs both scenarios from-graph and asserts green.

Behavioural contract (the run-from-graph scenarios, TDD Proof §):
1. **Capture journey** — deposit an idea (why + what); assert an Opportunity + a draft Requirement sourced from it land, chain whole.
2. **Traverse journey** — ask "what's open"; assert open ideas + roadmap + done come back **off the brain graph** (not the change-store).

Hard constraints (TDD sequencing note):
- **Every requirement for this change is emitted through the new capture path.** The `--from-srd` path is forbidden for this change.
- The matured opportunity's id is the real `source` of both dogfood Requirements (no synthetic ref — ADR-005).

## Definition of Done

### Red — Failing tests written
- [ ] `tests/integration/test_scenarios_from_graph.py::test_capture_and_traverse_journeys_run_green` — author + emit both journeys into a temp store, run `sulis-verify-acceptance --scenario` for each; assert both green.
- [ ] `tests/integration/test_scenarios_from_graph.py::test_capture_journey_lands_whole_chain` — the capture journey's from-graph run produces an Opportunity + draft Requirement with a whole `source`→`for_product`→`belongs_to_tenant` chain.
- [ ] `tests/integration/test_scenarios_from_graph.py::test_traverse_journey_reads_brain_not_change_store` — the traverse journey answers "what's open" from brain entities; asserting the answer is not sourced from `.changes/`.
- [ ] `tests/integration/test_scenarios_from_graph.py::test_dogfood_requirements_source_resolves` — the two dogfood Requirements' `source` resolves to the matured Opportunity id (no dangling, no synthetic).
- [ ] `tests/integration/test_scenarios_from_graph.py::test_dogfood_ideas_are_roadmap_labelled` — both dogfood ideas appear in the roadmap sidecar (SRD acceptance).

### Green — Implementation makes tests pass
- [ ] All Red tests pass; both scenarios run green from-graph.
- [ ] The dogfood ideas are captured via `sulis-capture` / `/sulis:capture` (WP-006/WP-009) — grep the WP's commands to confirm no `--from-srd` invocation for this change.
- [ ] The opportunity-analyst (WP-011) is run against this change's why (exercised, FR-10).
- [ ] Scenarios authored via `sulis-author-scenario` (reuse the shipped loop, PR #154) — no new scenario machinery.

### Blue — Refactor complete
- [ ] Shared scenario-fixture setup (temp store + bootstrap) extracted into the integration conftest if it duplicates WP-006/WP-008 fixtures.
- [ ] No new behaviour in Blue.
- [ ] Full suite green; both from-graph scenarios green.

## Sequence
- **dependsOn:** WP-006 (capture CLI), WP-008 (query CLI modes), WP-009 (capture skill), WP-010 (backlog skill), WP-011 (analyst), WP-012 (agent wiring) — the entire machinery must exist first (bootstrapping circularity).
- **blocks:** — (terminal WP; this is the verify/ship dogfood)
- **Parallelisable with:** — (gated on everything; runs last)

## Estimated Token Cost
- **Input:** ~14k (this WP + the scenario-authoring docs + the six dependency contracts)
- **Output:** ~5k (two authored journeys + the dogfood run + integration test)
- **Total:** ~19k

## Notes
- This is the WP that resolves the TDD's bootstrapping-circularity: the scenarios can only be authored-emitted-run once the path they verify exists. Build everything else first; do this last.
- "No requirement is emitted via the old `--from-srd` path for this change" is a MUST and is asserted in Green by inspection of the WP's own commands.
