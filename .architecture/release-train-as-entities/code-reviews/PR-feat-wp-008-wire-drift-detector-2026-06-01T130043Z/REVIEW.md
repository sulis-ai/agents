# Code Review: feat/wp-008-wire-drift-detector — Wire drift detector into branch-ci.yml

> **Timestamp:** 2026-06-01T130043Z (ISO 8601 UTC)
> **Author:** sulis-executor (WP-008)
> **Branch:** feat/wp-008-wire-drift-detector → change/create-release-train-as-entities
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds a new CI job to `branch-ci.yml` that runs the drift detector built in the previous task (WP-007). It also ships its own structural test so a future edit to the YAML can't silently break the wiring. There are no build errors, no issues to fix, and the scope is well-contained.

The job is deliberately set to "advisory" for now — it reports drift in the run logs but doesn't block merges. There's a clear comment explaining how to flip it to blocking once the 11 known reconciliation items are cleaned up in a follow-on change.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 219 lines across 2 files. Small, focused.

**Scope — clean.** Single concern: wire the drift detector into CI plus the test that protects the wiring.

**Safety — clean.** No database migrations, no schema changes, no secrets in the diff. The new CI job is additive and runs in advisory mode, so it cannot newly block other people's pull requests.

**Completeness — clean.** Source (the YAML addition) and its structural test ship together.

## Things to take away

Omitted — the pull request is clean and there's no specific lesson tied to it.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, etc.) for engineers and downstream agents. The author tier above contains everything the PR author needs to act.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all low severity)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced |
| Security | 0 | 0 | Nothing surfaced |
| Quality | 0 | 0 | Nothing surfaced |

### Build Verification (CR-01)

All mechanical floor checks clean:

- `python3 -m compileall plugins/sulis/scripts/tests/unit/test_branch_ci_has_drift_check.py` — clean
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/branch-ci.yml'))"` — parses successfully (both `branch-ci` + `canonical-drift-check` jobs present)
- `uv run pytest tests/unit/test_branch_ci_has_drift_check.py` — 8/8 pass
- `uv run pytest tests/unit/` (full unit suite regression) — 1296/1296 pass

No PR-introduced errors. No coverage gaps (full mechanical baseline exercised).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → low
  module_fan_out: 2 distinct top-level dirs     → low
  severity: low (single concern)

Size (PH-02):
  lines_added: 219, lines_removed: 0
  files_changed: 2
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: low (201-500 line band; 1-5 file band; well below mixed thresholds)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 1 (additive CI job, advisory mode)
  secret_pattern_hits: 0
  severity: low (advisory mode + continue-on-error: true prevents this job from
  introducing a new gate; the existing branch-ci required check is unchanged)

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: low (source + structural test ship together)
```

No PH-03 auto-downgrade triggered.

### Findings in the Changes

None.

### Findings in the Neighbours

None.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable
- **Existing security report:** none in `.security/release-train-as-entities/`
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m compileall` on new test, `python3 -c "import yaml; yaml.safe_load(...)"` on YAML, `uv run pytest` on the new test file + full unit suite. Base: 0 errors. Head: 0 new errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff size: 219 lines / 2 files. The line count is 19 above the carve-out threshold (200), but the file count (2) is well below (5) and the diff is a single concern (a new CI job + its structural test, both additive). Single-reader pass justified by single-concern, 2-file scope; recording the line-count deviation here per CR-08.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end. `branch-ci.yml` is 110 lines total post-edit (64 pre + 44 added + 2 spacing); test file is 175 lines new. Both inspected fully.
- [✓] **CR-04 Evidence discipline.** No findings raised, so no evidence required. Mechanical baseline outputs in `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** No findings; rubric not exercised.
- [✓] **CR-06 Verdict computed.** Verdict: `PASS`. Build Verification empty + 0 findings + lenses all produced output + all CR-01/03/07 floors satisfied + no auto-downgrade trigger fired.
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + explicit "nothing surfaced" note. Security: 0 findings + explicit "nothing surfaced" note (no scanners invoked — the diff has no source code beyond a structural pytest and CI YAML, so SEC-NN primitives have nothing to score against). Quality: 0 findings; build clean; test+source ship together; CR-10 patterns N/A on CI YAML config.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single feat). PH-02 Size: low (219 / 2). PH-03 Safety: low (advisory mode prevents new gate). PH-04 Completeness: low (test ships with source). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** working-tree diff against HEAD (changes uncommitted at review time per the Step 6.5 gate)
- **Neighbour expansion:** not exercised (no neighbour ring needed for an additive CI job whose only caller is the GitHub Actions runner)
- **Neighbour cap:** N/A
- **Scanners run:** py_compile, yaml.safe_load, pytest (new test + full unit suite regression)
- **Scanners unavailable:** none required for this diff shape
- **Lenses dispatched in parallel:** no — single-reader pass justified by 2-file single-concern scope (CR-02 carve-out, with line-count deviation noted)
