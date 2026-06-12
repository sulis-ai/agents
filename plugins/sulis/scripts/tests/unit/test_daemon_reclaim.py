"""WP-002 (harden-daemon-wedge-self-heal) — the PID-reuse-safe identity verify
+ kill/reclaim helpers for a **wedged** daemon holder.

Contract: ``WP-002-pid-reuse-safe-identity-verify-and-reclaim.md`` Definition of
Done > Red + spec §Constraints (best-effort recovery I/O, never crash) +
ADR-001 (the kill target's identity comes from the WP-001 pidfile, verified to
*still be our daemon* before any kill) + ADR-003 (stdlib-only). HD-002.

**The load-bearing safety invariant of the whole change**: a recycled PID whose
recorded ``start_token`` / ``cmdline_marker`` do not match the live process is
**never** killed. ``_is_our_daemon`` is a *pure* fail-closed decision (probes
injected) so every branch is exercised without a real kill; the side-effecting
kill lives only in ``_reclaim_wedged_holder``.

Verification posture (MEA-09, deterministic):
  * The pure verifier is exercised across every branch with **injected probes**
    (``start_token_of`` / ``cmdline_of``) — no real process needed, no mock of
    the function under test.
  * ``_reclaim_wedged_holder`` is exercised against **real, test-owned
    subprocesses** (a live ``sleep``-style python child the test spawns and is
    responsible for reaping): the fail-closed path spies ``os.kill`` and asserts
    it is **never called**; the happy path lets a real SIGTERM reap a real
    child. No mock of the OS kill except as an assertion spy.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# The helpers live on the daemon module (the daemon's own identity, not the
# engine's). Importing them is the first thing that fails before WP-002.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import session_manager_daemon  # noqa: E402

# A child that lives long enough for the test to drive a reclaim against it, but
# self-exits as a backstop so a failed reap can never leak a process past the
# suite. The reclaim's SIGTERM (default disposition: terminate) reaps it well
# before the backstop.
_LIVE_CHILD = "import time; time.sleep(30)"


def _spawn_live_child() -> subprocess.Popen:
    """Spawn a real, live, killable child and return the Popen handle. The
    caller owns reaping it (the happy-path test lets the reclaim's SIGTERM do
    so; the fail-closed test terminates it explicitly in a finally)."""
    return subprocess.Popen([sys.executable, "-c", _LIVE_CHILD])


def _spawn_then_reap_pid() -> int:
    """Spawn a trivial child, wait for it to exit, return its now-dead PID — the
    deterministic substrate for the dead-PID branch without racing a live one."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


# ── _is_our_daemon: the pure fail-closed verifier (probes injected) ──────────


def test_is_our_daemon_true_on_full_match() -> None:
    """True IFF the live process exists AND its cmdline contains the recorded
    marker AND its start-token equals the recorded one. All three present and
    matching → True."""
    record = {
        "pid": 4242,
        "start_token": "Tue Jun 10 11:22:33 2026",
        "cmdline_marker": "session_manager_daemon.py",
    }
    assert (
        session_manager_daemon._is_our_daemon(
            record,
            4242,
            start_token_of=lambda _pid: "Tue Jun 10 11:22:33 2026",
            cmdline_of=lambda _pid: (
                "python /opt/sulis/session_manager_daemon.py --socket /x.sock"
            ),
        )
        is True
    )


def test_is_our_daemon_false_when_cmdline_marker_absent() -> None:
    """A live process whose cmdline does NOT contain the recorded marker is not
    our daemon — fail closed even if the start-token happens to match."""
    record = {
        "pid": 4242,
        "start_token": "Tue Jun 10 11:22:33 2026",
        "cmdline_marker": "session_manager_daemon.py",
    }
    assert (
        session_manager_daemon._is_our_daemon(
            record,
            4242,
            start_token_of=lambda _pid: "Tue Jun 10 11:22:33 2026",
            cmdline_of=lambda _pid: "python /usr/bin/some_other_process.py",
        )
        is False
    )


def test_is_our_daemon_false_when_pid_dead() -> None:
    """A PID whose live cmdline is unreadable (process gone → cmdline probe
    returns None) cannot be proven to be our daemon → fail closed."""
    record = {
        "pid": 4242,
        "start_token": "Tue Jun 10 11:22:33 2026",
        "cmdline_marker": "session_manager_daemon.py",
    }
    assert (
        session_manager_daemon._is_our_daemon(
            record,
            4242,
            start_token_of=lambda _pid: "Tue Jun 10 11:22:33 2026",
            cmdline_of=lambda _pid: None,  # process gone
        )
        is False
    )


def test_is_our_daemon_false_when_start_token_unreadable() -> None:
    """A live process whose start-token cannot be read (ps unreadable → None)
    cannot be pinned to the recorded identity → fail closed. This is the
    PID-reuse anchor: without a matching start-token we never trust the PID."""
    record = {
        "pid": 4242,
        "start_token": "Tue Jun 10 11:22:33 2026",
        "cmdline_marker": "session_manager_daemon.py",
    }
    assert (
        session_manager_daemon._is_our_daemon(
            record,
            4242,
            start_token_of=lambda _pid: None,  # ps unreadable
            cmdline_of=lambda _pid: "python /opt/sulis/session_manager_daemon.py",
        )
        is False
    )


# ── _read_pidfile: best-effort parse, never raises ───────────────────────────


def test_read_pidfile_returns_none_on_torn_file(tmp_path: Path) -> None:
    """A half-written / unparseable pidfile yields None, never an exception —
    the caller treats a missing/torn record as 'no durable identity', and
    fails closed (does not kill)."""
    torn = tmp_path / "session-manager.pid"
    torn.write_text('{"pid": 4242, "start_token": "Tue Jun 10 11')  # truncated

    assert session_manager_daemon._read_pidfile(str(torn)) is None


def test_read_pidfile_returns_none_on_missing_file(tmp_path: Path) -> None:
    """A missing pidfile yields None, never an exception — the daemon never
    wrote one (or it was already removed) → no durable identity → fail closed."""
    missing = tmp_path / "nope.pid"
    assert session_manager_daemon._read_pidfile(str(missing)) is None


def test_read_pidfile_returns_none_on_non_mapping_record(tmp_path: Path) -> None:
    """A parseable-but-not-a-mapping pidfile (e.g. a bare JSON list) yields None
    — the record shape is wrong, so there is no usable identity → fail closed."""
    not_a_dict = tmp_path / "session-manager.pid"
    not_a_dict.write_text("[1, 2, 3]")
    assert session_manager_daemon._read_pidfile(str(not_a_dict)) is None


def test_is_our_daemon_false_when_record_has_no_recorded_identity() -> None:
    """A record missing its ``cmdline_marker`` / ``start_token`` cannot anchor an
    identity at all → fail closed, without even probing the live process."""
    probed: list[int] = []

    def _spy_token(pid: int) -> str | None:
        probed.append(pid)
        return "Tue Jun 10 11:22:33 2026"

    assert (
        session_manager_daemon._is_our_daemon(
            {"pid": 4242},  # no cmdline_marker, no start_token
            4242,
            start_token_of=_spy_token,
            cmdline_of=lambda _pid: "session_manager_daemon.py",
        )
        is False
    )
    assert probed == [], (
        "an empty-identity record must short-circuit to False before probing"
    )


# ── _ps_field: the shared best-effort ps probe ───────────────────────────────


def test_ps_field_returns_none_for_dead_pid() -> None:
    """The shared ``ps`` probe is best-effort: for a gone PID it returns None
    rather than raising. Both _process_start_token and _process_cmdline inherit
    this guarantee."""
    dead_pid = _spawn_then_reap_pid()
    assert session_manager_daemon._ps_field(dead_pid, "lstart=") is None
    assert session_manager_daemon._ps_field(dead_pid, "command=") is None


def test_ps_field_returns_none_when_subprocess_raises(monkeypatch) -> None:
    """If the ``ps`` invocation itself raises (e.g. ``ps`` is missing → OSError,
    or it times out → SubprocessError) the probe must degrade to None, never
    propagate — best-effort recovery I/O. This is the branch that keeps the
    whole identity check fail-closed when the host's ``ps`` is unusable."""

    def _boom(*_a, **_k):
        raise OSError("ps not found")

    monkeypatch.setattr(session_manager_daemon.subprocess, "run", _boom)
    assert session_manager_daemon._ps_field(4242, "command=") is None


# ── _reclaim_wedged_holder: fail-closed entry branches ───────────────────────


def test_reclaim_fails_closed_when_pidfile_missing(tmp_path: Path, monkeypatch) -> None:
    """No pidfile → no durable identity → return False, never kill. Spy os.kill
    to prove no signal is ever sent on the no-identity path."""
    kill_calls: list[tuple] = []
    monkeypatch.setattr(
        session_manager_daemon.os,
        "kill",
        lambda pid, sig: kill_calls.append((pid, sig)),
    )
    result = session_manager_daemon._reclaim_wedged_holder(
        str(tmp_path / "absent.pid"),
        str(tmp_path / "absent.sock"),
        term_wait_secs=0.5,
    )
    assert result is False
    assert kill_calls == [], "a missing pidfile must never lead to a kill"


def test_reclaim_fails_closed_when_pid_field_malformed(
    tmp_path: Path, monkeypatch
) -> None:
    """A record whose ``pid`` is not an int (torn / tampered) → return False,
    never kill — the kill target cannot even be identified."""
    pidfile = tmp_path / "session-manager.pid"
    pidfile.write_text(
        json.dumps(
            {
                "pid": "not-an-int",
                "start_token": "Tue Jun 10 11:22:33 2026",
                "cmdline_marker": "session_manager_daemon.py",
            }
        )
    )
    kill_calls: list[tuple] = []
    monkeypatch.setattr(
        session_manager_daemon.os,
        "kill",
        lambda pid, sig: kill_calls.append((pid, sig)),
    )
    result = session_manager_daemon._reclaim_wedged_holder(
        str(pidfile),
        str(tmp_path / "session-manager.sock"),
        term_wait_secs=0.5,
    )
    assert result is False
    assert kill_calls == [], "a malformed pid must never lead to a kill"


# ── _reclaim_wedged_holder: the side-effecting kill (real subprocesses) ──────


def test_reclaim_refuses_to_kill_on_pid_reuse_start_token_mismatch(
    tmp_path: Path, monkeypatch
) -> None:
    """THE LOAD-BEARING SAFETY TEST.

    The pidfile names a **live real** process (a child this test owns), but the
    recorded ``start_token`` / ``cmdline_marker`` do not match it — exactly the
    recycled-PID scenario. ``_reclaim_wedged_holder`` MUST NOT kill it: spy
    ``os.kill`` and assert it is **never called**; the function returns False
    (verification failed closed → the caller falls back to today's exit-1)."""
    child = _spawn_live_child()
    try:
        pidfile = tmp_path / "session-manager.pid"
        socket_path = tmp_path / "session-manager.sock"
        socket_path.write_text("")  # a stale socket sitting beside the pidfile
        # The recorded identity points at the LIVE child's PID but with a
        # start-token + marker that cannot match it — recycled-PID simulation.
        pidfile.write_text(
            json.dumps(
                {
                    "pid": child.pid,
                    "start_token": "Mon Jan 01 00:00:00 2001",  # cannot match
                    "cmdline_marker": "totally_different_marker_xyz",
                }
            )
        )

        kill_calls: list[tuple] = []
        real_kill = os.kill

        def _spy_kill(pid: int, sig: int) -> None:
            kill_calls.append((pid, sig))
            real_kill(pid, sig)

        monkeypatch.setattr(session_manager_daemon.os, "kill", _spy_kill)

        result = session_manager_daemon._reclaim_wedged_holder(
            str(pidfile),
            str(socket_path),
            term_wait_secs=0.5,
        )

        assert result is False, (
            "reclaim must fail closed (return False) on an identity mismatch"
        )
        assert kill_calls == [], (
            f"os.kill was called {kill_calls!r} on a PID-reuse mismatch — the "
            "load-bearing safety invariant is violated (a recycled PID was "
            "targeted for a kill)"
        )
        # The live child must be untouched (still running).
        assert child.poll() is None, "the unrelated live process was killed"
        # Fail-closed must NOT clear the stale socket/pidfile either — the
        # caller owns the fallback, the reclaim makes no destructive change
        # when it cannot prove identity.
        assert pidfile.exists(), "pidfile cleared despite refusing to reclaim"
        assert socket_path.exists(), "socket cleared despite refusing to reclaim"
    finally:
        child.terminate()
        child.wait(timeout=5)


def test_reclaim_kills_verified_holder_then_clears_pidfile_and_socket(
    tmp_path: Path, monkeypatch
) -> None:
    """Full identity match against a real, killable child: the reclaim sends
    SIGTERM, the child is reaped, and the stale pidfile + socket are unlinked;
    returns True. Identity is proven by stubbing the two probes to match the
    live child (the probe injection seam keeps this deterministic without
    depending on the host's real ``ps`` formatting)."""
    child = _spawn_live_child()
    reaped = False
    try:
        pidfile = tmp_path / "session-manager.pid"
        socket_path = tmp_path / "session-manager.sock"
        socket_path.write_text("")
        pidfile.write_text(
            json.dumps(
                {
                    "pid": child.pid,
                    "start_token": "Tue Jun 10 11:22:33 2026",
                    "cmdline_marker": "session_manager_daemon.py",
                }
            )
        )
        # Make identity provable for this exact live child.
        monkeypatch.setattr(
            session_manager_daemon,
            "_process_start_token",
            lambda _pid: "Tue Jun 10 11:22:33 2026",
        )
        monkeypatch.setattr(
            session_manager_daemon,
            "_process_cmdline",
            lambda _pid: f"python -c {_LIVE_CHILD!r} session_manager_daemon.py",
        )

        sent: list[tuple] = []
        real_kill = os.kill

        def _spy_kill(pid: int, sig: int) -> None:
            sent.append((pid, sig))
            real_kill(pid, sig)

        monkeypatch.setattr(session_manager_daemon.os, "kill", _spy_kill)

        result = session_manager_daemon._reclaim_wedged_holder(
            str(pidfile),
            str(socket_path),
            term_wait_secs=5.0,
        )

        assert result is True, "a verified-ours wedged holder must be reclaimed"
        # SIGTERM was the first signal sent to the verified holder.
        assert sent, "no kill signal was sent to the verified holder"
        assert sent[0] == (child.pid, _signal_term()), (
            f"first signal was {sent[0]!r}, expected SIGTERM to the holder"
        )
        # The child is actually dead now (the reclaim reaped a real process).
        child.wait(timeout=5)
        reaped = True
        assert not pidfile.exists(), "stale pidfile was not cleared after reclaim"
        assert not socket_path.exists(), "stale socket was not cleared after reclaim"
    finally:
        if not reaped:
            child.terminate()
            child.wait(timeout=5)


def test_reclaim_best_effort_survives_kill_racing_natural_death(
    tmp_path: Path, monkeypatch
) -> None:
    """A kill racing the holder's natural death raises ProcessLookupError; the
    reclaim swallows it and still completes (returns True, clears the stale
    files). Best-effort recovery I/O never crashes the recovery path."""
    pidfile = tmp_path / "session-manager.pid"
    socket_path = tmp_path / "session-manager.sock"
    socket_path.write_text("")
    pidfile.write_text(
        json.dumps(
            {
                "pid": 999_999,  # a plausible-but-irrelevant PID
                "start_token": "Tue Jun 10 11:22:33 2026",
                "cmdline_marker": "session_manager_daemon.py",
            }
        )
    )
    # Force identity to verify (so we reach the kill), then make the kill race a
    # natural death: os.kill raises ProcessLookupError as if the process just
    # exited between the verify and the signal.
    monkeypatch.setattr(
        session_manager_daemon,
        "_is_our_daemon",
        lambda *a, **k: True,
    )

    def _racing_kill(_pid: int, _sig: int) -> None:
        raise ProcessLookupError("no such process — it died first")

    monkeypatch.setattr(session_manager_daemon.os, "kill", _racing_kill)

    result = session_manager_daemon._reclaim_wedged_holder(
        str(pidfile),
        str(socket_path),
        term_wait_secs=0.5,
    )

    assert result is True, (
        "a kill racing natural death is a completed reclaim, not a failure"
    )
    assert not pidfile.exists(), "stale pidfile not cleared after the racing death"
    assert not socket_path.exists(), "stale socket not cleared after the racing death"


def test_reclaim_escalates_to_sigkill_when_holder_outlives_term_wait(
    tmp_path: Path, monkeypatch
) -> None:
    """A verified holder that does NOT die within the bounded SIGTERM wait is
    escalated to SIGKILL, then the stale files are cleared. Identity is forced
    to verify; ``_pid_alive`` is held True so the wait runs to its deadline; the
    monotonic clock is advanced deterministically so the test does not actually
    sleep out the 5s floor."""
    import signal as _signal

    pidfile = tmp_path / "session-manager.pid"
    socket_path = tmp_path / "session-manager.sock"
    socket_path.write_text("")
    pidfile.write_text(
        json.dumps(
            {
                "pid": 4242,
                "start_token": "Tue Jun 10 11:22:33 2026",
                "cmdline_marker": "session_manager_daemon.py",
            }
        )
    )
    monkeypatch.setattr(session_manager_daemon, "_is_our_daemon", lambda *a, **k: True)
    # The holder never dies during the wait → forces the SIGKILL escalation.
    monkeypatch.setattr(session_manager_daemon, "_pid_alive", lambda _pid: True)

    sent: list[tuple] = []
    monkeypatch.setattr(
        session_manager_daemon.os,
        "kill",
        lambda pid, sig: sent.append((pid, sig)),
    )

    # Advance the monotonic clock past the deadline on the second sample so the
    # bounded-wait loop exits via its `else` (SIGKILL) without real sleeping.
    ticks = iter([0.0, 0.0, 100.0, 100.0, 100.0])
    monkeypatch.setattr(session_manager_daemon.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(session_manager_daemon.time, "sleep", lambda _s: None)

    result = session_manager_daemon._reclaim_wedged_holder(
        str(pidfile),
        str(socket_path),
        term_wait_secs=0.5,
    )

    assert result is True
    assert (4242, int(_signal.SIGTERM)) in sent, "SIGTERM must be sent first"
    assert (4242, int(_signal.SIGKILL)) in sent, (
        "a holder outliving the wait must be escalated to SIGKILL"
    )
    assert not pidfile.exists()
    assert not socket_path.exists()


def test_sigkill_escalation_reverifies_identity_and_skips_on_pid_reuse(
    tmp_path: Path, monkeypatch
) -> None:
    """WP-005 — close the verify→SIGKILL TOCTOU wrong-kill window (ADVISORY-2).

    The holder passes the **initial** verify and is sent SIGTERM, then outlives
    the bounded wait — but in that wait its PID is **recycled** onto an unrelated
    process (the verified daemon died under SIGTERM and the OS reused its PID).
    ``_is_our_daemon`` flips: True for the first (gate) call, False for the
    second (the new pre-SIGKILL re-verify). The reclaim MUST NOT escalate to
    SIGKILL — sending it would land on the wrong process, the exact wrong kill
    this change exists to prevent. ``_pid_alive`` is held True so the wait runs
    to its deadline (otherwise the loop would ``break`` before the escalation and
    never reach the guard); the monotonic clock is advanced so the test does not
    sleep out the 5s floor.

    Asserts: ``os.kill(pid, SIGKILL)`` is **never** called; SIGTERM may have been
    sent (the holder *was* our daemon when we gated the SIGTERM); the stale
    pidfile + socket are still cleared and the reclaim returns True (the holder
    is gone — a recycled PID means the original process died, so this is a
    completed reclaim, fail-closed identically to a holder that died during the
    wait).
    """
    import signal as _signal

    pidfile = tmp_path / "session-manager.pid"
    socket_path = tmp_path / "session-manager.sock"
    socket_path.write_text("")
    pidfile.write_text(
        json.dumps(
            {
                "pid": 4242,
                "start_token": "Tue Jun 10 11:22:33 2026",
                "cmdline_marker": "session_manager_daemon.py",
            }
        )
    )

    # Identity is provable on the FIRST call (the SIGTERM gate) and NOT on the
    # SECOND (the pre-SIGKILL re-verify) — the PID was recycled mid-wait.
    verify_calls = {"n": 0}

    def _flipping_is_our_daemon(*_a, **_k) -> bool:
        verify_calls["n"] += 1
        return verify_calls["n"] == 1

    monkeypatch.setattr(
        session_manager_daemon, "_is_our_daemon", _flipping_is_our_daemon
    )
    # The PID stays "alive" throughout the wait (signal-0 liveness can't tell the
    # recycled process from the original) → the loop runs to its deadline and
    # reaches the escalation branch where the new guard lives.
    monkeypatch.setattr(session_manager_daemon, "_pid_alive", lambda _pid: True)

    sent: list[tuple] = []
    monkeypatch.setattr(
        session_manager_daemon.os,
        "kill",
        lambda pid, sig: sent.append((pid, sig)),
    )

    ticks = iter([0.0, 0.0, 100.0, 100.0, 100.0])
    monkeypatch.setattr(session_manager_daemon.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(session_manager_daemon.time, "sleep", lambda _s: None)

    result = session_manager_daemon._reclaim_wedged_holder(
        str(pidfile),
        str(socket_path),
        term_wait_secs=0.5,
    )

    assert (4242, int(_signal.SIGKILL)) not in sent, (
        f"SIGKILL was sent {sent!r} after the PID was recycled mid-wait — the "
        "load-bearing 'never kill the wrong PID' invariant is violated; the "
        "pre-SIGKILL re-verify guard must skip the kill on identity mismatch"
    )
    assert verify_calls["n"] >= 2, (
        "the SIGKILL escalation must re-verify identity (a second _is_our_daemon "
        f"call) before killing; saw only {verify_calls['n']} verify call(s)"
    )
    # The holder is gone (its PID was recycled → the original died); the reclaim
    # completes fail-closed: stale files cleared, returns True.
    assert result is True
    assert not pidfile.exists(), "stale pidfile not cleared after skipped SIGKILL"
    assert not socket_path.exists(), "stale socket not cleared after skipped SIGKILL"


def test_reclaim_breaks_wait_when_holder_dies_within_term_wait(
    tmp_path: Path, monkeypatch
) -> None:
    """A verified holder that dies promptly after SIGTERM (within the bounded
    wait) exits the wait via the ``break`` — no SIGKILL escalation. Identity is
    forced to verify; ``_pid_alive`` returns False on the first sample so the
    loop breaks immediately; only the SIGTERM is sent."""
    import signal as _signal

    pidfile = tmp_path / "session-manager.pid"
    socket_path = tmp_path / "session-manager.sock"
    socket_path.write_text("")
    pidfile.write_text(
        json.dumps(
            {
                "pid": 4242,
                "start_token": "Tue Jun 10 11:22:33 2026",
                "cmdline_marker": "session_manager_daemon.py",
            }
        )
    )
    monkeypatch.setattr(session_manager_daemon, "_is_our_daemon", lambda *a, **k: True)
    # Holder is already gone by the first liveness check → break, no SIGKILL.
    monkeypatch.setattr(session_manager_daemon, "_pid_alive", lambda _pid: False)

    sent: list[tuple] = []
    monkeypatch.setattr(
        session_manager_daemon.os,
        "kill",
        lambda pid, sig: sent.append((pid, sig)),
    )

    result = session_manager_daemon._reclaim_wedged_holder(
        str(pidfile),
        str(socket_path),
        term_wait_secs=0.5,
    )

    assert result is True
    assert sent == [(4242, int(_signal.SIGTERM))], (
        f"expected only a SIGTERM (holder died within the wait), got {sent!r}"
    )
    assert not pidfile.exists()
    assert not socket_path.exists()


def test_signal_pid_returns_false_when_process_already_gone(monkeypatch) -> None:
    """The best-effort signal helper reports a kill racing a natural death
    (ProcessLookupError) as 'not delivered' (False), without raising."""

    def _gone(_pid: int, _sig: int) -> None:
        raise ProcessLookupError("no such process")

    monkeypatch.setattr(session_manager_daemon.os, "kill", _gone)
    assert session_manager_daemon._signal_pid(4242, _signal_term()) is False


def test_signal_pid_returns_true_when_delivered(monkeypatch) -> None:
    """A delivered signal reports True. Spy os.kill so no real signal is sent."""
    monkeypatch.setattr(session_manager_daemon.os, "kill", lambda _p, _s: None)
    assert session_manager_daemon._signal_pid(4242, _signal_term()) is True


def _signal_term() -> int:
    import signal

    return int(signal.SIGTERM)
