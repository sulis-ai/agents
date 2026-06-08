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
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from _session_manager.classifier import RecoveryClass, classify
from _session_manager.events import NOT_AUTHORIZED, STDIN_BROKEN, EventError


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


# ── the turn-level Armor primitive (WP-005, ADR-001) ──────────────────────


class RecoveryDriver:
    """Drive retry / abandon / pause→resume around the lifecycle (ADR-001).

    The turn-level sibling of ``LifecycleManager``: where the lifecycle
    recovers a *dead process*, this recovers a *live session's turn* that
    ended in an ``error`` Event. It mirrors the lifecycle's around-the-core
    shape — constructed with the injected capabilities it needs and nothing
    more, owning *recovery* while the manager keeps owning the registry, the
    one-in-flight FIFO, and ``turn_complete`` (all byte-unchanged; the driver
    never touches ``Session.submit``).

    Injected capabilities (the ``LifecycleManager`` convention, ADR-001/002):

    - ``send`` — re-submit the stopped turn. The manager's FIFO serialises it,
      so a retry is just another turn, never a second in-flight turn. Returns
      ``True`` when the re-submitted turn cleared, ``False`` when it failed
      again (the blip-clears / never-clears distinction the driver loops on).
    - ``log_append`` — surface a recovery action as an :class:`EventError` on
      the **existing** log (no new stream, §3.5): every retry / abandon /
      pause is observable in ``read(follow=True)``.
    - ``reauth`` — the adapter's re-auth trigger; called **once** on a
      login-expiry, returns the :class:`ReauthTicket` carrying the re-login
      link + completion handle (ADR-004).
    - ``resume`` — trigger the **existing** same-key/same-log restart
      (``supports_resume`` + ``resume_ref``, the session-manager half of ADE
      ADR-002). The driver triggers it; it does not reimplement resume.
    - ``classify_failure`` — the per-session adapter's provider detection hint
      (ADR-003), passed to the classifier; ``None`` defers to the neutral
      arbiter.

    Tuning + determinism (ADR-002, MEA-09):

    - ``policy`` — the injected :class:`RetryPolicy` (default
      :data:`DEFAULT_RETRY_POLICY`); the path to per-run/per-provider is a
      composition-root selection, not a driver change.
    - ``clock`` — a monotonic ``now()`` callable (default ``time.monotonic``);
      the wall-clock budget is measured against it, a fake in tests.
    - ``sleep`` — the backoff wait (default ``time.sleep``); injected so tests
      advance the fake clock instead of really sleeping.
    - ``rng`` — the full-jitter source (default ``random.random``); seeded in
      tests for repeatable delays.
    - ``classifier`` — the neutral arbiter (default :func:`classify`); a fake
      in the per-class driver tests, swapped back to the real one at Blue
      (the CF-07 mock→real conformance step).

    Recovery is per-session: one ``RecoveryDriver`` instance drives the one
    session whose error it observed; it holds at most one pending re-auth
    ticket (it does not re-fire ``reauth`` on every observation). It never
    touches another session (isolation, ADR-001 §3.4 / NFR-SEC-06 analogue).
    """

    def __init__(
        self,
        *,
        send: Callable[[], bool],
        log_append: Callable[[EventError], None],
        reauth: Callable[[], ReauthTicket],
        resume: Callable[[], None],
        classify_failure: Callable[[EventError], RecoveryClass | None] | None = None,
        classifier: Callable[[EventError, RecoveryClass | None], RecoveryClass]
        | None = None,
        policy: RetryPolicy = DEFAULT_RETRY_POLICY,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
    ) -> None:
        self._send = send
        self._log_append = log_append
        self._reauth = reauth
        self._resume = resume
        self._classify_failure = classify_failure
        self._classifier = classifier if classifier is not None else classify
        self._policy = policy
        self._clock = clock
        self._sleep = sleep
        self._rng = rng
        # At most one pending re-auth ticket per session (idempotency, §Q10):
        # a login-expiry observed while already paused does not re-fire reauth.
        self._pending_ticket: ReauthTicket | None = None

    def observe(self, error: EventError) -> None:
        """Observe one ``error``-kind failure and drive recovery (the §3.1
        pipeline; order is load-bearing).

        1. **Skip process-death.** A ``STDIN_BROKEN`` "died mid-turn" is
           ``LifecycleManager``'s job (restart-on-death) — the driver no-ops so
           the two seams never double-handle (the sibling-not-stacked rule).
        2. **Classify** via the injected classifier, passing the adapter's
           ``classify_failure`` hint.
        3. **Branch** to retry / abandon / pause→resume.
        """
        # 1. Process-death is the lifecycle's seam, not this one — no-op before
        #    classification so the driver never even looks at it.
        if error.code == STDIN_BROKEN:
            return

        # 2. Classify (the adapter hint, else the neutral default).
        hint = self._classify_failure(error) if self._classify_failure else None
        verdict = self._classifier(error, hint)

        # 3. Branch.
        if verdict is RecoveryClass.TRANSIENT_BLIP:
            self._drive_retry(error)
        elif verdict is RecoveryClass.LOGIN_EXPIRED:
            self._drive_login_expired(error)
        else:  # RecoveryClass.DEAD_END
            self._abandon(error, reason="dead-end")

    def complete_reauth(self, ticket: ReauthTicket) -> None:
        """Resume the paused run after a re-auth ticket completes (ADR-004).

        Triggers the **existing** resume path (``supports_resume`` +
        ``resume_ref`` same-key/same-log restart). The agent wakes with full
        memory and **re-runs the incomplete step** — the driver only triggers
        the resume; it never fabricates a ``result`` (ADE ADR-002 / NFR-REL-04
        discipline, inherited not reimplemented). A completion for a ticket the
        driver is not waiting on is ignored (idempotent, §Q10)."""
        if self._pending_ticket is None:
            return
        if ticket.completion_handle != self._pending_ticket.completion_handle:
            return
        self._pending_ticket = None
        self._resume()

    # ── observability seam ─────────────────────────────────────────────────

    def _surface(self, *, category: str, code: str, message: str) -> None:
        """Surface one recovery action as an ``error`` Event on the **existing**
        log (§3.5 — every action is an Event, no new stream). The single place
        the driver writes to the log, so the "observable in ``read(follow=True)``"
        guarantee lives in one spot."""
        self._log_append(EventError(category=category, code=code, message=message))

    # ── branch implementations ────────────────────────────────────────────

    def _drive_retry(self, error: EventError) -> None:
        """Retry a transient blip with full-jitter backoff against the
        wall-clock budget; abandon as dead-end on exhaustion (§3.1, ADR-002).

        The wait is the injected ``sleep`` against the injected ``clock`` — no
        bare ``time.sleep`` (MEA-09). A re-submit that clears ends the loop
        (the run survives, no human restart); one that fails again advances the
        attempt. When ``next_delay`` returns ``None`` (the next backoff would
        push cumulative elapsed past the budget) the blip is reclassified
        dead-end and abandoned with a typed Event — not a silent hang.
        """
        start = self._clock()
        attempt = 0
        while True:
            elapsed = self._clock() - start
            delay = next_delay(attempt, elapsed, self._policy, rng=self._rng)
            if delay is None:
                self._abandon(error, reason="retry budget exhausted")
                return
            self._surface(
                category=error.category,
                code=error.code,
                message=(
                    f"retry scheduled: transient blip, attempt {attempt + 1} "
                    f"in {delay:.2f}s ({error.message})"
                ),
            )
            self._sleep(delay)
            if self._send():
                # The re-submitted turn cleared — the run survived. The FIFO
                # serialised the retry; one-in-flight is untouched.
                return
            attempt += 1

    def _drive_login_expired(self, error: EventError) -> None:
        """Pause→notify the run on a login-expiry (ADR-004).

        Calls ``reauth()`` once, surfaces the re-login link as a
        ``NOT_AUTHORIZED`` ``error`` Event (the notification rides the existing
        stream — no new screen), and **pauses**: it holds the session out of
        the retry loop pending the ticket and does **not** burn the retry
        budget (login-expiry is not a blip). Resume happens later via
        :meth:`complete_reauth`. If the session is already paused on a pending
        ticket, this is a no-op (one ticket per session, §Q10).
        """
        if self._pending_ticket is not None:
            return
        try:
            ticket = self._reauth()
        except Exception as exc:  # noqa: BLE001 - any reauth failure is fail-safe
            # Fail-safe (§Q12): a re-auth that itself fails is abandoned as a
            # dead-end with a typed, observable Event — contained, never a hang.
            self._abandon(error, reason=f"re-auth failed: {exc}")
            return
        self._pending_ticket = ticket
        self._surface(
            category=error.category,
            code=NOT_AUTHORIZED,
            message=(
                f"login expired — re-login here: {ticket.relogin_link} "
                f"(run paused, will resume after re-auth)"
            ),
        )

    def _abandon(self, error: EventError, *, reason: str) -> None:
        """Abandon the run with a typed, observable ``error`` Event reusing the
        observed code (§3.1). Used for a dead-end (immediately, budget not
        consulted) and for a transient blip whose budget is exhausted."""
        self._surface(
            category=error.category,
            code=error.code,
            message=f"abandoned: {reason} ({error.message})",
        )
