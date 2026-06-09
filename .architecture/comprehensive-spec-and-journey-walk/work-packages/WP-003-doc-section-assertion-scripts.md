---
id: WP-003
title: Build the document-section assertion scripts
status: pending
sequence_id: WP-003
dependsOn: []
blocks: [WP-005, WP-006]
estimated_token_cost:
  input: 5k
  output: 5k
tdd_section: 7.4 (Component Model — fixture harness scripts)
adrs: [ADR-001, ADR-002]
primitive: create
group: expand
kind: backend
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_doc_section_asserts.py::test_assert_doc_sections_detects_missing_section
---

## Context

The P1 always-comprehensive scenarios (SC-01..SC-05) assert on the produced
document's structure with five small, single-purpose assertion scripts. They
are grouped into one WP because each is a few lines, shares the same
document-parsing primitive, and they verify the same capability surface
(document completeness) — splitting them into five WPs would violate the
resist-over-decomposition rule. They are pure document inspectors with no
production-code dependency, so they are foundational.

## Contract

```python
# plugins/sulis/scripts/_assert_doc_sections.py   — --require <comma-list> ⇒ exit 0 iff all present
# plugins/sulis/scripts/_assert_same_section_set.py — <doc...> ⇒ exit 0 iff identical header set
# plugins/sulis/scripts/_assert_section_na.py       — --section <name> ⇒ exit 0 iff present AND "n/a — <reason>"
# plugins/sulis/scripts/_assert_measurable_nfr.py   — --categories <list> ⇒ exit 0 iff each has a numeric/threshold target
# plugins/sulis/scripts/_assert_no_depth_doc_gate.py — <skill/agent files> ⇒ exit 0 iff no emission branch on classify_depth
```

Invariants:
- Each script exits non-zero with a human-readable reason on failure
  (the reason is what the founder-facing gate rollup surfaces in plain English).
- `_assert_section_na.py` distinguishes a present-but-n/a section from a
  silently-dropped one (NFR-R01) — a missing heading fails, an `n/a — <reason>`
  passes, a bare `n/a` with no reason fails.
- `_assert_no_depth_doc_gate.py` is a static inspector: it greps the skill/agent
  text for a branch that conditions section existence on depth (SC-04, FR-03).

## Definition of Done

### Red — Failing tests written
- [ ] `test_doc_section_asserts.py::test_assert_doc_sections_detects_missing_section` — a doc missing `nfr` ⇒ non-zero.
- [ ] `test_doc_section_asserts.py::test_same_section_set_detects_drift` — two docs with different header sets ⇒ non-zero.
- [ ] `test_doc_section_asserts.py::test_section_na_requires_justification` — bare `n/a` ⇒ non-zero; `n/a — <reason>` ⇒ zero.
- [ ] `test_doc_section_asserts.py::test_measurable_nfr_rejects_adjective_only` — "fast" ⇒ non-zero; "< 5 ms" ⇒ zero.
- [ ] `test_doc_section_asserts.py::test_no_depth_doc_gate_flags_branch` — a fixture skill with `if depth == lite: skip nfr` ⇒ non-zero.

### Green — Implementation makes tests pass
- [ ] All five scripts exist and pass their tests.
- [ ] Shared markdown-section-parsing helper extracted (used by all five).
- [ ] Follows `references/boring-code.md`.

### Blue — Refactor complete
- [ ] The section-parsing helper is the single source of header detection (no per-script regex duplication).
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** none (pure inspectors)
- **blocks:** WP-005 (`_assert_no_depth_doc_gate` proves the branch was severed), WP-006 (the doc-emitter WP's Red uses `_assert_doc_sections`/`_assert_same_section_set`/`_assert_section_na`/`_assert_measurable_nfr`)
- **Parallelisable with:** WP-001, WP-002, WP-004

## Estimated Token Cost

- **Input:** ~5k
- **Output:** ~5k (five small scripts + shared helper + test file)
- **Total:** ~10k

## Notes

- These are the SC-01..SC-05 assertion halves. Building them before the P1
  production WPs means those WPs land test-first.

## Acceptance Evidence

- Branch: feat/wp-003-doc-section-assertion-scripts (deleted post-merge)
- Squash-merge SHA on dev: `58ce728185be51d2c25fd8b08d080b56ce7b9a66`
- Completed: `2026-06-09T20:51:36Z` (Step 12 by calling session)
