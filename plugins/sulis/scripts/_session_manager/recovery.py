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
import threading
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
    """The *per-sequence* wall-clock cap (~10-15 min). When the *next* backoff
    would push the current retry sequence's cumulative elapsed past this, the
    sequence is reclassified dead-end and abandoned. **Reset on every genuine
    clear** (``note_turn_cleared``) so a later, unrelated blip gets a fresh
    window — which is exactly why it cannot, alone, bound a pathological provider
    that alternates result/error (each clear refunds the window). The absolute,
    non-resettable bound is :attr:`max_lifetime_retries`."""

    max_lifetime_retries: int = 200
    """The ABSOLUTE per-session retry ceiling a turn-clear does **not** reset
    (CH-01KTMK hardening FIX 2). Where :attr:`total_budget_seconds` bounds one
    *sequence*, this bounds the *lifetime* retry count across all sequences on a
    single long-lived session, accumulated on the driver (``_lifetime_retries``)
    and never refunded by ``note_turn_cleared``.

    Without it the ~12-min give-up guarantee is evadable: a provider alternating
    result/error refunds the per-sequence window every cycle, so total retries are
    unbounded even though each window honours its cap. With it, such abuse is
    bounded to a finite total and abandoned with a typed "absolute retry ceiling"
    Event.

    Defaulted (so the field is backward-compatible — existing constructions need
    not pass it) to **200**: deliberately generous for legitimate use (a healthy
    long-lived session retries a handful of times per genuine blip, nowhere near
    200 lifetime retries) while bounding a pathological alternating provider to a
    finite total. The per-sequence wall-clock cap stays the primary give-up
    mechanism for the common single-incident case; this is the abuse backstop."""


DEFAULT_RETRY_POLICY = RetryPolicy(
    base_delay_seconds=1.0,
    max_delay_seconds=60.0,
    multiplier=2.0,
    jitter="full",
    total_budget_seconds=720.0,  # 12 min — mid of the ~10-15 min band
    max_lifetime_retries=200,  # the absolute, turn-clear-proof abuse backstop
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

    - ``send`` — re-submit the stopped turn **fire-and-forget** (the WP-007 wired
      contract). The manager's FIFO serialises it, so a retry is just another
      turn, never a second in-flight turn. The ack is the *enqueue*, NOT the
      outcome: the re-submitted turn's result arrives LATER as a brand-new
      ``error`` Event → a fresh :meth:`observe` (the blip failed again) or a
      genuine ``result`` Event → :meth:`note_turn_cleared` (the blip cleared).
      The driver therefore does NOT treat the ``send`` ack as "cleared"; it
      drives recovery as an event-driven state machine across observations.
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

    Recovery is per-session and **stateful across observations**: one
    ``RecoveryDriver`` instance drives the one session whose error it observed.
    Because the wired ``send`` is fire-and-forget, a never-clearing blip's
    re-submitted turn fails again as a *fresh* ``observe`` call — so the
    wall-clock retry budget cannot live inside one ``observe`` (it would reset
    every time). Instead the driver holds the current retry sequence's
    wall-clock start (``_retry_started_at``) and attempt count (``_retry_attempt``)
    on the instance; each transient-blip observation advances the SAME sequence,
    the budget accumulates, and a never-clearing blip abandons exactly when
    ``next_delay`` returns ``None``. A genuine clear (:meth:`note_turn_cleared`)
    resets the sequence so a later, unrelated blip gets a fresh budget. The
    driver also holds at most one pending re-auth ticket (it does not re-fire
    ``reauth`` on every observation). It never touches another session
    (isolation, ADR-001 §3.4 / NFR-SEC-06 analogue).

    **Thread-safety.** ``observe`` runs on the manager's short-lived recovery
    thread (off the pump, §3.1) while ``note_turn_cleared`` runs on the stdout
    pump thread that appended the clearing ``result``. Both mutate the retry
    sequence state, so the small read-modify-write of (``_retry_started_at``,
    ``_retry_attempt``) is guarded by a lock. The lock is held only around the
    state transition — never across the injected ``sleep`` or ``send`` — so it
    cannot reintroduce the WP-007 self-deadlock (the pump's slot-release path is
    never blocked on a recovery wait).
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
        # The current transient-blip retry sequence, accumulated ACROSS
        # observations (the fire-and-forget wiring): the wall-clock start of the
        # first failure in the sequence, and the attempt count. ``None`` start
        # means no retry is in progress. Guarded by ``_retry_lock`` because
        # ``observe`` (recovery thread) and ``note_turn_cleared`` (pump thread)
        # both touch it.
        self._retry_started_at: float | None = None
        self._retry_attempt: int = 0
        # CH-01KTMK FIX 2 — the ABSOLUTE lifetime retry counter. Accumulates the
        # number of retries scheduled across ALL sequences on this session and is
        # **never** reset by ``note_turn_cleared`` (unlike the per-sequence start/
        # attempt above). When it reaches ``policy.max_lifetime_retries`` the
        # driver abandons with a typed "absolute retry ceiling" Event — the
        # turn-clear-proof give-up guarantee. Guarded by ``_retry_lock`` (same
        # read-modify-write as the sequence state).
        self._lifetime_retries: int = 0
        self._retry_lock = threading.Lock()
        # CH-01KTMK FIX 1 — the one-recovery-thread-in-flight-per-session guard.
        # ``_on_error_event`` (the manager) spawns a daemon thread per routed
        # error; left unbounded, a pathological provider's error stream piles up
        # sleeping recovery threads (they sleep on the backoff curve) → thread/
        # memory exhaustion. This Event is the in-flight flag: the manager calls
        # :meth:`try_begin_recovery` before dispatching and only spawns a thread
        # if it wins the slot; a fresh error arriving while a recovery thread is
        # already driving the sequence is COALESCED (the existing sequence already
        # handles it — ``observe`` serialises the state under ``_retry_lock``),
        # not given its own thread. :meth:`end_recovery` clears it when the
        # recovery thread finishes (in a ``finally``, so a faulting recovery never
        # wedges the slot shut). Guarded by the same lock so begin/end is atomic.
        self._recovery_in_flight = threading.Event()

    # ── CH-01KTMK FIX 1 — the one-thread-in-flight dispatch guard ──────────

    def try_begin_recovery(self) -> bool:
        """Try to claim the single recovery slot for this session (FIX 1).

        Returns ``True`` if the caller won the slot and should dispatch a
        recovery thread; ``False`` if a recovery thread is already in flight for
        this session and the caller should **coalesce** — i.e. let the existing
        sequence handle the error rather than spawn a second thread. Atomic
        under ``_retry_lock`` so two pump threads racing to route concurrent
        errors cannot both win.

        Coalescing is correct because the driver's :meth:`observe` already
        serialises the retry-sequence state under the same lock: a transient blip
        in flight is already being retried on the accumulating budget, so a fresh
        transient error for the same session is the SAME condition the in-flight
        sequence is handling. A genuinely different condition (e.g. a login-expiry
        while a transient retry is in flight) is not lost: the in-flight retry
        thread, on its next observation of the re-submitted turn's outcome, will
        observe and route it through the same serialised pipeline. The simplest
        correct rule — one recovery thread per session — holds."""
        with self._retry_lock:
            if self._recovery_in_flight.is_set():
                return False
            self._recovery_in_flight.set()
            return True

    def end_recovery(self) -> None:
        """Release the single recovery slot (FIX 1) — called by the manager in a
        ``finally`` on the recovery thread, so even a faulting ``observe`` frees
        the slot and never wedges the session's recovery shut. Idempotent."""
        with self._retry_lock:
            self._recovery_in_flight.clear()

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
        driver is not waiting on is ignored (idempotent, §Q10).

        **``_pending_ticket`` is read+cleared under ``_retry_lock`` (CH-01KTMK
        ADVISORY-1).** The small read-modify-write is held under the lock for
        symmetry with the rest of the driver's shared state; the injected
        ``_resume`` is then called OUTSIDE the lock, so the lock is never held
        across an injected call (the WP-007 no-deadlock invariant)."""
        with self._retry_lock:
            if self._pending_ticket is None:
                return
            if ticket.completion_handle != self._pending_ticket.completion_handle:
                return
            self._pending_ticket = None
        self._resume()

    def note_turn_cleared(self) -> None:
        """A turn genuinely completed (a ``result``) — end the retry sequence.

        Wired from the manager's event fan-out: when a session's turn produces a
        ``result`` (``adapter.turn_complete`` is True), the run survived, so the
        current transient-blip retry sequence (if any) is over. Resetting the
        accumulated budget here is what gives a LATER, unrelated blip a fresh
        wall-clock budget — the "transient blip that clears → survives" semantics
        across a long-lived session. Idempotent: a clear with no retry in
        progress is a harmless no-op.

        **Resets the per-sequence window only, NOT the absolute lifetime ceiling
        (CH-01KTMK FIX 2).** ``_reset_retry_sequence`` clears the per-sequence
        start/attempt so the next blip gets a fresh wall-clock window; it
        deliberately leaves ``_lifetime_retries`` untouched, so a provider
        alternating result/error cannot refund the absolute ceiling by clearing.
        The normal case is preserved (each genuine blip recovers on a fresh
        window); only the turn-clear-proof abuse bound survives the clear."""
        self._reset_retry_sequence()

    # ── observability seam ─────────────────────────────────────────────────

    def _surface(self, *, category: str, code: str, message: str) -> None:
        """Surface one recovery action as an ``error`` Event on the **existing**
        log (§3.5 — every action is an Event, no new stream). The single place
        the driver writes to the log, so the "observable in ``read(follow=True)``"
        guarantee lives in one spot."""
        self._log_append(EventError(category=category, code=code, message=message))

    # ── branch implementations ────────────────────────────────────────────

    def _drive_retry(self, error: EventError) -> None:
        """Advance the transient-blip retry sequence by ONE step against the
        wall-clock budget that accumulates ACROSS observations; abandon on
        exhaustion (§3.1, ADR-002).

        Event-driven, not a blocking loop (the WP-007 fire-and-forget wiring):
        the re-submitted turn's outcome arrives later as a *fresh* observation,
        so each call schedules at most one retry and then **returns** — the next
        failure re-enters :meth:`observe` and advances the SAME sequence. The
        budget therefore must live on the instance:

        - If no sequence is in progress (``_retry_started_at is None``) this is
          the first failure: stamp the wall-clock start and reset the attempt to
          0.
        - Compute ``elapsed`` from that start and ``delay = next_delay(attempt,
          elapsed, …)``. ``None`` ⇒ the budget is exhausted: abandon with a
          typed Event (not a silent hang) and reset the sequence.
        - Otherwise surface a "retry scheduled" Event, wait the jittered delay on
          the injected ``sleep`` against the injected ``clock`` (no bare
          ``time.sleep``, MEA-09), fire the **fire-and-forget** ``send`` (the ack
          is the enqueue, never "cleared"), advance the attempt, and return.

        The injected fake ``sleep`` advances the fake ``clock`` in tests, so a
        never-clearing blip walks the curve to genuine budget exhaustion
        deterministically. A genuine clear resets the sequence via
        :meth:`note_turn_cleared`.
        """
        with self._retry_lock:
            if self._retry_started_at is None:
                self._retry_started_at = self._clock()
                self._retry_attempt = 0
            start = self._retry_started_at
            attempt = self._retry_attempt

        # CH-01KTMK FIX 2 — the ABSOLUTE lifetime ceiling, checked BEFORE the
        # per-sequence window. A turn-clear refunds the window (``_reset_retry_\
        # sequence``) but never the lifetime counter, so a provider alternating
        # result/error cannot evade this bound. When the lifetime retry count has
        # reached the cap, abandon with a typed "absolute retry ceiling" Event and
        # end the sequence — the turn-clear-proof give-up guarantee.
        if self._lifetime_retries >= self._policy.max_lifetime_retries:
            self._abandon_sequence(error, reason="absolute retry ceiling exceeded")
            return

        elapsed = self._clock() - start
        delay = next_delay(attempt, elapsed, self._policy, rng=self._rng)
        if delay is None:
            # Per-sequence wall-clock budget exhausted — abandon and end the
            # sequence (a later, unrelated blip starts a fresh window).
            self._abandon_sequence(error, reason="retry budget exhausted")
            return

        self._surface(
            category=error.category,
            code=error.code,
            message=(
                f"retry scheduled: transient blip, attempt {attempt + 1} "
                f"in {delay:.2f}s ({error.message})"
            ),
        )
        with self._retry_lock:
            # Count this scheduled retry against the ABSOLUTE lifetime ceiling
            # BEFORE the fire-and-forget ``send`` — accumulated across sequences,
            # never reset by a turn-clear (FIX 2). Counting before the send (not
            # after) is what makes the ceiling robust to the fire-and-forget
            # re-entry: the re-submitted turn's outcome arrives as a *later*
            # observation, so a retry must be counted at the point it is
            # dispatched, not after its outcome is known.
            self._lifetime_retries += 1
            # Advance only if the sequence is still the one we were driving — a
            # racing clear could have reset it while we computed the delay.
            if self._retry_started_at == start:
                self._retry_attempt = attempt + 1
        self._sleep(delay)
        # Release the recovery slot BEFORE the fire-and-forget re-submit (FIX 1,
        # load-bearing for the never-clearing sequence). The re-submitted turn's
        # re-error arrives as a *fresh* routed event that must be able to win the
        # slot and advance the SAME sequence; if the slot were only released after
        # ``_send`` (by the manager's ``finally``), a re-error landing in that
        # race window would coalesce-and-drop, stalling the sequence instead of
        # walking it to budget/ceiling exhaustion. Releasing here, before the
        # send, guarantees the slot is open when the replay errors back. The
        # manager's ``finally`` ``end_recovery`` remains an idempotent backstop
        # for the non-retry branches (dead-end abandon, login pause) that never
        # re-submit.
        self.end_recovery()
        # Fire-and-forget re-submit: the FIFO serialises it (one-in-flight
        # untouched); the turn's outcome comes back as a fresh observe / clear.
        self._send()

    def _reset_retry_sequence(self) -> None:
        """Clear the current retry sequence's accumulated budget state (start +
        attempt), so the next transient blip begins a fresh wall-clock budget.
        Lock-guarded — called from both the recovery thread (on abandon) and the
        pump thread (on a genuine clear, :meth:`note_turn_cleared`)."""
        with self._retry_lock:
            self._retry_started_at = None
            self._retry_attempt = 0

    def _abandon_sequence(self, error: EventError, *, reason: str) -> None:
        """End the current retry sequence and give up: reset the per-sequence
        window, then surface a typed, observable abandon Event (§3.1).

        The shared "give up on this sequence" step both give-up branches of
        :meth:`_drive_retry` take — the per-sequence wall-clock budget exhaustion
        and the absolute lifetime ceiling (CH-01KTMK FIX 2). Resetting the window
        before abandoning lets a later, unrelated blip start fresh; the lifetime
        counter is deliberately NOT reset here (it persists across sequences —
        that is what makes the absolute ceiling turn-clear-proof)."""
        self._reset_retry_sequence()
        self._abandon(error, reason=reason)

    def _drive_login_expired(self, error: EventError) -> None:
        """Pause→notify the run on a login-expiry (ADR-004).

        Calls ``reauth()`` once, surfaces the re-login link as a
        ``NOT_AUTHORIZED`` ``error`` Event (the notification rides the existing
        stream — no new screen), and **pauses**: it holds the session out of
        the retry loop pending the ticket and does **not** burn the retry
        budget (login-expiry is not a blip). Resume happens later via
        :meth:`complete_reauth`. If the session is already paused on a pending
        ticket, this is a no-op (one ticket per session, §Q10).

        **``_pending_ticket`` is read+written under ``_retry_lock`` (CH-01KTMK
        ADVISORY-1).** The lock guards only the small reads/writes — the injected
        ``_reauth`` and the ``_surface`` log append run OUTSIDE the lock, so the
        lock is never held across an injected call (the WP-007 no-deadlock
        invariant). The pending-ticket idempotency check and the eventual store
        are each a lock-guarded read-modify-write.
        """
        with self._retry_lock:
            if self._pending_ticket is not None:
                return
        try:
            ticket = self._reauth()
        except Exception as exc:  # noqa: BLE001 - any reauth failure is fail-safe
            # Fail-safe (§Q12): a re-auth that itself fails is abandoned as a
            # dead-end with a typed, observable Event — contained, never a hang.
            self._abandon(error, reason=f"re-auth failed: {exc}")
            return
        with self._retry_lock:
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
