# fix: SRD FR/NFR header regex no longer drops inline-body headings

Closes #170.

## Problem

`sulis-verify-requirements` parsed only 1 of 15 FR/NFR blocks in a well-formed
SRD with `FR-01..11` + `NFR-01..04`. The same regex powers
`_requirement_emission` (which the verifier calls out to), so any inline-body
heading was BOTH missing from the brain AND from the verify gate's coverage
list — a silent gap on top of an unreliable verdict.

## Root cause

Both `_verify_requirements._FR_HEADER_RE` and `_requirement_emission._FR_HEADER_RE`
were:

```python
r"^\*\*((?:FR|NFR)-\d+(?:\.\d+)?):\s*(.+?)\*\*\s*$"
```

The trailing `\s*$` anchors the match to end-of-line, so the canonical
`**FR-NN: Title.** body text on the same line.` shape (heading + inline body)
never matched — only headings sitting alone on their line did. The lesson's
SRD presumably mixed shapes, with FR-05 being the lone standalone heading
that surfaced.

## Fix

Drop the `\s*$` anchor in BOTH regexes — the closing `**` is the heading
terminator; whatever follows on the same line is body text. The non-greedy
`(.+?)\*\*` still stops at the first closing `**`, so embedded bold inside
a title is handled the same way it was before.

## Tests

- `test_inline_body_canonical_format` — multi-FR SRD with all headings in
  the canonical inline-body shape; asserts all four IDs enumerate.
- `test_mixed_inline_and_standalone_headings` — real-world mix; asserts the
  inline-body block is NOT silently dropped (RED before fix surfaced
  `['FR-01', 'FR-03']` instead of `['FR-01', 'FR-02', 'FR-03']`).
- Existing 11 enumeration + verdict-shape tests still pass; emitter +
  verifier regression green (29 tests).
