---
id: WP-005
title: Author Ask-phase prose — confirm/override + ambiguous fields + per-field diff (--update)
status: pending
kind: docs
primitive: create
group: GENERATE
change_id: CH-01KT1W
sequence_id: WP-005
dependsOn: []
blocks: [WP-008]
estimated_token_cost:
  input: 2k
  output: 3k
tdd_section: FR-009 (re-discovery diff flow); FR-011 (confirmation gate); ADR-005
adrs: [ADR-005]
---

## Context

Authors the **Ask-phase prose fragments** that WP-008's `SKILL.md`
will include verbatim. Two Steps live in the Ask phase per TDD
§Canonical Identifiers:

- `confirm-or-override-inferences` (Step ULID `01KT1WDSST06CONFIRMOVRD`) — surfaces every inferred value from WP-004 as a confirmation prompt
- `gather-ambiguous-fields` (Step ULID `01KT1WDSST07GATHERAMBFL`) — prompts for fields the repo can't reveal

Plus the `--update` per-field diff flow per ADR-005 / FR-009.

The prompts are **founder English** (FE-01..FE-10) — no internal IDs,
no token-count surface, one field per prompt, plain-language framing.

This WP is the **founder-facing UX of discovery**. It has no code
dependencies: it's text. It can be authored at t=0 in parallel with
WP-001. WP-008 includes the resulting fragment files.

## Contract

### Files created

```
plugins/sulis/skills/discover-project/_prompts/
├── confirm-or-override.md       # the inferred-values confirmation prose
├── gather-ambiguous-fields.md   # the human-only fields prose
├── per-field-diff.md            # the --update diff flow per ADR-005
└── examples/
    ├── example-confirm-prompt.txt          # one rendered example per prompt — for diff visibility
    ├── example-ambiguous-prompt.txt
    └── example-per-field-diff.txt
```

6 files. No code; markdown + plain-text examples.

### Confirm-or-override prose (excerpt — full file authored in Green)

```markdown
<!-- canonical:step:confirm-or-override-inferences -->

For each value the Infer phase proposed, ask the founder to confirm or
override. One field per prompt. Confidence is not displayed (TDD §Armor
§Observability — confidence is internal taxonomy).

Prompt template (one per inferred field):

> I think `<field-name-in-plain-English>` should be `<inferred-value>`.
> Keep that, or override?
> [Enter] to keep · type a new value to override

Where `<field-name-in-plain-English>` is the friendly version of the
Configuration Vocabulary field — e.g.,
- `deploy_target` → "where you publish releases"
- `primary_branch` → "your main branch"
- `release_branch_model` → "how you cut releases"
```

### Gather-ambiguous-fields prose (excerpt)

```markdown
<!-- canonical:step:gather-ambiguous-fields -->

For fields the repo can't reveal (Project name, brand-scope choices,
optional descriptions), ask directly. One question per prompt.

Required prompts:

> What should we call this project?
> [your project name]

Optional prompts (skip if the answer is "no" or empty):

> Anything else worth knowing about this project? A short description
> helps when you're looking at it six months from now.
> [optional — Enter to skip]
```

### Per-field diff prose (excerpt — the `--update` flow per ADR-005)

```markdown
<!-- canonical:step:gather-ambiguous-fields -->
<!-- annotated under gather-ambiguous-fields because diff approvals are the human gate
     during re-discovery; per ADR-005, the diff is presented one field at a time -->

When `--update` is set and a Project entity already exists, present the
diff one field at a time. Show only fields whose proposed value differs
from the stored value. Hide metadata fields that change every run
(`valid_from`, derived timestamps).

Prompt template (one per changed field):

> `<field-name-in-plain-English>` has changed since last discovery.
>   Existing: <stored-value>
>   Proposed: <new-value>
> Keep existing, or apply proposed?
> [k] keep existing · [p] apply proposed
```

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_discover_project_prompts.py::test_confirm_prompt_uses_founder_english` — grep prompt file for internal IDs (regex: `[A-Z]{2,}-\d{2,}`, `dna:`, `ULID`, `FR-\d`, `WP-\d`, `ADR-\d`); count MUST be 0
- [ ] `tests/unit/test_discover_project_prompts.py::test_ambiguous_prompt_uses_founder_english`
- [ ] `tests/unit/test_discover_project_prompts.py::test_per_field_diff_uses_founder_english`
- [ ] `tests/unit/test_discover_project_prompts.py::test_confirm_prompt_one_field_per_prompt` — the example file shows N >= 3 distinct prompts each ending with the keep-or-override choice line
- [ ] `tests/unit/test_discover_project_prompts.py::test_no_confidence_displayed` — neither prompt files nor examples surface the LLM's `confidence` value (regex `confidence` matches 0)
- [ ] `tests/unit/test_discover_project_prompts.py::test_no_token_count_displayed_in_ask_prose` — `tokens` / `budget` surfaces appear in the structured-stderr log (TDD §Armor §Observability), NOT in the Ask prompts
- [ ] `tests/unit/test_discover_project_prompts.py::test_per_field_diff_excludes_metadata_fields` — per ADR-005, the diff prose mentions excluded fields (`valid_from`, etc.)
- [ ] `tests/unit/test_discover_project_prompts.py::test_canonical_step_annotations_present` — each prose file carries the `<!-- canonical:step:<name> -->` annotation matching its target Step (per ADR-001 + WP-009)
- [ ] `tests/unit/test_discover_project_prompts.py::test_examples_show_keep_or_override_binary` — the per-field-diff example shows exactly `[k]` and `[p]` (binary choice; no third option per ADR-005)

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/skills/discover-project/_prompts/confirm-or-override.md` authored
- [ ] `plugins/sulis/skills/discover-project/_prompts/gather-ambiguous-fields.md` authored
- [ ] `plugins/sulis/skills/discover-project/_prompts/per-field-diff.md` authored
- [ ] Three example files at `_prompts/examples/` show rendered prompts
- [ ] All 9 Red tests pass
- [ ] Each prose file opens with the canonical Step annotation (`<!-- canonical:step:<name> -->`)

### Blue — Refactor complete

- [ ] Plain-English field-name dictionary (Configuration Vocabulary → friendly name) is one section in `confirm-or-override.md` — not duplicated across files
- [ ] Example files render exactly what the prompt template would produce (no aspirational text)
- [ ] Each prose file ≤ 80 lines (founder-readable in one screen)
- [ ] Read-aloud test (FE-06 §5): each prompt sentence read aloud sounds like a person, not a form

## Sequence

- **dependsOn:** — (no code deps; text only)
- **blocks:** WP-008 (SKILL.md includes these fragments)
- **Parallelisable with:** WP-001, WP-002, WP-003, WP-004, WP-006, WP-007, WP-009

## Estimated Token Cost

- **Input:** ~2k (ADR-005 + FR-009/FR-011 + Configuration Vocabulary field names from release-train SRD + FE-01..FE-10 patterns from `references/founder-english.md`)
- **Output:** ~3k (3 prose files ≈ 240 LOC + 3 example renderings ≈ 60 LOC)
- **Total:** ~5k

## Notes

- This is the only `kind: docs` WP outside WP-008 (the skill itself). It can run at t=0 because it has zero code dependencies — the prose stands alone.
- The `<!-- canonical:step:<name> -->` annotation format is fixed by ADR-001 + exercised by WP-009's parser. Each prose file MUST open with the correct annotation, otherwise WP-009's drift detector will flag a missing-Step coverage at PR time.
- The per-field-diff prose is annotated against the same `gather-ambiguous-fields` Step that handles other ambiguous fields — per ADR-005's "Ask phase implements the diff presentation logic". The annotation comment explains this so future readers understand the binding.
- Confidence values from `InferredValue.confidence` are NEVER surfaced to the founder in the Ask phase. They live in the structured stderr log (TDD §Armor §Observability) for debug only.
