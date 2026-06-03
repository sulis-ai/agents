---
id: WP-009
title: Create /sulis:capture skill (founder-English capture front door)
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-009
dependsOn: [WP-006]
blocks: [WP-013]
estimated_token_cost:
  input: 8k
  output: 4k
tdd_section: Form — /sulis:capture skill; FR-01, FR-02, FR-05; NFR-02
adrs: [ADR-003, ADR-004]
primitive: create
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/methodology/test_capture_skill_shape.py::test_skill_frontmatter_and_no_jargon
---

## Context

The founder-facing front door for capture (FR-01). A new skill at
`plugins/sulis/skills/capture/SKILL.md` that walks the why-then-what in one
sitting (FR-02), speaks only plain English (no entity/IDEF0/ref vocabulary —
NFR-02), and invokes the `sulis-capture` CLI (WP-006) under the hood. Per
ADR-003 it carries the quick/full branch: quick is the in-conversation
default; for `full`, the skill **recommends running the opportunity-analyst
agent** first (ADR-004 store hand-off — same recommendation pattern the Sulis
agent uses for requirements-analyst), then resumes with the returned
opportunity id. EXPAND-Create (new skill body). `kind: backend` because the
skill's behaviour is verified via the capture scenario journey (TDD §5) +
the CLI it drives; its *shape* (frontmatter, no-jargon) is checked by a
methodology test.

Per the skill-authoring standard, the body is a thin workflow that cites
standards rather than restating them, and runs the audience triage before
any question reaches the founder.

## Contract

The skill file `plugins/sulis/skills/capture/SKILL.md` MUST carry:
- **Frontmatter:** `name: capture`, a founder-English `description:` (no internal IDs).
- **Workflow body** that: (1) elicits the why in plain English and refuses to proceed without one (FR-02 — the orchestrator is the hard gate, the skill is the friendly prompt); (2) elicits the what in the same sitting; (3) offers the Roadmap flag in plain language ("set this aside for later?"); (4) for the `full` intensity, recommends `claude --agent opportunity-analyst` and resumes on the returned idea-id; (5) invokes `sulis-capture` with the gathered fields; (6) renders the `{"ok":…}` envelope into a plain-English confirmation or a plain-English error (NFR-01 — a brain-unavailable `ok:false` reads as "couldn't save that right now", never a stack trace).
- **No jargon (NFR-02):** the body never instructs the founder to type entity types, ref ids, ULIDs, `--seed`, or `dna:*` strings. Internal IDs do not appear in founder-facing prose.
- **Founder-English + AAF triage:** any question runs the three-step pre-question triage; convention-shaped choices are taken silently.

Behavioural contract (what the scenario journey asserts):
- A captured idea with a why + what lands an Opportunity + a draft Requirement sourced from it (drives the capture journey, WP-013).
- An attempt with no why is refused in plain English; nothing is emitted.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/methodology/test_capture_skill_shape.py::test_skill_frontmatter_and_no_jargon` — `SKILL.md` exists, has `name`/`description` frontmatter, and the body contains no banned jargon tokens (`dna:`, `--seed`, `ULID`, `IDEF0`, `unevaluatedProperties`, `for_product`, `belongs_to_tenant`, `tool_ref`).
- [ ] `tests/methodology/test_capture_skill_shape.py::test_skill_invokes_capture_cli` — the body references `sulis-capture` as the invocation seam (not a re-implementation of capture logic in prose).
- [ ] `tests/methodology/test_capture_skill_shape.py::test_skill_recommends_analyst_for_full` — the body contains the `claude --agent opportunity-analyst` recommendation for the full path (ADR-004).
- [ ] Behavioural coverage is the **capture scenario journey** authored in WP-013 (run-from-graph) — listed here as the founder-facing verification artifact per TDD §5.

### Green — Implementation makes tests pass
- [ ] All Red tests pass.
- [ ] The skill body cites the relevant standards (founder-English, AAF) by path rather than restating them (skill-authoring discipline).
- [ ] Manual smoke: running `/sulis:capture` against this repo's store deposits a test idea and reports it in plain English.

### Blue — Refactor complete
- [ ] Any prose duplicated between the quick and full walkthroughs is consolidated into one shared explanation with a branch note.
- [ ] No new behaviour in Blue.
- [ ] Methodology + scenario tests green.

## Sequence
- **dependsOn:** WP-006 (the CLI the skill invokes)
- **blocks:** WP-013 (the capture scenario journey exercises this skill; the dogfood captures *through* it)
- **Parallelisable with:** WP-010 (the backlog skill), WP-011 (the analyst agent)

## Estimated Token Cost
- **Input:** ~8k (this WP + WP-006 contract + an existing skill for shape)
- **Output:** ~4k (SKILL.md + methodology test)
- **Total:** ~12k

## Notes
- The hard why-first gate lives in the orchestrator (WP-004), not in skill prose (ADR-003 rejected "branch in the skill prose"). The skill's job is the friendly plain-English door; if the founder gives no why, the CLI returns `ok:false` and the skill renders it kindly.
- Consider authoring via `/sulis:add-skill` so the skill-authoring quality gates run.
