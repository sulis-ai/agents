---
id: WP-004
title: SessionManager six-method surface + warm process + one-in-flight queue
kind: backend
primitive: EXPAND-Create
group: expand
status: ready
dependsOn: [WP-001, WP-002, WP-003]
estimated_token_cost: { input: ~20k, output: ~16k }
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_session_manager_core.py"
---

## Context

Contract §2.2 (the six-method surface), §2.6 (one-in-flight per key). This is the
core that composes the log (WP-001), the types (WP-002), and the adapter (WP-003)
into the consumer-facing capability. It owns: the keyed session registry, the
warm subprocess + its stdin/stdout/stderr pump threads (adapted from AE
`terminal_pool.py` I/O threads), and the per-key one-in-flight FIFO queue.

Lifecycle/recovery (WP-005), eviction (WP-006), and guards (WP-007) layer ON
this — keep this WP to the happy-path surface + concurrency so they stay separable.

Module: `plugins/sulis/scripts/_session_manager/manager.py` (the `SessionManager`),
plus `_session_manager/session.py` (one warm `Session`: process handle + pumps +
log + queue). `__init__.py` re-exports `SessionManager`, `SessionSpec`, `Session`,
the event types, and `ProviderAdapter`.

## Contract

The six methods exactly per §2.2 (signatures + semantics):

```python
class SessionManager:
    def __init__(self, adapters: dict[str, ProviderAdapter], **tuning): ...
    def open(self, key: str, spec: SessionSpec) -> Session            # get-or-spawn, idempotent
    def send(self, key: str, command: str) -> int                     # submit only; returns landing offset; never blocks on reply
    def read(self, key: str, since: int = 0, follow: bool = False) -> Iterator[Event]   # delegates to the key's EventLog
    def health(self, key: str) -> Health                              # {alive, state, pid, provider}
    def status(self) -> list[SessionStatus]                           # snapshot of all sessions
    def close(self, key: str) -> None                                 # terminate + release; idempotent
```

`Session` holds: `key`, `spec`, the `EventLog`, the subprocess + three pump
threads, the per-key in-flight lock + FIFO queue, `resumed: bool`, `turn` counter.

**Decoupling invariant (§2.2, load-bearing):** `send` returns
`log.next_offset()` for the landing turn and enqueues; it does NOT wait for any
event. `read` is the only content path. A queued `send` returns its eventual
landing offset (forward ref via WP-001's `next_offset` semantics).

**One-in-flight per key (§2.6):** a `send` while a turn runs is queued FIFO; the
slot frees when `adapter.turn_complete(event)` is true for an in-flight event,
then the next queued command is written to stdin. Different keys run in parallel
(separate Sessions, separate locks).

`Health` / `SessionStatus` are small frozen dataclasses (add to WP-002's events
module or a `_session_manager/state.py`; pick one and note it).

**Liveness primitive — owned here (load-bearing for the parallel Armor wave):**
this WP owns and exposes `is_alive(session) -> bool`, the single liveness check
(`process.poll()` / signal-0 style). It is the basis for both `health(key)`
(which reports `alive`) and `status()` (which snapshots every session's
liveness), so it is intrinsically a WP-004 concern — not a shared primitive
discovered later. `is_alive` is part of WP-004's public surface and is consumed
unchanged by WP-005 (restart-on-death detection) and WP-006 (dead-process
detection in the maintenance tick). There is no separate liveness WP.

## Definition of Done

### Red (failing tests first)
Drive against a **fake adapter** that spawns a tiny scripted child process (a real
subprocess emitting recorded NDJSON on a delay) — NOT a mocked manager. The
manager's own threading/queue/log behaviour is exercised for real (MEA-09: real
adapter + real child, recorded output).
- `test_open_get_or_spawn_idempotent` — second `open` on a live key returns the same Session, spawns nothing.
- `test_open_unknown_provider_expected_error` — `UNKNOWN_PROVIDER`.
- `test_open_cwd_not_found_expected_error` — `CWD_NOT_FOUND`.
- `test_send_returns_landing_offset_immediately` — `send` returns before any event arrives; the offset equals where the first event lands.
- `test_send_then_read_follow_streams_turn` — `off=send(); read(since=off, follow=True)` yields chunk* then result (the request/response composition, §2.2).
- `test_read_no_session_expected_error` — `NO_SESSION`.
- `test_one_in_flight_queues_second_send` — two `send`s back-to-back; second runs only after first's `result`; both landing offsets correct (proves §2.6 queue).
- `test_different_keys_run_in_parallel` — two keys, two turns overlap in wall-clock (proves §2.6 per-key, not global).
- `test_read_never_blocked_by_send` — a follower reads while a turn runs; not serialised behind the in-flight lock.
- `test_health_reflects_pid_and_alive` — `health` returns alive/pid/provider for a live session; `NO_SESSION` for unknown.
- `test_status_snapshots_all_sessions` — `status()` lists every open key with memory/last_activity/log_len fields.
- `test_close_terminates_and_is_idempotent` — `close` ends pumps + child; second `close` is a no-op; closing unknown key is a no-op.

### Green
- Implement the registry, the warm `Session` with three pump threads (stdin
  writer drains the queue; stdout reader decodes via adapter + appends to log;
  stderr reader captures), the per-key in-flight lock. Adapt AE's
  `stdin_writer`/`stdout_reader`/`stderr_reader` thread shape — re-shaped to
  append decoded Events to the log.
- `close`: SIGTERM then SIGKILL (§2.2), join pumps, `log.close()`.
- Boring code: explicit thread objects, explicit `queue.Queue`, no async magic
  unless the repo's other foundation modules use asyncio (they don't — threads).

### Blue (refactor)
- If the follower-notification primitive from WP-001 and the queue-drain here are
  the same wait/notify shape, extract once (the WP-001 Blue note flagged this).
- Confirm `manager.py` imports the adapter only via the Protocol, never a concrete
  adapter (adapters injected via constructor dict). Dependency inward (MEA-01).
- Leave clean seams for WP-005/006/007 to attach: a `_on_process_death(session)`
  hook, a `_maintenance_tick()` hook, a per-turn `_guard` hook — define them as
  no-op extension points here so the Armor WPs fill them without editing core flow.
- `is_alive(session)` is implemented here (backing `health`/`status`) and exported
  for WP-005/006 to consume directly — neither re-implements it.

## Notes
- Defining the three extension-point hooks here is what keeps WP-005/006/007
  parallelisable and conflict-free (each fills one hook in its own module).
- Tuning kwargs (idle timeout, memory cap) are accepted in `__init__` but unused
  until WP-005/006 — accept and store them now to avoid signature churn.
