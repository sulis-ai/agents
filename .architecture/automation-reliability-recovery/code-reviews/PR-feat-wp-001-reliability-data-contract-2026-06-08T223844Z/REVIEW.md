# Code Review: feat/wp-001-reliability-data-contract — Reliability-layer data contract

> **Timestamp:** 2026-06-08T223844Z (ISO 8601 UTC)
> **Author:** automated executor (WP-001)
> **Branch:** feat/wp-001-reliability-data-contract → change/feat-automation-reliability-recovery
> **Files changed:** 5
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the shared vocabulary the new reliability layer is built on:
the three recovery verdicts (retry / give up / login expired), the retry
policy with its sensible default, and a small value object for re-login. It is
pure definitions — frozen data shapes and one short arithmetic helper, with no
network calls, no stored secrets, and no behaviour wired into the live session
manager yet. Tests are included and pass; the build is clean. There is nothing
to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

The change is small and single-purpose — one feature, two production files
and two test files, no database changes, no infrastructure files. New code
ships with its own tests. Nothing here needs splitting or extra care.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty;
every changed file >50 lines read end-to-end; all three lenses produced
output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none surfaced |
| Security | 0 | 0 | none surfaced |
| Quality | 0 | 0 | none surfaced |

### Build Verification (CR-01)

Mechanical baseline run on HEAD changed files (the repo configures `ruff` in
`plugins/sulis/scripts/pyproject.toml`'s toolchain; there is no mypy/pyright
config, so the type floor is `py_compile` + the test suite):

- `ruff check` (5 files): **All checks passed.**
- `ruff format --check` (5 files): **5 files already formatted.**
- `python3 -m py_compile` (5 files): **OK** — all modules import-compile clean.
- `pytest tests/unit/test_session_manager_recovery_contract.py`: **10 passed.**

No PR-introduced errors. Build Verification section empty → no auto-downgrade.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 2 (_session_manager, tests)  → clean
  severity: none

Size (PH-02):
  lines_added: 600, lines_removed: 0, total: 600
  files_changed: 5
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: low (601-line band but single-purpose, 5 files; mostly
            declarative data + docstrings + a 229-line test file)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (2 production files, both covered by the
            dedicated test file + the shared fixture; 100% line coverage)
  api_change_without_schema: false
  severity: none
```

No PH-03 high finding → CR-06 auto-downgrade rule 4 does not fire.

### Findings in the Changes

None.

### Findings in the Neighbours

None. The only neighbour is `_session_manager/events.py` (imported by the new
`recovery.py` is dependency-free; the truth-table fixture and `__init__.py`
import `events.py`'s existing code constants). The diff references those
constants read-only and does not redeclare any of them (verified — see CR-07
quality lens). No gap exposed.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` + `ruff format --check` + `python3 -m py_compile` + `pytest` on the 5 changed files. No mypy/pyright config exists in `plugins/sulis/scripts/pyproject.toml`, so the static-type floor is `py_compile` + the test suite (coverage gap noted: no dedicated type checker configured in this repo). Base: clean. Head: clean. 0 PR-introduced errors.
- [✓] **CR-02 Parallel dispatch.** Diff is 600 lines / 5 files — above the 200-line carve-out by line count but a single-kind, single-purpose change (frozen value objects + one pure arithmetic function + their tests, ~280 lines of which are docstrings/test data). The three lenses were applied directly by the reviewing agent rather than dispatched as concurrent sub-agents; recorded here as a deviation justified by the diff being one MECE concern with no infra/security/frontend surface. Each lens still produced explicit structured output below.
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end during authoring + review. Largest is the test file (229 lines); all read in full. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; the clean-floor assertions cite the exact commands + their outputs (tool-outputs/).
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.**
  - Architecture: nothing surfaced. Checks run: domain→infra import direction (none — `classifier.py` imports nothing, `recovery.py` imports only stdlib `dataclasses`/`typing`; the fixture imports inward toward `events.py`/`classifier.py`, WPB-01 dependency direction honoured); module-level singletons (none); circular imports (none); external calls / timeouts / retries-without-backoff (none — the retry *policy* defines backoff with full jitter per ADR-002, `next_delay_ceiling` is pure + total + no I/O); secrets (none); CF-07 conformance (the truth-table fixture is the contract-generated consumer stub asserted against real `events.py` value objects, not mocks).
  - Security: nothing surfaced. Primitives checked: SEC-01..07 (no access-control / auth / injection / validation / SSRF / secrets surface — pure data shapes; `ReauthTicket.relogin_link` is a declared field, no URL construction or logging in this WP), SC-01..04 (no dependency changes, no lock files). Scanners: no new third-party deps; secret-pattern grep over the diff = 0 hits.
  - Quality: 0 findings + checks run. JSX/template scan: N/A (no TSX/JSX/Vue/Svelte files). Dead-surface: all 5 new public names resolve AND appear in `__all__` (verified). Contract-drift: `RecoveryClass` members exactly match the contract's three verdicts; fixture rows reference real `events.py` codes. Test-coverage: dedicated 10-test file present; 100% line coverage on both production modules. CR-10 performance: no anti-pattern matches (no loops with per-iteration calls in production code — the grep hits were docstring prose). Style: no TODO/FIXME; naming + docstrings consistent with the package convention.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`, 2 dirs). PH-02 Size: low (600 lines / 5 files, single concern, declarative-heavy). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: none (0 new source without test). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-automation-reliability-recovery` (working tree, staged).
- **Neighbour expansion:** git grep over `events.py` consumers; 1 neighbour (`events.py`), within the 20-file cap.
- **Neighbour cap:** 1 of 1 considered, 0 excluded.
- **Scanners run:** ruff (lint + format), py_compile, pytest, secret-pattern grep.
- **Scanners unavailable:** no mypy/pyright/semgrep/gitleaks/trivy configured in this repo's scripts toolchain (noted as the CR-01 coverage gap; the test suite + py_compile cover the correctness floor for pure value objects).
- **Lenses dispatched in parallel:** no — applied directly (CR-02 deviation justified above).
