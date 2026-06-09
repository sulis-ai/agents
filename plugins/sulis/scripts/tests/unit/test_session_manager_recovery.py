"""WP-005 — tests for the ``RecoveryDriver`` (the turn-level Armor primitive).

Contract: ``.architecture/automation-reliability-recovery/`` ADR-001 (the
driver sits *around* the lifecycle, mirroring ``LifecycleManager``), ADR-002
(the injected ``RetryPolicy`` + wall-clock budget against an injected clock),
ADR-003 (provider-neutral classification + the thin per-provider detection
hint), ADR-004 (login-expired pause→notify→resume reusing the existing
``supports_resume`` + ``resume_ref`` path, no fabricated completion).

The driver is built against **fakes** (ADR-001 — it consumes injected manager
capabilities, never the live ``SessionManager``):

- a fake ``send`` that re-submits the stopped turn **fire-and-forget** (the
  WP-007 wired contract): it acks the enqueue immediately, and the re-submitted
  turn's *outcome* arrives LATER as a fresh ``observe()`` (a re-error) or a
  ``note_turn_cleared()`` (a genuine result). The fake models this faithfully —
  on a never-clearing blip it re-feeds the same error into ``observe()`` so the
  driver advances the SAME retry sequence across observations (the budget
  accumulates on the driver instance, not inside one ``observe()``); on a
  clearing blip it calls ``note_turn_cleared()`` to mimic the result event;
- a fake ``log_append`` recording every recovery action as an
  :class:`~_session_manager.events.EventError` on the existing log surface
  (no new stream, §3.5);
- a fake ``reauth`` returning a :class:`~_session_manager.recovery.ReauthTicket`;
- a fake ``resume`` standing in for the existing same-key/same-log restart;
- a fake monotonic ``clock`` + a no-op ``sleep`` that advances it, so the
  wall-clock budget is exercised with **no real sleeping** (MEA-09);
- a seeded ``rng`` so the jittered backoff is deterministic.

The driver is an **event-driven state machine**: it holds the wall-clock start
+ attempt of the current retry sequence on the instance (``_retry_started_at`` /
``_retry_attempt``), accumulating the budget ACROSS ``observe()`` calls. This
matches the live wiring (WP-007), where a fire-and-forget ``send`` means each
replay's failure re-enters as a brand-new ``observe()`` — so the budget MUST
live on the driver, not in a blocking intra-observe loop. A genuine clear
(``note_turn_cleared``) resets the sequence so a later, unrelated blip gets a
fresh budget.

One test per acceptance branch (the WP's Definition of Done).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from _session_manager import events as ev
from _session_manager.classifier import RecoveryClass
from _session_manager.recovery import (
    RetryPolicy,
    ReauthTicket,
    RecoveryDriver,
)


# ── fakes (the injected manager capabilities) ─────────────────────────────


class FakeClock:
    """A monotonic clock the test drives by hand — ``now()`` reads it, the
    fake ``sleep`` advances it. No real time passes (MEA-09)."""

    def __init__(self) -> None:
        self._t = 0.0

    def now(self) -> float:
        return self._t

    def sleep(self, seconds: float) -> None:
        # The driver's only "wait" — advance the wall clock without sleeping,
        # so the budget is exercised deterministically.
        self._t += seconds


@dataclass
class FakeManager:
    """Records every capability the driver invokes, so a test asserts the
    sequence of recovery actions without a live session.

    ``send`` is **fire-and-forget** (the WP-007 wired contract): it acks the
    enqueue immediately and returns ``True``; the re-submitted turn's *outcome*
    arrives LATER, modelled here by re-driving the driver:

    - ``clears_after=N`` → the Nth re-submit "clears": the fake calls
      ``driver.note_turn_cleared()`` (mimicking the result event that genuinely
      completed the turn). Earlier re-submits re-feed the observed error into
      ``driver.observe()`` (mimicking the replayed turn erroring again).
    - ``clears_after=None`` → the blip never clears: every re-submit re-feeds the
      observed error into ``driver.observe()`` so the SAME retry sequence
      advances and the wall-clock budget accumulates on the driver — until
      ``next_delay`` returns ``None`` and the driver abandons + resets.

    The fake's ``observe`` re-entry is what models the async wiring: the driver
    must accumulate budget ACROSS observations, never inside one ``observe``.
    ``_resend_depth`` guards against an unbounded recursion if a driver bug ever
    failed to abandon (it raises instead of hanging the test)."""

    # send() acks the fire-and-forget enqueue. ``clears_after`` re-submits that
    # many times before the turn clears (note_turn_cleared); None = never clears.
    clears_after: int | None = None
    appended: list[ev.EventError] = field(default_factory=list)
    send_count: int = 0
    resume_count: int = 0
    reauth_count: int = 0
    reauth_ticket: ReauthTicket = field(
        default_factory=lambda: ReauthTicket(
            relogin_link="https://example.test/relogin?token=abc",
            completion_handle="reauth-1",
        )
    )
    # Wired by the test after construction so the fire-and-forget ``send`` can
    # re-drive the driver with the turn's later outcome (re-error / clear).
    driver: "RecoveryDriver | None" = None
    observed_error: "ev.EventError | None" = None
    _resend_depth: int = 0
    _max_resend_depth: int = 1000  # safety net: a non-abandoning driver bug

    def send(self) -> bool:
        self.send_count += 1
        # The enqueue is fire-and-forget: ack immediately, then model the
        # re-submitted turn's later outcome by re-driving the driver.
        if self.driver is None or self.observed_error is None:
            return True
        self._resend_depth += 1
        if self._resend_depth > self._max_resend_depth:
            raise AssertionError(
                "driver never abandoned a never-clearing blip — the wall-clock "
                "budget did not accumulate across observations (the defect)"
            )
        if self.clears_after is not None and self.send_count >= self.clears_after:
            # The replayed turn produced a genuine result → the sequence is over.
            self.driver.note_turn_cleared()
        else:
            # The replayed turn errored again → a fresh observation advances the
            # SAME retry sequence (the budget keeps accumulating on the driver).
            self.driver.observe(self.observed_error)
        return True

    def log_append(self, error: ev.EventError) -> None:
        self.appended.append(error)

    def reauth(self) -> ReauthTicket:
        self.reauth_count += 1
        return self.reauth_ticket

    def resume(self) -> None:
        self.resume_count += 1


def make_driver(
    manager: FakeManager,
    *,
    classifier=None,
    classify_failure=None,
    policy: RetryPolicy | None = None,
    clock: FakeClock | None = None,
    rng=None,
) -> RecoveryDriver:
    """Construct a driver wired to a FakeManager + fake clock, with a tiny
    sleep-free budget by default so the never-clears loop terminates fast."""
    clock = clock or FakeClock()
    tiny = policy or RetryPolicy(
        base_delay_seconds=1.0,
        max_delay_seconds=4.0,
        multiplier=2.0,
        jitter="full",
        total_budget_seconds=10.0,
    )
    driver = RecoveryDriver(
        send=manager.send,
        log_append=manager.log_append,
        reauth=manager.reauth,
        resume=manager.resume,
        classify_failure=classify_failure,
        classifier=classifier,
        policy=tiny,
        clock=clock.now,
        sleep=clock.sleep,
        rng=rng or random.Random(0).random,
    )
    # Wire the fire-and-forget ``send`` back to the driver so a re-submit can
    # model the replayed turn's later outcome (re-error / clear) — the async
    # wiring the budget state machine must survive.
    manager.driver = driver
    return driver


# A fake classifier that always returns one verdict (the per-branch driver
# tests pin the verdict; the real classify is swapped back in at Blue, CF-07).
def fixed_classifier(verdict: RecoveryClass):
    def _classify(error: ev.EventError, hint: RecoveryClass | None) -> RecoveryClass:
        return verdict

    return _classify


# ── acceptance #1 — transient-blip that clears → run survives ─────────────


def test_transient_blip_clears_run_survives() -> None:
    """A transient blip that clears on the first replay: the driver re-submits
    via the injected fire-and-forget ``send`` (no human restart), the replayed
    turn's genuine result resets the retry sequence (``note_turn_cleared``), the
    run survives, and it is NOT abandoned."""
    manager = FakeManager(clears_after=1)  # the 1st re-submit's turn clears
    driver = make_driver(
        manager, classifier=fixed_classifier(RecoveryClass.TRANSIENT_BLIP)
    )

    error = ev.EventError(category="protocol", code=ev.SOCKET_CLOSED, message="reset")
    manager.observed_error = error
    driver.observe(error)

    # The turn was re-submitted (recovery happened without a human).
    assert manager.send_count >= 1
    # No "abandoned" Event was emitted — the run survived.
    abandoned = [e for e in manager.appended if "abandon" in e.message.lower()]
    assert abandoned == []
    # The clear reset the retry sequence (a later, unrelated blip gets a fresh
    # budget) — the driver is no longer holding an in-progress retry start.
    assert driver._retry_started_at is None
    # The re-auth/resume paths were never touched (this is a blip, not a login).
    assert manager.reauth_count == 0
    assert manager.resume_count == 0


# ── acceptance #2 — transient-blip that never clears → abandoned at budget ─


def test_transient_blip_never_clears_abandoned_at_budget() -> None:
    """A transient blip that NEVER clears is retried against the wall-clock
    budget that **accumulates across observations** (the fire-and-forget wiring):
    each re-submit's replayed turn errors again and re-enters ``observe()``,
    advancing the SAME retry sequence; when ``next_delay`` returns None (budget
    exhausted) the driver abandons with a typed 'abandoned' ``error`` Event
    carrying the OBSERVED code — not a silent hang, and not an infinite retry.

    This is the #2 core promise (fail cleanly, never hang) at the unit level:
    the budget MUST live on the driver instance, so a never-clearing blip walks
    the curve to exhaustion and abandons exactly once."""
    manager = FakeManager(clears_after=None)  # never clears
    clock = FakeClock()
    driver = make_driver(
        manager,
        classifier=fixed_classifier(RecoveryClass.TRANSIENT_BLIP),
        clock=clock,
    )

    observed = ev.EventError(
        category="protocol", code=ev.SOCKET_CLOSED, message="reset"
    )
    manager.observed_error = observed
    driver.observe(observed)

    # It retried (sent at least once) then gave up — the budget accumulated
    # across the re-observations rather than resetting on each one.
    assert manager.send_count >= 1
    # A typed 'abandoned' Event was emitted exactly once, reusing the observed
    # code — never an infinite retry, never a second abandon.
    abandoned = [e for e in manager.appended if "abandon" in e.message.lower()]
    assert len(abandoned) == 1
    assert abandoned[0].code == observed.code
    assert "budget exhausted" in abandoned[0].message.lower()
    # The clock advanced to/over the budget (it did not hang forever).
    assert clock.now() >= 10.0
    # The retry sequence was reset after the abandon (a later blip starts fresh).
    assert driver._retry_started_at is None
    # Login paths untouched.
    assert manager.reauth_count == 0
    assert manager.resume_count == 0


# ── note_turn_cleared resets the budget so a LATER blip starts fresh ───────


def test_note_turn_cleared_resets_budget_for_a_later_blip() -> None:
    """A clean turn after some retries (``note_turn_cleared``) resets the retry
    sequence, so a LATER, unrelated transient blip gets a **fresh** wall-clock
    budget — the "transient blip that clears → survives, then a new blip retries
    on its own budget" semantics (the live wiring's reset hook).

    Without the reset, a single long-lived session would carry a stale,
    near-exhausted budget into every future blip and abandon prematurely. The
    reset is what keeps each independent blip's budget independent."""
    # First sequence: a blip that clears on the 2nd replay (one re-error, then a
    # clear) — so the driver does accumulate some elapsed before clearing.
    manager = FakeManager(clears_after=2)
    clock = FakeClock()
    driver = make_driver(
        manager,
        classifier=fixed_classifier(RecoveryClass.TRANSIENT_BLIP),
        clock=clock,
    )
    observed = ev.EventError(
        category="protocol", code=ev.SOCKET_CLOSED, message="reset"
    )
    manager.observed_error = observed
    driver.observe(observed)

    # The clear reset the sequence: no in-progress retry start lingers, and no
    # abandon fired (the run survived).
    assert driver._retry_started_at is None
    assert driver._retry_attempt == 0
    assert [e for e in manager.appended if "abandon" in e.message.lower()] == []
    # The clock advanced some (a real retry happened) but the budget is now
    # released, so a later blip is NOT inheriting an exhausted clock.
    cleared_at = clock.now()
    assert cleared_at > 0.0

    # A LATER, unrelated blip starts a brand-new sequence from "now": its start
    # is the current clock, attempt 0 — proving the budget is fresh.
    later = ev.EventError(category="protocol", code=ev.SOCKET_CLOSED, message="again")
    manager.observed_error = later
    manager.clears_after = manager.send_count + 1  # clears on its first replay
    driver.observe(later)
    # It scheduled a retry on a fresh budget (a "retry scheduled" notice landed
    # for the second blip) and survived again — never prematurely abandoned.
    assert [e for e in manager.appended if "abandon" in e.message.lower()] == []
    assert driver._retry_started_at is None  # the later blip also cleared + reset


# ── acceptance #3 — dead-end → abandoned immediately, budget NOT consulted ─


def test_dead_end_abandoned_without_burning_budget() -> None:
    """A dead-end is abandoned immediately with a typed ``error`` Event; the
    retry budget is NOT consulted (no re-submit, no backoff wait)."""
    manager = FakeManager()
    clock = FakeClock()
    driver = make_driver(
        manager,
        classifier=fixed_classifier(RecoveryClass.DEAD_END),
        clock=clock,
    )

    observed = ev.EventError(
        category="expected", code=ev.UNKNOWN_PROVIDER, message="declined"
    )
    driver.observe(observed)

    # Abandoned immediately: no turn re-submitted, no backoff wait.
    assert manager.send_count == 0
    assert clock.now() == 0.0  # budget never consulted → clock never advanced
    abandoned = [e for e in manager.appended if "abandon" in e.message.lower()]
    assert len(abandoned) == 1
    assert abandoned[0].code == observed.code
    assert manager.reauth_count == 0
    assert manager.resume_count == 0


# ── acceptance #4 — login-expired → pause → notify → resume ───────────────


def test_login_expired_pause_notify_resume_no_fabricated_completion() -> None:
    """A login-expiry calls ``reauth()`` once, emits a NOT_AUTHORIZED ``error``
    Event carrying the re-login link, PAUSES (does not burn the retry budget),
    and on ticket completion resumes via the existing ``resume`` path — the
    step is re-run, never reported done (no fabricated completion)."""
    manager = FakeManager()
    clock = FakeClock()
    driver = make_driver(
        manager,
        classifier=fixed_classifier(RecoveryClass.LOGIN_EXPIRED),
        clock=clock,
    )

    observed = ev.EventError(
        category="expected", code=ev.NOT_AUTHORIZED, message="auth expired"
    )
    driver.observe(observed)

    # reauth() called exactly once (one pending ticket per session, not re-fired).
    assert manager.reauth_count == 1
    # The notification is a NOT_AUTHORIZED error Event carrying the re-login link.
    notifications = [e for e in manager.appended if e.code == ev.NOT_AUTHORIZED]
    assert len(notifications) == 1
    assert manager.reauth_ticket.relogin_link in notifications[0].message
    # Paused, not retried: the budget was NOT burned.
    assert manager.send_count == 0
    assert clock.now() == 0.0
    # No 'abandoned' Event — login-expiry pauses, it does not fail the run.
    assert [e for e in manager.appended if "abandon" in e.message.lower()] == []

    # On ticket completion the driver resumes via the EXISTING resume path …
    driver.complete_reauth(manager.reauth_ticket)
    assert manager.resume_count == 1
    # … and never fabricates a completion: no 'result' is emitted by the driver;
    # the re-run produces it. The driver only triggers the resume.
    assert all(e.code != "RESULT_FABRICATED" for e in manager.appended)


def test_login_expired_reauth_failure_abandons_fail_safe() -> None:
    """If ``reauth()`` itself fails, the driver abandons as dead-end with a
    typed, observable ``error`` Event — fail-safe, it does NOT let the
    exception escape ``observe`` and it does NOT hang (TDD §Q12)."""

    def boom() -> ReauthTicket:
        raise RuntimeError("re-auth backend unreachable")

    manager = FakeManager()
    manager.reauth = boom  # type: ignore[assignment]
    driver = make_driver(
        manager, classifier=fixed_classifier(RecoveryClass.LOGIN_EXPIRED)
    )

    observed = ev.EventError(
        category="expected", code=ev.NOT_AUTHORIZED, message="auth expired"
    )
    # observe() must not raise — the failure is contained.
    driver.observe(observed)

    # A typed 'abandoned' Event was surfaced (observable, not a silent hang),
    # and the run was not left paused on a phantom ticket.
    abandoned = [e for e in manager.appended if "abandon" in e.message.lower()]
    assert len(abandoned) == 1
    assert abandoned[0].code == observed.code
    assert manager.resume_count == 0


# ── acceptance #5 — process-death STDIN_BROKEN → driver no-ops ────────────


def test_process_death_error_is_noop() -> None:
    """A STDIN_BROKEN 'died mid-turn' error is the LifecycleManager's job
    (restart-on-death). The recovery driver no-ops on it — no classify, no
    retry, no abandon, no resume — so the two seams never double-handle."""
    manager = FakeManager()
    clock = FakeClock()

    # A classifier that would raise if called, proving the driver short-circuits
    # BEFORE classification for process-death.
    def exploding_classifier(error, hint):  # pragma: no cover - must not run
        raise AssertionError("classifier must not run for a process-death error")

    driver = make_driver(manager, classifier=exploding_classifier, clock=clock)

    observed = ev.EventError(
        category="protocol", code=ev.STDIN_BROKEN, message="died mid-turn"
    )
    driver.observe(observed)

    # Pure no-op: nothing happened at all.
    assert manager.appended == []
    assert manager.send_count == 0
    assert manager.resume_count == 0
    assert manager.reauth_count == 0
    assert clock.now() == 0.0


# ── Blue — mock→real classifier conformance (CF-07) ───────────────────────


def test_driver_conforms_with_the_real_classifier() -> None:
    """The CF-07 swap step: drive each branch through the **real**
    ``classifier.classify`` (WP-002) — no fake classifier injected — and
    confirm the driver routes identically. This proves the driver's contract
    with the classifier is the real seam, not an artefact of the fakes.

    Mapping under the real neutral arbiter (ADR-003): a ``protocol`` error →
    transient-blip; ``expected``/``NOT_AUTHORIZED`` → login-expired; any other
    ``expected`` or an ``internal`` error → dead-end.
    """
    # protocol → transient-blip → re-submitted, survives when it clears.
    blip_mgr = FakeManager(clears_after=1)
    blip_driver = make_driver(blip_mgr)  # classifier=None → the REAL classify
    blip_error = ev.EventError(
        category="protocol", code=ev.SOCKET_CLOSED, message="reset"
    )
    blip_mgr.observed_error = blip_error
    blip_driver.observe(blip_error)
    assert blip_mgr.send_count >= 1
    assert [e for e in blip_mgr.appended if "abandon" in e.message.lower()] == []

    # expected/NOT_AUTHORIZED → login-expired → reauth + NOT_AUTHORIZED notice.
    login_mgr = FakeManager()
    login_driver = make_driver(login_mgr)
    login_driver.observe(
        ev.EventError(category="expected", code=ev.NOT_AUTHORIZED, message="expired")
    )
    assert login_mgr.reauth_count == 1
    assert [e for e in login_mgr.appended if e.code == ev.NOT_AUTHORIZED]
    assert login_mgr.send_count == 0  # paused, budget not burned

    # expected (other) → dead-end → abandoned immediately, budget not consulted.
    dead_mgr = FakeManager()
    dead_clock = FakeClock()
    dead_driver = make_driver(dead_mgr, clock=dead_clock)
    dead_driver.observe(
        ev.EventError(category="expected", code=ev.NO_SESSION, message="gone")
    )
    assert dead_mgr.send_count == 0
    assert dead_clock.now() == 0.0
    assert [e for e in dead_mgr.appended if "abandon" in e.message.lower()]


def test_resume_emits_no_result_before_the_rerun_produces_one() -> None:
    """No fabricated completion (ADR-004 / ADE ADR-002): the driver's resume
    path triggers the existing same-key/same-log restart and emits **no**
    ``result`` Event of its own — the re-run produces the result. The driver
    only ever appends ``error``-kind payloads (notifications / abandons), never
    a result on the run's behalf."""
    manager = FakeManager()
    driver = make_driver(
        manager, classifier=fixed_classifier(RecoveryClass.LOGIN_EXPIRED)
    )
    driver.observe(
        ev.EventError(category="expected", code=ev.NOT_AUTHORIZED, message="expired")
    )
    driver.complete_reauth(manager.reauth_ticket)

    # Resume was triggered exactly once via the existing path …
    assert manager.resume_count == 1
    # … and the driver fabricated nothing: every Event it appended is an
    # EventError (an error-kind payload), never a TurnResult.
    assert all(isinstance(e, ev.EventError) for e in manager.appended)


# ── CH-01KTMK hardening FIX 2 — the absolute (lifetime) retry ceiling ──────
#
# The per-sequence wall-clock window (``total_budget_seconds``) is reset on
# every genuine clear (``note_turn_cleared``). A pathological provider that
# alternates result/error therefore resets that window every cycle, so the
# ~12-min give-up guarantee is evadable over a long-lived session — each window
# honours the cap, but the total retry count is unbounded. The fix adds an
# ABSOLUTE ceiling a turn-clear does NOT reset: a per-session ``_lifetime_retries``
# counter that accumulates across sequences, capped by
# ``RetryPolicy.max_lifetime_retries``. When the lifetime cap is hit the driver
# abandons with a typed, observable "absolute retry ceiling exceeded" Event.


class AlternatingProvider(FakeManager):
    """A pathological provider that alternates result/error to try to evade the
    per-sequence wall-clock window (the FIX 2 abuse case).

    Each fire-and-forget ``send`` "clears" the replayed turn immediately
    (``note_turn_cleared`` — the per-sequence window resets), then, while the
    abuse budget remains, re-feeds a *fresh* error into ``observe`` — modelling a
    provider that lets one retry succeed, then fails the very next turn. Without
    an absolute ceiling this loops forever (every clear refunds the window); with
    the ceiling it must abandon once the lifetime retry count is exhausted."""

    cycles_remaining: int = 50

    def send(self) -> bool:
        self.send_count += 1
        if self.driver is None or self.observed_error is None:
            return True
        # The replayed turn clears (the per-sequence window resets) …
        self.driver.note_turn_cleared()
        # … then the provider fails the very next turn (a fresh, unrelated blip)
        # for as long as the abuse budget remains. A safety bound on the re-entry
        # depth so a non-abandoning driver bug fails the test instead of hanging.
        if self.cycles_remaining > 0:
            self.cycles_remaining -= 1
            self.driver.observe(self.observed_error)
        return True


def test_absolute_ceiling_survives_turn_clears_and_abandons() -> None:
    """A provider that alternates result/error — refunding the per-sequence
    wall-clock window on every clear — is STILL bounded by the absolute lifetime
    retry ceiling, which ``note_turn_cleared`` does NOT reset. The driver abandons
    with a typed, observable "absolute retry ceiling" Event once the lifetime cap
    is hit, instead of retrying unboundedly over a long-lived session.

    This is the FIX 2 core promise: the ~12-min per-window give-up guarantee is no
    longer evadable by alternating result/error — there is a hard lifetime bound a
    turn-clear cannot reset."""
    # A generous per-sequence window (never the binding constraint here) + a tiny
    # absolute lifetime ceiling so the abuse loop terminates fast and deterministically.
    policy = RetryPolicy(
        base_delay_seconds=1.0,
        max_delay_seconds=4.0,
        multiplier=2.0,
        jitter="full",
        total_budget_seconds=10_000.0,  # huge: the per-window cap never binds
        max_lifetime_retries=5,  # the binding absolute ceiling
    )
    manager = AlternatingProvider()
    clock = FakeClock()
    driver = make_driver(
        manager,
        classifier=fixed_classifier(RecoveryClass.TRANSIENT_BLIP),
        policy=policy,
        clock=clock,
    )

    observed = ev.EventError(
        category="protocol", code=ev.SOCKET_CLOSED, message="reset"
    )
    manager.observed_error = observed
    driver.observe(observed)

    # The absolute ceiling fired: a typed "absolute retry ceiling" abandon Event
    # was emitted exactly once, reusing the observed code — the give-up guarantee
    # held despite every per-sequence window being refunded by a clear.
    ceiling_abandons = [
        e
        for e in manager.appended
        if "abandon" in e.message.lower()
        and "absolute" in e.message.lower()
        and "ceiling" in e.message.lower()
    ]
    assert len(ceiling_abandons) == 1, [e.message for e in manager.appended]
    assert ceiling_abandons[0].code == observed.code
    # The driver stopped retrying at the cap (it did not loop forever): the number
    # of scheduled retries is bounded by the lifetime ceiling, not the 50-cycle
    # abuse budget.
    retries = [e for e in manager.appended if "retry scheduled" in e.message.lower()]
    assert len(retries) <= policy.max_lifetime_retries


def test_turn_clear_still_refunds_the_per_window_budget_normally() -> None:
    """The normal-case semantics are PRESERVED (FIX 2 must not break recovery): a
    genuine transient blip that clears, followed much later by an unrelated blip,
    still recovers normally — the per-sequence wall-clock window still resets on a
    clear. Only the absolute lifetime ceiling is non-resettable, and with a
    generous default it never binds for legitimate use.

    Here two independent blips each clear on their first replay, well under the
    lifetime ceiling: neither is abandoned, and the absolute ceiling never fires."""
    policy = RetryPolicy(
        base_delay_seconds=1.0,
        max_delay_seconds=4.0,
        multiplier=2.0,
        jitter="full",
        total_budget_seconds=10.0,
        max_lifetime_retries=100,  # generous: never binds for two clean blips
    )
    manager = FakeManager(clears_after=1)
    clock = FakeClock()
    driver = make_driver(
        manager,
        classifier=fixed_classifier(RecoveryClass.TRANSIENT_BLIP),
        policy=policy,
        clock=clock,
    )

    first = ev.EventError(category="protocol", code=ev.SOCKET_CLOSED, message="one")
    manager.observed_error = first
    driver.observe(first)
    # The first blip cleared: the per-sequence window reset, nothing abandoned.
    assert driver._retry_started_at is None
    assert [e for e in manager.appended if "abandon" in e.message.lower()] == []

    # A LATER, unrelated blip clears on its first replay too — still no abandon,
    # the absolute ceiling did not fire (a legitimate run is unbounded by it).
    later = ev.EventError(category="protocol", code=ev.SOCKET_CLOSED, message="two")
    manager.observed_error = later
    manager.clears_after = manager.send_count + 1
    driver.observe(later)
    assert [e for e in manager.appended if "abandon" in e.message.lower()] == []


def test_in_flight_guard_admits_one_then_coalesces_until_released() -> None:
    """The driver's one-recovery-thread-in-flight guard (FIX 1) admits the first
    caller, COALESCES every subsequent caller (returns ``False`` — no second
    thread) while a recovery is in flight, and re-opens once ``end_recovery``
    releases the slot. This is the driver-level contract the manager's
    ``_on_error_event`` dispatch gate calls."""
    manager = FakeManager()
    driver = make_driver(
        manager, classifier=fixed_classifier(RecoveryClass.TRANSIENT_BLIP)
    )

    # First caller wins the slot …
    assert driver.try_begin_recovery() is True
    # … every concurrent caller coalesces (no second recovery thread spawned).
    assert driver.try_begin_recovery() is False
    assert driver.try_begin_recovery() is False
    # Releasing re-opens the slot for the next recovery.
    driver.end_recovery()
    assert driver.try_begin_recovery() is True
    # end_recovery is idempotent (safe to call from the manager's finally even on
    # a path that did not win the slot).
    driver.end_recovery()
    driver.end_recovery()
    assert driver.try_begin_recovery() is True


def test_default_policy_has_a_generous_absolute_ceiling() -> None:
    """``DEFAULT_RETRY_POLICY`` carries a sensible absolute ceiling that bounds
    abuse while being generous for legitimate use (FIX 2 default choice).

    The default is in the low hundreds — enough that no legitimate long-lived
    session ever hits it, small enough that a pathological alternating provider is
    bounded to a finite total retry count."""
    from _session_manager.recovery import DEFAULT_RETRY_POLICY

    assert DEFAULT_RETRY_POLICY.max_lifetime_retries >= 50
    assert DEFAULT_RETRY_POLICY.max_lifetime_retries <= 1000
