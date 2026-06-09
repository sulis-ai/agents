# ADR-003 — Classification is provider-neutral; detection is a thin adapter hint

- **Status:** accepted
- **Date:** 2026-06-08
- **Change:** CH-01KTMK · automation-reliability-recovery
- **Deciders:** SEA

## Context

The spec demands the classifier + retry policy be **provider-neutral**
(covered by tests that don't depend on the Claude adapter), while the
*detection* of "which raw failure is a login-expiry vs transient blip vs
dead-end" is per-provider and must live behind the existing
`ProviderAdapter` seam. The constraint is to add only thin detection +
re-auth, not to fork or widen the seam.

The existing facts the design must honour:

- `events.py` already carries a provider-neutral `(category, code)` on
  every `EventError` — `protocol` codes (`SPAWN_FAILED`, `STDIN_BROKEN`,
  `SOCKET_CLOSED`), `expected` codes (`NO_SESSION`, `UNKNOWN_PROVIDER`,
  `CWD_NOT_FOUND`, `NOT_AUTHORIZED`, …), `internal` codes (`DECODE_FAILED`,
  `LOG_CORRUPT`, `PTY_OPEN_FAILED`). Login-expiry maps to the existing
  `NOT_AUTHORIZED`.
- The **Claude adapter** already collapses provider HTTP failures into a
  single `expected` error whose `code` is the raw `api_error_status`
  (e.g. `"401"`, `"403"`, `"429"`, `"400"`) — see
  `adapters/claude.py::_error_payload`. So at the shared layer, a
  rate-limit (429), an auth-expiry (401/403), and a bad-request (400) all
  arrive as `category="expected"` with **different raw codes** the shared
  classifier cannot interpret without provider knowledge.

That is the crux: the *category* is provider-neutral but insufficient
(429 and 401 are both `expected`); the *raw code's meaning* is
provider-specific. So the split must put the **mapping** behind the
adapter and the **policy** in the shared classifier.

## Decision

**Add one thin, additive method to the `ProviderAdapter` Protocol —
`classify_failure(error: EventError) -> RecoveryClass | None` — that
returns the provider's detection hint, and keep the shared classifier as
the provider-neutral arbiter that uses the hint plus a category-based
default.** Also add a thin `reauth_*` capability for the re-auth trigger
(below). Nothing else on the seam changes.

```
# adapter.py (additive to the Protocol; defaulted so existing adapters
# and future Codex/Gemini adapters need only override to be specific)
class ProviderAdapter(Protocol):
    ...  # unchanged: capabilities, spawn_argv, encode, decode, turn_complete

    def classify_failure(self, error: EventError) -> "RecoveryClass | None":
        """Provider-specific detection hint: map THIS provider's raw failure
        to a recovery class, or None to defer to the neutral default."""

    def reauth(self) -> "ReauthTicket":
        """Begin re-auth for this provider; return a ticket carrying the
        re-login link the notification surfaces and a way to confirm
        completion. Used only when classify_failure → login-expired."""
```

- **Provider-neutral classifier (`classifier.py`).** Pure function over
  `EventError`:
  1. Ask the adapter for a hint (`classify_failure`). If it returns a
     class, use it.
  2. Otherwise apply the **neutral default**, derived from `category`
     alone (no raw-code interpretation): `protocol` → transient-blip
     (transport wobble, retry-with-backoff — matches the `ProtocolError`
     docstring already in `events.py`); `internal` → dead-end (a bug; the
     existing model says "log + escalate, do not retry"); `expected` →
     dead-end **except** `NOT_AUTHORIZED` → login-expired (the one
     `expected` code with a neutral meaning, already defined in
     `events.py`).
  - The classifier's tests use a fake adapter / no adapter, satisfying
    "provider-neutral, covered without the Claude adapter".
- **Claude detection (`adapters/claude.py`).** Implement
  `classify_failure`: raw code `"401"`/`"403"` → login-expired; `"429"`
  and connection-reset shapes → transient-blip; `"400"` and other
  deterministic declines → dead-end. This is the *only* place Claude's
  HTTP-status vocabulary is interpreted — the shared layer never sees
  `"401"` as a magic string.
- **Re-auth trigger.** `reauth()` is the thin per-provider action behind
  the seam; for Claude it produces the re-login link the notification
  carries (ADR-004) and a confirmation handle. A second provider supplies
  its own `reauth()` with zero shared-layer change.

## Alternatives considered

- **Put HTTP-status interpretation in the shared classifier (rejected).**
  Leaks Claude's `api_error_status` vocabulary into provider-neutral code
  — the exact coupling the spec forbids. A Gemini adapter might not use
  HTTP status codes at all; the shared layer must not assume them.
- **Widen `EventError` with a `recovery_class` field set by the adapter's
  `decode()` (rejected — over-widening the seam).** `decode()` is the hot
  per-line parser and the error model is the frozen Form invariant;
  threading recovery semantics into it couples the error vocabulary to
  this one feature. A separate `classify_failure` method keeps detection
  additive and the error model pure (the spec: "add a new code only where
  none fits" — none is needed; `NOT_AUTHORIZED` already exists).
- **A standalone per-provider classifier registry outside the adapter
  (rejected).** Splits provider knowledge across two places (the adapter
  *and* a registry). The adapter is already "the only agent-specific
  surface" (§2.4); detection belongs there, beside `decode`.

## Consequences

- `adapter.py` gains two **defaulted, additive** Protocol methods
  (`classify_failure`, `reauth`) — the `@runtime_checkable` conformance
  test extends to assert both adapters answer the shape. No existing
  method signature changes (the `io_mode` / `brief_change_id` additive
  precedent).
- A `RecoveryClass` enum (`TRANSIENT_BLIP` / `DEAD_END` / `LOGIN_EXPIRED`)
  lives in the shared layer (`classifier.py`), imported by adapters — the
  vocabulary is neutral; only the *mapping* is per-provider.
- The neutral default means a brand-new adapter that doesn't override
  `classify_failure` still gets safe behaviour (protocol→retry,
  internal/expected→dead-end, NOT_AUTHORIZED→login) — graceful, honest,
  no crash.
- No new error code is added: `NOT_AUTHORIZED` already carries
  login-expiry; the three categories already carry the neutral defaults.
  (Honours the spec's "add a new code only where none fits".)
