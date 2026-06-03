---
id: WP-010
title: Create /sulis:backlog skill (traverse off the brain graph)
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-010
dependsOn: [WP-008]
blocks: [WP-013]
estimated_token_cost:
  input: 7k
  output: 4k
tdd_section: Form — /sulis:backlog skill; FR-07; NFR-02
adrs: [ADR-006]
primitive: create
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/methodology/test_backlog_skill_shape.py::test_skill_reads_brain_not_change_store
---

## Context

The founder-facing **Traverse path** command (FR-07). A new skill at
`plugins/sulis/skills/backlog/SKILL.md` that answers, off the brain graph,
what's **open** (draft/hypothesis), what's on the **Roadmap**, and what's
**done/built** (implemented/verified) — by invoking the new
`sulis-brain-query` modes (WP-008). It is explicitly **not**
`/sulis:dashboard` or `/sulis:inbox` (which read the change-store); the skill
body states the distinction so future maintainers don't conflate them.
Speaks plain English (open/roadmap/done — NFR-02). EXPAND-Create.

## Contract

The skill file `plugins/sulis/skills/backlog/SKILL.md` MUST carry:
- **Frontmatter:** `name: backlog`, a founder-English `description:`.
- **Workflow body** that: (1) invokes `sulis-brain-query --open` / `--roadmap` / `--done` (and `--by-type`/`--by-state` for narrower asks); (2) renders the entity lists into plain-English groups ("Open ideas", "On your roadmap", "Done") with no entity-type/ref vocabulary (NFR-02); (3) reports an empty result as "nothing open yet" rather than an error (NFR-01); (4) states it reads the brain graph, distinct from `/sulis:dashboard`/`/sulis:inbox`.
- **No jargon (NFR-02):** never shows `dna:*` ids, states, or schema vocabulary to the founder; presents names/titles.

Behavioural contract (asserted by the traverse scenario journey, WP-013):
- Asking the backlog returns open ideas + roadmap + done, sourced from brain entities (not the change-store).
- An empty store reads as "nothing yet", not an error.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/methodology/test_backlog_skill_shape.py::test_skill_reads_brain_not_change_store` — the body invokes `sulis-brain-query` (brain seam), and explicitly notes it is distinct from dashboard/inbox; it does not read `.changes/` or the change-store.
- [ ] `tests/methodology/test_backlog_skill_shape.py::test_skill_frontmatter_and_no_jargon` — frontmatter present; body free of `dna:`, raw state names exposed to the founder, `for_product`, etc.
- [ ] `tests/methodology/test_backlog_skill_shape.py::test_skill_covers_open_roadmap_done` — the three founder-facing views are all present in the body.
- [ ] Behavioural coverage is the **traverse scenario journey** authored in WP-013 (run-from-graph).

### Green — Implementation makes tests pass
- [ ] All Red tests pass.
- [ ] The body cites founder-English/AAF standards by path; does not restate the open/done mapping (that lives in the query seam, WP-007/WP-008).
- [ ] Manual smoke: `/sulis:backlog` against this repo's store lists the dogfood Roadmap items in plain English.

### Blue — Refactor complete
- [ ] Rendering logic for the three groups shares one plain-English formatter description (no three near-identical prose blocks).
- [ ] No new behaviour in Blue.
- [ ] Methodology + scenario tests green.

## Sequence
- **dependsOn:** WP-008 (the CLI modes it invokes)
- **blocks:** WP-013 (the traverse scenario journey exercises this skill)
- **Parallelisable with:** WP-009 (capture skill), WP-011 (analyst agent), WP-012 (agent wiring)

## Estimated Token Cost
- **Input:** ~7k (this WP + WP-008 contract + an existing skill for shape)
- **Output:** ~4k (SKILL.md + methodology test)
- **Total:** ~11k

## Notes
- FR-07's "the state of the work" is answered from brain entities; the change-store views (`/sulis:dashboard`, `/sulis:inbox`) answer a *different* question. The body must keep the two clearly apart.
