---
id: WP-007
title: Runaway / timeout turn guards → terminal states + surfaced error events
kind: backend
primitive: EXPAND-Create
group: expand
status: ready
dependsOn: [WP-004, WP-005]
estimated_token_cost: { input: ~12k, output: ~10k }
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/integration/test_session_guards.py"
---

## Context

Contract §2.7 (runaway / timeout guards). The **Armor** primitive that bounds a
single turn: a turn exceeding its time budget → `TERMINATED_TIMEOUT`; runaway
tool-call behaviour → `TERMINATED_RUNAWAY`. Both surface an `error` Event into
the log first, then move to the terminal state (so a follower sees the failure).
Adapted from AE `claude_session.py` safety metrics / runaway monitoring (ADR-001).

Depends on WP-005 because it adds the `TERMINATED_*` transitions to the same
state-machine transition map (WP-005 Blue note); needs WP-004's per-turn `_guard`
hook.

Module: `plugins/sulis/scripts/_session_manager/guards.py`, attaching to WP-004's
per-turn `_guard` hook and WP-005's transition map.

## Contract

- **timeout guard:** each in-flight turn has a configurable budget. Exceeding it →
  surface `Event(kind="error", error=EventError("expected","TURN_TIMEOUT",...))`,
  release the in-flight slot, move session to `TERMINATED_TIMEOUT`. (Whether the
  session then auto-restarts is WP-005's recovery path — coordinate so a timeout
  is treated as a recoverable terminal, not a permanent disable, unless budget
  exhausted.)
- **runaway guard:** runaway tool-call behaviour (e.g. tool_use rate / count past
  a threshold within a turn) → `Event(kind="error", error=EventError(...,"RUNAWAY",...))`,
  release slot, `TERMINATED_RUNAWAY`.
- Both guards must **release the one-in-flight slot** (§2.6) so a queued send
  isn't wedged behind a killed turn.
- The error Event is appended to the log *before* the state transition, so a
  `read(follow=True)` observer sees `error` then the terminal effect.

## Definition of Done

### Red (failing tests first)
Real child process driven to misbehave on cue (a scripted child that hangs, or
emits tool_use in a tight loop). Deterministic budgets (small, injected), no
real-time flakiness.
- `test_turn_timeout_surfaces_error_then_terminal` — a turn that exceeds budget → `error` Event (`TURN_TIMEOUT`) then state `TERMINATED_TIMEOUT`.
- `test_timeout_releases_in_flight_slot` — after a timeout, a queued `send` runs (slot freed, §2.6 not wedged).
- `test_runaway_tool_calls_terminate` — child emits tool_use past the runaway threshold → `error` (`RUNAWAY`) then `TERMINATED_RUNAWAY`.
- `test_runaway_releases_slot` — queued send proceeds after runaway kill.
- `test_error_event_precedes_terminal_state` — the `error` Event's offset is appended before the session leaves EXECUTING (a follower sees error first).
- `test_normal_turn_under_budget_unaffected` — a fast, well-behaved turn never trips either guard (no false positives).
- `test_timeout_terminal_is_recoverable_not_disabled` — a single timeout doesn't permanently disable the session (it composes with WP-005 recovery within budget).

### Green
- Implement a per-turn watchdog (timer started when a turn enters EXECUTING,
  cancelled on `turn_complete`) and a per-turn tool_use counter. On trip: append
  error Event, release slot, transition. Add `TERMINATED_TIMEOUT`/`TERMINATED_RUNAWAY`
  to WP-005's transition map.
- Boring, explicit threading.Timer; thresholds are injected tuning values.

### Blue (refactor)
- Confirm the slot-release path is the *same* one `turn_complete` uses in WP-004
  (don't fork "free the slot" logic — one method, called by both completion and
  guard-trip).
- Confirm guards live behind the `_guard` hook so WP-004 core flow is untouched.

## Notes
- These are the §2.6/§2.7 safety metrics from AE, given tests for the first time.
- Coordinate budget semantics with WP-005: timeout → recoverable terminal;
  repeated timeouts within a turn-budget exhaust the recovery budget → DISABLED.
