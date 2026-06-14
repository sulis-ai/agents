---
id: WP-002
title: "Mint path: teach the prefixed {CH-HANDLE}-WP-NNN id in the plan-work + design + agent surfaces"
status: pending
change_id: 01KTR381SP5DMB1N8RBKHCVV9Q
kind: docs
primitive: extend
group: REINFORCE
sequence_id: WP-002
dependsOn: []
blocks: []
estimated_token_cost:
  input: 6k
  output: 4k
tdd_section: "§4 Mint path"
adrs: [ADR-002]
verification:
  na: true
  justification: "Docs/agent-prompt edits with no runtime surface; the prefixed-id behaviour is verified by WP-001's parser/branch tests. Correctness here is a docs-truth read against the shipped matcher, not a separate test artifact."
---

> **ID-SCHEME NOTE:** this WP's own id is the **bare** `WP-002` (chicken-and-egg,
> ADR-002) even though the rows it authors *teach* the new prefixed shape.

## Context

The authored example/canonical id rows that teach how a WP id is rendered live
in five markdown surfaces (TDD §4). They currently show the bare `WP-NNN`. After
WP-001 ships the widened matcher, the **mint** path must produce the prefixed
`{CH-HANDLE}-WP-NNN` shape — so these surfaces are updated to teach it. This is
docs/agent-prompt truth catching up to the shipped behaviour.

**Primitive = extend; group = REINFORCE / Document.** No code; the
authored-example rows gain the handle prefix.

## Contract

### Files modified

```
plugins/sulis/skills/plan-work/references/work-package-template.md  (id: / sequence_id: template rows)
plugins/sulis/skills/design/SKILL.md                                (canonical WP-id mentions)
plugins/sulis/agents/engineering-architect.md                       (WP-id example/contract rows)
plugins/sulis/agents/orchestrator.md                                (WP-id example rows)
plugins/sulis/agents/executor.md                                    (WP-id example rows)
```

### Behavioural contract

- The plan-work template's `id:` / `sequence_id:` example rows render the
  prefixed shape `{CH-HANDLE}-WP-NNN` (e.g. `CH-5DMB1N-WP-001`), with a short
  note that the prefix is the parent change's handle and the `NNN` is the
  per-change 1/2/3 sequence (unchanged).
- The design + three agent surfaces describe/illustrate the prefixed shape
  consistently. Any place that previously said "mint `WP-NNN`" now says "mint
  `{CH-HANDLE}-WP-NNN`".
- **Back-compat note carried where the id shape is taught:** legacy bare
  `WP-NNN` ids remain valid and parseable for one release (point at ADR-002 /
  the standards rather than re-explaining).
- **No change to the founder-facing surface.** WP ids are already stripped from
  founder-facing output (FE-06); these are operator/agent-facing instructional
  surfaces only.

### What this WP is NOT

- It does **not** edit `_wpxlib.py` or any code (that is WP-001).
- It does **not** edit the two standards files (`WORK_PACKAGE_STANDARD`,
  `change-work-standard`) — that is WP-003.
- It does **not** rewrite this change's own WP ids to the prefixed shape
  (chicken-and-egg, ADR-002).

## Definition of Done

### Red — n/a (docs)

Per EP-07, prose/agent-prompt edits with no behavioural surface do not require a
characterisation test. The behaviour these rows *describe* is proven by WP-001's
parser/branch tests.

### Green — edits land

- [ ] `work-package-template.md` `id:` / `sequence_id:` rows show
      `{CH-HANDLE}-WP-NNN` with the one-line prefix-explanation.
- [ ] `design/SKILL.md`, `engineering-architect.md`, `orchestrator.md`,
      `executor.md` consistently teach the prefixed shape.
- [ ] Each surface that teaches the id shape carries the one-release
      legacy-bare-id back-compat note (by reference to ADR-002 / the standards).
- [ ] No surface instructs minting this change's *own* WPs as prefixed (the
      chicken-and-egg carve-out is respected; if any surface needs it, it notes
      that the first prefixed mint is the next change after CH-5DMB1N).

### Blue — hygiene

- [ ] Wording is consistent across all five surfaces (same example handle, same
      back-compat phrasing) — no drift between them.
- [ ] Operator vocabulary discipline respected (`design/SKILL.md` already warns
      WP-NNN must not leak founder-facing — that guidance stays accurate).

## Sequence

- **dependsOn:** none — independent markdown; describes WP-001's shape but does
  not require it to be merged first to be authored.
- **blocks:** none.
- **Parallelisable with:** WP-001, WP-003.

## Estimated Token Cost

- **Input:** ~6k (the five surfaces' WP-id regions).
- **Output:** ~4k (the prefixed-shape rows + back-compat notes across five
  files).
- **Total:** ~10k.

## Notes

- **Why separate from WP-001:** clean code/markdown separation (constraint 5).
  These surfaces are instructional; they teach the shape WP-001 implements.
  Bundling them with the code WP would mix kinds and inflate the diff.
- **Why one WP for all five surfaces:** they teach one identical shape; splitting
  per-file would fragment a single coherent docs edit with no independent value.

## Verification Plan

- **What is verified:** the five mint surfaces teach `{CH-HANDLE}-WP-NNN`
  consistently, carry the one-release back-compat note, and respect the
  chicken-and-egg carve-out. Verified by reading the edited rows against the
  shipped matcher (WP-001) — a docs-truth check, not a test artifact (`na` per
  frontmatter justification).
- **Per-kind adapter (`docs`):** no executable artifact; correctness is the
  read-against-shipped-behaviour check above.

## Acceptance Evidence

- Branch: wp/extend-unique-wp-ids/wp-002-mint-path-canonical-id-rows (deleted post-merge)
- Health status: `n/a (no-deploy profile)`
- Smoke-test verdict: n/a
- Completed: `2026-06-10T08:31:53Z` (Step 12 by calling session)
