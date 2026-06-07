---
id: WP-006
title: Idle-eviction + LRU memory-cap + dead-process detection
kind: backend
primitive: EXPAND-Create
group: expand
status: ready
dependsOn: [WP-004]
estimated_token_cost: { input: ~14k, output: ~11k }
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/integration/test_session_eviction.py"
---

## Context

Contract §2.7 (idle-eviction, memory cap with LRU, dead-process detection). The
**Armor** primitive for resource bounds: warm sessions cost RAM, so the manager
caps how many it holds and reaps idle ones. Adapted from AE `terminal_pool.py`
`perform_maintenance` loop + idle-eviction + dead-process detection (ADR-001).

Decided-by-default tuning (Working Set 2026-06-05T12:24:53Z): **memory cap
derived from host RAM with a conservative floor** — not founder-facing.

Module: `plugins/sulis/scripts/_session_manager/maintenance.py`, attaching to the
`_maintenance_tick` hook WP-004 exposes (runs on a background timer thread).

## Contract

- **idle-eviction:** a session with no activity past a configurable idle timeout
  is `close()`d and its process released (AE `perform_maintenance`).
- **memory-cap LRU:** total warm sessions are bounded by a memory limit (default
  derived from host RAM, e.g. a fraction of available, with a conservative
  floor of N sessions). When a new `open` would exceed the cap, the
  least-recently-used session is evicted first. `last_activity` (updated on
  send/read) is the LRU key.
- **dead-process detection:** the maintenance tick calls WP-004's
  `is_alive(session)` liveness primitive and, on detecting an unexpected death,
  fires WP-004's `_on_process_death` (which WP-005 handles). This WP owns the
  *maintenance tick / scheduling of detection*; liveness itself (`is_alive`) is
  owned and exposed by WP-004; recovery is owned by WP-005. This WP consumes
  `is_alive`; it does not re-implement the poll.
- Eviction is graceful: SIGTERM→SIGKILL, log closed, registry entry removed.
  An evicted key's next `open` is a fresh spawn (or resume, if capable + ref).

## Definition of Done

### Red (failing tests first)
Real child processes; drive the maintenance tick synchronously in tests (inject a
manual clock / call `_maintenance_tick()` directly) so timing is deterministic —
no `sleep`-based flakiness.
- `test_idle_session_evicted_after_timeout` — a session idle past the timeout is closed by the tick; its process is gone (`health` → NO_SESSION).
- `test_active_session_not_evicted` — recent activity resets the idle clock; not evicted.
- `test_memory_cap_evicts_lru_first` — fill to cap, `open` one more → the least-recently-used is evicted, not a random or newest one (assert by last_activity ordering).
- `test_lru_order_updated_on_send_and_read` — `send`/`read` bump `last_activity` so a busy old session survives over an idle newer one.
- `test_cap_default_derives_from_host_ram_with_floor` — with a tiny simulated RAM, the cap clamps to the conservative floor (not zero).
- `test_dead_process_detected_by_tick` — kill a child; the next tick detects it and fires `_on_process_death` (assert the hook is called; recovery itself is WP-005's test).
- `test_eviction_is_graceful` — evicted session's log is closed, followers released, registry entry removed; no leaked threads.

### Green
- Implement the maintenance loop as a daemon timer thread calling
  `_maintenance_tick()`; expose the tick for direct test invocation.
- LRU via `last_activity` timestamps; cap default = `derive_cap(host_ram)` with a
  documented floor constant. Explicit, boring; no weakref/GC trickery.

### Blue (refactor)
- The maintenance tick consumes WP-004's `is_alive(session)` primitive for
  liveness — do not extract or re-implement it here; it already lives in WP-004
  (backing `health`/`status`) and WP-005 consumes the same one.
- Confirm `last_activity` updates live in WP-004's send/read (one line each) and
  this WP only *reads* them — don't fork the activity-tracking.

## Notes
- This is the resource-bound Armor that lets the foundation host many keys
  (the cockpit's many changes + the CLI's keys) on a founder laptop without OOM.
- `derive_cap` reads available RAM via `os`/`psutil` — prefer stdlib if a
  good-enough reading exists (avoid adding a dep for a tuning floor); justify in
  Green if `psutil` is pulled in.
