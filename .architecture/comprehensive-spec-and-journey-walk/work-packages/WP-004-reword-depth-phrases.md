---
id: WP-004
title: Reword the depth proposal phrases to describe interview size
status: pending
sequence_id: WP-004
dependsOn: []
blocks: []
estimated_token_cost:
  input: 4k
  output: 2k
tdd_section: 7.4 (Component Model — _specify_classifier.py)
adrs: [ADR-001]
primitive: refactor
group: reorganise
kind: backend
characterisation_test: plugins/sulis/scripts/tests/test_specify_classifier.py::test_proposal_sentence_current_wording
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_specify_classifier.py::test_depth_phrase_describes_interview_not_doc_shape
---

## Context

`_specify_classifier.py`'s `_DEPTH_PHRASE` / `_DEPTH_ALT` (around line 236)
describe the *document* as thin ("a quick lite spec (three lines)") rather than
the *interview* as short. FR-04 requires the founder-facing proposal sentence to
describe interview size only — never document completeness. This is a wording
change to a pure function's string constants; `classify_depth` semantics and
purity (C-03) are untouched. Per the REORGANISE doctrine, a characterisation
test pins the current `proposal_sentence` output before the reword.

Advances DESIGN.md §6.5 hop A2 (GAP → WP) and the §7.4 `_specify_classifier.py`
row.

## Contract

```python
# plugins/sulis/scripts/_specify_classifier.py (this WP modifies — strings only)
# _DEPTH_PHRASE / _DEPTH_ALT: reword so the rendered proposal_sentence reads
#   e.g. "I'll ask a few quick questions" (lite) — interview size, NOT
#   "three lines" / "the deep version with the flows drawn out" (doc shape).
# classify_depth(...) signature + return shape UNCHANGED. Purity preserved.
```

Invariants:
- `classify_depth` remains pure and deterministic (C-03, NFR-01: < 5 ms).
- The reworded phrase contains no reference to which document sections exist
  (FR-04).
- Founder English (C-06, FE-01..10): no internal IDs, no jargon.

## Definition of Done

### Red — Failing tests written
- [ ] `test_specify_classifier.py::test_proposal_sentence_current_wording` — characterisation test pinning the pre-change output (passes before, updated after).
- [ ] `test_specify_classifier.py::test_depth_phrase_describes_interview_not_doc_shape` — asserts the reworded phrase mentions interview/questions, NOT "lines"/"sections"/"document".

### Green — Implementation makes tests pass
- [ ] `_DEPTH_PHRASE`/`_DEPTH_ALT` reworded; the new assertion passes.
- [ ] `classify_depth` unit tests still pass unchanged (purity regression).
- [ ] Characterisation test updated to the new expected output, with the diff reviewed.

### Blue — Refactor complete
- [ ] No duplicated phrasing across `_DEPTH_PHRASE`/`_DEPTH_ALT`.
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** none
- **blocks:** none (the wording is independent of the doc-shape sever)
- **Parallelisable with:** all other WPs (string-only scope)

## Estimated Token Cost

- **Input:** ~4k
- **Output:** ~2k
- **Total:** ~6k

## Notes

- REORGANISE-Refactor: the characterisation test is mandatory (CLAUDE.md EP-07).
- This is the cheapest P1 WP; it can land first to de-risk the founder-facing
  wording independent of the larger doc-shape sever (WP-005).
