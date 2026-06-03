# Code Review: feat/wp-011-emitter-characterisation-test — WP-011 emitter characterisation test

> **Timestamp:** 2026-06-03T155813Z (ISO 8601 UTC)
> **Author:** executor (WP-011)
> **Branch:** feat/wp-011-emitter-characterisation-test → change/feat-product-project-opportunity-evolution
> **Files changed:** 2 (both new test files; no production code)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a single self-contained test file that takes a faithful snapshot
of how three parts of the system save their data today, before a later change
rewrites them. There are no build or lint errors, every check passes, and the
change touches only test code — no production behaviour moves. There is nothing
that needs fixing.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 264 added lines across 2 files, one of which is an empty package
marker. Single concern, single test file.

**Scope — clean.** One `test` commit, one logical concern (pin current emit
behaviour). No mixing of refactor and feature.

**Safety — clean.** No migrations, no schema/IDL changes, no infrastructure files,
no secrets. Test-only.

**Completeness — clean.** The change IS the test. It pins three emit paths against
real adapters over temp directories (no mocks), and every assertion line executes
(full coverage of the new file).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the single
changed file >50 lines was read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — test-only diff, no module/import/resilience surface |
| Security | 0 | 0 | none — no auth/injection/secret/external-call surface in a test |
| Quality | 0 | 0 | none — characterisation test, 100% line coverage, real adapters |

### Build Verification (CR-01)

Mechanical baseline ran on HEAD. The project configures **ruff** (resolved from
`pyproject.toml`) as its linter; no mypy/pyright is configured, so no type gate
applies (consistent with sibling test files). Correctness floor: the test suite is
the build for this Python scripts package.

- `ruff check tests/characterisation/` → `All checks passed!` (exit 0)
- `pytest tests/characterisation/` → 3 passed
- Full suite (separately, Step 3): 1994 passed, 9 skipped — no regression

No PR-introduced errors. Build Verification section empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {test}                   → clean
  module_fan_out: 1 (tests/characterisation)   → clean
  severity: none

Size (PH-02):
  lines_added: 264, lines_removed: 0, total: 264
  files_changed: 2 (1 is an empty __init__.py marker)
  severity: none (single self-contained test file)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the diff IS the test)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The test references (read-only) `_product_emission`, `_opportunity_emission`,
`_discovery._compose_entity`, `_discovery.minter.write_project_entity`, and
`_entity_adapter_local.LocalFileEntityAdapter`. It pins their current behaviour and
introduces no new coupling. No pre-existing gaps were exposed.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this project
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check tests/characterisation/` (the configured linter). HEAD: 0 errors. No mypy/pyright configured (coverage gap noted, not a silent skip — the project has no type gate). Correctness floor via pytest: 3 passed (file), 1994 passed full-suite.
- [✓] **CR-02 Dispatch shape.** Diff is 264 lines / 2 files. Just over the 200-line line-count threshold, but a single self-contained test file with zero production surface: the architecture + security lenses have no live surface (no modules/imports/resilience added; no auth/injection/secret/external-call). Quality is the sole substantive lens and the file was read end-to-end. Recorded here per CR-02.
- [✓] **CR-03 Full-file reads.** The one changed file >50 lines (`test_living_entity_emit_baseline.py`, 218 lines) was read and authored end-to-end. The `__init__.py` is empty.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; absence is itself evidenced by the scan logs in `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; no unread >50-line file; every lens produced explicit output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: domain/infra imports (none added), singletons (none), circular imports (none), new external calls/timeouts/CB (none — test-only). Security: nothing surfaced — primitives checked SEC-01..07 / SC-01..04 not applicable (no auth, no injection sink, no secret, no dependency add). Quality: nothing surfaced — build-verification follow-up (0), JSX scan (n/a, no TSX/JSX), dead-surface (none — every helper/import used), contract-drift (n/a), test-coverage observation (the diff IS the test; 100% line coverage of the new file), CR-10 perf scan (no loops, no N+1/O(N²)/waterfall/unbounded-materialisation patterns).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none ({test}). PH-02 Size: none (264 lines / 2 files). PH-03 Safety: none (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none. No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached origin/change/feat-product-project-opportunity-evolution`
- **Neighbour expansion:** git grep / direct read of the five referenced modules
- **Neighbour cap:** 5 of 5 referenced modules considered, 0 excluded
- **Scanners run:** ruff (lint), pytest (correctness)
- **Scanners unavailable:** mypy/pyright (not configured by the project — no type gate); Gitleaks/Semgrep/Trivy (no security surface in a test-only diff — not run)
- **Lenses dispatched in parallel:** no — single-reader justified by the test-only, zero-production-surface diff (CR-02 note above)
