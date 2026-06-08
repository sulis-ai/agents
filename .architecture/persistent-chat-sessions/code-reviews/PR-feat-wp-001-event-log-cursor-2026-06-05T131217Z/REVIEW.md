# Code Review: WP-001 — Append-only offset-addressed per-session event log + cursor read

> **Timestamp:** 2026-06-05T131217Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-event-log-cursor → change/refactor-persistent-chat-sessions
> **Files changed:** 4 (3 new source + 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the foundation piece for persistent chat sessions: a per-session log that records every event in order and lets readers follow along live, catch up after a disconnect, or replay the whole history — all through one read mechanism. It is brand-new, self-contained code with no callers yet, and it ships with a thorough set of tests that exercise the tricky parts (two threads, live following, eviction) for real rather than faking them.

One performance issue was found and fixed during review: the live-follow path originally re-scanned the entire log on every new event, which would have slowed down on long conversations. It now jumps straight to the right spot. No other issues.

## What to fix

No issues that need attention. The one finding (a slow re-scan on the live-follow path) was fixed inline during the review and verified — see "Things to take away" for the detail.

## How this pull request is shaped

**Size — clean.** 603 lines across 4 files: three small source files and their test. One cohesive new module.

**Scope — clean.** A single concern (the event log), one Conventional Commit type.

**Safety — clean.** No database migrations, no schema/IDL changes, no infrastructure files, no secrets. Pure in-memory data structure using only the Python standard library.

**Completeness — clean.** 15 tests cover every behaviour, including the threaded live-tail, multi-viewer, eviction, and the close-releases-followers path. Coverage on the new code is 100%.

## Things to take away

1. **The live-follow path is the one spot worth keeping an eye on as this grows.** The original version was correct but re-read the whole log each time a new event arrived. On a short turn that's invisible; on a long-running session it would compound. The fix was to use the fact that the log's positions are contiguous, so the code can compute exactly where to start reading instead of scanning. Same idea applies anywhere you find yourself filtering a growing list on every tick — there's usually a direct index you can compute instead.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files read end-to-end (authored); all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — mypy/ruff/compileall all clean on HEAD).
- **PR Hygiene:** 0 findings (PH-01..04 all clean).
- **In the changes:** 1 finding (0 critical, 0 high, 1 medium — **resolved inline**), 0 remaining.
- **In the neighbours:** 0 (no neighbours — the module is wave-1; nothing imports it yet).
- **Draft fixes:** 0 (the single finding was fixed inline, not deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Dependency direction confirmed inward (MEA-01); no provider/process imports. |
| Security | 0 | 0 | Nothing surfaced — pure stdlib in-memory structure, no secrets/network/subprocess. |
| Quality | 1 (resolved) | 0 | CR-10 scan-heavy filter on `follow` path — fixed inline (`_slice_from`, O(k)). |

### Build Verification (CR-01)

No PR-introduced errors. Tool outputs in `tool-outputs/`:
- `mypy _session_manager/` → `Success: no issues found in 3 source files`.
- `ruff check _session_manager/ tests/unit/test_session_event_log.py` → `All checks passed!`.
- `python3 -m compileall -q _session_manager/` → OK (the branch-ci.yml gate).

Base run not separately diffed: the changed files are all newly-added, so every line is PR-introduced; running the checks on HEAD with a clean result is sufficient (no pre-existing errors to subtract).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts) → clean
  severity: clean

Size (PH-02):
  lines_added: 603 (3 source: 38+61+196=295; 1 test: 308), lines_removed: 0
  files_changed: 4
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: clean (cohesive single new module; under the spirit of PH-02
            despite >200 raw lines — see CR-02 note in Methodology)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (every source file is exercised by the test file)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

#### `plugins/sulis/scripts/_session_manager/event_log.py:153, 177` — medium (quality / CR-10) — RESOLVED INLINE

**Pattern:** CR-10 #10 — scan-heavy filter over a growing collection on a hot path.

**Quoted text (before fix):**
```python
snapshot = [ev for ev in self._events if ev.offset >= since]      # _read_history
ready = [ev for ev in self._events if ev.offset >= cursor]        # _read_follow loop body
```

**Why it matters:** `_read_follow` re-enters its `while True` loop on every append (woken by the condition variable). Each iteration filtered the *entire* retained deque to find events at/after the cursor — O(n) per append, O(n²) over a turn for a long-lived follower. The contract's default retention is "the whole live session" (INDEX decided-by-default), so `n` grows unbounded within a session; the hot path is exactly the live-tail case the capability exists to serve.

**Fix applied:** Extracted `_slice_from(offset)` (used by both read paths — a real 2-consumer extraction). Offsets are contiguous within the retained window, so the deque start index is `offset - oldest_offset` directly; `itertools.islice(self._events, start, None)` returns the tail in O(k) (k = events yielded). The steady-state follower's cursor sits near the end, so each wake is O(events-since-last-wake), not O(log-length).

**Verification:** 15 tests still pass; coverage on `event_log.py` 100%; mypy/ruff clean; full unit suite 1836 passed / 9 skipped. The dead `start < 0` clamp introduced with the first cut was removed (every caller runs `_check_not_evicted` first, guaranteeing `start >= 0`) — documented as a precondition, keeping the code free of unreachable branches (EP-08).

**Iterations:** 1 (within the 3-iteration inline-fix budget).

### Findings in the Neighbours

None. The module is wave-1 foundation code; no existing file imports `_session_manager`. (WP-004 will be the first consumer.)

### Watch List

- **`Event` type provenance (WP-002 ownership).** `events.py` is owned by WP-002 (parallel peer, unmerged at authoring time). WP-001 defines `Event` here against the locked contract §2.3 shape per its own Notes. On WP-002 merge, the two definitions must reconcile (WP-002 narrows the `Any | None` payload fields to `ToolUse`/`TurnResult`/`EventError`). Not a defect in this PR — a documented integration point. No failing test to ground a delta; tracked here per CR-04.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** mypy + ruff check + compileall on HEAD. 0 errors. All changed files are new, so HEAD-clean == no PR-introduced errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Diff is 603 lines but is one cohesive new module (3 source + its test) with zero neighbours; the executor authored every line in this same session and re-read each end-to-end. The carve-out's intent (breadth coverage of unfamiliar code) does not apply to a single self-authored module with no integration surface. Recorded per CR-02.
- [✓] **CR-03 Full-file reads.** All 4 files read end-to-end (authored + re-reviewed). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line and quoted text. The Watch-List item is grounded (no delta, per CR-04).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 1 medium (resolved), 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; every lens produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings (dependency-direction confirmed inward; no singletons; no infra imports). Security: nothing surfaced — primitives SEC-01..07 N/A (no auth/injection/network surface), SC-01..04 N/A (stdlib-only, no new deps); scanners: secret-pattern grep (0 hits), subprocess/eval/network grep (0 hits). Quality: CR-01 follow-up (clean), no JSX (Python), dead-surface (none), contract-drift (none — types match §2.3), test-coverage (15 tests, 100%), CR-10 perf (1 finding, fixed).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single feat, 1 dir). PH-02 Size: clean-in-spirit (603 lines, cohesive module). PH-03 Safety: clean (0 migrations/schemas/secrets/infra). PH-04 Completeness: clean (every source file tested). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/refactor-persistent-chat-sessions` (working tree; pre-commit — Step 7 commits).
- **Neighbour expansion:** none required (no importers of the new package).
- **Neighbour cap:** n/a.
- **Scanners run:** grep-based secret scan, subprocess/eval/network scan, CR-10 pattern scan; mypy; ruff.
- **Scanners unavailable:** gitleaks / semgrep / trivy not installed locally — coverage gap accepted given the surface is stdlib-only in-memory code with no secrets, dependencies, or external calls.
- **Lenses dispatched in parallel:** no (single-reader per CR-02 note above).
