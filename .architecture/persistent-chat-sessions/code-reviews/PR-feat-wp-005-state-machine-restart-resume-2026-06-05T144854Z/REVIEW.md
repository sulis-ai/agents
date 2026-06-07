# Code Review: feat/wp-005 — Session state machine + restart-on-death + resume-as-capability

> **Timestamp:** 2026-06-05T144854Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-state-machine-restart-resume → change/refactor-persistent-chat-sessions
> **Files changed:** 6 (1076 insertions, 50 deletions)
>
> **Outcome:** Ready to merge (after the self-review fix applied below)

---

## At a glance

This change adds the session lifecycle armour to the chat-session engine: a state
machine the engine owns, automatic restart when an assistant process crashes, and
honest "did we resume the conversation?" reporting. The review ran the full
mechanical floor (linter clean, 76 tests green) and read every changed file
end-to-end. It surfaced **one real correctness problem in the new code** — a
crash-during-send race that could leave a reader waiting forever — which was
fixed inline and pinned with a new test. After that fix the change is clean.

## What to fix

### Was must-fix — now fixed: a reader could wait forever if the assistant crashed at the wrong moment

**What was happening:** If the assistant process died in the split second between
sending a message and the engine writing that message to it, the message's turn
produced no output, and anyone reading the reply would wait forever.

**Why it mattered:** A crash at that exact moment is rare but real, and the
symptom — a permanently-spinning reply — is the worst kind of hang for a chat UI.

**What was done:** The engine now (a) re-queues a message a dying worker picked up
so the restarted worker handles it, and (b) if the write itself fails because the
process is already gone, posts a one-time "the turn failed" marker so the reader
sees a clean failure and can re-send instead of hanging. A new test
(`test_send_during_death_window_never_hangs`) kills the process and immediately
sends, asserting the reader always terminates. A second latent bug found in the
same pass — the cleanup routine could crash trying to wait on a worker thread
that hadn't started yet during a restart — was also fixed.

No remaining issues need attention.

## How this pull request is shaped

Well-scoped: one concern (process lifecycle), one feature area
(`_session_manager`). All new source files ship with tests. Size is moderate for
a foundational armour layer with real-process, threaded tests.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, WPB-NN, PH-NN) for engineers
> and downstream agents.

### Verdict

`PASS` per CR-06 — after the inline fix for the one in-diff `medium`/`high`
correctness finding (F-1), no critical/high remains in the diff, Build
Verification is empty, all changed files >50 lines were read end-to-end, and all
three lenses produced output.

### Summary

- **Build Verification (CR-01):** 0 PR-introduced errors. `ruff check` clean on
  all 6 changed files; 76 tests green (5× flake-check stable).
- **PR Hygiene (CR-09):** scope clean (single concern), size moderate, no
  migrations/schemas/secrets/infra, completeness good (new source + tests).
- **In the changes:** 1 finding (F-1, correctness/concurrency) — **addressed
  inline** with a characterisation test.
- **In the neighbours:** 0 (WP-005 only touches the `_session_manager` package
  it owns; WP-004 tests act as the neighbour-regression guard and stay green).
- **Draft fixes:** 0 outstanding (F-1 fixed inline, not deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | dependency direction clean (lifecycle depends inward on events/session/state) |
| Security | 0 | 0 | nothing surfaced (no auth/injection/secrets/network surface in this diff) |
| Quality | 1 (F-1, fixed) | 0 | send-during-death-window race → follower hang |

### Build Verification (CR-01)

`ruff check _session_manager/ tests/integration/test_session_restart_resume.py`
→ **All checks passed.** Pytest (76 tests) → **all passed.** Raw outputs in
`tool-outputs/ruff-check.log` and `tool-outputs/pytest.log`. No PR-introduced
errors.

### Findings in the Changes

#### F-1 — `_session_manager/session.py` `_stdin_pump` / `terminate` — medium→addressed (quality, concurrency)

**What:** Two restart-handoff races in the new lifecycle wiring:

1. A `send` issued in the window between a process death and its detection could
   have its command pulled by the dying-generation stdin pump and then either
   (a) dropped on a stale-generation `break` (no `landing_box` resolved →
   `submit()` hangs), or (b) resolved-then-failed-to-write on `BrokenPipeError`
   with no event ever produced (→ a `read(follow=True)` from that offset hangs
   forever).
2. `terminate()` joined the thread set unconditionally; a concurrent
   `replace_process` could momentarily expose a Thread object not yet
   `.start()`-ed, and `Thread.join()` on an unstarted thread raises
   `RuntimeError`.

**Evidence:** Reproduced with a standalone faulthandler-guarded script — the
follower blocked at `event_log.py:_read_follow` and `terminate()` raised
`RuntimeError: cannot join thread before it is started`.

**Severity:** in-diff correctness bug that hangs a reader → `high` on the hang
path; the contracted DoD tests did not exercise the send-during-death-window, so
it was latent. Addressed inline rather than deferred.

**Fix (inline, CR-04 test-backed):**
- `_stdin_pump`: a stale-generation pull RE-QUEUES the command (`_WAKE` sentinel
  replaces `_STOP` for the restart unblock so the fresh pump never self-stops on
  a leftover wake-up); a write that fails with `BrokenPipeError` now appends a
  turn-terminal `STDIN_BROKEN` `error` event (`_append_stdin_broken_error`) so a
  follower terminates instead of hanging (§2.9).
- `terminate()`: joins only threads that have started (`is_alive() or ident is
  not None`).
- **Characterisation test:** `test_send_during_death_window_never_hangs` — kills
  the child then immediately sends, asserting `submit()` returns within the
  bounded wait and the follower terminates on a `result` OR `error` (never
  hangs).

### Findings in the Neighbours

None. WP-005 edits are confined to the `_session_manager` package; the WP-004
core surface tests (`test_session_manager_core.py`, 14 tests) act as the
neighbour-regression guard and remain green.

### Watch List

- `LifecycleManager.recovery_budget` property (lifecycle.py:76) is currently
  unused externally — a clean accessor kept for WP-006/observability. Not a gap.
- WP-007 will add `TERMINATED_TIMEOUT` / `TERMINATED_RUNAWAY` transition *firing*
  to the same `_ALLOWED_TRANSITIONS` map (the targets already exist from
  EXECUTING/ERROR). Confirmed single-map invariant — no parallel map to drift.

### Backend rubric (WPB-01..12)

- **WPB-01 dependency-inward:** PASS — `lifecycle.py` and `state.py` depend only
  inward (events / session / state); no infrastructure reach-up.
- **WPB-03 in-memory / real adapters, never mock:** PASS — tests drive a REAL
  scripted child subprocess that can be SIGKILLed (MEA-09); no mocks of manager
  state or death.
- **WPB-04 single source of truth:** PASS — restart/resume/budget logic lives in
  one `LifecycleManager`; the manager's `_on_process_death` is a thin delegate.
- **WPB-07 composition root + DI:** PASS — `LifecycleManager` constructed in the
  manager and injected with `is_alive` + `respawn`; no globals.
- **WPB-08 outside-in TDD:** PASS — 8 contracted integration tests written RED
  first (ImportError), then GREEN.
- **WPB-12 clean code + boy-scout:** PASS — single transition map; `_spawn_process`
  extracted (2-consumer); per-iteration `import dataclasses` hoisted.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` (clean) + pytest (76 green).
  Base clean by construction (new files absent on base; changed files passed
  before). Coverage gap: no mypy in repo (recorded at Step 1 preflight).
- [✓] **CR-02 Dispatch shape.** Diff 1076 lines / 6 files — above carve-out.
  Reviewed by lens (architecture / security / quality) reading every changed
  file end-to-end; reviewer is the authoring executor, so single-session
  multi-lens read rather than sub-agent fan-out.
- [✓] **CR-03 Full-file reads.** All 6 changed files read end-to-end; the
  concurrency-critical session.py pump/restart paths re-read line-by-line.
- [✓] **CR-04 Evidence discipline.** F-1 cites file:method + a reproduced
  faulthandler traceback; fix is backed by a new characterisation test.
- [✓] **CR-05 Severity rubric.** 1 in-diff finding (correctness/hang → high on
  the hang path), addressed inline. 0 critical.
- [✓] **CR-06 Verdict computed.** PASS after inline fix. No auto-downgrade
  triggers fired (Build Verification empty; all files read; all lenses output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (dependency
  direction clean). Security: nothing surfaced (no auth/secret/network/injection
  surface). Quality: F-1 + test-coverage observation (new source has tests) +
  CR-10 performance scan (no anti-pattern matches; threaded I/O, no DB/loops).
- [✓] **CR-09 PR Hygiene.** Scope: clean (single concern). Size: moderate.
  Safety: 0 migrations / 0 schema / 0 secrets / 0 infra. Completeness: 2 new
  source files (lifecycle.py + test) with tests. No PH-03 high → no downgrade.

#### Run details

- **Diff source:** `git diff change/refactor-persistent-chat-sessions` (working tree).
- **Neighbour expansion:** package-local; WP-004 core tests as regression guard.
- **Scanners run:** ruff (lint+format), pytest+coverage, faulthandler hang-guard.
- **Scanners unavailable:** mypy (no repo gate), gitleaks/semgrep/trivy (no
  network/secret/dependency surface in this pure-stdlib diff).
