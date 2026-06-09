# Code Review: feat/wp-008-budget-accumulation — never-clearing retry now abandons at the wall-clock budget

> **Timestamp:** 2026-06-09T004643Z (ISO 8601 UTC)
> **Author:** executor (WP-008 budget-accumulation remediation)
> **Branch:** feat/wp-008-budget-accumulation → change/feat-automation-reliability-recovery
> **Files changed:** 5 (2 production, 3 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes a real reliability bug: a transient failure that never recovered would retry forever and never give up, even though there is supposed to be a roughly 12-minute time limit after which it abandons cleanly. The fix makes the recovery driver remember how long it has been retrying across each failure, so it now correctly stops at the time limit and reports a clean "gave up" message instead of hanging silently. The build is clean, the change is small and well-scoped, and it comes with tests at three levels (unit, wiring, and a full end-to-end test through the real machinery) — including turning a previously-skipped "known gap" test into one that genuinely passes. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

One minor point for awareness (not a blocker): in the retry code, after a backoff wait the code re-checks whether the retry sequence is still the one it started by comparing two timestamps for equality. That comparison is correct here, but a "has this been reset?" check reads a touch more clearly than comparing timestamps. It is a style preference, not a correctness problem — the logic is sound either way.

## How this pull request is shaped

**Size — clean.** 385 lines added, 109 removed across 5 files. Comfortably reviewable.

**Scope — clean.** Single concern: make the retry budget accumulate across the live (asynchronous) wiring so a never-clearing failure abandons at the time limit. The two production files changed are exactly the ones the fix needs (the recovery driver and the one line of manager wiring that tells it when a turn genuinely succeeded).

**Safety — clean.** No database migrations, no schema/IDL changes, no infrastructure files, no secrets. The change is pure in-process logic.

**Completeness — strong.** Tests accompany the change at every level: the driver's own unit tests were updated to the new model, the wiring tests gained a test for the new reset hook, and the end-to-end test's previously-skipped budget-exhaustion case now passes for real with no skip remaining.

## Things to take away

Not applicable — this is a focused, well-tested fix. Nothing to add.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty (no PR-introduced errors); all changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). ruff clean; the 12 mypy findings are pre-existing on BASE (the `_tuning.get(...) -> object` kwargs pattern), mypy is not a configured project gate (no config; ruff is the gate).
- **PR Hygiene:** 0 high, 0 medium findings (CR-09 / PH-01..PH-04 all clean/low).
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single low finding is awareness-only; no characterisation test would fail, so no delta per CR-04).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — the fix removes an unbounded-retry hang (Armor improvement); lock held only around state RMW, never across sleep/send (deadlock-safe) |
| Security | 0 | 0 | None — no new external calls, no secrets, no auth/injection surface; pure in-process state machine |
| Quality | 1 (low) | 0 | Float-equality re-check after backoff (correct but a None-check reads clearer) |

### Build Verification (CR-01)

No PR-introduced errors. ruff `check` passed on all 5 changed files and the whole `_session_manager` package. mypy emits 12 errors but all 12 are present identically on BASE (`_session_manager/manager.py` lines 139–201, 400 — the `**self._tuning` `object`-typed kwargs pattern that predates this WP); none is introduced by the diff, and mypy is not a configured gate in this repo. Build Verification section is therefore empty → PASS not blocked.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {fix}                    → clean (single type)
  module_fan_out: 1 top-level area (_session_manager + its tests)
  severity: low

Size (PH-02):
  lines_added: 385, lines_removed: 109, total: 494
  files_changed: 5
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: low (≤500 line band; ≤5 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (no new source files; modified files all have tests)
  api_change_without_schema: false
  test_changes: 3 test files updated, including an xfail→pass flip
  severity: none
```

### Findings in the Changes

#### `_session_manager/recovery.py:410` — low (quality)

**Quoted text:**
```python
with self._retry_lock:
    # Advance only if the sequence is still the one we were driving — a
    # racing clear could have reset it while we waited/sent.
    if self._retry_started_at == start:
        self._retry_attempt = attempt + 1
```

**Observation:** The post-send guard compares the current `_retry_started_at` against the `start` captured before the backoff wait, to skip the attempt-advance if a racing `note_turn_cleared` reset the sequence. The comparison is correct: a reset sets `_retry_started_at = None` (`None != start`), and a *new* sequence would stamp a fresh `self._clock()` value (different from `start` unless the clock is frozen — but a real monotonic clock advances, and the test fake advances on every sleep). The float-equality is therefore safe in practice.

**Why it's only low:** The behaviour is correct under both the real monotonic clock and the test's advancing fake clock. The note is purely about readability — an explicit "was the sequence reset?" predicate (e.g. tracking a monotonically-increasing sequence id) would express the intent without relying on timestamp identity. Not worth changing for a 2-line critical section with a clear comment.

**No delta:** No characterisation test would fail (the logic is correct), so per CR-04 this stays on the Watch List, not the delta queue.

### Findings in the Neighbours

None. The neighbour ring (the `Session.release_turn_for_retry` slot-release seam, the classifier, the `next_delay` policy, the `_on_error_event` fan-out) was read; the diff integrates with them through their existing public surface without exposing new gaps. `next_delay`/`next_delay_ceiling` are unchanged and already return `None` on budget exhaustion — the fix consumes that signal correctly.

### Watch List

- `_session_manager/recovery.py:410` float-equality sequence re-check (see Findings in the Changes — correct, readability-only).

### Cross-Reference

- No prior `.security/automation-reliability-recovery/` viability report exists.
- No existing hardening-deltas to cite or dedupe against.
- This change closes the SF-8bad33b8 known gap (the previously-`xfail` `test_budget_exhausted_abandon_known_gap`, now `test_budget_exhausted_abandon_at_wall_clock`, passing).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` (all 5 files + package — clean); `python3 -m mypy _session_manager/{recovery,manager}.py` (12 errors, all pre-existing on BASE, mypy not a gate); build verification via `pytest` recovery suite (29 passed). Delta: 0 PR-introduced errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass.** Diff is 494 lines / 5 files — above the 200-line threshold, but the production logic is two files I authored and read end-to-end; the three lenses were applied analytically in-session (no sub-agent dispatch available in the executor session). Recorded as a deviation: lens rigour preserved (each lens produced explicit output below), reads were full-file.
- [✓] **CR-03 Full-file reads.** Both production files (`recovery.py` changed region + surrounding class, `manager.py` `_on_error_event`) and all three test files read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line and quoted text.
- [✓] **CR-05 Severity rubric.** Applied: 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks run: domain/infra import direction, new singletons, circular imports, timeout/backoff/circuit-breaker, lock-deadlock analysis on the new critical section — the fix is a net Armor improvement). Security: nothing surfaced (primitives checked: SEC-01..07, SC-01..04 — no new external calls, no secrets, no auth/injection/SSRF surface; pure in-process state machine). Quality: 1 low finding + dead-surface scan (none) + contract-drift scan (the `send -> bool` ack now ignored, explicitly documented — not silent drift) + test-coverage observation (strong: unit + wiring + e2e, xfail→pass) + CR-10 performance scan (no anti-patterns; the fix *removes* an unbounded retry loop, making `_drive_retry` O(1) per observation).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single `fix`, one module area). PH-02 Size: low (494 lines / 5 files). PH-03 Safety: none (0 migrations / schemas / secrets / infra). PH-04 Completeness: none (no new source; tests updated incl. xfail→pass flip). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-automation-reliability-recovery` (working tree — changes uncommitted at review time, committed immediately after).
- **Neighbour expansion:** git grep / direct read of `Session.release_turn_for_retry`, `classifier.classify`, `next_delay`, `_on_error_event` fan-out.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** ruff (lint), mypy (type, advisory — not a gate).
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (no new dependency, secret, or infra surface in a pure in-process Python logic change — security lens reasoned from the diff content).
- **Lenses dispatched in parallel:** no (executor session; lenses applied analytically in-session with full-file reads — recorded as the CR-02 deviation above).
