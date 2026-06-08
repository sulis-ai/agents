---
id: WP-001
title: Append-only offset-addressed per-session event log + cursor read
kind: backend
primitive: EXPAND-Create
group: expand
status: ready
dependsOn: []
estimated_token_cost: { input: ~12k, output: ~10k }
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_session_event_log.py"
---

## Context

Contract §2.5 (log/cursor semantics) and §2.1 (session = ordered, offset-addressed,
append-only event log). This is the **Form spine** of the whole capability — the
single mechanism that lets one `read()` serve live-tail, reconnect catch-up,
multi-viewer, and history (contract §2.2 decoupling invariant). Everything else
(manager, adapter, lifecycle) reads from or appends to this.

Module: `plugins/sulis/scripts/_session_manager/event_log.py`.

## Contract

A per-session `EventLog` (no provider knowledge, no process knowledge — pure
data + cursor logic):

```python
class EventLog:
    def append(self, event: Event) -> int:
        """Append; assign the next monotonic offset (starts at 0); return it."""

    def read(self, since: int = 0, follow: bool = False) -> Iterator[Event]:
        """Yield events with offset >= since, in order.
        follow=False: yield what is present now, then stop (history).
        follow=True : yield from `since`, then block-yield new appends live
                      until the log is closed.
        since > current max under follow=True: wait for it (forward ref, §2.5).
        since > current max under follow=False: Expected error.
        since < oldest retained offset: Expected OFFSET_EVICTED (§2.5)."""

    def next_offset(self) -> int:
        """The offset the NEXT appended event will receive (the forward bookmark
        send() returns, §2.2)."""

    def close(self) -> None:
        """Release any follow() waiters cleanly (StopIteration)."""
```

Concurrency: appends and `read(follow=True)` happen on **different threads**
(the stdout pump appends; readers follow). The log MUST be thread-safe and a
follower MUST be woken on append (condition variable / queue fan-out), never
busy-poll. Retention default = unbounded for the live session (decided-by-default);
the cap is configurable and, when exceeded, evicts oldest and serves
`OFFSET_EVICTED` to readers whose `since` predates the oldest retained offset.

## Definition of Done

### Red (failing tests first)
- `test_append_returns_monotonic_offsets` — offsets 0,1,2… stable, unique.
- `test_next_offset_is_forward_reference` — `next_offset()` equals the offset the
  next `append` returns; holds across concurrent appends.
- `test_read_history_then_stops` — `read(since=0, follow=False)` yields all present, raises StopIteration.
- `test_read_since_offset_history` — `read(since=N)` skips < N.
- `test_read_follow_yields_live_appends` — start `read(follow=True)` on a thread, append after, follower receives in order (proves §2.5 live tail).
- `test_read_follow_from_future_offset_waits` — `read(since=max+1, follow=True)` blocks then yields when the offset materialises (forward-ref bookmark).
- `test_read_history_past_max_is_expected_error` — `read(since=max+1, follow=False)` raises Expected.
- `test_two_followers_independent_cursors` — two `read(follow=True)` from different `since` both get the full tail, no interference (proves §2.5 multi-viewer).
- `test_offset_evicted_when_since_predates_cap` — with a forced small cap, a reader whose `since` is evicted gets `OFFSET_EVICTED` Expected error (proves retention + §2.5).
- `test_close_releases_followers` — `close()` ends all live `read(follow=True)` iterators without hang.

### Green
- Implement `EventLog` with a lock + condition variable; followers register and
  are notified on append. Boring, explicit, no metaclass magic (boring-code).
- Eviction by configurable cap (count or bytes); default cap = unbounded.

### Blue (refactor)
- Extract the follower-notification primitive if a second waiter pattern appears
  later (it will, in the manager) — but only if duplication is real now; else note for WP-004.
- Confirm no `Event` type leakage forces `event_log.py` to import provider code
  (it imports only WP-002 types). Dependency points inward (MEA-01).

## Notes
- This is the AE "stdout_queue" idea generalised into an addressable, replayable
  log (ADR-001: AE had queues, no log — this is the adaptation, with tests).
- `Event` comes from WP-002; if WP-002 isn't merged yet, define against its locked
  shape (contract §2.3) and integrate on merge.
