# Code Review: feat/wp-001-preflight-ci-conclusion-helper — Non-polling pre-flight CI-conclusion helper

> **Timestamp:** 2026-05-28T135202Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/wp-001-preflight-ci-conclusion-helper → change/harden-preflight-dev-drift-check
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one small, focused helper that asks GitHub "what's the latest recorded test result for this branch?" and answers without waiting around. It comes with five tests that cover every answer it can give (passing, failing, still-running, and "no results yet"), and the whole existing test suite still passes. There are no build errors and nothing needs fixing.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: 176 new lines across 2 files — the new helper plus its dedicated test file. One concern, one feature type. The new behaviour ships with its own tests. Nothing about the shape of this change raises a flag.

## Things to take away

(Omitted — the change is clean and well-shaped; there is nothing specific worth flagging.)

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the changed file >50 lines (`_wpxlib.py`) read end-to-end across the modified region; all three lenses produced output. No auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (no lens findings)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

No type-checker is configured for this repo (stdlib-only tooling per `.sulis/repo-contract.yml`). The compile floor was used as the mechanical baseline: `python3 -m py_compile` on both changed files and `python3 -m compileall -q plugins/sulis/scripts` — both clean (see `tool-outputs/py_compile.log`). The full unit suite (`pytest plugins/sulis/scripts/tests/unit/ -q`) reports 770 passed, 1 skipped (pre-existing skip), including the 5 new tests. Coverage gap recorded: no static type-checker → the build floor is compile + the existing test gate.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean
  module_fan_out: 1 top-level dir (plugins/)    → clean
  severity: none

Size (PH-02):
  lines_added: 176, lines_removed: 0, total: 176
  files_changed: 2
  severity: none (<=200 line / <=5 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (helper ships with its own test file)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The single neighbour of note is `_poll_ci` (`_wpxlib.py:1196`), the other consumer of `_gh_check_runs`. It is intentionally left unmodified (WP Contract + HD-001) — the new helper deliberately duplicates the pass-set predicate so the train verdict and the pre-flight verdict can diverge independently. No finding: this is documented design intent, not drift.

### Lens detail

**Architecture lens — nothing surfaced.** Checks run: dependency direction (the helper depends inward on the domain-owned `GHClient` port via `_gh_check_runs`, never on infrastructure — WPB-01); no new module-level singletons or `getInstance()` accessors (it reuses `_resolve_gh`'s existing seam through `_gh_check_runs`); no new circular imports; one bounded external read per call (a single `check_runs` API call, not in a loop). The `gh=` keyword preserves the existing injection seam (WPB-03 — tests use a real in-test stub implementing the Protocol, not a mock of an internal). Outside-in TDD honoured (WPB-08): tests written first and confirmed failing for the right reason (`AttributeError`).

**Security lens — nothing surfaced.** Primitives checked: SEC-01..07, SC-01..04. No secrets in the diff; no injection vector (`repo`/`branch` are forwarded to the existing port, not interpolated into a shell command in this helper); no auth surface; no new dependencies (uses `_gh_check_runs`, `time` and `json` already imported). Scanners: none run (no signal in the diff — pure stdlib helper + test); recorded as a coverage note, not a gap.

**Quality lens — nothing surfaced.** (1) Build verification: clean. (2) JSX/template identifier scan: N/A (Python). (3) Dead surface: none — the helper is consumed by WP-003 (its `blocks` edge); the test file exercises every branch. (4) Contract drift: none — the four-string verdict set is a closed set, documented in the docstring and each branch is asserted by a test. (5) Test coverage: 5 tests cover `failed`+names, `green`+empty, `pending` (with a `time.sleep` never-called assertion), the lesson-#59 explicit-conclusion guard, and `unknown`. (6) Style: descriptive name, single small function, docstring documents "why" (faithfulness rationale + intentional divergence). (7) CR-10 performance: no anti-pattern matches — the two list comprehensions each iterate the already-fetched `runs`/`statuses` once (O(N) over a single commit's check-runs), with no per-item external call; the `not all(...)` short-circuits. No N+1, no unbounded materialisation, no repeated invariant in a loop.

### Watch List

Empty.

### Cross-Reference

- **Existing Hardening Deltas covered:** HD-001 (this WP implements it).
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m py_compile <changed files>`; `python3 -m compileall -q plugins/sulis/scripts`. Base & Head: 0 errors. Coverage gap: no static type-checker configured (stdlib-only per repo-contract) — compile + unit-test gate used.
- [✓] **CR-02 Single-reader pass.** Justified by diff size: 176 lines, 2 files (within the ≤200-line AND ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** The one changed file >50 lines (`_wpxlib.py`) had its modified region (the new 51-line helper) and surrounding context (`_gh_check_runs`, `_poll_ci`, the GHClient Protocol) read end-to-end. The test file (125 lines) read end-to-end. Unread: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens outputs cite the helper body and line ranges.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed. Security: 0 findings + primitives listed. Quality: 0 findings + all seven outputs produced (build-verification follow-up, JSX scan N/A, dead-surface, contract-drift, test-coverage observation, style, CR-10 perf).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`, one module). PH-02 Size: none (176 lines / 2 files). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: none (test ships with the helper). PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** local git working tree vs `change/harden-preflight-dev-drift-check` (branch not yet committed at review time; review run pre-commit per Step 6.5).
- **Neighbour expansion:** git grep for `_gh_check_runs` consumers → `_poll_ci` (the one neighbour); within the 20-file cap.
- **Neighbour cap:** 1 of 1 considered, 0 excluded.
- **Scanners run:** none (no signal — pure stdlib helper + unit test).
- **Scanners unavailable:** gitleaks / semgrep / trivy not invoked (no applicable signal in the diff).
- **Single-reader pass:** yes (CR-02 carve-out).
