"""``_session_manager.recovery`` — the injected retry policy + the re-auth
ticket value object (ADR-002, ADR-004).

WP-001 contributes the **shapes** the recovery driver (WP-005) and the policy
(WP-003) are built against:

- :class:`RetryPolicy` — the frozen, injected backoff policy value object, with
  the module-level :data:`DEFAULT_RETRY_POLICY` fallback constant (ADR-002).
  The same convention ``manager.py`` already uses for ``recovery_budget`` and
  the turn guards: tuning values are constructor kwargs with ``DEFAULT_*``
  module constants, selected at the composition root — never a literal buried
  in the retry loop. The path to per-run / per-provider is a composition-root
  selection, not a driver change.
- :func:`next_delay_ceiling` — the deterministic core of the backoff curve:
  the jitter-free per-attempt ceiling, and the budget-exhaustion ``None``
  signal. WP-003's full ``next_delay`` applies full jitter *within* this
  ceiling (``random_between(0, ceiling)``); pinning the ceiling here is the
  single source of truth the contract's stub table asserts against, so the
  policy and the driver agree on the curve without re-spelling it.

WP-003 adds:

- :func:`next_delay` — the full backoff curve the driver schedules on: full
  jitter (the AWS convention, CP-01) sampled *within* the
  :func:`next_delay_ceiling` band — ``random_between(0, ceiling)`` — or
  ``None`` on budget exhaustion (reusing the ceiling's exhaustion signal, so
  the two never disagree). The RNG is injectable (default ``random.random``)
  so it is testable with a seeded source and no real ``time.sleep``; the
  clock is the driver's concern (``elapsed_seconds`` is passed in, WP-005).
- :class:`ReauthTicket` — the value object ``adapter.reauth()`` returns: the
  re-login link the notification surfaces + a completion handle the driver
  waits on (ADR-003/004).

**No new error code.** Login-expiry rides the existing ``NOT_AUTHORIZED``
code from ``events.py``; this module declares no code constants.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RetryPolicy:
    """The backoff/give-up policy, injected into the recovery driver (ADR-002).

    Frozen so the policy the driver was constructed with cannot drift under it
    mid-run. Backoff is the established convention (CP-01): exponential base
    with full jitter, bounded by a total wall-clock budget.
    """

    base_delay_seconds: float
    """First backoff step (seconds)."""

    max_delay_seconds: float
    """Per-step ceiling (seconds) — the curve never sleeps longer than this."""

    multiplier: float
    """Exponential base, e.g. ``2.0``."""

    jitter: Literal["full", "none"]
    """Jitter strategy. ``"full"`` is the AWS convention (CP-01): the actual
    sleep is ``random_between(0, ceiling)``, preventing thundering-herd on a
    shared provider outage."""

    total_budget_seconds: float
    """The wall-clock cap (~10-15 min). When the *next* backoff would push
    cumulative elapsed past this, the run is reclassified dead-end and
    abandoned."""


DEFAULT_RETRY_POLICY = RetryPolicy(
    base_delay_seconds=1.0,
    max_delay_seconds=60.0,
    multiplier=2.0,
    jitter="full",
    total_budget_seconds=720.0,  # 12 min — mid of the ~10-15 min band
)
"""The persistent-default policy (ADR-002). The *fallback* the driver uses
when the composition root injects nothing — not a hardcoded literal in the
retry loop."""


def next_delay_ceiling(
    attempt: int,
    elapsed_seconds: float,
    policy: RetryPolicy,
) -> float | None:
    """The jitter-free backoff ceiling for ``attempt`` (ADR-002), or ``None``
    on budget exhaustion.

    Returns ``min(max_delay_seconds, base_delay_seconds * multiplier**attempt)``
    — the upper bound a full-jitter ``next_delay`` (WP-003) samples within
    (``random_between(0, ceiling)``). Returns ``None`` when ``elapsed_seconds``
    has reached or exceeded ``total_budget_seconds``: the signal to reclassify
    a ``TRANSIENT_BLIP`` as a ``DEAD_END`` and abandon.

    Pure and total: every ``(attempt, elapsed, policy)`` triple yields a float
    or ``None``; it never raises. The budget is wall-clock, not attempt-count
    (ADR-002).
    """
    if elapsed_seconds >= policy.total_budget_seconds:
        return None
    uncapped = policy.base_delay_seconds * (policy.multiplier**attempt)
    return min(policy.max_delay_seconds, uncapped)


def next_delay(
    attempt: int,
    elapsed_seconds: float,
    policy: RetryPolicy,
    rng: Callable[[], float] = random.random,
) -> float | None:
    """The full-jitter backoff delay before the next attempt (ADR-002), or
    ``None`` on budget exhaustion.

    Full jitter (the AWS convention, CP-01): the delay is sampled uniformly in
    ``[0, ceiling]`` where ``ceiling`` is the jitter-free per-attempt ceiling
    :func:`next_delay_ceiling` pins — ``random_between(0, min(max_delay,
    base * multiplier**attempt))``. Sampling the whole band (rather than always
    sleeping the ceiling) prevents thundering-herd on a shared provider outage.

    Returns ``None`` when the budget is exhausted — i.e. exactly when
    :func:`next_delay_ceiling` returns ``None`` (``elapsed_seconds`` has reached
    ``policy.total_budget_seconds``). Reusing the ceiling's exhaustion signal
    keeps the policy and the ceiling from ever disagreeing; ``None`` is the
    driver's signal to reclassify ``TRANSIENT_BLIP`` → ``DEAD_END`` and abandon.

    Pure: the RNG is injected (``rng`` defaults to :func:`random.random`, a
    ``() -> float`` in ``[0, 1)``) so the curve is testable with a seeded source
    and **no real** ``time.sleep`` — the clock is the driver's concern; this
    function only consumes the ``elapsed_seconds`` it is handed (WP-005).
    """
    ceiling = next_delay_ceiling(attempt, elapsed_seconds, policy)
    if ceiling is None:
        return None
    return rng() * ceiling


@dataclass(frozen=True)
class ReauthTicket:
    """What ``adapter.reauth()`` returns for a login-expired stoppage
    (ADR-003/004).

    Frozen value object carrying the two things the driver needs: the re-login
    link the notification surfaces on the existing event stream, and a handle
    the driver waits on to confirm re-auth completed before it resumes the
    paused run. No new durable store, no new stream — the link rides the
    existing ``error`` Event (``NOT_AUTHORIZED``), the resume reuses the
    existing same-key/same-log path (ADR-004).
    """

    relogin_link: str
    """The re-login URL the notification Event carries for the operator."""

    completion_handle: str
    """An opaque handle the driver waits on for the re-auth confirmation
    signal; how the operator completes re-login is the platform's existing
    surface, outside this layer (ADR-004)."""
