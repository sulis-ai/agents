# Data Contract — reliability-layer (classifier → recovery driver; recovery driver → log)

> **Tier:** Lightweight (internal seam) per CONTRACT_FIRST_STANDARD. One
> process, one language (Python), in-process library binding — **no
> ProtocolError on the seam itself** (CF-08: library transport). The
> contract is the **typed value objects** the producer (classifier) hands
> the consumer (recovery driver), and the **Event shape** the driver emits
> back into the existing log. Transport-agnostic; the binding is in-process
> Python calls.

This is a genuine producer/consumer seam (CF-01): the **classifier**
produces a `RecoveryClass` verdict that the **recovery driver** consumes to
decide retry / abandon / pause. Pinning it as a contract lets the two be
built and tested in parallel (CF-05) — the driver against a fake classifier,
the classifier against the `events.py` truth-table — and keeps the verdict
vocabulary from being re-spelled on either side (CF-11 spirit, one source).

## Operations (CF-02)

### `classify(error: EventError, adapter_hint: RecoveryClass | None) -> RecoveryClass`

Pure. Maps an observed `EventError` (from `events.py`, the existing frozen
type — referenced, not re-declared) to exactly one recovery class, using the
per-provider hint when present and the neutral category default otherwise
(ADR-003).

**Input types**

- `error: EventError` — `{category: "protocol"|"expected"|"internal",
  code: str, message: str}` (the existing `events.py` value object).
- `adapter_hint: RecoveryClass | None` — the provider's
  `classify_failure(error)` result (ADR-003); `None` means "defer to
  neutral default".

**Output type**

- `RecoveryClass` — enum, the shared neutral vocabulary:
  `TRANSIENT_BLIP` | `DEAD_END` | `LOGIN_EXPIRED`.

### `next_delay(attempt: int, elapsed_seconds: float, policy: RetryPolicy) -> float | None`

Pure. The backoff curve (ADR-002). Returns the jittered delay before the
next attempt, or **`None`** when the next attempt would exceed
`policy.total_budget_seconds` — the signal to reclassify `TRANSIENT_BLIP`
→ `DEAD_END` and abandon.

**Output:** `float` seconds (full jitter:
`random_between(0, min(max_delay, base * multiplier**attempt))`), or `None`
on budget exhaustion.

## The classification truth table (CF-04 — the stubs, incl. non-happy cases)

The contract's examples ARE the classifier's truth table. Provider-neutral
(no adapter hint):

| `error.category` | `error.code` | `adapter_hint` | → `RecoveryClass` | Rationale |
|---|---|---|---|---|
| `protocol` | `SOCKET_CLOSED` | `None` | `TRANSIENT_BLIP` | transport wobble; `ProtocolError` doc says retry-with-backoff |
| `protocol` | `STDIN_BROKEN` | `None` | `TRANSIENT_BLIP` | transport; retryable |
| `protocol` | `SPAWN_FAILED` | `None` | `TRANSIENT_BLIP` | transport; retryable |
| `expected` | `NOT_AUTHORIZED` | `None` | `LOGIN_EXPIRED` | the one neutral expected code with login meaning |
| `expected` | `CWD_NOT_FOUND` | `None` | `DEAD_END` | deterministic decline; retry repeats it |
| `expected` | `UNKNOWN_PROVIDER` | `None` | `DEAD_END` | deterministic decline |
| `expected` | `NO_SESSION` | `None` | `DEAD_END` | deterministic decline |
| `internal` | `DECODE_FAILED` | `None` | `DEAD_END` | a bug; model says log+escalate, don't retry |
| `internal` | `LOG_CORRUPT` | `None` | `DEAD_END` | a bug; don't retry |
| any | any | `TRANSIENT_BLIP` | `TRANSIENT_BLIP` | adapter hint wins (provider knows better) |
| `expected` | `"401"` (raw Claude) | `LOGIN_EXPIRED` | `LOGIN_EXPIRED` | Claude `classify_failure` maps 401/403 → login |
| `expected` | `"429"` (raw Claude) | `TRANSIENT_BLIP` | `TRANSIENT_BLIP` | Claude maps 429 → rate-limit blip |
| `expected` | `"400"` (raw Claude) | `DEAD_END` | `DEAD_END` | Claude maps bad-request → dead-end |

`next_delay` stubs (policy: base=1, max=60, mult=2, budget=720, full jitter):

| `attempt` | `elapsed_seconds` | → result | Note |
|---|---|---|---|
| 0 | 0 | a float in `[0, 1]` | first step, full jitter |
| 3 | 10 | a float in `[0, 8]` | `min(60, 1·2³)=8` |
| 10 | 700 | a float in `[0, 60]` | capped at max_delay |
| any | 720 | `None` | budget exhausted → reclassify dead-end |

## Errors (CF-03)

The seam itself is an **in-process library call** (CF-08) — there is no
ProtocolError category at this seam. The *domain* errors it reasons about
are the three existing `events.py` categories, which are the **input** to
`classify`, not failures of `classify`:

| Category | At this seam | Recovery |
|---|---|---|
| **Expected** | `classify` given an `EventError` whose `(category, code)` is unrecognised AND no adapter hint | Falls through to the **neutral category default** (never raises): `protocol`→blip, `internal`/`expected`→dead-end. A genuinely unknown code is treated as dead-end, the safe direction (don't retry forever). |
| **Internal** | a bug in the pure function (should never happen — it's total over the three categories) | Surfaces as an `InternalError`; the driver logs it as an `error` Event and abandons (fail-safe). |

`classify` is **total** — every `(category, code, hint)` triple yields a
class; it never raises for an unknown code (it defaults dead-end). This is
the CF-04 "error + empty cases" guarantee: an unrecognised future code is a
defined, safe outcome, not a crash.

## The emitted-Event shape (recovery driver → existing log)

Every recovery action the driver takes is an Event appended to the
**existing** log (ADR-001, ADR-004 — no new stream, no new Event kind, no
new code). The shapes, all using `events.py`'s existing `Event` +
`EventError`:

| Action | Event kind | `error.category` | `error.code` | message carries |
|---|---|---|---|---|
| Retry scheduled (transient-blip) | `error` | `protocol` | the observed code (reused) | "transient failure; retry N in ~Ms" |
| Abandon (dead-end) | `error` | the observed category | the observed code (reused) | "abandoned: <reason>" |
| Abandon (budget exhausted) | `error` | `expected` | the observed code (reused) | "retry budget exhausted (~12 min); abandoned as dead-end" |
| Abandon (absolute ceiling) | `error` | the observed category | the observed code (reused) | "abandoned: absolute retry ceiling exceeded (...)" |
| Login-expired notification | `error` | `expected` | `NOT_AUTHORIZED` (reused) | "login expired — re-login: <link>" |
| Resume after re-auth | `result`/`chunk` | — | — | normal turn stream (no fabricated completion) |

**No new error code is introduced** — every row reuses an existing
`events.py` constant (the spec's "add a new code only where none fits";
none is needed). The absolute-ceiling abandon (below) likewise reuses the
observed code.

## Provider-abuse hardening (CH-01KTMK ship-gate)

Two invariants harden the layer against a pathological/adversarial provider;
both are additive and preserve every recovery-class behaviour above.

**One recovery thread in flight per session (CONCERN-1).** The manager
dispatches recovery off the pump thread on a daemon thread. Dispatch is gated
on a per-driver in-flight guard (`try_begin_recovery` / `end_recovery`): at most
one recovery thread drives a session's sequence at a time. A fresh error
arriving while a recovery thread is in flight (notably while it sleeps on the
backoff curve) is **coalesced** into the existing sequence — the driver's
`observe` already serialises the sequence state under its lock — rather than
spawning its own thread, so a rapid error stream cannot pile up sleeping
recovery threads (thread/memory exhaustion). The slot is released immediately
before the fire-and-forget re-submit, so the replay's re-error always finds the
slot open and the never-clearing sequence still walks to exhaustion. The
WP-007/WP-008 deadlock fixes are untouched (the slot release stays on the pump
thread; the driver lock is never held across an injected call).

**Absolute, turn-clear-proof retry ceiling (CONCERN-2).** The per-sequence
wall-clock window (`total_budget_seconds`, ~12 min) resets on every genuine
clear, so a provider alternating result/error refunds it every cycle and the
give-up guarantee was evadable over a long-lived session. `RetryPolicy` gains
a `max_lifetime_retries` knob (defaulted to **200** — generous for legitimate
use, finite for abuse) and the driver accumulates a `_lifetime_retries` counter
across sequences that `note_turn_cleared` does **not** reset. When the lifetime
count reaches the cap the driver abandons with the typed "absolute retry ceiling
exceeded" Event (the row above). The normal case is preserved: each genuine blip
still recovers on a fresh per-sequence window; only the absolute lifetime bound
survives a clear.

## Conformance check (CF-07)

The seam is internal/library, so conformance is: (1) the classifier's
truth-table test (above) passes against real `events.py` value objects
(not mocks — the existing types); (2) the recovery driver, built against a
fake classifier returning each `RecoveryClass`, drives the correct action
and emits the contracted Event shape; (3) the Claude adapter's
`classify_failure` produces the hints in the last three truth-table rows.
Swap fake-classifier → real classifier and the driver tests still pass —
that is the swap-mock→real conformance step.
