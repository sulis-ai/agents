"""WP-005 — tests for the ``RecoveryDriver`` (the turn-level Armor primitive).

Contract: ``.architecture/automation-reliability-recovery/`` ADR-001 (the
driver sits *around* the lifecycle, mirroring ``LifecycleManager``), ADR-002
(the injected ``RetryPolicy`` + wall-clock budget against an injected clock),
ADR-003 (provider-neutral classification + the thin per-provider detection
hint), ADR-004 (login-expired pause→notify→resume reusing the existing
``supports_resume`` + ``resume_ref`` path, no fabricated completion).

The driver is built against **fakes** (ADR-001 — it consumes injected manager
capabilities, never the live ``SessionManager``):

- a fake ``send`` that re-submits a turn and reports whether the turn then
  cleared (``True``) or failed again (``False``) — the blip-clears / never-
  clears distinction;
- a fake ``log_append`` recording every recovery action as an
  :class:`~_session_manager.events.EventError` on the existing log surface
  (no new stream, §3.5);
- a fake ``reauth`` returning a :class:`~_session_manager.recovery.ReauthTicket`;
- a fake ``resume`` standing in for the existing same-key/same-log restart;
- a fake monotonic ``clock`` + a no-op ``sleep`` that advances it, so the
  wall-clock budget is exercised with **no real sleeping** (MEA-09);
- a seeded ``rng`` so the jittered backoff is deterministic.

One test per acceptance branch (the WP's Definition of Done). In RED these
fail because ``RecoveryDriver`` does not exist yet.
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
    sequence of recovery actions without a live session."""

    # send() returns True when the re-submitted turn clears, False when it
    # fails again. ``clears_after`` re-submits that many times before clearing;
    # None means it never clears.
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

    def send(self) -> bool:
        self.send_count += 1
        if self.clears_after is None:
            return False
        return self.send_count >= self.clears_after

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
    return RecoveryDriver(
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


# A fake classifier that always returns one verdict (the per-branch driver
# tests pin the verdict; the real classify is swapped back in at Blue, CF-07).
def fixed_classifier(verdict: RecoveryClass):
    def _classify(error: ev.EventError, hint: RecoveryClass | None) -> RecoveryClass:
        return verdict

    return _classify


# ── acceptance #1 — transient-blip that clears → run survives ─────────────


def test_transient_blip_clears_run_survives() -> None:
    """A transient blip that clears on the second attempt: the driver
    re-submits via the injected ``send`` (no human restart), the run survives,
    and it is NOT abandoned."""
    manager = FakeManager(clears_after=2)  # fails once, clears on the 2nd send
    driver = make_driver(
        manager, classifier=fixed_classifier(RecoveryClass.TRANSIENT_BLIP)
    )

    error = ev.EventError(category="protocol", code=ev.SOCKET_CLOSED, message="reset")
    driver.observe(error)

    # The turn was re-submitted (recovery happened without a human).
    assert manager.send_count >= 1
    # No "abandoned" Event was emitted — the run survived.
    abandoned = [e for e in manager.appended if "abandon" in e.message.lower()]
    assert abandoned == []
    # The re-auth/resume paths were never touched (this is a blip, not a login).
    assert manager.reauth_count == 0
    assert manager.resume_count == 0


# ── acceptance #2 — transient-blip that never clears → abandoned at budget ─


def test_transient_blip_never_clears_abandoned_at_budget() -> None:
    """A transient blip that never clears is retried against the wall-clock
    budget; when ``next_delay`` returns None (budget exhausted) the driver
    abandons with a typed 'abandoned' ``error`` Event carrying the OBSERVED
    code — not a silent hang."""
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
    driver.observe(observed)

    # It retried (sent at least once) then gave up.
    assert manager.send_count >= 1
    # A typed 'abandoned' Event was emitted, reusing the observed code.
    abandoned = [e for e in manager.appended if "abandon" in e.message.lower()]
    assert len(abandoned) == 1
    assert abandoned[0].code == observed.code
    # The clock advanced to/over the budget (it did not hang forever).
    assert clock.now() >= 10.0
    # Login paths untouched.
    assert manager.reauth_count == 0
    assert manager.resume_count == 0


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
    blip_driver.observe(
        ev.EventError(category="protocol", code=ev.SOCKET_CLOSED, message="reset")
    )
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
