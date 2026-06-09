---
id: WP-005
title: Sever the depth-to-document-shape branch in specify and the analyst path
status: pending
sequence_id: WP-005
dependsOn: [WP-003]
blocks: [WP-006]
estimated_token_cost:
  input: 7k
  output: 4k
tdd_section: 7.3 (Data Flow) + 7.4 (specify/SKILL.md, requirements-analyst.md)
adrs: [ADR-001]
primitive: refactor
group: reorganise
kind: docs
characterisation_test: plugins/sulis/scripts/tests/test_drive_specify.py::test_drive_specify_emits_document_at_lite
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_doc_section_asserts.py::test_no_depth_doc_gate_flags_branch
---

## Context

`specify/SKILL.md` (lines 54–56) and the requirements-analyst path branch the
*document shape* on depth: lite → 10-line SPEC; standard → 5-section SPEC; deep
→ full doc. ADR-001 removes that branch — depth feeds the interview sizer only,
never which sections exist (FR-01/02/03/05). This is a REORGANISE change to skill
+ agent prose; the characterisation test is `_drive_specify`'s "emits a document
at lite" (WP-003 builds the static `_assert_no_depth_doc_gate` inspector that
proves the branch is gone).

Advances DESIGN.md §6.5 hop A4 (GAP → WP) and the §7.3 data-flow contrast
(the branch this WP removes).

## Contract

```text
# plugins/sulis/skills/specify/SKILL.md (this WP modifies)
#   Remove the depth→doc-shape branch at lines 54–56. Depth sizes the interview
#   (Step 4 modes stay); the emission step ALWAYS routes to the comprehensive
#   emitter (WP-006), regardless of depth.
# plugins/sulis/agents/requirements-analyst.md (this WP modifies)
#   The full comprehensive structure becomes the DEFAULT emit, not the deep-only
#   emit. No depth gate on section existence.
```

Invariants:
- After this WP, `_assert_no_depth_doc_gate.py` passes against
  `specify/SKILL.md`, `draft-architecture/SKILL.md`, and
  `requirements-analyst.md` — zero emission branches condition section existence
  on depth (SC-04, FR-03).
- The interview itself (depth-sized) is unchanged — only its coupling to doc
  shape is severed.
- Founder English preserved in all founder-facing prose (C-06).

## Definition of Done

### Red — Failing tests written
- [ ] `test_doc_section_asserts.py::test_no_depth_doc_gate_flags_branch` — passes against a fixture with the branch; this WP makes it pass against the real files.
- [ ] `test_drive_specify.py::test_drive_specify_emits_document_at_lite` — at lite depth, a full document is produced (characterisation; SC-01 precondition).
- [ ] `_assert_no_depth_doc_gate.py plugins/sulis/skills/specify/SKILL.md plugins/sulis/skills/draft-architecture/SKILL.md plugins/sulis/agents/requirements-analyst.md` exits 0 (SC-04 exact command).

### Green — Implementation makes tests pass
- [ ] The lines 54–56 branch removed from `specify/SKILL.md`; emission routes always to the comprehensive emitter.
- [ ] `requirements-analyst.md` emits the full structure by default.
- [ ] `_assert_no_depth_doc_gate` exits 0 against all three files.

### Blue — Refactor complete
- [ ] No residual depth-conditioned wording about "thin"/"full" documents.
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** WP-003 (`_assert_no_depth_doc_gate` is the proving inspector)
- **blocks:** WP-006 (the emitter the severed path routes to)
- **Parallelisable with:** WP-004 (different file scope)

## Estimated Token Cost

- **Input:** ~7k (this WP + the two skill files + the analyst agent)
- **Output:** ~4k (edits across three prose files)
- **Total:** ~11k

## Notes

- ADR-001: decouple by *removing* a branch, not adding one. Resist the urge to
  add an `if always_comprehensive:` flag — there is no flag; the comprehensive
  emitter is the only path.
- `kind: docs` — the change is to skill + agent prose; the assertion lives in
  WP-003's script.
