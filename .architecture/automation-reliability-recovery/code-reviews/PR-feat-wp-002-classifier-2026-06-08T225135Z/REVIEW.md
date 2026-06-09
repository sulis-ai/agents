# Code Review: feat/wp-002-classifier — Provider-neutral classifier

> **Timestamp:** 2026-06-08T225135Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-classifier → change/feat-automation-reliability-recovery
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one small, pure decision function — given an observed failure
and an optional provider hint, it returns one of three recovery verdicts
(retry, give up, or re-login). There are no build errors, the new behaviour is
fully tested (every row of the agreed decision table, plus the "unknown future
error" safety case), and the function deliberately keeps provider-specific
knowledge out — that boundary is even checked automatically by a test. Nothing
needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean**

Small and focused: 3 files, about 210 lines, most of which is the test file.

**Scope — clean**

A single concern: the new classifier function and the test that proves it.

**Safety — clean**

No database migrations, no schema or infrastructure files, no secrets. The new
code touches nothing live — nothing calls it yet (the recovery driver wires it
up in a later piece of work), so there's no behaviour change to existing flows.

**Completeness — clean**

The change adds 1 new test file (4 tests, one parametrised across all 13 rows
of the agreed decision table) alongside the new function. New behaviour is
covered.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — pure inward-pointing dependency, contract test present |
| Security | 0 | 0 | none — no secrets, no auth surface, no new deps |
| Quality | 0 | 0 | none — build clean, behaviour fully tested |

### Build Verification (CR-01)

Empty. The project's mechanical floor is ruff (no mypy/pyright configured —
recorded as a coverage gap in Methodology). `ruff check` and `ruff format
--check` both pass on all three changed files (see
`tool-outputs/ruff-head.log`). The full classifier + regression suite is green:
40 passed (see `tool-outputs/test-head.log`).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (_session_manager + its tests)
  severity: clean

Size (PH-02):
  lines_added: ~210, lines_removed: ~8
  files_changed: 3 (1 new test, 2 modified)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: clean (≤200 production lines; test file dominates)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0 (gitleaks clean)
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (classify() ships with its test file)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The only neighbour is `events.py` (the value objects `classify` consumes,
unchanged) and `_recovery_contract_fixtures.py` (the shared truth-table fixture
the test imports, unchanged). The package re-export in `__init__.py` is
additive (`classify` added to imports + `__all__`).

### Watch List

Empty.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this project
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` + `ruff format --check` on the 3 changed files; full pytest suite (classifier + recovery_contract + core). Base: clean. Head: clean (0 new errors, 40 tests pass). Coverage gap: no static typechecker (mypy/pyright) is configured in the project — ruff is the only mechanical floor available; recorded here per CR-01.
- [✓] **CR-02 Single-reader pass justified by diff size: ~210 lines, 3 files (production change is one 28-line pure function + a 3-entry dict; the test file is the bulk). Within the ≤200-production-line / ≤5-file carve-out.**
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (authored this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; tool outputs captured under `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced. Checks run: dependency direction (imports `events.py` only, inward-pointing — verified by AST parse), no domain→infra import, no singletons, no circular import, resilience N/A (pure function, no external calls/timeouts/CB), contract test present (truth table vs real value objects, CF-07). Security: nothing surfaced. Primitives checked: SEC-01..07 (no auth surface, no injection vector, no validation gap — pure total function over typed inputs), SC-01..04 (no new dependencies). Scanners run: Gitleaks (no leaks found). Quality: 0 findings. Build verification follow-up: none. JSX scan: N/A (backend, no TSX/JSX). Dead-surface: none (`classify` re-exported + consumed by tests; `_CATEGORY_DEFAULT` consumed by `classify`). Contract-drift: none (all 13 contract truth-table rows + the unknown-code totality case covered). Test-coverage: new behaviour fully tested (100% line coverage on classifier.py). CR-10 performance: no anti-pattern matches (pure function, no loops, no IO).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single `feat` concern). PH-02 Size: clean (~210 lines / 3 files). PH-03 Safety: clean (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: clean (new function ships with tests). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** staged working-tree diff vs `change/feat-automation-reliability-recovery` (changes not yet committed at review time — review runs against staged content, which is what will be committed at Step 7).
- **Neighbour expansion:** git grep / direct read. Neighbours: `events.py` (consumed, unchanged), `_recovery_contract_fixtures.py` (consumed by test, unchanged). 2 of 2 considered; none excluded.
- **Neighbour cap:** not reached (2 files).
- **Scanners run:** Gitleaks (clean). Semgrep + Trivy available but not run — no dependency or rule-pattern surface in a 3-entry pure-mapping change.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (diff within threshold).
