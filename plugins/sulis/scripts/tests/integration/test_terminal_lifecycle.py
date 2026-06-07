"""WP-010 (CH-01KTGY) — visible-lifecycle gate + the headless regression gate.

This is the LAST WP's backend half: the named lifecycle gate proving the reused
lifecycle (spawn/warm/health/restart-on-death/idle-evict, base §2.7) holds for
**visible** (pty-backed) sessions exactly as it does for headless pipe sessions
(spec §Acceptance #5), AND the aggregated headless-pipe non-regression gate
(spec §Acceptance #4, the non-goal made executable).

Contract: ``SESSION_MANAGER_CONTRACT.extension.md`` §2.12.3 (detach is
orthogonal to the process lifecycle; restart-on-death re-creates the PTY and
keeps the scrollback across the restart; an idle pty session with zero viewers
is idle-evicted by the SAME timer as a headless pipe session), §2.12.5
(``io_mode``/``viewer_count`` observability), §2.15 (``NOT_PTY_SESSION``).
TDD §3 (visible-lifecycle + headless-pipe non-regression rows), §6.4.

What this WP owns vs aggregates (WP boundary / INDEX regression-gate-in-three-
places): WP-003 owns the pty io-model, WP-004 owns attach/viewer + the
``is_alive`` liveness primitive, WP-005 owns restart-on-death recovery + the
socket, WP-006 owns idle-eviction/LRU. This WP does **not** re-implement any of
them — it drives them together as the named **visible-lifecycle** gate and
re-asserts the **regression gate** so it cannot be silently dropped (the gate is
held here AND in WP-003 Blue AND WP-005 Blue, per the INDEX regression note).

Verification posture (MEA-09, no mocks): a **real** pty-backed child (WP-006's
``fake_claude_child`` ``pty`` mode) over a **real** ``os.openpty()`` pair the
manager owns from spawn; a **real** pipe-backed child for the regression half.
The maintenance tick is driven **synchronously** (``mgr._maintenance_tick()``)
and idle is stamped against the manager's own clock — no ``sleep``-based
flakiness (mirrors WP-006's eviction suite). Restart-on-death is driven by
killing the real child and letting the EOF-driven ``on_death`` fire.

Tests (RED first, per the WP Definition of Done #5 + the regression gate #4):
    test_terminal_lifecycle.py::test_restart_recreates_pty
    test_terminal_lifecycle.py::test_idle_pty_evicted
    test_terminal_lifecycle.py::test_attach_on_pipe_is_not_pty_regression
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from _session_manager.adapter import SessionSpec
from _session_manager.events import ExpectedError
from _session_manager.manager import SessionManager

# Shared test helpers live under tests/lib (mirrors the session suites' import
# pattern — sys.path.insert, then import). ``session_child_adapters`` carries the
# real pty + pipe ProviderAdapters extracted at the 2-consumer threshold (EP-03,
# shared with tests/unit/test_viewer.py + tests/integration/test_socket_server.py
# — this WP-010 lifecycle gate is the third consumer the module was built for).
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402
from session_child_adapters import (  # noqa: E402
    PIPE_CHILD_SOURCE as _PIPE_CHILD_SOURCE,
    PipeChildAdapter as _PipeChildAdapter,
    PtyChildAdapter as _PtyChildAdapter,
)

# Bounded wait for the genuinely-threaded assertions (a death the test performs,
# a master read the pump must drain): long enough never to flake on a loaded
# runner, short enough that a real hang fails fast. Matches the session suites.
_WAIT = 5.0


def _wait_for(predicate, timeout: float = _WAIT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _pty_manager(child: Path, **tuning: object) -> SessionManager:
    """A manager over the real pty-backed child, maintenance driven by the test
    (``start_maintenance=False``) so eviction/restart timing is deterministic —
    mirrors WP-006's ``_manager`` helper."""
    tuning.setdefault("start_maintenance", False)
    return SessionManager({"pty": _PtyChildAdapter(child)}, **tuning)


def _pty_spec(tmp_path: Path) -> SessionSpec:
    return SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")


def _write_pipe_child(tmp_path: Path) -> Path:
    """The scripted pipe child (the chat path) — the regression gate's subject."""
    p = tmp_path / "pipe_child.py"
    p.write_text(_PIPE_CHILD_SOURCE)
    return p


def _kill_and_reap(session) -> None:
    """Kill the session's child AND reap it before returning (the deterministic
    way to take a live child out from under the manager).

    A bare ``kill()`` is not enough on a loaded host: ``process.poll()`` (what
    ``is_alive`` reads) can report ``None`` for a beat after the kill, racing the
    restart's death-confirmation step. Reaping with a bounded ``wait()`` makes
    the death deterministic before restart-on-death confirms it (the exact
    rationale documented in test_session_restart_resume.py::_kill_and_reap)."""
    proc = session.process
    proc.kill()
    try:
        proc.wait(timeout=_WAIT)
    except subprocess.TimeoutExpired:  # pragma: no cover — a wedged kill
        pass


# ─── visible-lifecycle (§2.12.3) — restart re-creates the PTY (acceptance #5) ──


def test_restart_recreates_pty(tmp_path: Path) -> None:
    """A pty-backed child dies → restart-on-death re-creates the PTY (a fresh
    ``os.openpty`` master) on the SAME key, keeping the scrollback across the
    restart, and a live viewer reattaches to the new master (§2.12.3,
    acceptance #5 — the reused lifecycle holds for visible sessions).

    Drives the real lifecycle end-to-end: open(pty) → produce pre-death output
    (lands in scrollback) → kill the real child → ``_on_process_death`` re-spawns
    → assert the session is alive again on a NEW master fd, the scrollback
    survived, and a fresh attach streams the kept snapshot then new live bytes.
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = _pty_manager(child)
    try:
        session = mgr.open("term", _pty_spec(tmp_path))
        assert mgr.is_alive(session)
        first_master = session.pty_master_fd
        assert first_master is not None

        # Pre-death output → lands in the scrollback the restart must keep.
        os.write(session.pty_master_fd, b"BEFORE_DEATH\n")
        assert _wait_for(
            lambda: b"BEFORE_DEATH" in session.scrollback.snapshot()
        ), "pre-death output never reached the scrollback"

        # Take the real child out and route the death through the manager's
        # restart-on-death (recovery is WP-005's; we drive the detection).
        _kill_and_reap(session)
        mgr._on_process_death(session)

        # Restart re-created the PTY: alive again, on a FRESH master fd.
        assert _wait_for(lambda: mgr.is_alive(session)), (
            "restart-on-death did not bring the pty session back alive"
        )
        assert session.pty_master_fd is not None
        assert session.pty_master_fd != first_master, (
            "restart did not re-create the PTY (master fd unchanged)"
        )

        # The scrollback survived the restart (restart-is-not-a-new-key applied
        # to the scrollback model, §2.12.3).
        assert b"BEFORE_DEATH" in session.scrollback.snapshot(), (
            "scrollback was not kept across the restart"
        )

        # A live viewer reattaches to the NEW master and streams: the kept
        # snapshot first, then fresh live bytes off the re-created PTY.
        viewer = mgr.attach("term")
        os.write(session.pty_master_fd, b"AFTER_RESTART\n")
        acc = bytearray()
        deadline = time.monotonic() + _WAIT
        it = viewer.stream()
        while time.monotonic() < deadline:
            try:
                chunk = next(it)
            except StopIteration:  # pragma: no cover — stream should stay open
                break
            if chunk:
                acc.extend(chunk)
                if b"AFTER_RESTART" in acc:
                    break
        assert b"BEFORE_DEATH" in acc, (
            f"reattach snapshot missing kept scrollback; saw {bytes(acc)!r}"
        )
        assert b"AFTER_RESTART" in acc, (
            f"reattach live feed missing post-restart output; saw {bytes(acc)!r}"
        )
        viewer.detach()

        # Observability: health reports the visible session as pty + alive.
        health = mgr.health("term")
        assert health.io_mode == "pty", health
        assert health.alive is True, health
    finally:
        mgr.shutdown()


# ─── visible-lifecycle (§2.12.3) — idle pty evicted by the same timer (#5) ─────


def test_idle_pty_evicted(tmp_path: Path) -> None:
    """An idle ``pty`` session with ZERO attached viewers is idle-evicted by the
    SAME maintenance timer as a headless pipe session (§2.12.3 — viewer presence
    is not activity; no special-casing for pty; acceptance #5).

    Determinism: a tiny idle timeout + stamping ``last_activity`` into the past
    against the manager's own maintenance clock, then driving the tick directly
    (mirrors WP-006's eviction suite — no sleep-based flakiness)."""
    child = fake_claude_child.write_child(tmp_path)
    mgr = _pty_manager(child, idle_timeout=10.0)
    try:
        session = mgr.open("term", _pty_spec(tmp_path))
        proc = session.process
        assert mgr.is_alive(session)

        # Zero viewers: a pty session with no viewer attached is "headless but
        # alive" — and idle-eligible exactly like a pipe session.
        assert mgr.health("term").viewer_count == 0

        # Make it look idle against the manager's own clock, then tick.
        session.last_activity = mgr._maintenance.clock() - 100.0
        mgr._maintenance_tick()

        # Evicted by the same timer: no longer owned + process terminated.
        assert "term" not in mgr.status_keys(), (
            "idle pty session was not evicted by the maintenance tick"
        )
        assert _wait_for(lambda: proc.poll() is not None), (
            "evicted pty session's process was not terminated"
        )
        assert all(row.key != "term" for row in mgr.status())
    finally:
        mgr.close("term")
        mgr.shutdown()


# ─── the headless-pipe non-regression gate (acceptance #4, the non-goal) ──────


def test_attach_on_pipe_is_not_pty_regression(tmp_path: Path) -> None:
    """The regression gate, aggregated (spec §Acceptance #4): a session opened
    WITHOUT the pty io-mode behaves exactly as the base contract — ``io_mode``
    defaults to ``"pipe"``, the chat turn round-trips unchanged — and ``attach``
    on that pipe session declines with ``NOT_PTY_SESSION`` (§2.15): there is no
    terminal to attach to. This is the non-goal (no chat-through-pty; the headless
    path is byte-unchanged) made executable. Held HERE and in WP-003 Blue +
    WP-005 Blue so it cannot be silently dropped (INDEX regression note).

    The full base-contract suite (test_session_manager_contract.py) running green
    with ``io_mode`` defaulted is the other half of this gate; that suite is run
    unchanged in the same pytest invocation (TDD §6.4 — 'the existing contract
    suite, re-run with defaulted io_mode')."""
    pipe_child = _write_pipe_child(tmp_path)
    mgr = SessionManager(
        {"pipe": _PipeChildAdapter(pipe_child)}, start_maintenance=False
    )
    try:
        # Open WITHOUT io_mode → defaults to "pipe" (additive, defaulted field):
        # every existing caller is byte-unchanged.
        spec = SessionSpec(provider="pipe", cwd=str(tmp_path))
        session = mgr.open("chat", spec)
        assert session.spec.io_mode == "pipe", session.spec

        # The chat turn round-trips unchanged (the base §2.2/§2.5 content model).
        mgr.send("chat", "hello")
        events = []
        deadline = time.monotonic() + _WAIT
        for ev in mgr.read("chat", since=0, follow=True):
            events.append(ev)
            if ev.kind == "result" or time.monotonic() > deadline:
                break
        assert any(ev.kind == "chunk" and ev.text == "hello" for ev in events), (
            f"pipe chat turn did not round-trip unchanged; saw {events!r}"
        )

        # Observability: a pipe session is headless with no terminal.
        health = mgr.health("chat")
        assert health.io_mode == "pipe", health
        assert health.viewer_count == 0, health

        # attach on a pipe session declines with NOT_PTY_SESSION (§2.15) — there
        # is no terminal to attach to; the consumer must open io_mode="pty".
        with pytest.raises(ExpectedError) as exc:
            mgr.attach("chat")
        assert "NOT_PTY_SESSION" in str(exc.value) or "pipe io-mode" in str(
            exc.value
        ), f"attach on a pipe session did not decline NOT_PTY_SESSION: {exc.value!r}"
    finally:
        mgr.close("chat")
        mgr.shutdown()
