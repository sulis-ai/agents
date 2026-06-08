# Code Review: feat/wp-002-event-vocabulary — Shared provider-neutral event vocabulary + three-category errors

> **Timestamp:** 2026-06-05T130903Z (ISO 8601 UTC)
> **Author:** WP-002 executor
> **Branch:** feat/wp-002-event-vocabulary → change/refactor-persistent-chat-sessions
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the small, shared set of "event types" the chat session system speaks — the four kinds of thing that can happen during a turn (a piece of text, a tool being used, a turn finishing, an error) plus the three kinds of error (a connection problem, an expected refusal, or an unexpected bug). It's a foundation piece: pure data definitions with no moving parts, no network, no database, no permissions to get wrong.

The code is clean. The build passes, the types check out, and the tests are thorough (every line is exercised). One small typing issue in the tests was found and fixed during review. Nothing else needs attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: 3 files, all brand new, all about one thing (the event types). Nothing mixed in.

**Scope — clean.** A single concern: define the shared vocabulary. No refactor, no unrelated changes.

**Safety — clean.** No database changes, no infrastructure, no secrets, no config.

**Completeness — clean.** The one new behaviour (rejecting malformed events at construction) ships with tests, and the tests cover every branch.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty (after the one inline fix during review); all files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors remaining (1 found during review, fixed inline — see below) (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings (1 medium fixed inline during the review pass)
- **In the neighbours:** 0 findings (no neighbours — module is dependency-free; consumers WP-001/WP-003 not yet landed)
- **Draft fixes:** 0 (the one issue was fixed inline, not deferred)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced (pure domain layer, zero infra imports) |
| Security | 0 | 0 | nothing surfaced (no I/O, no auth, no untrusted input) |
| Quality | 0 | 0 | one mypy union-attr in tests — fixed inline |

### Build Verification (CR-01)

Mechanical baseline run on HEAD: `ruff check`, `ruff format --check`, `mypy`.

One PR-introduced error was found during the baseline and **fixed inline during this review** (Step 6.5 Path A — inline fix, re-run clean):

#### `tests/unit/test_session_event_types.py:230-231` — medium (quality) — RESOLVED

**Error (before fix):** `error: Item "None" of "EventError | None" has no attribute "category"  [union-attr]` (and `.code` at 231).

**Cause:** the test dereferenced `ev.error.category` where `ev.error` is typed `EventError | None`; mypy cannot narrow the Optional without a guard.

**Fix applied:** inserted `assert ev.error is not None` before the dereference in both roundtrip tests. This narrows the type for mypy and strengthens the assertion (the test now also proves the payload is populated, not merely truthy).

**Post-fix baseline:** `mypy _session_manager/ tests/...` → `Success: no issues found in 3 source files`. `ruff check` → `All checks passed!`. `ruff format --check` → 3 files already formatted. Tests → 22 passed.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 2 dirs (_session_manager, tests/unit) → clean
  severity: none

Size (PH-02):
  lines_added: 478, lines_removed: 0, total: 478
  files_changed: 3
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (3 files; additive new module; ~250 of the lines are tests)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (events.py + __init__.py both covered by test_session_event_types.py)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None remaining. (One medium fixed inline — see Build Verification.)

### Findings in the Neighbours

None. The module is deliberately dependency-free (SESSION_MANAGER_CONTRACT §2.3 Form invariant): it imports nothing from the log or the manager. Its prospective consumers (WP-001 log, WP-003 adapter) have not yet landed, so there is no neighbour ring to expand into.

### Watch List

- **Factory classmethods (`Event.chunk(...)`).** The WP's Blue step conditionally adds named constructors *only when a second call site exists* (WP-003's `decode()`). Deferred correctly per the 2-consumer rule; revisit when WP-003 lands. Not a gap — a documented deferral.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this project
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`, `mypy` on `_session_manager/` + the test file. Base: n/a (all files new — no base version). Head: 1 mypy union-attr error in tests, fixed inline; post-fix clean. Coverage gap: none. (No `bandit`/`pip-audit` run — module is stdlib-only pure types with no dependency surface; recorded as a deliberate non-gap, not a coverage hole.)
- [✓] **CR-02 Single-reader pass.** Diff is 478 lines / 3 files. Above the 200-line threshold, but the substance is a single pure-types module + its test (≈250 lines are test assertions of value-object behaviour). Read every file end-to-end; no sampling. Recorded here per the carve-out note discipline.
- [✓] **CR-03 Full-file reads.** All 3 changed files (events.py 175 lines, __init__.py 69 lines, test 232 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line and the verbatim mypy error.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 1 medium (fixed inline), 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none (Build Verification empty after inline fix; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced. Checks run: domain/infra import-direction (none — zero imports beyond stdlib `dataclasses`/`typing`), singletons (none), circular imports (none), external calls / timeout / CB / secrets (n/a — no I/O). Security: nothing surfaced. Primitives checked: SEC-01..07 (no auth/injection/SSRF/secrets surface), SC-01..04 (no third-party deps), DAT-03 (no logging). No untrusted-input deserialization. Quality: 1 finding (fixed inline) + dead-surface (none — all `__all__` exports are the public vocabulary consumed downstream) + contract-drift (none — §2.9 code constants verified equal to the contract strings by `test_code_constant_values_match_contract`) + test-coverage observation (comprehensive: 22 tests, 100% line coverage on both source files) + CR-10 performance (no anti-pattern matches — no loops over collections, no DB/RPC/FS calls).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat` concern). PH-02 Size: none (3 files, additive). PH-03 Safety: none (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none (new source covered by tests). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** local git (staged new files vs `change/refactor-persistent-chat-sessions`)
- **Neighbour expansion:** n/a — dependency-free module; no callers/callees exist yet (consumers are future WPs)
- **Neighbour cap:** 0 of 0
- **Scanners run:** ruff, mypy
- **Scanners unavailable:** bandit / pip-audit not run (no dependency or I/O surface to scan — deliberate non-gap)
- **Lenses dispatched in parallel:** no (single-reader pass; carve-out justified above)
