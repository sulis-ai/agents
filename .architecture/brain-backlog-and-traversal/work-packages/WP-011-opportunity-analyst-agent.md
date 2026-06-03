---
id: WP-011
title: Create opportunity-analyst agent (JTBD facilitation, hypothesis→validated→defined)
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-011
dependsOn: [WP-001]
blocks: [WP-013]
estimated_token_cost:
  input: 12k
  output: 6k
tdd_section: Form — opportunity-analyst agent; FR-11; ADR-004, ADR-005
adrs: [ADR-004, ADR-005]
primitive: create
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/methodology/test_opportunity_analyst_agent_shape.py::test_agent_frontmatter_and_jtbd_facilitation
---

## Context

The full facilitation agent (FR-11) that pressure-tests and matures the
*why* — mirroring `requirements-analyst`, framed around the brain's
job-to-be-done shape (*"when… I want… so I can…"*). A new agent body at
`plugins/sulis/agents/opportunity-analyst.md`. It takes a raw or
quick-captured opportunity and matures it through the brain's opportunity
states (**hypothesis → validated → defined**): clarifies the problem, who
has it, the job, the evidence, and the boundary against adjacent whys. It
**emits/updates the Opportunity entity** via the single-idea emission path
(WP-001's `compose_opportunity_from_idea` + the `sulis-emit-opportunity`
write seam, generalised for single-opportunity intake per ADR-005), and
composes with capture **through the store** (ADR-004 — hands back a
`dna:opportunity:<ulid>`, no shared code path). It stands alone too: maturing
an existing opportunity later is the same operation. EXPAND-Create (new
agent body). The agent is the quality bar that makes opportunity-first real,
not a prompt that accepts any answer.

`kind: backend`: the agent's behaviour is verified by the pressure-test
scenario journey (TDD §5 / SRD acceptance scenario 2); its *shape*
(frontmatter, JTBD facilitation discipline, emits-by-id) is checked by a
methodology test.

## Contract

The agent file `plugins/sulis/agents/opportunity-analyst.md` MUST carry:
- **Frontmatter:** `name: opportunity-analyst`, `description:` (founder-English), `model: inherit`, `memory: project`, and any `skills:` it needs (mirroring requirements-analyst's frontmatter shape).
- **System prompt** establishing: one-question-at-a-time JTBD facilitation; the opportunity state arc (hypothesis → validated → defined); the five things it clarifies (problem, who, job, evidence, boundary); the founder-English register.
- **Emission contract:** the agent emits/updates an Opportunity via the single-idea path (ADR-005), populating `job_statement`, and (on maturation) `evidence`/`impact`, advancing `state`; it returns the `dna:opportunity:<ulid>` id (the hand-off medium per ADR-004).
- **Composition:** the body documents both modes — (a) invoked out-of-band by capture's `full` path (returns the id capture reads back); (b) stand-alone (mature an existing opportunity by id later).
- It writes only Opportunity entities (its lane); it does not emit Requirements (that is capture's job) — keeping the no-orphan invariant owned by the orchestrator.

Behavioural contract (asserted by the pressure-test scenario journey, WP-013):
- A raw why fed to the agent matures into an Opportunity that moves hypothesis → validated/defined with a populated `job_statement`.
- The emitted opportunity id resolves and its `for_product` chain is whole (so capture can source a Requirement from it).

## Definition of Done

### Red — Failing tests written
- [ ] `tests/methodology/test_opportunity_analyst_agent_shape.py::test_agent_frontmatter_and_jtbd_facilitation` — agent file exists; frontmatter has `name`/`description`/`model`/`memory`; body establishes one-question-at-a-time JTBD facilitation and the hypothesis→validated→defined arc.
- [ ] `tests/methodology/test_opportunity_analyst_agent_shape.py::test_agent_emits_opportunity_by_id_handoff` — body documents emitting/updating the Opportunity and returning its id (ADR-004 store hand-off), and that it does NOT call capture directly.
- [ ] `tests/methodology/test_opportunity_analyst_agent_shape.py::test_agent_stands_alone_and_composes` — body documents both the capture-composed mode and the stand-alone mode (FR-11).
- [ ] `tests/methodology/test_opportunity_analyst_agent_shape.py::test_agent_stays_in_lane` — body states it emits only Opportunities, not Requirements.
- [ ] Behavioural coverage is the **pressure-test scenario journey** authored in WP-013 (run-from-graph) — SRD acceptance scenario 2.

### Green — Implementation makes tests pass
- [ ] All Red tests pass.
- [ ] The agent reuses the single-idea emission path (WP-001) and the existing `sulis-emit-opportunity` write seam generalised for single-opportunity intake (ADR-005) — it does not reimplement Opportunity persistence.
- [ ] The body cites coaching/founder-English standards by path (agent-authoring discipline), does not restate them.
- [ ] Manual smoke: run the agent against a raw why; confirm a matured Opportunity lands and its id resolves.

### Blue — Refactor complete
- [ ] Facilitation prose that mirrors requirements-analyst is referenced/adapted, not copy-pasted wholesale where a shared standard already says it.
- [ ] No new behaviour in Blue.
- [ ] Methodology + scenario tests green.

## Sequence
- **dependsOn:** WP-001 (`compose_opportunity_from_idea` — the single-idea emission path the agent's emission rides; per ADR-005 the agent and capture share this path)
- **blocks:** WP-013 (the pressure-test scenario journey + the dogfood's full-rooting matures this change's own opportunity via this agent)
- **Parallelisable with:** WP-009, WP-010, WP-012

## Estimated Token Cost
- **Input:** ~12k (this WP + requirements-analyst body for shape + WP-001 contract)
- **Output:** ~6k (agent body + methodology test)
- **Total:** ~18k

## Notes
- ADR-004 is explicit: the analyst and capture share **no code path** — they share the entity. Keep the hand-off as a returned id, never a function call.
- Consider authoring via `/sulis:add-agent` so the agent-authoring quality gates (body-density conformance, citation headers) run.

## Acceptance Evidence

- Branch: feat/wp-011-opportunity-analyst-agent (deleted post-merge)
- Completed: `2026-06-03T08:40:48Z` (Step 12 by calling session)
