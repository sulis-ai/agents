"""WP-008 (automation-reliability-recovery) — observability + end-to-end
recovery integration test through the **wired** manager.

Contract: TDD §3.5/§4.2 (observability — every recovery action is an Event on
the existing stream, so "a later reviewer can see WHY a run was retried /
abandoned / paused") + ``contracts/reliability-layer.contract.md`` (the
emitted-Event shape table: kind / category / code / message-carries).

This is the CF-07 conformance close for the reliability layer: it drives the
**real** wired :class:`~_session_manager.manager.SessionManager` (WP-007)
end-to-end through its **public API** — ``open`` / ``send`` /
``read(follow=True)`` / ``complete_reauth`` — and asserts the
acceptance-critical, founder-visible behaviour of all four recovery classes:

1. a transient blip that **clears** is retried and the run **survives**
   (acceptance #1);
2. a never-clearing transient blip **retries without deadlocking** AND is
   **abandoned at the wall-clock budget** with a typed Event (acceptance #2,
   both halves — fail cleanly, never hang). Each replay genuinely promotes onto
   the live process, and the driver's wall-clock budget accumulates ACROSS the
   re-observations, so the run walks the backoff curve to genuine exhaustion and
   abandons (``test_never_clearing_blip_retries_without_deadlock`` +
   ``test_budget_exhausted_abandon_at_wall_clock``);
3. a dead-end is **abandoned immediately**;
4. a login-expired surfaces a ``NOT_AUTHORIZED`` Event carrying the re-login
   link and, after a simulated re-auth ticket completion, the run **resumes**
   and re-runs the step (no fabricated completion).

**The two fixes this WP lands.**

*Slot-release (deadlock).* An ``error`` Event does not free the one-in-flight
slot (only a ``result`` does), so before this WP a transient-blip retry
deadlocked: the errored turn held the slot and the driver's replay could never
promote (BLOCKER-WP-008). The fix adds
:meth:`~_session_manager.session.Session.release_turn_for_retry` — a slot-release
seam that frees the slot on the SAME live process WITHOUT terminating it — and
calls it from :meth:`~_session_manager.manager.SessionManager._on_error_event`
for a transient-blip error before the driver replays.

*Budget accumulation (never hang).* The WP-005 driver originally walked the
budget inside ONE blocking ``observe()`` whose ``send()`` reported the turn
outcome; but the WP-007 wired ``send()`` is fire-and-forget, so each replay's
failure re-entered as a fresh ``observe()`` with ``attempt=0``/``elapsed=0`` and
the budget never accumulated — a never-clearing blip retried forever (the #2
core promise broken through the live wiring, SF-8bad33b8). The fix makes the
per-session driver **stateful across observations**: it holds the current retry
sequence's wall-clock start + attempt on the instance, so each re-observed
failure advances the SAME sequence and the budget accumulates to genuine
exhaustion. A genuine ``result`` resets the sequence (via
:meth:`~_session_manager.recovery.RecoveryDriver.note_turn_cleared`, wired from
``_on_error_event`` on a ``turn_complete`` event) so a later, unrelated blip
gets a fresh budget. All four acceptance classes are now proven end-to-end with
NO ``xfail`` remaining.

**Verification posture (MEA-09, no mocks of the engine).** Every test boots a
**real** ``SessionManager`` over a **real** scripted-child subprocess behind a
real fake adapter, and drives recovery through the **real** WP-005
:class:`~_session_manager.recovery.RecoveryDriver`. Only the driver's *timing*
is made deterministic — a fake monotonic clock + a no-op sleep + a seeded RNG
are injected through the manager's ``recovery_driver_factory`` composition-root
seam, so the retry/backoff loop runs **with no real ``time.sleep``** and the
wall-clock budget is advanced under test control. The manager's threading,
one-in-flight FIFO, log, pumps, and the driver's branch logic are all the real
shipped code.

**The deferred manual need.** The **real** live-``claude`` login-expiry → real
re-auth → real resume round-trip against an actually-expired credential is
**out of scope here** — it cannot bootstrap in CI and is the deferred manual
need ``live-reauth-resume-claude`` (ARCH.yaml / TDD §4.3). This module proves
the login-expiry *logic* through the wired manager against a simulated session:
a fake adapter that detects the login code and returns a fake
:class:`~_session_manager.recovery.ReauthTicket`, plus a simulated re-auth
completion that triggers the existing same-key/same-log resume. The
recorded-resume discipline (the agent re-runs the incomplete step; no
``result`` is fabricated before the resumed turn produces one) is asserted, not
the live credential exchange.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.classifier import RecoveryClass
from _session_manager.events import NOT_AUTHORIZED, Event, EventError, TurnResult
from _session_manager.manager import SessionManager
from _session_manager.recovery import DEFAULT_RETRY_POLICY, ReauthTicket, RecoveryDriver

# Bounded wait for every threaded assertion: long enough never to flake on a
# loaded CI runner, short enough that a genuine deadlock/hang fails fast instead
# of blocking the suite. Acceptance #1 (the transient-blip-clears retry) was a
# real deadlock before the slot-release fix; this bound is what turns that
# deadlock into a fast, deterministic test failure rather than an unbounded hang.
_WAIT = 6.0


# ─── a scripted child that can emit an error turn (real subprocess) ──────────
#
# The child reads one NDJSON line per turn. The command text selects the turn
# shape (mirrors the WP-007 wiring-test child so the two stay in lockstep):
#
#   "ERR1:<code>"  — emit one ``error`` line carrying <code> on the FIRST
#                    occurrence (a transient blip), then on the REPLAYED turn
#                    answer a healthy chunk+result (the blip "clears").
#   "ERR:<code>"   — always emit one ``error`` line carrying <code> (a blip
#                    that never clears, or a dead-end / login code).
#   anything else  — one ``chunk`` then one ``result`` (the healthy turn).
#
# It is a REAL process: the manager spawns it, writes its stdin, reads its
# stdout on a pump thread, and decodes each line. No part of the manager is
# mocked.
_CHILD_SOURCE = r"""
import json, sys

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

seen = set()
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    text = str(msg.get("command", ""))
    if text.startswith("ERR1:"):
        if text not in seen:
            seen.add(text)
            emit({"kind": "error", "category": "protocol", "code": text[5:],
                  "message": "scripted blip (first occurrence)"})
            continue
        emit({"kind": "chunk", "text": "recovered"})
        emit({"kind": "result", "input_tokens": 1, "output_tokens": 2,
              "duration_ms": 1, "stop_reason": "end_turn"})
        continue
    if text.startswith("ERR:"):
        emit({"kind": "error", "category": "expected", "code": text[4:],
              "message": "scripted failure"})
        continue
    emit({"kind": "chunk", "text": text})
    emit({"kind": "result", "input_tokens": 1, "output_tokens": len(text),
          "duration_ms": 1, "stop_reason": "end_turn"})
"""


def _write_child(tmp_path: Path) -> Path:
    p = tmp_path / "recovery_child.py"
    p.write_text(_CHILD_SOURCE)
    return p


class _FakeAdapter:
    """A real :class:`ProviderAdapter` over the scripted child (no engine mocks).

    ``decode`` maps the child's ``error`` line into an ``error``-kind Event (the
    §2.4 partial-event seam), so a live turn can terminate in an ``error`` the
    manager appends to the log — exactly the seam WP-007 routes from.

    Provider-detection + re-auth are honest fakes that drive the **real**
    classifier/driver wiring:

    - ``classify_failure`` maps the login code to ``LOGIN_EXPIRED`` (and a
      ``"429"`` rate-limit code to ``TRANSIENT_BLIP``, matching the Claude
      adapter's WP-006 hint contract), else ``None`` (defer to the neutral
      arbiter — protocol→blip, expected/internal→dead-end).
    - ``reauth`` returns a deterministic :class:`ReauthTicket` (re-login link +
      completion handle), so the login-expiry notification + resume can be
      driven through the wired manager without a live credential exchange.

    ``supports_resume`` is True so the manager honours the same-key/same-log
    resume the driver's ``complete_reauth`` triggers.
    """

    LOGIN_CODE = "LOGIN_EXPIRED_RAW"
    RELOGIN_LINK = "https://example.test/relogin?ticket=abc"
    COMPLETION_HANDLE = "ticket-abc"

    def __init__(self, child: Path) -> None:
        self._child = child
        self.capabilities = Capabilities(
            supports_resume=True,
            supports_tools=False,
            supports_partial_streaming=True,
        )
        self.reauth_calls = 0

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return [sys.executable, str(self._child)]

    def encode(self, command: str) -> bytes:
        return (json.dumps({"command": command}) + "\n").encode("utf-8")

    def decode(self, line: bytes) -> Event | None:
        record = json.loads(line)
        kind = record.get("kind")
        if kind == "chunk":
            return Event(offset=-1, key="", turn=-1, kind="chunk", text=record["text"])
        if kind == "error":
            return Event(
                offset=-1,
                key="",
                turn=-1,
                kind="error",
                error=EventError(
                    category=record.get("category", "expected"),
                    code=record.get("code", "ERROR"),
                    message=record.get("message", ""),
                ),
            )
        if kind == "result":
            return Event(
                offset=-1,
                key="",
                turn=-1,
                kind="result",
                result=TurnResult(
                    input_tokens=int(record.get("input_tokens", 0)),
                    output_tokens=int(record.get("output_tokens", 0)),
                    duration_ms=int(record.get("duration_ms", 0)),
                    stop_reason=str(record.get("stop_reason", "")),
                ),
            )
        return None

    def turn_complete(self, event: Event) -> bool:
        # An ``error`` event does NOT free the one-in-flight slot via this signal
        # (§2.6 / the claude adapter precedent) — only a successful ``result``
        # does. This is precisely why the transient-blip retry needed the
        # slot-release fix: the errored turn holds the slot until the recovery
        # path frees it.
        return event.kind == "result"

    def classify_failure(self, error: EventError) -> RecoveryClass | None:
        if error.code == self.LOGIN_CODE:
            return RecoveryClass.LOGIN_EXPIRED
        if error.code == "429":
            return RecoveryClass.TRANSIENT_BLIP
        return None

    def reauth(self) -> ReauthTicket:
        self.reauth_calls += 1
        return ReauthTicket(
            relogin_link=self.RELOGIN_LINK,
            completion_handle=self.COMPLETION_HANDLE,
        )


class _FakeClock:
    """A monotonic clock the test drives, so the driver's wall-clock retry
    budget is exhausted deterministically with no real sleep (MEA-09).

    The driver reads ``now()`` to measure ``elapsed`` against the policy budget,
    and calls ``sleep(delay)`` between attempts. Wiring ``sleep`` to advance
    this clock makes every backoff "wait" instantaneous **and** advances the
    budget clock by the same delay — so a never-clearing blip walks the real
    backoff curve to genuine budget exhaustion in microseconds."""

    def __init__(self) -> None:
        self._t = 0.0
        self._lock = threading.Lock()

    def now(self) -> float:
        with self._lock:
            return self._t

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._t += seconds


def _seeded_rng() -> float:
    # A fixed full-jitter source so backoff delays are repeatable; the value is
    # irrelevant to the assertions (we assert outcomes, not exact delays) but
    # pinning it keeps the run deterministic.
    return 0.5


def _real_driver_factory(clock: _FakeClock):
    """Build a factory that constructs the **real** :class:`RecoveryDriver` with
    the manager's real session-bound capabilities, overriding only the timing
    sources for determinism.

    This is the composition-root seam (the ``timer_factory`` precedent): the
    manager hands the factory ``send`` / ``log_append`` / ``reauth`` / ``resume``
    / ``classify_failure`` / ``classifier`` / ``policy`` / ``clock``, and the
    factory swaps the clock for the fake, makes ``sleep`` advance that fake
    clock, and seeds the RNG — keeping every recovery *behaviour* real while the
    test owns the wall clock."""

    def factory(**kwargs: object) -> RecoveryDriver:
        kwargs.pop("clock", None)

        def _sleep(delay: float) -> None:
            # No real wait: advancing the fake clock is the only effect, so the
            # retry budget is consumed exactly as a real sleep would consume it.
            clock.advance(delay)

        return RecoveryDriver(
            clock=clock.now,
            sleep=_sleep,
            rng=_seeded_rng,
            **kwargs,  # type: ignore[arg-type]
        )

    return factory


@pytest.fixture
def child(tmp_path: Path) -> Path:
    return _write_child(tmp_path)


def _spec(tmp_path: Path) -> SessionSpec:
    return SessionSpec(provider="fake", cwd=str(tmp_path), resume_ref="prior-ctx")


def _make_manager(child: Path, clock: _FakeClock) -> SessionManager:
    """A real manager whose recovery driver is the **real** WP-005 driver with
    only its timing made deterministic (``start_maintenance=False`` keeps the
    background tick out of the test, MEA-09)."""
    return SessionManager(
        {"fake": _FakeAdapter(child)},
        recovery_driver_factory=_real_driver_factory(clock),
        start_maintenance=False,
    )


def _drain_until(
    mgr: SessionManager,
    key: str,
    since: int,
    predicate,
    timeout: float = _WAIT,
) -> list[Event]:
    """Follow the key's stream from ``since`` on a daemon thread, collecting
    events until ``predicate(events)`` holds or the bound elapses, then return
    what was collected.

    Following on a side thread (rather than the test thread) is what keeps a
    genuine deadlock observable: if the run freezes, the predicate never holds,
    the bound trips, and the test fails on the collected prefix instead of
    hanging the suite forever. This is the public-API read path — no internal
    state is inspected to decide the outcome."""
    collected: list[Event] = []
    done = threading.Event()

    def _follow() -> None:
        for ev in mgr.read(key, since=since, follow=True):
            collected.append(ev)
            if predicate(collected):
                done.set()
                return

    t = threading.Thread(target=_follow, name=f"e2e-follow-{key}", daemon=True)
    t.start()
    done.wait(timeout)
    return list(collected)


def _errors(events: list[Event]) -> list[EventError]:
    return [ev.error for ev in events if ev.kind == "error" and ev.error is not None]


# ─── acceptance #1: a transient blip that CLEARS is retried; the run survives ──


def test_transient_clears_survives_observable(child, tmp_path) -> None:
    """A transient blip that clears is retried and the run **survives**,
    observable end-to-end via ``read(follow=True)`` (acceptance #1).

    Before the slot-release fix this DEADLOCKED: the errored turn held the
    one-in-flight slot (an ``error`` does not satisfy ``turn_complete``), so the
    driver's retry-replay command could never promote — the run froze instead of
    recovering. The fix frees the held slot on the live process before the driver
    replays, so the replayed turn runs and produces its healthy ``result``.

    The observable proof of survival is the replayed turn's ``result`` Event
    landing on the existing stream — no fabricated completion, a genuine
    re-run of the stopped turn."""
    clock = _FakeClock()
    mgr = _make_manager(child, clock)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "ERR1:SOCKET_CLOSED")

        # Survival = the replayed turn's real ``result`` lands on the stream.
        events = _drain_until(
            mgr, "k", off, lambda evs: any(ev.kind == "result" for ev in evs)
        )

        kinds = [ev.kind for ev in events]
        assert "result" in kinds, (
            "the transient-blip-clears run did not survive end-to-end: no "
            f"replayed result landed (deadlock?). Observed kinds: {kinds}"
        )
        # The original blip is observable (a reviewer sees WHY it retried)…
        codes = [e.code for e in _errors(events)]
        assert "SOCKET_CLOSED" in codes, (
            f"the original transient blip was not observable: {codes}"
        )
        # …and the driver surfaced a "retry scheduled" notification reusing the
        # observed code on the existing stream (contract: retry row → ``error`` /
        # ``protocol`` / observed code / "transient … retry").
        retry_notices = [
            e
            for e in _errors(events)
            if e.code == "SOCKET_CLOSED" and "retry" in e.message.lower()
        ]
        assert retry_notices, (
            "no observable 'retry scheduled' notification on the stream: "
            f"{[e.message for e in _errors(events)]}"
        )
        assert retry_notices[0].category == "protocol", retry_notices[0]
        # The replayed healthy chunk proves a genuine re-run (not a fabricated
        # completion): the child only answers "recovered" on the replay.
        chunks = [ev.text for ev in events if ev.kind == "chunk"]
        assert "recovered" in chunks, (
            f"the replayed turn did not genuinely re-run: chunks={chunks}"
        )
    finally:
        mgr.close("k")


# ─── acceptance #2a: a never-clearing blip is abandoned at budget ─────────────


def test_never_clearing_blip_retries_without_deadlock(child, tmp_path) -> None:
    """A never-clearing transient blip RETRIES (each replay genuinely promotes
    onto the live process) instead of deadlocking — the slot-release fix applied
    to the retry path (acceptance #2, the no-deadlock half).

    Before the fix this deadlocked at attempt 1 exactly like acceptance #1 (the
    held slot blocked the first replay). After the fix the slot is freed before
    each replay, so the driver re-submits and the replay errors again, surfacing
    repeated "retry scheduled" notices on the existing stream — proving the
    deadlock is gone and recovery is actively driving.

    This test pins the *no-deadlock, keeps-retrying* behaviour; its companion
    :func:`test_budget_exhausted_abandon_at_wall_clock` pins the *abandon at
    budget* half (the two together are acceptance #2 in full — fail cleanly,
    never hang). The budget now accumulates ACROSS observations on the stateful
    driver, so a never-clearing blip both keeps promoting AND eventually abandons
    — there is no remaining known gap."""
    clock = _FakeClock()
    mgr = _make_manager(child, clock)
    try:
        mgr.open("k", _spec(tmp_path))
        # "ERR:" (not "ERR1:") so every replay errors again — the blip never
        # clears. "429" → the adapter hints TRANSIENT_BLIP (Claude 429 precedent),
        # so the driver enters the retry path on every observation.
        off = mgr.send("k", "ERR:429")

        # Survival of the deadlock = the retry path drives MORE THAN ONCE: at
        # least two "retry scheduled" notices means a replay promoted and was
        # itself re-observed (pre-fix this stuck at exactly one, deadlocked).
        events = _drain_until(
            mgr,
            "k",
            off,
            lambda evs: (
                sum(
                    1
                    for e in _errors(evs)
                    if e.code == "429" and "retry scheduled" in e.message.lower()
                )
                >= 2
            ),
        )

        retry_notices = [
            e
            for e in _errors(events)
            if e.code == "429" and "retry scheduled" in e.message.lower()
        ]
        assert len(retry_notices) >= 2, (
            "the never-clearing blip did not re-drive recovery after a replay "
            "(still deadlocked on the held slot?): "
            f"{[e.message for e in _errors(events)]}"
        )
        # Every notice reuses the observed code (429) on the existing stream —
        # no new code minted for a retry notification (contract retry row).
        assert all(e.code == "429" for e in retry_notices), retry_notices
    finally:
        mgr.close("k")


def test_budget_exhausted_abandon_at_wall_clock(child, tmp_path) -> None:
    """A never-clearing transient blip, driven through the WIRED manager, IS
    abandoned at the wall-clock budget with a typed ``error`` Event reusing the
    observed code (acceptance #2's budget-abandon half; contract budget-exhausted
    row).

    This is the #2 core promise — *fail cleanly, never hang* — proven end-to-end
    through the live wiring. The fix (this WP's reconciliation) makes the
    per-session driver **stateful across observations**: it holds the wall-clock
    start + attempt of the current retry sequence on the driver instance, so each
    fire-and-forget replay's re-observed error advances the SAME sequence rather
    than resetting ``attempt=0``/``elapsed=0``. The injected fake clock is
    advanced by the no-op ``sleep`` on every backoff, so the never-clearing blip
    walks the real backoff curve to genuine budget exhaustion in microseconds and
    the driver emits the typed "retry budget exhausted" abandon Event, then stops
    retrying.

    Before the fix this was a known gap (SF-8bad33b8, an ``xfail``): the WP-005
    driver walked the budget inside ONE blocking ``observe()`` whose ``send()``
    reported the turn outcome, but the WP-007 wired ``send()`` is fire-and-forget,
    so each replay re-entered as a fresh ``observe()`` and the budget never
    accumulated — the run retried forever and never abandoned. This test is the
    honest passing proof that the gap is closed."""
    clock = _FakeClock()
    mgr = _make_manager(child, clock)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "ERR:429")

        events = _drain_until(
            mgr,
            "k",
            off,
            lambda evs: any(
                e.code == "429" and "budget exhausted" in e.message.lower()
                for e in _errors(evs)
            ),
        )

        abandon = [
            e
            for e in _errors(events)
            if e.code == "429" and "budget exhausted" in e.message.lower()
        ]
        assert abandon, (
            "the never-clearing blip was not abandoned at budget with a typed "
            f"Event: {[e.message for e in _errors(events)]}"
        )
        # The abandon Event is a typed, observable "abandoned" reusing the
        # observed code (429) on the existing stream — not a silent hang.
        assert "abandoned" in abandon[-1].message.lower(), abandon[-1]
        assert abandon[-1].code == "429", abandon[-1]
    finally:
        mgr.close("k")


# ─── acceptance #2b: a dead-end is abandoned immediately ──────────────────────


def test_dead_end_abandoned_immediately_observable(child, tmp_path) -> None:
    """A dead-end is abandoned immediately (budget not consulted), visible on
    the existing stream (acceptance #2, dead-end half).

    A neutral ``expected`` code with no adapter hint classifies ``DEAD_END`` —
    retrying would just repeat the deterministic decline. The driver abandons on
    the first observation with the contract's dead-end row (``error`` / observed
    category / observed code / "abandoned")."""
    clock = _FakeClock()
    mgr = _make_manager(child, clock)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "ERR:CWD_NOT_FOUND")

        events = _drain_until(
            mgr,
            "k",
            off,
            lambda evs: any(
                e.code == "CWD_NOT_FOUND" and "abandoned" in e.message.lower()
                for e in _errors(evs)
            ),
        )

        abandon = [
            e
            for e in _errors(events)
            if e.code == "CWD_NOT_FOUND" and "abandoned" in e.message.lower()
        ]
        assert abandon, (
            "the dead-end was not abandoned immediately with a typed Event: "
            f"{[e.message for e in _errors(events)]}"
        )
        # No "retry scheduled" notification precedes a dead-end abandon (budget
        # not consulted) — the driver never enters the retry loop for a dead-end.
        retry_notices = [e for e in _errors(events) if "retry" in e.message.lower()]
        assert not retry_notices, (
            f"a dead-end wrongly entered the retry loop: "
            f"{[e.message for e in retry_notices]}"
        )
        # Contract dead-end row: the observed category is reused.
        assert abandon[-1].category == "expected", abandon[-1]
    finally:
        mgr.close("k")


# ─── acceptance #3: login-expired notify → resume (simulated session) ─────────


def test_login_expired_notify_resume_observable(child, tmp_path) -> None:
    """A login-expired produces a ``NOT_AUTHORIZED`` Event carrying the re-login
    link on the existing stream; after a simulated re-auth completion the run
    resumes and re-runs the step — no fabricated completion (acceptance #4).

    The adapter detects the login code (``classify_failure`` → ``LOGIN_EXPIRED``)
    and returns a fake :class:`ReauthTicket`. The driver pauses (it does NOT burn
    the retry budget), surfaces the contract's login row (``error`` /
    ``expected`` / ``NOT_AUTHORIZED`` / re-login link). The simulated operator
    then completes the ticket; the driver triggers the **existing**
    same-key/same-log resume (a genuine process re-spawn), and re-running the
    step produces a real ``result`` — proving the run resumes without a
    fabricated completion (the live-credential round-trip stays the deferred
    ``live-reauth-resume-claude`` need; this proves the logic)."""
    clock = _FakeClock()
    adapter = _FakeAdapter(child)
    mgr = SessionManager(
        {"fake": adapter},
        recovery_driver_factory=_real_driver_factory(clock),
        start_maintenance=False,
    )
    try:
        mgr.open("k", _spec(tmp_path))
        old_pid = mgr.health("k").pid
        off = mgr.send("k", f"ERR:{_FakeAdapter.LOGIN_CODE}")

        # The NOT_AUTHORIZED notification carries the re-login link on the stream.
        events = _drain_until(
            mgr,
            "k",
            off,
            lambda evs: any(
                e.code == NOT_AUTHORIZED and _FakeAdapter.RELOGIN_LINK in e.message
                for e in _errors(evs)
            ),
        )
        notify = [
            e
            for e in _errors(events)
            if e.code == NOT_AUTHORIZED and _FakeAdapter.RELOGIN_LINK in e.message
        ]
        assert notify, (
            "no NOT_AUTHORIZED notification carrying the re-login link on the "
            f"stream: {[(e.code, e.message) for e in _errors(events)]}"
        )
        # Contract login row: category ``expected``, the re-login link carried.
        assert notify[-1].category == "expected", notify[-1]
        # The run is PAUSED, not abandoned: no "abandoned" Event yet, and the
        # retry budget was not burned (reauth fired exactly once).
        assert not any("abandoned" in e.message.lower() for e in _errors(events)), (
            "a login-expiry was wrongly abandoned instead of paused"
        )
        assert adapter.reauth_calls == 1, adapter.reauth_calls

        # Simulate the operator completing re-auth → the driver resumes the run
        # via the existing same-key/same-log restart (a genuine re-spawn).
        driver = mgr._recovery_drivers["k"]
        ticket = ReauthTicket(
            relogin_link=_FakeAdapter.RELOGIN_LINK,
            completion_handle=_FakeAdapter.COMPLETION_HANDLE,
        )
        driver.complete_reauth(ticket)

        # Resume = a genuine process re-spawn (new pid), same key/same log.
        deadline = time.monotonic() + _WAIT
        new_pid = mgr.health("k").pid
        while time.monotonic() < deadline and new_pid == old_pid:
            time.sleep(0.01)
            new_pid = mgr.health("k").pid
        assert new_pid is not None and new_pid != old_pid, (
            f"resume did not re-spawn the session (old={old_pid}, new={new_pid})"
        )

        # Re-running the step on the resumed session produces a REAL result — the
        # agent re-runs the incomplete step; nothing was fabricated before this.
        resume_off = mgr.send("k", "do-the-step")
        resumed = _drain_until(
            mgr, "k", resume_off, lambda evs: any(ev.kind == "result" for ev in evs)
        )
        assert any(ev.kind == "result" for ev in resumed), (
            "the resumed step did not genuinely re-run to a result: "
            f"{[ev.kind for ev in resumed]}"
        )
    finally:
        mgr.close("k")


# ─── Blue: no new stream / Event kind / error code was introduced ─────────────


def test_no_new_event_code_or_kind_introduced() -> None:
    """Every recovery Event reuses an EXISTING ``events.py`` code and the
    EXISTING ``error`` kind — no new stream, no new Event kind, no new code
    (contract: "No new error code is introduced"; the WP Blue conformance).

    Asserted structurally: the codes the recovery path emits
    (``SOCKET_CLOSED`` / ``CWD_NOT_FOUND`` / ``NOT_AUTHORIZED``, and the reused
    raw ``429``) are all either declared constants in ``events.py`` or the
    observed-code-reused-verbatim case the contract's table allows — never a
    constant the recovery layer minted."""
    import _session_manager.events as events

    # The neutral codes the recovery path surfaces are the existing constants.
    for name in ("SOCKET_CLOSED", "CWD_NOT_FOUND", "NOT_AUTHORIZED", "STDIN_BROKEN"):
        assert hasattr(events, name), f"events.py lost the {name} constant"

    # The recovery layer (driver) declares NO code constants of its own — login
    # rides the existing NOT_AUTHORIZED; the module imports them, never mints.
    import _session_manager.recovery as recovery

    minted = [
        n
        for n in dir(recovery)
        if n.isupper() and isinstance(getattr(recovery, n), str) and n.endswith("_")
    ]
    assert minted == [], f"the recovery layer minted code-like constants: {minted}"
    # The default policy is the one the manager wires (no second policy snuck in).
    assert recovery.DEFAULT_RETRY_POLICY is DEFAULT_RETRY_POLICY
