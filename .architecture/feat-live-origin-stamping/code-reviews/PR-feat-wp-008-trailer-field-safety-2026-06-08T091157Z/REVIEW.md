# Code Review: WP-008 — Trailer field-separator safety + non-fatal autonomous stamp

> **Timestamp:** 2026-06-08T091157Z (ISO 8601 UTC)
> **Author:** executor (WP-008)
> **Branch:** feat/wp-008-trailer-field-safety → change/feat-live-origin-stamping
> **Files changed:** 2 (`_origin_stamp.py` + its test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change hardens the origin-stamping writer against two latent gaps that a
security review flagged as defence-in-depth. The build is clean, the new
behaviour is fully covered by tests written test-first, and the change is
tightly scoped to one file plus its test. There is nothing that needs
attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: 134 changed lines across two files (one source file
and its test), one type of change (hardening), no database changes, no
configuration changes, and tests added for every new behaviour. This is the
shape a reviewer wants to see.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the changes; Build Verification empty;
both changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `ruff check` clean,
  `compileall` clean (the repo's CI lint gate per `branch-ci.yml`).
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — composes existing guard, no new coupling |
| Security | 0 | 0 | none — diff *closes* two ADVISORY findings |
| Quality | 0 | 0 | none — new behaviour fully tested |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` → "All checks passed!"; `compileall` →
clean. Note: `ruff format --check` would reformat pre-existing untouched code
(`_git` / `_rewrite_commit_message` / `stamp_origin` dict literals in the
file's lower half) — those lines are not in this diff and `ruff format` is not
part of the repo's CI lint gate (`branch-ci.yml` runs `compileall`, not
`ruff format`). The added lines are already format-clean. Out of scope per
EP-07 (Boy Scout scoped to changed lines).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type {harden}; module_fan_out 1 dir   → clean
Size (PH-02):        +126 / -8; files_changed 2                    → clean
Safety (PH-03):      migrations 0; schema 0; infra 0; secrets 0    → clean
Completeness (PH-04): new_source_without_test 0; tests added       → clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The only callers of the changed symbols (`format_trailer`,
`autonomous_env`) are the two sibling test suites
(`test_executor_autonomous_origin.py`, `test_assisted_grammar_conformance.py`),
both green at HEAD.

### Lens output

- **Architecture lens: nothing surfaced.** Checks run: import-direction (no new
  imports), singletons (none added), circular paths (none), resilience
  (the new `try/except ValueError` is a graceful-degradation guard matching
  ADR-013's non-fatal invariant, not a swallowed error path that hides
  failure). `_is_trailer_safe` *reuses* `_has_control_char` (EP-03) rather than
  duplicating the control-char check.
- **Security lens: nothing surfaced.** Primitives checked: SEC-02 (injection) —
  this diff *tightens* the trailer-field boundary by refusing the grammar's own
  `;`/`=` separators, closing a segment-forging vector; SEC availability — the
  non-fatal `autonomous_env` removes a commit-abort path (a malformed run now
  degrades to unstamped, never aborts). No secrets (Gitleaks pattern scan on
  the diff: 0 hits). No new external calls, no new I/O.
- **Quality lens: nothing surfaced.** Build Verification: clean. No JSX
  (Python diff). Dead surface: none — both new symbols are consumed
  (`_is_trailer_safe` by `format_trailer`; `_TRAILER_SEPARATORS` by
  `_is_trailer_safe`). Contract drift: none — trailer grammar unchanged.
  Test coverage: 6 new tests added, each RED-proven against current code
  before the fix; file coverage 89% (every new line exercised). Style: clean.
  Performance (CR-10): the only loop is `any(sep in value for sep in
  _TRAILER_SEPARATORS)` over a 2-element tuple — bounded, benign; no
  anti-pattern matches.

### Watch List

None.

### Cross-Reference

- This WP *implements* the two ADVISORY findings from the CH-01KTHP security
  review (ADVISORY-01 field-separator safety; ADVISORY-02 non-fatal stamp).
- No existing hardening deltas duplicated.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `python3 -m compileall` (the repo CI lint gate). Base + Head: 0 errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size:** 134 lines, 2 files (within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files (`_origin_stamp.py` 364 lines, `test_origin_stamp.py` ~530 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All assessments cite the diff/symbol; no findings to evidence (zero surfaced).
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at all severities.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives/scanners listed. Quality: all seven outputs produced (build / jsx[n.a.] / dead-surface / contract-drift / test-coverage / style / CR-10).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: clean (+126/-8, 2 files). PH-03 Safety: clean (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: clean (tests added). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** working-tree diff vs `change/feat-live-origin-stamping` (pre-commit; Step 7 commits next).
- **Neighbour expansion:** `git grep` on changed symbols → 2 sibling test files only.
- **Neighbour cap:** 2 of 2 considered, 0 excluded.
- **Scanners run:** ruff, compileall, git-grep secret pattern scan.
- **Single-reader:** yes (within CR-02 carve-out).
