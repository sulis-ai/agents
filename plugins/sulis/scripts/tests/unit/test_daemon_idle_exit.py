"""WP-003 (change-owned-terminal-shared-session) — the daemon-level idle-empty
auto-exit watcher.

Contract: ``WP-003-shared-daemon-singleton.md`` Definition of Done > Red
(``tests/unit/test_daemon_idle_exit.py``) + TDD §2.1/§3 + ADR-001
(daemon-level shutdown policy: idle-empty auto-exit — zero sessions held
continuously for ``SULIS_DAEMON_IDLE_EXIT_SECS`` (default 1800s) → self-
shutdown). This is **distinct** from the engine's per-session idle eviction
(``maintenance.py``): the watcher reaps the *whole daemon* when it has owned
**no sessions at all** for the window, so a forgotten daemon never lingers.

Verification posture (MEA-09, deterministic): the watcher is a small pure-ish
helper taking an **injected clock** + a ``status_keys`` callable, so a test
drives "time" by stepping the clock and asserts the shutdown callback fires
exactly when the window elapses with the manager continuously empty — no real
sleeping, no flake.

Tests (RED first, per the WP Definition of Done):
    test_daemon_idle_exit.py::test_watcher_fires_shutdown_after_window_continuously_empty
    test_daemon_idle_exit.py::test_watcher_does_not_fire_while_a_session_exists
    test_daemon_idle_exit.py::test_a_session_appearing_resets_the_empty_window
    test_daemon_idle_exit.py::test_watcher_fires_shutdown_at_most_once
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# The watcher lives on the daemon module (it is the daemon's lifecycle policy,
# not the engine's). Importing it is the first thing that fails before WP-003.
import session_manager_daemon
from session_manager_daemon import IdleEmptyExitWatcher


class _FakeClock:
    """A hand-cranked monotonic clock — the test steps time deterministically."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = float(start)

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += float(seconds)


def test_watcher_fires_shutdown_after_window_continuously_empty() -> None:
    """With zero sessions held continuously for the configured window, the
    watcher's ``tick`` fires the shutdown callback exactly once the window
    elapses — not before. Fails before the watcher exists."""
    clock = _FakeClock()
    fired: list[bool] = []
    watcher = IdleEmptyExitWatcher(
        status_keys=lambda: set(),  # always empty
        idle_exit_secs=1800.0,
        on_idle_empty=lambda: fired.append(True),
        clock=clock,
    )

    # First tick observes "empty since now"; the window has not elapsed.
    watcher.tick()
    assert fired == [], "watcher fired before the empty window elapsed"

    # Just before the window: still no fire.
    clock.advance(1799.0)
    watcher.tick()
    assert fired == [], "watcher fired one second before the window elapsed"

    # The window elapses: the daemon self-shuts-down.
    clock.advance(1.0)
    watcher.tick()
    assert fired == [True], "watcher did not fire once the empty window elapsed"


def test_watcher_does_not_fire_while_a_session_exists() -> None:
    """A daemon that still owns at least one session is NOT idle-empty: even far
    past the window, the watcher never fires while ``status_keys`` is non-empty
    (the rule is zero sessions, distinct from per-session idle eviction). Fails
    before the watcher exists."""
    clock = _FakeClock()
    fired: list[bool] = []
    watcher = IdleEmptyExitWatcher(
        status_keys=lambda: {"chg_A"},  # always one session
        idle_exit_secs=1800.0,
        on_idle_empty=lambda: fired.append(True),
        clock=clock,
    )

    watcher.tick()
    clock.advance(100_000.0)  # far past the window
    watcher.tick()
    assert fired == [], "watcher self-shut-down while a session was still alive"


def test_a_session_appearing_resets_the_empty_window() -> None:
    """The window must be *continuous* emptiness: a session appearing partway
    through resets the empty-since clock, so the watcher only fires a full window
    after the daemon goes empty *again*. Fails before the watcher exists."""
    clock = _FakeClock()
    fired: list[bool] = []
    keys: set[str] = set()
    watcher = IdleEmptyExitWatcher(
        status_keys=lambda: set(keys),
        idle_exit_secs=1800.0,
        on_idle_empty=lambda: fired.append(True),
        clock=clock,
    )

    # Empty for most of the window …
    watcher.tick()
    clock.advance(1700.0)
    # … then a session opens (resets the empty window).
    keys.add("chg_A")
    watcher.tick()
    clock.advance(1700.0)
    keys.discard("chg_A")  # empty again, but the window restarts from here
    watcher.tick()
    assert fired == [], "watcher fired without a full continuous empty window"

    # A full window of continuous emptiness from the reset → now it fires.
    clock.advance(1800.0)
    watcher.tick()
    assert fired == [True], "watcher did not fire after a fresh full empty window"


def test_watcher_fires_shutdown_at_most_once() -> None:
    """Once the watcher has triggered shutdown it does not re-fire on later ticks
    (shutdown is a one-way door — a second ``on_idle_empty`` would double-stop the
    server). Fails before the watcher exists."""
    clock = _FakeClock()
    fired: list[bool] = []
    watcher = IdleEmptyExitWatcher(
        status_keys=lambda: set(),
        idle_exit_secs=10.0,
        on_idle_empty=lambda: fired.append(True),
        clock=clock,
    )

    watcher.tick()
    clock.advance(11.0)
    watcher.tick()  # fires
    clock.advance(11.0)
    watcher.tick()  # must NOT fire again
    assert fired == [True], f"watcher fired more than once: {fired!r}"


def test_idle_exit_secs_must_be_positive() -> None:
    """A non-positive window is a programming error, declined at construction —
    a zero/negative window would make the daemon exit the instant it goes empty,
    defeating the bound. Fails before the watcher exists."""
    with pytest.raises(ValueError):
        IdleEmptyExitWatcher(
            status_keys=lambda: set(),
            idle_exit_secs=0.0,
            on_idle_empty=lambda: None,
        )


# ─── config resolution (the env-overridable tuning seams, ADR-001) ────────────


def test_resolve_default_lock_is_absolute_under_dot_sulis() -> None:
    """The stable lock lives at ``~/.sulis/session-manager.lock`` — an absolute
    path beside the stable socket (ADR-001)."""
    lock = session_manager_daemon.resolve_default_lock()
    assert os.path.isabs(lock), lock
    assert lock.endswith(os.path.join(".sulis", "session-manager.lock")), lock


def test_resolve_idle_exit_secs_default_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset → the 1800s production default (ADR-001)."""
    monkeypatch.delenv("SULIS_DAEMON_IDLE_EXIT_SECS", raising=False)
    assert (
        session_manager_daemon.resolve_idle_exit_secs()
        == session_manager_daemon.DEFAULT_IDLE_EXIT_SECS
    )


def test_resolve_idle_exit_secs_honours_a_valid_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A positive override is honoured (the test/CI injection seam)."""
    monkeypatch.setenv("SULIS_DAEMON_IDLE_EXIT_SECS", "12.5")
    assert session_manager_daemon.resolve_idle_exit_secs() == 12.5


@pytest.mark.parametrize("bad", ["not-a-number", "0", "-5"])
def test_resolve_idle_exit_secs_falls_back_on_a_bad_override(
    monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    """A non-positive or unparseable override degrades to the safe default —
    a bad tuning value must not crash the daemon or defeat the bound (ADR-001)."""
    monkeypatch.setenv("SULIS_DAEMON_IDLE_EXIT_SECS", bad)
    assert (
        session_manager_daemon.resolve_idle_exit_secs()
        == session_manager_daemon.DEFAULT_IDLE_EXIT_SECS
    )


# ─── the singleton flock helpers (the daemon's single-instance arbiter) ───────


def test_acquire_singleton_lock_grants_then_blocks_a_second_acquirer(
    tmp_path: Path,
) -> None:
    """The first acquirer of the flock wins (returns an fd); a second non-blocking
    acquirer on the SAME lock is refused (returns ``None``) — the load-bearing
    singleton arbitration (ADR-001). Releasing the first lets the second win."""
    lock_path = str(tmp_path / "x.lock")

    first_fd = session_manager_daemon._acquire_singleton_lock(lock_path)
    assert first_fd is not None, "first acquirer did not win the lock"
    try:
        # While the first holds it, a second acquirer must lose (None, not block).
        second_fd = session_manager_daemon._acquire_singleton_lock(lock_path)
        assert second_fd is None, "a second acquirer won a held lock"
    finally:
        session_manager_daemon._release_singleton_lock(first_fd)

    # After release, a fresh acquirer wins (the lock is free).
    third_fd = session_manager_daemon._acquire_singleton_lock(lock_path)
    assert third_fd is not None, "lock was not released for a later acquirer"
    session_manager_daemon._release_singleton_lock(third_fd)


def test_acquire_singleton_lock_creates_parent_dir_0o700(tmp_path: Path) -> None:
    """The lock's parent dir is created 0o700 when absent (the §2.8.1 gate parity)
    so a fresh ``~/.sulis`` works without a separate mkdir (ADR-001)."""
    nested = tmp_path / "fresh" / "dir"
    lock_path = str(nested / "x.lock")
    assert not nested.exists()

    fd = session_manager_daemon._acquire_singleton_lock(lock_path)
    assert fd is not None
    try:
        assert nested.is_dir(), "parent dir was not created"
        mode = nested.stat().st_mode & 0o777
        assert mode == 0o700, f"parent dir mode is {oct(mode)}, expected 0o700"
    finally:
        session_manager_daemon._release_singleton_lock(fd)


def test_release_singleton_lock_is_best_effort_idempotent(tmp_path: Path) -> None:
    """Releasing is best-effort: double-release (or release of an already-closed
    fd) does not raise — the clean-stop path must not crash on teardown."""
    lock_path = str(tmp_path / "x.lock")
    fd = session_manager_daemon._acquire_singleton_lock(lock_path)
    assert fd is not None
    session_manager_daemon._release_singleton_lock(fd)
    # Second release of the now-closed fd must be a no-op, not an exception.
    session_manager_daemon._release_singleton_lock(fd)


# ─── the pty-provider selection seam (real adapter vs fake child) ─────────────


def test_build_pty_adapter_is_real_interactive_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no test seam set, the daemon wires the REAL interactive Claude pty
    adapter (WP-004) under provider pty — production behaviour (TDD §2.1)."""
    from _session_manager.adapters.claude_pty import InteractiveClaudePtyAdapter

    monkeypatch.delenv("SULIS_DAEMON_PTY_CHILD", raising=False)
    adapter = session_manager_daemon._build_pty_adapter()
    assert isinstance(adapter, InteractiveClaudePtyAdapter)


def test_build_pty_adapter_uses_fake_child_when_seam_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With ``SULIS_DAEMON_PTY_CHILD`` set, the daemon wires the fake pty child
    via PtyChildAdapter (the MEA-09 test substrate) — so the integration suite
    runs without the real ``claude`` binary (the WP-009 lesson)."""
    from session_child_adapters import PtyChildAdapter

    child = tmp_path / "fake.py"
    child.write_text("import sys; sys.exit(0)\n")
    monkeypatch.setenv("SULIS_DAEMON_PTY_CHILD", str(child))
    adapter = session_manager_daemon._build_pty_adapter()
    assert isinstance(adapter, PtyChildAdapter)


def test_build_server_wires_bound_guard_over_a_real_manager(tmp_path: Path) -> None:
    """The composition root wires a real SessionManager (pty provider) +
    SocketServer with the §2.13.4 binding guard ON. Constructed but not started
    here (no bind) — proves the wiring shape without a live socket. Engine
    maintenance is stopped immediately so the test leaks no background thread."""
    socket_path = str(tmp_path / "d.sock")
    child = tmp_path / "fake.py"
    child.write_text("import sys; sys.exit(0)\n")
    os.environ["SULIS_DAEMON_PTY_CHILD"] = str(child)
    try:
        server, manager = session_manager_daemon._build_server(socket_path)
    finally:
        os.environ.pop("SULIS_DAEMON_PTY_CHILD", None)
    try:
        assert server.socket_path == socket_path
        # The guard is ON: the server carries a bound-key resolver.
        assert server._bound_key_for is not None
        assert manager.status_keys() == set()
    finally:
        manager.shutdown()
