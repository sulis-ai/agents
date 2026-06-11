# Code Review: feat/wp-007-pure-core-property-tests — Phase-1 pure-core property tests

> **Timestamp:** 2026-06-11T145659Z (ISO 8601 UTC)
> **Author:** WP-007 executor
> **Branch:** feat/wp-007-pure-core-property-tests → change/fix-use-change-id-not-handle
> **Files changed:** 1
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one new test file that checks the change-identity safety rules against many randomly generated inputs, rather than just one fixed example. There are no build errors, no production code changed, and the file only adds protective tests. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

The change is small and single-purpose: one new test file, 246 lines, no production code, no database changes, no new dependencies. This is exactly the shape a focused testing change should have — easy to review and low risk.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the single changed file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `ruff check` all checks passed, `py_compile` OK.
- **PR Hygiene:** 0 high/medium findings (CR-09 / PH-01..PH-04). Single `test:` commit type, 1 file, 246 lines, 0 migrations, 0 secrets.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — test-only diff |
| Security | 0 | 0 | none — synthetic inputs, no secrets/deps |
| Quality | 0 | 0 | none — no dead surface, bounded test loops |

### Build Verification (CR-01)

`plugins/sulis/scripts/tests/unit/test_change_identity_properties.py`: `ruff check` → "All checks passed!"; `ruff check --select F` (pyflakes: unused imports/names) → "All checks passed!"; `python -m py_compile` → OK. No PR-introduced errors. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {test}; module_fan_out 1 dir → severity none
Size (PH-02):         lines_added 246, removed 0, files_changed 1 → severity low
Safety (PH-03):       migrations 0, schemas 0, infra 0, secret_hits 0 → severity none
Completeness (PH-04): new_source_without_test 0 (the diff IS the test layer) → severity none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The diff imports the WP-006 strategies module (`unit._change_identity_strategies`) and the pure functions under test (`ulid_handle`, `change_worktree_path` from `_wpxlib`; `_changes_matching_handle`, `_select_change_id_refusing_conflict` from `sulis-change`) read-only via the established `SourceFileLoader` pattern — no neighbour code modified.

### Watch List

None.

### Cross-Reference

- No existing security report under `.security/use-change-id-not-handle/`.
- No existing hardening deltas applicable.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uvx ruff check` (incl. `--select F`), `python -m py_compile`. Base (file absent) vs Head: 0 new errors. Coverage gap: no mypy/pyright configured for this scripts project (none in `pyproject.toml` or CI); ruff is the configured/available linter and it passed.
- [✓] **CR-02 Single-reader pass.** Diff is 246 lines / 1 file. Above the 200-line band but a single self-contained TEST file with zero production surface; read end-to-end by one reader. Justified by the test-only, single-file scope.
- [✓] **CR-03 Full-file reads.** The one changed file (246 lines) was read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; mechanical outputs captured in `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; full-file read done; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no production code; checked domain-import direction, singletons, circular imports, resilience/observability surface — none present in a test). Security: nothing surfaced (primitives SEC-01..07 / SC-01..04 checked; synthetic generated ULIDs, no secrets, no new dependencies, no auth/injection/SSRF surface). Quality: 0 findings — no build errors; no JSX; no dead surface (all 10 imported names referenced, ruff F-rules pass); no contract drift (properties assert real function behaviour); test-coverage = the diff is the test layer; CR-10 performance: nested loops are over bounded generated record-sets (`max_size=12`, ≤150 examples) in test code, not a production hot path — benign by context.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `test:` concern). PH-02 Size: low (246 lines / 1 file). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: none (the change is itself test code). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** working-tree new file vs `change/fix-use-change-id-not-handle` (reviewed pre-commit at the Step 6.5 gate).
- **Neighbour expansion:** git grep; the functions under test are imported read-only, not modified.
- **Scanners run:** ruff (incl. pyflakes F-rules), py_compile.
- **Scanners unavailable:** mypy/pyright (not configured for this project); Gitleaks/Semgrep/Trivy (no secret/dependency/infra surface in a synthetic-input test file — no signal to scan).
- **Single-reader pass:** test-only, single-file, read end-to-end.
