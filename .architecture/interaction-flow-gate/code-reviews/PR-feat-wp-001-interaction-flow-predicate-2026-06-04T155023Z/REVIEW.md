# Code Review: feat/wp-001-interaction-flow-predicate — Interaction-flow gate predicate + recognition

> **Timestamp:** 2026-06-04T155023Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/wp-001-interaction-flow-predicate → change/gate-interaction-flow-gate
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds two small checking functions that decide (1) whether a piece
of work is an "interaction contract" and (2) whether its flow has been properly
exercised before it can be marked done. Both are pure checks — they read a few
fields and return a yes/no or a clear error message. There are no build errors,
the change is tightly scoped to one file plus its tests, and it ships with a
full set of tests covering every pass and fail path. Nothing needs attention
before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 216 lines across 2 files (73 lines of logic, 143 lines of
tests). Small and easy to review thoroughly.

**Scope — clean.** A single feature, one logical concern, all in one module
plus its test file.

**Safety — clean.** No database migrations, no schema changes, no
infrastructure files, no secrets.

**Completeness — clean.** The new behaviour ships with its tests. Sixteen tests
cover every branch: the recognition check (true / false / case-insensitive) and
the evidence check (passes for both valid evidence sources; rejects empty
timestamp, blank source, unknown source token, and missing attestation, plus an
explicit "a bare timestamp alone must not pass" guard).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the changes; Build Verification empty;
both changed files read end-to-end; all three lenses produced output. No
auto-downgrade triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — pure predicates, no new imports/singletons/cycles |
| Security | 0 | 0 | none — no secrets/network/subprocess; in-process frontmatter check |
| Quality | 0 | 0 | none — CR-01 clean, CR-10 clean, full test coverage |

### Build Verification (CR-01)

Mechanical baseline ran `ruff check` on both changed files, comparing BASE vs
HEAD. HEAD reports 2 `E402` errors at `_wpxlib.py:3805-3806`
(`import secrets`, `import time` not at top of file). Both are **present
identically on BASE** — pre-existing in untouched code, not introduced by this
PR. PR-introduced error count: **0**. Build Verification section empty.

Test suite (proof floor): `pytest tests/unit/test_interaction_flow_gate.py
tests/unit/test_visual_contract_gate.py` → 32 passed (16 new + 16 sibling
regression). Logs in `tool-outputs/pytest.log`, `tool-outputs/ruff-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 dir; severity none
Size (PH-02):         lines_added 216, removed 0, total 216; files_changed 2; severity none
Safety (PH-03):       migrations 0, schema/idl 0, infra 0, secrets 0; severity none
Completeness (PH-04): new_source_without_test 0 (behaviour added to existing module ships with new 16-test file); severity none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The functions are added as siblings of `is_visual_contract_wp` /
`visual_contract_signed_off`; no neighbour symbol was modified.

### Watch List

- The two new symbols (`is_interaction_contract_wp`,
  `interaction_flow_exercised`) are exported but not yet **called** by any
  enforcer. This is **not** dead surface — the WP Contract explicitly scopes
  enforcement wiring to WP-002 ("This is a pure predicate — no enforcement
  wiring"). WP-001 `blocks` WP-002 in the INDEX. The symbols are exercised by
  the 16 unit tests. No action.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none present under `.security/interaction-flow-gate/`
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Command: `ruff check` on both changed files. Base: 2 E402 (pre-existing). Head: 2 E402 (same). PR-introduced: 0. Plus `pytest` 32 passed. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified by diff size: 73 lines of logic + 143 lines of new tests across 2 files (≤5-file carve-out; the line count is dominated by self-contained new test code with no interleaved logic).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (`_wpxlib.py` new region 73 lines; test file 143 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings raised; the one Watch List note cites the WP Contract + INDEX `blocks` edge as evidence.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses emitted output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no new imports/singletons/cycles; checked diff for domain→infra imports). Security: nothing surfaced (primitives checked: SEC secret-exposure, injection, external-call surface; no secrets/network/subprocess/eval; pure frontmatter check). Quality: CR-01 follow-up (0), CR-10 perf scan (no anti-pattern matches — `fm.get()` scalar reads only, no loops/IO/N+1), dead-surface (none; forward-use documented), contract-drift (none), test-coverage (16 tests cover all branches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (216 lines / 2 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (tests shipped). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/gate-interaction-flow-gate...HEAD` (local; staged + new file)
- **Neighbour expansion:** git grep — sibling visual-gate functions inspected; no neighbour symbol modified
- **Neighbour cap:** not reached (0 neighbours modified)
- **Scanners run:** ruff (lint), pytest (proof). Gitleaks/Semgrep/Trivy not run — manual secret/injection scan over a 73-line pure-predicate diff with no secret-shaped strings, no network, no subprocess (coverage gap recorded: automated scanners unavailable in worktree; diff surface is trivially non-attackable).
- **Lenses dispatched in parallel:** no — single-reader carve-out per CR-02
