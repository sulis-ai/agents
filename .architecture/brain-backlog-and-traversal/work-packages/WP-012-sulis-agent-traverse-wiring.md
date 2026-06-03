---
id: WP-012
title: Wire traverse + opportunity-analyst routing into the Sulis agent body
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-012
dependsOn: [WP-008, WP-011]
blocks: [WP-013]
estimated_token_cost:
  input: 9k
  output: 4k
tdd_section: Form — Sulis-agent traverse routing (REORGANISE, characterised); FR-08; ADR-004, ADR-006
adrs: [ADR-004, ADR-006]
primitive: refactor
group: reorganise
characterisation_test: plugins/sulis/scripts/tests/unit/test_route_inventory.py::test_existing_dispatch_routes_preserved
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_sulis_agent_traverse_wiring.py::test_agent_answers_whats_open_off_brain
---

## Context

The **only edit to internal code** in this change (TDD Form: "REORGANISE on
an internal subject and therefore carries a characterisation test"). Edits
`plugins/sulis/agents/sulis.md` to add two routing capabilities:

1. **Conversational traverse (FR-08):** the agent answers "what's open /
   deferred / on the roadmap / the state of the requirements" inline by
   calling the `sulis-brain-query` seam (WP-008) — the founder need not
   remember `/sulis:backlog`.
2. **Analyst recommendation (ADR-004):** a founder saying "I want to think
   through the why properly" → recommend the opportunity-analyst, the same
   `dispatch_via` shape as the existing `requirements-analyst` row.

Because `sulis.md` is existing internal code, this is REORGANISE-Refactor,
not Create — it carries a characterisation test that pins the *existing*
routing behaviour (the `dispatch_via` rows, `artifact_owners` map) so the
edit demonstrably preserves it before adding the new rows (EP-07 / MEA Proof).

Reuse mandate: the new analyst row reuses the existing `dispatch_via`
recommendation pattern verbatim; the traverse capability calls the existing
`sulis-brain-query` CLI — no new mechanism.

## Contract

Edits to `plugins/sulis/agents/sulis.md`:
- Add `opportunity-analyst: ["recommend \`claude --agent opportunity-analyst\`"]` to the `dispatch_via` block (mirrors the `requirements-analyst` row).
- Add a routing row / capability: founder intent matching "what's open / what's deferred / what's on the roadmap / state of the requirements" → call `sulis-brain-query --open|--roadmap|--done` and render the result in founder English (FR-08, NFR-02).
- Add `opportunity-analyst` to the agent's known-specialist list where the existing specialists are enumerated.
- The brain-traverse answer is rendered without entity/ref vocabulary (NFR-02), distinct from `/sulis:dashboard`/`/sulis:inbox` (change-store).

Invariants the characterisation test pins (MUST hold after the edit):
- Every existing `dispatch_via` row (context-cartographer, requirements-analyst, engineering-architect, executor, security-reviewer) is unchanged.
- Every existing `artifact_owners` mapping is unchanged.
- The existing trigger phrases for existing specialists still resolve.

## Definition of Done

### Red — Failing tests written
- [ ] **Characterisation (write first, must PASS before edit):** `tests/unit/test_route_inventory.py::test_existing_dispatch_routes_preserved` — snapshot the current `dispatch_via` + `artifact_owners` from `sulis.md`; assert all existing rows present. (If an equivalent assertion already exists in the route test suite, extend it rather than duplicate.)
- [ ] `tests/unit/test_sulis_agent_traverse_wiring.py::test_agent_answers_whats_open_off_brain` — the body contains a routing capability that maps "what's open"-class intent to `sulis-brain-query` (the brain seam), explicitly not the change-store.
- [ ] `tests/unit/test_sulis_agent_traverse_wiring.py::test_agent_recommends_opportunity_analyst` — the `dispatch_via` block contains the `opportunity-analyst` recommendation row (ADR-004).
- [ ] `tests/unit/test_sulis_agent_traverse_wiring.py::test_existing_routes_still_present_after_edit` — re-assert the characterisation snapshot post-edit (the routes survived).
- [ ] Behavioural coverage: the **traverse scenario journey** (WP-013) asserts the agent answers "what's open" off the brain graph (FR-08, SRD acceptance scenario 3, agent variant).

### Green — Implementation makes tests pass
- [ ] Characterisation test passes BEFORE the edit (proves the baseline), then the edit is made, then it still passes (EP-07 discipline).
- [ ] All Red tests pass.
- [ ] The new analyst row is byte-for-pattern identical in shape to the requirements-analyst row (reuse the convention).
- [ ] No existing routing behaviour changed (only additions).

### Blue — Refactor complete
- [ ] If the traverse-rendering guidance duplicates the backlog skill's prose, the agent references the shared founder-English rendering rather than restating it.
- [ ] No new behaviour beyond the two additions.
- [ ] All route tests + the new wiring tests green.

## Sequence
- **dependsOn:** WP-008 (the CLI modes the agent calls), WP-011 (the agent it recommends must exist)
- **blocks:** WP-013 (the traverse scenario journey's agent variant)
- **Parallelisable with:** WP-009, WP-010

## Estimated Token Cost
- **Input:** ~9k (this WP + `sulis.md` routing section + the route test suite)
- **Output:** ~4k (the edit + characterisation/wiring tests)
- **Total:** ~13k

## Notes
- This is the only WP that touches pre-existing internal code. The characterisation test is mandatory (EP-07, MEA Proof, WORK_PACKAGE_STANDARD REORGANISE rule) — it is what licenses the edit.
- The edit is additive: new rows, no rewrites of existing routing. If the edit would require restructuring existing rows, stop and re-scope.
