# Code Review: feat/wp-001-scenario-contract-fields — Add isolation + verdict_invariant optional fields to scenario.schema.json

> **Timestamp:** 2026-06-08T205347Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/wp-001-scenario-contract-fields → change/feat-verification-substrate
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds two new optional settings to the Scenario contract — one for how a test run isolates its state, one for how the run checks that the right data was saved. Both are optional, so every Scenario that already exists keeps working untouched. The change is small (151 lines across two files), comes with its own tests, and those tests prove both the new behaviour and the backward-compatibility. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Well-shaped and focused. One concern (the shared schema contract these two downstream pieces of work depend on), two files, both directly in scope, tests included. Nothing here suggests a split or raises a safety concern.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all low/clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

None. `ruff check` clean; `ruff format --check` clean; the schema passes `Draft202012Validator.check_schema` (valid JSON Schema 2020-12). Regression: 49 schema + instance-valid tests pass.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 2 files, 1 logical concern   → clean
  severity: low

Size (PH-02):
  lines_added: 151, lines_removed: 0, total: 151
  files_changed: 2
  severity: low (<=200 line / <=5 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 1 (scenario.schema.json — ADDITIVE + OPTIONAL only)
  infra_files: 0
  secret_pattern_hits: 0
  severity: low (additive optional schema change; backward-compatible by construction; no required-array edit)

Completeness (PH-04):
  new_source_without_test: 0 (the only new .py file IS the test)
  api_change_without_schema: false
  severity: low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The only Python module that loads `scenario.schema.json` is the new test itself (`test_scenario_schema.py`). No consumer hardcodes the Scenario `required` list or a property count, so the additive change exposes no neighbour gap.

### Watch List

None.

### Lens output (CR-07)

- **Architecture lens: nothing surfaced.** Checks run: dependency-direction (the change is a data file + an offline test, no module imports added to any core); new singletons (none); circular imports (none); contract-drift (the two added properties match `contracts/verdict-invariant.contract.md` producer-side shape and TDD §A byte-for-byte — `kind` required, `poll.attempts` required minimum 1, `unevaluatedProperties:false` on both object levels); `required` array unchanged (verified: `['id','name','verifies','exercises','journey','state','sys_status']`).
- **Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no access-control / injection / validation surface — JSON schema data + offline jsonschema test), SC-01..04 (no new dependency; jsonschema already vendored), DAT-03 (no logging). Secret-pattern scan over the diff: 0 hits.
- **Quality lens: nothing surfaced.** (1) Build Verification follow-up: none. (2) JSX/template scan: N/A (no TSX/JSX/Vue/Svelte). (3) Dead surface: none (both test functions are pytest-collected; fixture used). (4) Contract-drift: none — schema matches the contract artifact; nested `unevaluatedProperties:false` proven to reject unknown nested props, missing `kind`, and `attempts<1`. (5) Test coverage: the diff IS test-first — two round-trip tests against the real vendored schema (MEA-09, no mock), covering with-fields and without-fields. (6) Style: clean (ruff). (7) CR-10 performance: no anti-pattern matches (no loops over collections; the only iteration is error-message formatting on validation failure).

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` + `ruff format --check` on the changed `.py`; `Draft202012Validator.check_schema` on the changed schema; regression `pytest -k "scenario_schema or instance_valid"`. Base: clean. Head: clean (0 new errors). Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 151 lines, 2 files** (≤200 lines AND ≤5 files).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (`scenario.schema.json` 121 lines; `test_scenario_schema.py` 105 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings; lens checks cite the concrete shape verified.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each emitted explicit "nothing surfaced" with the checks run.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single `feat`). PH-02 Size: low (151 lines / 2 files). PH-03 Safety: low (1 additive+optional schema file, 0 migrations, 0 secrets, 0 infra). PH-04 Completeness: low (the new source file is the test). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-verification-substrate...HEAD` (staged worktree diff)
- **Neighbour expansion:** `git grep` over `plugins/sulis/scripts` for `scenario.schema.json` loaders + `verdict_invariant`/`isolation` consumers
- **Neighbour cap:** 1 of 1 considered (only the new test loads the schema); cap not reached
- **Scanners run:** ruff (lint + format), jsonschema meta-schema check, diff secret-pattern grep
- **Scanners unavailable:** gitleaks/trivy/semgrep not invoked separately — diff is a data file + offline test with no dependency/secret surface; grep-based secret scan substituted and recorded
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (151 lines / 2 files)
