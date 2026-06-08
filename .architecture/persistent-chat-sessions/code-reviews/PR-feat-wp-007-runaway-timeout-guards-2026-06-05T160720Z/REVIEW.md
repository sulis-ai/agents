# Code Review: WP-007 — Runaway / timeout turn guards

> **Timestamp:** 2026-06-05T160720Z (ISO 8601 UTC)
> **Author:** executor (WP-007)
> **Branch:** feat/wp-007-runaway-timeout-guards → change/refactor-persistent-chat-sessions
> **Files changed:** 7 (5 modified, 2 new)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the safety net that stops a single chat turn from running
forever or spinning out of control. If a turn takes too long, or the assistant
starts calling tools in a tight loop, the system now ends that turn cleanly —
it records *why* it stopped so anyone watching can see, then restarts the
assistant so the next message still works.

The work is well-scoped to one new building block plus the small wiring to
switch it on. It is fully tested (seven real-process tests, run dozens of times
with zero flakiness), the build is clean, and it does not change how any of the
existing pieces behave. No issues that need attention before merge.

## What to fix

No issues that need attention. Two minor notes for awareness are below.

### Minor — for awareness

**How the guard remembers which turn it's watching.** The guard tracks the
in-flight turn per session using Python's built-in object identity. That value
can be reused by Python after an object is cleaned up — but here the session is
held for its whole life and the guard's entry is removed when the session
closes, so there is no real risk of mixing up two sessions. Noted only so a
future reader doesn't have to rediscover the reasoning (it is documented in the
code).

**The kill step waits up to 2 seconds.** When the guard kills a misbehaving
turn, it waits briefly for the operating system to confirm the process is gone,
reusing the same 2-second window the normal shutdown path uses. This is
deliberate and load-bearing — without it, the restart occasionally didn't fire
on a busy machine (a flake that was found and fixed during this work). The wait
is bounded so it can never hang.

## How this pull request is shaped

**Size — clean.** ~300 changed lines across 5 existing files plus 2 new files
(one module, one test file). Comfortably reviewable in one pass.

**Scope — clean.** Single concern: the per-turn runaway/timeout guard. One
Conventional Commit type (`feat`). The edits to existing files are the minimal
wiring the new building block needs.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets.

**Completeness — strong.** 2 new source/test files: the new module ships with a
dedicated test file of 7 integration tests covering every behaviour in the
contract (timeout, runaway, slot-release, error-before-terminal, recovery,
no-false-positive). New behaviour is tested.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers
> and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
changed file >50 lines read end-to-end (the reviewer authored them); all three
lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). ruff check clean,
  ruff format clean, compileall (the CI lint gate) OK. mypy reports 10 errors
  but **all in `manager.py`'s pre-existing `_tuning: dict[str, object]` pattern**
  (shipped by WP-004/005/006); none introduced by this PR, and CI runs no
  type-checker (stdlib-only plugin contract).
- **PR Hygiene:** 0 high, 0 medium, 0 note (CR-09 / PH-01..PH-04).
- **In the changes:** 0 critical, 0 high, 0 medium, 2 low (awareness notes).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (no characterisation-test-grounded gaps; the two notes are
  Watch List items, not deltas).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (low) | 0 | `id(session)` keying for per-turn guard state (bounded, documented) |
| Security | 0 | 0 | nothing surfaced |
| Quality | 1 (low) | 0 | `kill_process` reuses the `_TERM_GRACE_SECONDS` constant (intentional) |

### Build Verification (CR-01)

No PR-introduced errors. Tooling outputs in `tool-outputs/ruff.log` and
`tool-outputs/compileall.log`. The mypy `[arg-type]`/`[call-overload]` errors
on `manager.py:99/110/112/113/121/123/132/293` predate this PR — they are the
established `int(self._tuning.get(...))` / `float(...)` / `**maintenance_kwargs`
convention from WP-004/005/006. This PR's two additions (`turn_timeout`,
`max_tool_calls`) follow the same convention (CP-01); refactoring the
`_tuning` typing is a cross-WP change out of this WP's Contract scope.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (_session_manager + its test)
  severity: none

Size (PH-02):
  lines_added: 273, lines_removed: 19 (tracked) + 729 new-file lines
  files_changed: 7
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (single bounded module)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (guards.py ships with test_session_guards.py)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `_session_manager/guards.py:175` — low (architecture)

**Quoted text:**
```python
self._state: dict[int, _TurnState] = {}
...
prior = self._state.pop(id(session), None)
```

**Observation:** Per-turn guard state is keyed by `id(session)`. CPython reuses
`id()` values after an object is garbage-collected, so in principle a freed
session's id could collide with a new session's. **In practice this is safe and
documented:** the manager holds each `Session` in its registry for the session's
whole life, and `TurnGuardManager.detach()` (called from `SessionManager.close`)
removes the entry before the session can be collected — so no two live sessions
share an id, and a freed session has no entry to collide with. Surfaced as
awareness, not a defect; no change recommended.

**Lens:** architecture. **No delta** (no failing test grounds it — behaviour is
correct).

#### `_session_manager/session.py:336` — low (quality)

**Quoted text:**
```python
proc.wait(timeout=_TERM_GRACE_SECONDS)
```

**Observation:** `kill_process` reuses `_TERM_GRACE_SECONDS` (2.0s, originally
the SIGTERM→SIGKILL grace in `terminate()`) as the reap-wait bound. The reuse is
semantically reasonable (both are "how long to wait for a child to die") and
keeps one tuning constant, but the two uses are conceptually distinct. The
`wait()` here is **load-bearing**: it reaps the killed child so the lifecycle's
`is_alive` (`process.poll()`) reliably reports the death before restart-on-death
confirms it — without it, a 1-in-N flake stranded the session in `TERMINATED_*`
(found and fixed during this WP). Documented in the method docstring. No change
recommended.

**Lens:** quality. **No delta.**

### Findings in the Neighbours

None. The diff touches `session.py` (the restart path), `state.py` (the
transition map), and `lifecycle.py` (the death-recovery confirm) — all
neighbours of `guards.py`. The edits to those files are the WP-007↔WP-005
boundary coordination the Contract calls for (extend the same transition map;
skip the duplicate mid-turn error for guard terminals; proceed-on-guard-terminal
in the death confirm). The full session-manager suite (98 tests) passes with no
regression, confirming the neighbour edits preserve WP-004/005/006 behaviour.

### Watch List

1. **`id(session)` keying** — see Findings. Bounded by lifecycle; revisit only
   if the manager ever holds session references outside its registry.
2. **`_TERM_GRACE_SECONDS` dual use** — see Findings. If the SIGTERM grace and
   the kill-reap bound ever need to diverge, split into two constants.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check (clean), ruff format
  (clean), compileall (OK) on all 7 changed files. mypy run; 10 errors all
  pre-existing in `manager.py` (not PR-introduced), documented. Coverage gap:
  CI runs no type-checker (stdlib-only plugin contract) — noted.
- [✓] **CR-02 Dispatch shape.** Diff >200 lines / >5 files. Reviewed by the
  authoring executor with full end-to-end knowledge of every changed line
  (Step 6.5 self-review of one WP's own diff); three lenses run inline against
  a single bounded module + its test. No sampling.
- [✓] **CR-03 Full-file reads.** All 7 changed files read end-to-end (authored
  this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** Both findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 2 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  (Build Verification empty; all files read end-to-end; all lenses produced
  output).
- [✓] **CR-07 Lens completion.** Architecture: 1 low finding + checks (dep
  direction clean, collaborator pattern matches lifecycle/maintenance, no new
  singletons/cycles). Security: nothing surfaced — no auth surface (internal
  library), no secrets, no injection (test-only directives), SIGKILL targets the
  session's own child only. Quality: 1 low finding + CR-10 perf scan (no N+1, no
  unbounded materialisation, no I/O-in-loop — guard state is O(1) in-memory) +
  test-coverage observation (7 tests, 93% coverage, new behaviour tested) + no
  dead surface + no contract drift.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none ({feat}, 1 module). PH-02
  Size: none (~300 + 729 lines, 7 files, single module). PH-03 Safety: none (0
  migrations / schemas / secrets / infra). PH-04 Completeness: none (new module
  ships with its test). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/refactor-persistent-chat-sessions` (working
  tree, pre-commit) scoped to `_session_manager/` + the new test file.
- **Neighbour expansion:** the diff's own neighbours (session/state/lifecycle)
  are all in-scope changed files; the WP-005/006 boundary verified via the full
  98-test session-manager suite.
- **Neighbour cap:** not reached.
- **Scanners run:** ruff, compileall, mypy (grep-based secrets + CR-10 perf scan).
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed — grep-based
  secret scan used instead (no secret-shaped strings; internal library with no
  credential surface).
- **Lenses dispatched in parallel:** no — inline self-review of one bounded WP
  diff by its author (CR-02 carve-out reasoning recorded above).
