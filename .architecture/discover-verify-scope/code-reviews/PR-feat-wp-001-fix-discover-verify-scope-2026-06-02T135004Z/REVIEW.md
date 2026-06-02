# Code Review: feat/wp-001-fix-discover-verify-scope — Fix the discover-project verify gate that rolls back every mint in consumer repos

> **Timestamp:** 2026-06-02T135004Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-fix-discover-verify-scope → change/fix-discover-verify-scope
> **Files changed:** 5 (3 source + 2 new test files)
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes the bug that made it impossible to adopt Sulis in any repo other than the marketplace's own — the post-mint check failed 100% of the time in consumer repos and rolled the new project record back every time. The fix is three small, surgical corrections plus the two tests whose absence let the bug ship. The changes are well-scoped, fully tested, and the existing release pipeline's behaviour is left byte-for-byte unchanged. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 208 lines of source change across 3 files, plus 397 lines of new tests. Small and focused.

**Scope — clean.** A single concern (one bug, three combined causes, one verify path). All commits are `fix:`.

**Safety — clean.** No database migrations, no schema/IDL changes, no infrastructure files, no secrets.

**Completeness — clean.** Two new test files cover the new behaviour: a real-subprocess test for the new single-entity check mode and a consumer-repo regression test that drives the real verify gate from outside the marketplace repo. Both were written to fail against the broken code first, then pass after the fix.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed source files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff check clean, mypy clean.
- **PR Hygiene:** 0 findings (PH-01 scope low, PH-02 size low, PH-03 safety none, PH-04 completeness none).
- **In the changes:** 0 findings.
- **In the neighbours:** 1 dropped (neighbour `low` pre-existing format drift).
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — `__file__` resolution removes cwd coupling (structural improvement) |
| Security | 0 | 0 | none — `git symbolic-ref` fixed argv, no injection |
| Quality | 0 | 0 | none — new behaviour fully tested |

### Build Verification (CR-01)

ruff check: `All checks passed!` (tool-outputs/ruff-check.log). mypy: `Success: no issues found in 3 source files` (tool-outputs/mypy.log). No PR-introduced errors → Build Verification section empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):      commit_type_spread {fix}; module_fan_out 1 dir   → severity low
Size (PH-02):       source +208 / -17, 3 source files; 397 test lines → severity low
Safety (PH-03):     migrations 0; schema 0; infra 0; secrets 0        → severity none
Completeness (PH-04): new_source_without_test 0; api_change_without_schema false → severity none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None retained. One dropped: pre-existing `ruff format` drift in `_discovery/inspector.py` (lines 169, 362) — present on the base branch, not introduced by this PR. Neighbour `low` → dropped per CR-05 ring-downgrade.

### Watch List

- **Pre-existing format drift, `_discovery/inspector.py:169,362`.** `ruff format --check` would reformat two pre-existing constructs (a long `NonGitDirectoryError(...)` call and the `_parse_github_workflow` return). Confirmed present on the base branch (`change/fix-discover-verify-scope`) before this change, and no CI workflow runs `ruff format`. Left untouched to keep the diff surgical and protect the regression-guard (no unrelated edits to a file carrying behaviour-preserving bug fixes). Would be swept by a repo-wide `ruff format` pass — out of scope for this WP.

### Cross-Reference

- No prior `.security/discover-verify-scope/` report.
- No existing hardening-deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check + mypy on the 3 changed source modules + 2 new test files. Base: clean. Head: clean. Coverage gap: none. (`ruff format` drift is pre-existing + no CI gate → Watch List, not Build Verification.)
- [✓] **CR-02 Single-reader pass justified by diff size:** 3 source files / 208 lines (≤5 files, ≤200 source lines). Tests add 2 files / 397 lines of straightforward test code.
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end (each <250 lines of change). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; the single Watch-List item cites file:line and is grounded in the `ruff format --diff` output.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low in changes. 1 neighbour low dropped.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: cross-layer imports, new singletons, circular imports, resilience on the new subprocess call). Security: nothing surfaced (checks: secret patterns, argv injection on `git symbolic-ref`, path traversal on prefix-strip, schema-validation input handling). Quality: nothing surfaced (build-verification follow-up none; no JSX; no dead surface; no contract drift; test-coverage observation = new behaviour fully tested; CR-10 = no anti-pattern matches — the projects loop is O(N×1) over a 1-element constant, schema loaded once outside the loop, one non-looped best-effort subprocess).
- [✓] **CR-09 PR Hygiene applied.** Scope low; Size low; Safety none; Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/fix-discover-verify-scope...feat/wp-001-fix-discover-verify-scope`
- **Neighbour expansion:** git grep on the changed symbols (`_DEFAULT_DRIFT_DETECTOR`, `read_root`, `_scope_drift_entries`, `cross_tenant_ref_is_allowed`); regression-guard tests confirm callers unaffected.
- **Scanners run:** ruff (lint + format-check), mypy. Gitleaks/Semgrep/Trivy unavailable in-env → manual secret + injection scan of the added lines (documented above).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (diff within size limit).
