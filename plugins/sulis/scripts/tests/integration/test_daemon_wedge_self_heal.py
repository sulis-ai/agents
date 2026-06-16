"""WP-004 (harden-daemon-wedge-self-heal) — the **headline end-to-end self-heal
acceptance proof**, plus the two guard scenarios it shares the substrate with.

Contract: ``WP-004-wedge-self-heal-integration-test.md`` Definition of Done > Red
+ spec §Acceptance + §Verification Plan ("The wedge scenario") + ADR-001 /
ADR-003. HD-003. This is the load-bearing observable proof of the whole
WP-001→WP-002→WP-003 chain: a real wedged daemon (a fake holder that takes the
flock + writes a matching identity pidfile but never serves the socket) is
detected past the grace window, verified-as-ours, killed, the lock reclaimed,
and a **fresh daemon boots and answers a real ``status`` round-trip** — i.e. a
spawn that previously raised ``DaemonStartError`` / exited 1 now returns a live
socket. The pass condition is the spec's explicit one: ``daemon_is_live`` true
(a real round-trip), **not** "the function ran". (The file was first authored
under WP-003's structural rewire; WP-004 owns the end-to-end ``daemon_is_live``
acceptance assertion.)

The race-loser branch (``main()``'s ``lock_fd is None`` path) distinguishes a
**mid-boot** holder (slow-but-legitimate boot, socket comes live inside
``resolve_wedge_grace_secs()`` → reused, exit 0, **never killed**) from a
**wedged** holder (flock held, no live socket past the window → the holder is
declared wedged, the WP-002 verified reclaim is called, the lock is re-acquired,
and a fresh daemon boots).

Verification posture (MEA-09, no mocks): the wedged / mid-boot holder is a
**real** test-owned subprocess that takes the real ``fcntl.flock`` via the real
daemon helper and writes a real identity pidfile via the real daemon helper, so
``_is_our_daemon`` verifies it the same way production would. The second daemon
is the **real** daemon process, observed over a **real** AF_UNIX socket via the
real ``daemon_client.daemon_is_live`` probe. A short
``SULIS_DAEMON_WEDGE_GRACE_SECS`` keeps the suite fast without changing the path
under test.

Tests (RED first, per the WP Definition of Done):
    test_daemon_wedge_self_heal.py::test_mid_boot_holder_inside_grace_window_is_not_killed
    test_daemon_wedge_self_heal.py::test_wedged_holder_is_reclaimed_and_a_fresh_daemon_comes_up
    test_daemon_wedge_self_heal.py::test_unverifiable_holder_falls_back_to_exit_one
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# The daemon entrypoint + the shared fake pty child live under
# plugins/sulis/scripts (this file's grandparent), with the fake child in
# tests/lib. Mirror the singleton / pidfile suites' import wiring.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_DAEMON_SCRIPT = _SCRIPTS_DIR / "session_manager_daemon.py"

sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402

# The real daemon-presence liveness probe (stdlib-only, terminal-only; ADR-003).
# WP-004's observable pass condition is a real ``status`` round-trip through this
# exact probe — the same one production callers use — not an inference from
# READY/flock/pidfile. (Spec §Verification Plan: "a live socket, not 'the
# function ran'".) The scripts dir is on sys.path via the root tests/conftest.py,
# so this resolves ambiently — matching the sibling ``test_ensure_daemon.py``.
from _session_manager import daemon_client  # noqa: E402

# Bounded wait for a process/thread assertion (matches the sibling daemon
# suites' _WAIT): long enough never to flake on a loaded CI runner, short enough
# that a real hang fails fast.
_WAIT = 8.0


# ─── a real holder of the singleton flock (the thing the second daemon meets) ──
#
# Two shapes, one helper script: a **wedged** holder (takes the flock + writes a
# valid identity pidfile, then sleeps forever without ever binding the socket)
# and a **mid-boot** holder (takes the flock, sleeps a beat, then binds + serves
# the socket via the engine's SocketServer so it comes live INSIDE the grace
# window). Both use the *real* daemon helpers so identity verification and the
# live-socket probe behave exactly as in production.

_HOLDER_SRC = """\
import os, sys, time
sys.path.insert(0, {scripts!r})
sys.path.insert(0, {testlib!r})
import session_manager_daemon as smd

mode = sys.argv[1]            # "wedged" | "midboot"
lock_path = sys.argv[2]
pidfile_path = sys.argv[3]
socket_path = sys.argv[4]
boot_delay = float(sys.argv[5])

fd = smd._acquire_singleton_lock(lock_path)
if fd is None:
    sys.stderr.write("holder failed to take the lock\\n")
    sys.exit(2)

# Write the real identity pidfile so a reclaim can verify (or, for mid-boot,
# the daemon's own bind path makes the socket live before the window elapses).
smd._write_pidfile(pidfile_path, os.getpid())

if mode == "midboot":
    time.sleep(boot_delay)    # slow-but-legitimate boot, INSIDE the grace window
    server, _manager = smd._build_server(socket_path)
    server.start()            # socket comes live now
    sys.stdout.write("HOLDER_LIVE\\n")
    sys.stdout.flush()

# Sleep forever (wedged: never binds; mid-boot: stays serving). The test reaps
# us; the long sleep is a backstop so a missed reap can never leak past the run.
time.sleep(120)
"""


def _write_holder(tmp_path: Path) -> Path:
    """Materialise the holder helper as a file **named with the marker** so its
    live command line contains ``session_manager_daemon.py`` — the cmdline half
    of the PID-reuse-safe identity check. (The production daemon's argv always
    contains the entrypoint filename; the helper reproduces that.)"""
    holder = tmp_path / "holder_session_manager_daemon.py"
    holder.write_text(
        _HOLDER_SRC.format(
            scripts=str(_SCRIPTS_DIR),
            testlib=str(_SCRIPTS_DIR / "tests" / "lib"),
        )
    )
    return holder


def _spawn_holder(
    holder: Path,
    mode: str,
    lock_path: str,
    pidfile_path: str,
    socket_path: str,
    *,
    boot_delay: float,
    env: dict,
) -> subprocess.Popen:
    """Spawn the real flock-holder and wait until it has taken the lock + written
    its identity pidfile (so the second daemon deterministically meets a held
    lock). For mid-boot, also wait until it reports ``HOLDER_LIVE``."""
    proc = subprocess.Popen(
        [
            sys.executable,
            str(holder),
            mode,
            lock_path,
            pidfile_path,
            socket_path,
            str(boot_delay),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(_SCRIPTS_DIR),
        env=env,
    )
    # Wait until the identity pidfile exists → the holder owns the lock now.
    deadline = time.monotonic() + _WAIT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read() if proc.stderr else ""
            raise AssertionError(f"holder exited early (rc={proc.returncode}): {err}")
        if os.path.exists(pidfile_path):
            break
        time.sleep(0.02)
    else:
        proc.kill()
        raise AssertionError("holder never wrote its identity pidfile")
    return proc


def _reap(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=_WAIT)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive
        proc.kill()
        proc.wait(timeout=_WAIT)


@pytest.fixture
def fake_pty_child(tmp_path: Path) -> Path:
    """The shared fake-``claude`` child in ``pty`` mode (a real subprocess) — the
    MEA-09 substrate the second daemon's pty provider is pointed at."""
    return fake_claude_child.write_child(tmp_path)


@pytest.fixture
def holder_env(fake_pty_child: Path) -> dict:
    """Child env for the holder + the second daemon: the fake pty child, a long
    idle window (never trips mid-test), and a SHORT wedge-grace window so the
    test exercises the real wedged-vs-mid-boot decision quickly."""
    env = os.environ.copy()
    env["SULIS_DAEMON_PTY_CHILD"] = str(fake_pty_child)
    env["SULIS_DAEMON_IDLE_EXIT_SECS"] = "3600"
    env["SULIS_DAEMON_WEDGE_GRACE_SECS"] = "1.5"
    return env


@pytest.fixture
def socket_path(tmp_path: Path) -> str:
    # Kept short — AF_UNIX path length is bounded (~104 bytes on macOS).
    return str(tmp_path / "d.sock")


@pytest.fixture
def lock_path(tmp_path: Path) -> str:
    return str(tmp_path / "d.lock")


@pytest.fixture
def pidfile_path(tmp_path: Path) -> str:
    return str(tmp_path / "d.pid")


def _run_second_daemon(
    socket_path: str, lock_path: str, pidfile_path: str, env: dict
) -> subprocess.Popen:
    """Launch the REAL daemon as the race-loser (the holder already owns the
    lock). Returns the Popen so the caller can wait + inspect rc / streams."""
    return subprocess.Popen(
        [
            sys.executable,
            str(_DAEMON_SCRIPT),
            "--socket",
            socket_path,
            "--lock",
            lock_path,
            "--pidfile",
            pidfile_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(_SCRIPTS_DIR),
        env=env,
    )


# ─── the RED tests ────────────────────────────────────────────────────────────


def test_mid_boot_holder_inside_grace_window_is_not_killed(
    holder_env: dict,
    socket_path: str,
    lock_path: str,
    pidfile_path: str,
    tmp_path: Path,
) -> None:
    """MID-BOOT PROTECTION (the regression guard, spec §Acceptance).

    A holder that takes the flock and brings its socket live **inside** the grace
    window (a slow-but-legitimate boot) is reused: the second daemon sees the
    live socket within the window, prints READY, and exits 0 — and the holder is
    **never** SIGTERMed/SIGKILLed (it is still alive after the second exits).
    Fails today if asserted against the new grace path (today's 5s poll predates
    the wedge/reclaim distinction)."""
    holder_script = _write_holder(tmp_path)
    # Socket comes live ~0.5s in — well inside the 1.5s grace window.
    holder = _spawn_holder(
        holder_script,
        "midboot",
        lock_path,
        pidfile_path,
        socket_path,
        boot_delay=0.5,
        env=holder_env,
    )
    try:
        second = _run_second_daemon(socket_path, lock_path, pidfile_path, holder_env)
        try:
            rc = second.wait(timeout=_WAIT)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            second.kill()
            raise AssertionError("second daemon never exited on the mid-boot path")
        out = second.stdout.read() if second.stdout else ""
        err = second.stderr.read() if second.stderr else ""
        assert rc == 0, (
            f"second daemon exited {rc} on a mid-boot holder, expected 0 "
            f"(reuse, not reclaim); stderr={err!r}"
        )
        assert "READY" in out, f"second daemon did not print READY: {out!r}"
        # The mid-boot holder must be UNTOUCHED — never killed.
        assert holder.poll() is None, (
            "the mid-boot holder was killed — mid-boot protection regressed "
            "(a legitimate slow boot inside the grace window must be reused)"
        )
    finally:
        _reap(holder)


def test_wedged_holder_is_reclaimed_and_a_fresh_daemon_comes_up(
    holder_env: dict,
    socket_path: str,
    lock_path: str,
    pidfile_path: str,
    tmp_path: Path,
) -> None:
    """WEDGE SELF-HEAL — the headline acceptance proof (spec §Acceptance +
    §Verification Plan).

    A holder that takes the flock + writes a valid identity pidfile but **never**
    serves the socket is wedged. Past the grace window the second daemon declares
    it wedged, reclaims it (kills the verified holder), re-acquires the lock,
    boots a fresh daemon, prints READY, and serves a live socket — instead of
    exiting 1 after the timeout. The wedged holder is dead afterwards. Fails
    today: the race-loser branch only polls then returns 1, it never reclaims.

    **The observable pass condition (WP-004) is a real ``daemon_is_live`` round-
    trip** against the fresh daemon's socket — a genuine ``status`` request/reply
    over the AF_UNIX socket, the spec's "a live socket, not 'the function ran'".
    READY/flock/pidfile are corroborating evidence; the round-trip is the proof."""
    holder_script = _write_holder(tmp_path)
    holder = _spawn_holder(
        holder_script,
        "wedged",
        lock_path,
        pidfile_path,
        socket_path,
        boot_delay=0.0,
        env=holder_env,
    )
    reaped = False
    try:
        second = _run_second_daemon(socket_path, lock_path, pidfile_path, holder_env)
        # The fresh daemon prints READY once it has reclaimed + bound.
        deadline = time.monotonic() + _WAIT
        ready = False
        while time.monotonic() < deadline:
            if second.poll() is not None:
                err = second.stderr.read() if second.stderr else ""
                raise AssertionError(
                    f"second daemon exited (rc={second.returncode}) without "
                    f"self-healing the wedge; stderr={err!r}"
                )
            line = second.stdout.readline() if second.stdout else ""
            if line.startswith("READY"):
                assert socket_path in line, f"READY did not name the socket: {line!r}"
                ready = True
                break
        assert ready, "fresh daemon never printed READY after reclaiming the wedge"

        # ── THE observable acceptance: a real ``status`` round-trip ──────────────
        # The spec's pass condition (WP-004): a previously-blocked spawn now
        # returns a *live socket*. We prove it the way a production caller would —
        # ``daemon_client.daemon_is_live`` connects to the socket and exchanges a
        # real ``status`` request/reply. This is "a live socket", NOT "the function
        # ran": if the fresh daemon were not genuinely serving, this is False.
        assert daemon_client.daemon_is_live(socket_path, timeout=_WAIT), (
            "the fresh daemon did not answer a real `status` round-trip after the "
            "wedge self-heal — the reclaim printed READY but the socket is not "
            "live (spec §Verification Plan: a live socket, not 'the function ran')"
        )

        # The wedged holder must be DEAD (the reclaim killed the verified holder).
        holder.wait(timeout=_WAIT)
        reaped = True
        assert holder.returncode is not None, "wedged holder was not reclaimed (killed)"

        # The fresh daemon owns the lock now: a non-blocking flock attempt fails.
        import fcntl

        with open(lock_path, "a") as lf:
            with pytest.raises(OSError):
                fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # And it serves: the pidfile now names the FRESH daemon, not the holder.
        record = json.loads(Path(pidfile_path).read_text())
        assert record["pid"] == second.pid, (
            f"pidfile pid {record.get('pid')!r} is not the fresh daemon's "
            f"{second.pid} — the reclaim did not boot a fresh daemon"
        )
        _reap(second)
    finally:
        if not reaped:
            _reap(holder)


def test_unverifiable_holder_falls_back_to_exit_one(
    holder_env: dict,
    socket_path: str,
    lock_path: str,
    pidfile_path: str,
    tmp_path: Path,
) -> None:
    """FAIL-CLOSED (spec §Constraints).

    A wedged holder whose identity cannot be verified (here: no identity pidfile
    at all — a torn/absent record) is **never** killed. Past the grace window the
    reclaim fails closed and the second daemon falls back to **today's exact
    behaviour**: the 'mid-boot or wedged; ensure-daemon will retry' stderr line +
    ``return 1``. The holder is left alive (not reclaimed). Fails today only in
    that the grace path does not exist yet; the fail-closed *outcome* is the
    invariant this pins."""
    holder_script = _write_holder(tmp_path)
    holder = _spawn_holder(
        holder_script,
        "wedged",
        lock_path,
        pidfile_path,
        socket_path,
        boot_delay=0.0,
        env=holder_env,
    )
    try:
        # Remove the identity pidfile AFTER the holder took the lock → the
        # reclaim has no durable identity to verify → it must fail closed.
        os.unlink(pidfile_path)

        second = _run_second_daemon(socket_path, lock_path, pidfile_path, holder_env)
        try:
            rc = second.wait(timeout=_WAIT)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            second.kill()
            raise AssertionError("second daemon never exited on the fail-closed path")
        err = second.stderr.read() if second.stderr else ""
        assert rc == 1, (
            f"second daemon exited {rc}, expected 1 (fail closed when identity "
            f"cannot be verified); stderr={err!r}"
        )
        assert "ensure-daemon will retry" in err, (
            f"fail-closed path did not emit today's stderr line: {err!r}"
        )
        # The unverifiable holder must be UNTOUCHED — fail closed never kills.
        assert holder.poll() is None, (
            "an unverifiable holder was killed — fail-closed safety regressed"
        )
    finally:
        _reap(holder)
