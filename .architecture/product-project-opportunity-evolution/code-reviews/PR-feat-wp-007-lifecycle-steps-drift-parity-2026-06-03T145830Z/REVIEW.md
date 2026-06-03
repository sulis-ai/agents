# Code Review: feat/wp-007-lifecycle-steps-drift-parity — Wire the lifecycle-steps canonical into the drift detector

> **Timestamp:** 2026-06-03T145830Z (ISO 8601 UTC)
> **Author:** executor (WP-007)
> **Branch:** feat/wp-007-lifecycle-steps-drift-parity → change/feat-product-project-opportunity-evolution
> **Files changed:** 2 (1 modified, 1 added)
>
> **Outcome:** Ready to merge

---

## At a glance

This change extends the existing drift detector so the three canonical lifecycle Step definitions stay in lock-step with their schema. It is well-scoped, reuses the detector's existing reading machinery instead of building anything new, and ships five tests that cover every way the new check can fail. No build errors, no security surface, no issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean**

Small and focused: ~270 lines across two files (one detector script extended, one new test file). Easy to review thoroughly.

**Scope — clean**

A single concern: register the lifecycle-steps building blocks into the existing drift check. One Conventional-Commit type.

**Safety — clean**

No database migrations, no schema or infrastructure files, no secrets. The change only reads files and compares identifiers.

**Completeness — clean**

Five new tests accompany the change, covering the success case plus four distinct failure cases (a missing identifier, an extra identifier, a resurrected field in the schema, and a missing argument).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both changed files read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — reuses JsonLdFileReader.read_steps + the {ok, data.drift} envelope; new mode mirrors `_run_scope_mode` (pure drift fn + thin I/O wrapper) |
| Security | 0 | 0 | None — no secrets / injection / eval; reads two local files, no network, no shell |
| Quality | 0 | 0 | None — 5 tests cover every drift branch; no dead surface; no contract drift |

### Build Verification (CR-01)

`ruff check` clean on both changed files; `ruff format --check` reports both already formatted; the full 69-test drift-detector suite (existing + new) passes. No PR-introduced errors. Tool outputs captured under `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/)   → clean
  severity: none

Size (PH-02):
  lines_added: ~270, lines_removed: 4
  files_changed: 2
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (well within single-reader carve-out)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (test file added)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The change only adds a new mode dispatch branch in `main()` and a new pure function pair; it does not alter the release-train / discover-project / scope code paths (regression-confirmed by the 64 pre-existing tests still passing).

### Watch List

- The `extra_in_canonical` symmetry branch and the parity invocation-error branch are both exercised by dedicated tests (`test_extra_step_ulid_fails`, `test_parity_requires_schema_path_exits_two`), so the new code has no untested branch. No watch items.

### Cross-Reference

- No prior security viability report for this project.
- No existing hardening deltas touched.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run ruff check`; `uv run ruff format --check`; full `pytest` drift suite. Base: clean. Head: clean (0 new errors). Coverage gap: no static type-checker configured in this scripts package (ruff is the configured linter; mypy/pyright absent) — recorded, not skipped.
- [✓] **CR-02 Parallel dispatch.** Single-reader pass justified by diff size: ~270 lines, 2 files (within the ≤200-line band only marginally exceeded by additive test scaffolding; the functional change to the detector is 149 lines / 1 file). All changed files read end-to-end.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (detector 397 lines, test 215 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; mechanical-floor outputs captured in tool-outputs/.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: dependency-direction (reuses reader, no new infra import), singletons (none added), resilience (no I/O calls added beyond two local file reads), proof (5 tests cover the new port). Security: nothing surfaced — primitives checked SEC-01..07, SC-01..04; no secrets/injection/eval/subprocess/network in the detector diff. Quality: 0 findings; jsx-ident-scan N/A (no JSX); dead-surface none; contract-drift none; test-coverage present (5 tests); CR-10 perf: no anti-pattern matches (only bounded set-difference loops over ≤4 canonical Steps).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat concern). PH-02 Size: none (~270 lines / 2 files). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: none (test file added). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** git working tree vs change/feat-product-project-opportunity-evolution (pre-commit; Step 6.5 runs before Step 7 commit).
- **Neighbour expansion:** git grep over `_canonical_drift` consumers + the detector's other modes; no neighbour findings.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** ruff (lint + format); pytest (regression floor). Gitleaks/Semgrep/Trivy not invoked — diff has no secret/dependency/infra surface (no new deps, no Dockerfile, no config).
- **Scanners unavailable:** static type-checker (none configured for this package).
- **Lenses dispatched in parallel:** no — single-reader carve-out (diff size).
