"""The shared session-manager **daemon** — the singleton, on-demand, long-lived
manager both views attach to (TDD §2.1/§3, ADR-001, WP-003).

This is the *spine* of the change-owned-terminal-shared-session model: one
manager instance owns a change's session, and the cockpit (browser) and the
desktop terminal are two **views** of that one session. The daemon is what makes
"two views, one session" true — without it you are back to three parallel worlds
(an ephemeral cockpit host on a temp socket, a standalone desktop ``claude``).

It is a thin **singleton + stable-socket + lifecycle** wrapper around the frozen
engine (``_session_manager/``), composing exactly the pieces the (now-retired)
``session_manager_host`` standalone ``main`` composed — the
:class:`SessionManager` + :class:`SocketServer` + the WP-001
:class:`BindingManager` / :class:`ConnectionBindingRegistry` (the §2.13.4 guard)
— but at three points the host did not:

1. **Stable socket** (``~/.sulis/session-manager.sock``, env-overridable) instead
   of an ephemeral temp path, so both views find the *same* manager (ADR-001).
2. **Singleton via ``fcntl.flock``** (``LOCK_EX | LOCK_NB``) on
   ``~/.sulis/session-manager.lock``, taken **before** binding the socket. The
   lock-holder is the **sole binder**: only it reaches the engine's
   ``SocketServer.start`` (whose unconditional stale-socket ``os.unlink`` is the
   race ADR-001 closes). A second daemon that fails the lock confirms the
   existing socket answers a ``status`` ping and exits **0** — losing the race is
   normal, not an error.
3. **The real interactive Claude pty adapter** (WP-004) registered under provider
   ``pty``, so a get-or-spawn for a change runs the change's interactive
   ``claude --agent sulis`` in its worktree — not the fake echo child the host
   wired. (The fake child stays test-only, reachable via the
   ``SULIS_DAEMON_PTY_CHILD`` seam so the integration suite runs without the real
   binary — the WP-009 ``--verbose`` lesson: CI cannot run real ``claude``.)
4. **Daemon-level idle-empty auto-exit** — when the manager has held **zero
   sessions** continuously for ``SULIS_DAEMON_IDLE_EXIT_SECS`` (default 1800s)
   the daemon self-shuts-down (server stop, manager shutdown, socket unlink, lock
   release) and exits 0; the next ``ensure-daemon`` restarts it. This bounds a
   forgotten daemon without coupling its lifetime to any window. It is **distinct
   from** the engine's per-session idle eviction (``maintenance.py``, which stays
   ON): that reaps one *idle session*; this reaps the *whole empty daemon*.

**Independence (founder directive, MUST; ADR-003).** This module imports nothing
from the cockpit chat relay, the chat ``SessionBridge``, or the ``platform``
communication service. The daemon owns the engine for the **terminal** over the
socket directly — terminal-only. (Codified by an import-graph test.)

The engine is reused, **never modified**: the flock gates the engine's existing
stale-socket unlink so only the lock-holder binds — no engine edit needed
(ADR-001 § Consequences).
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

# Run from any cwd: the engine package + the daemon-presence binding live under
# this file's directory; the shared test pty child lives in tests/lib. Mirror the
# host's import wiring so the daemon resolves its imports regardless of cwd.
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_SCRIPTS / "tests" / "lib") not in sys.path:
    sys.path.insert(0, str(_SCRIPTS / "tests" / "lib"))

import fcntl  # noqa: E402

from _session_manager import daemon_client  # noqa: E402
from _session_manager.adapter import ProviderAdapter  # noqa: E402
from _session_manager.adapters.claude_pty import (  # noqa: E402
    InteractiveClaudePtyAdapter,
)
from _session_manager.binding import (  # noqa: E402
    BindingManager,
    ConnectionBindingRegistry,
)
from _session_manager.manager import SessionManager  # noqa: E402
from _session_manager.socket_server import SocketServer  # noqa: E402

# ── tuning defaults ───────────────────────────────────────────────────────────

#: Default daemon idle-empty window in seconds (ADR-001): zero sessions held
#: continuously for this long → the daemon self-shuts-down. 30 minutes — generous
#: enough that an active founder never trips it, bounded enough that a forgotten
#: daemon does not linger forever. Overridable via ``SULIS_DAEMON_IDLE_EXIT_SECS``
#: (the test/CI injection seam, mirroring the socket override).
DEFAULT_IDLE_EXIT_SECS = 1800.0

#: How often the idle-empty watcher samples the manager, in seconds. Small
#: relative to the window so the daemon exits promptly after it crosses the
#: threshold, but not so small it busy-spins.
_IDLE_WATCH_INTERVAL_SECS = 30.0

#: Env seams (test/CI injection). ``SULIS_DAEMON_PTY_CHILD`` points the pty
#: provider at the shared fake child (a real subprocess, not a mock — MEA-09) so
#: the integration suite runs without the real ``claude`` binary; production
#: leaves it unset and the real interactive adapter is wired.
_ENV_IDLE_EXIT = "SULIS_DAEMON_IDLE_EXIT_SECS"
_ENV_PTY_CHILD = "SULIS_DAEMON_PTY_CHILD"

#: The stable singleton lock path (ADR-001), parallel to the stable socket the
#: daemon-presence binding resolves. Overridable via ``--lock`` so each test gets
#: an isolated lock + socket pair.
_LOCK_FILENAME = "session-manager.lock"


def resolve_default_lock() -> str:
    """The stable singleton-lock path: ``~/.sulis/session-manager.lock``.

    Lives beside the stable socket (``daemon_client.resolve_default_socket``);
    the flock on it is the daemon's single-instance arbiter (ADR-001). Always an
    absolute path.
    """
    return str(Path.home() / ".sulis" / _LOCK_FILENAME)


def resolve_idle_exit_secs() -> float:
    """The idle-empty window in seconds (``SULIS_DAEMON_IDLE_EXIT_SECS`` or the
    default). A non-positive or unparseable override falls back to the default —
    a bad tuning value must degrade to the safe bound, not crash the daemon."""
    raw = os.environ.get(_ENV_IDLE_EXIT)
    if not raw:
        return DEFAULT_IDLE_EXIT_SECS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_IDLE_EXIT_SECS
    return value if value > 0 else DEFAULT_IDLE_EXIT_SECS


# ── the idle-empty auto-exit watcher (the daemon's lifecycle policy) ──────────


class IdleEmptyExitWatcher:
    """Fires a shutdown callback when the manager has owned **zero sessions**
    continuously for ``idle_exit_secs`` (ADR-001 daemon-level idle-empty auto-
    exit).

    This is the *daemon's* lifecycle policy, distinct from the engine's per-
    session idle eviction (``maintenance.py``): it reaps the whole daemon when it
    is *empty*, not one idle session. A small pure-ish helper taking an injected
    ``clock`` + a ``status_keys`` callable so it is unit-testable without real
    sleeping (MEA-09): a test steps the clock and calls :meth:`tick`.

    The window is *continuous* emptiness — a session appearing resets the empty-
    since mark, so the daemon only exits after a full window with no sessions at
    all. Shutdown is a one-way door: :meth:`tick` fires ``on_idle_empty`` at most
    once (a second call would double-stop the server).

    Args:
        status_keys: returns the set of keys the manager currently owns (the
            manager's cheap, side-effect-free ``status_keys`` — consumed, not
            re-implemented).
        idle_exit_secs: the continuous-empty window before shutdown. Must be > 0.
        on_idle_empty: the shutdown callback, invoked once when the window
            elapses with the manager continuously empty.
        clock: the monotonic clock used to measure the window — injectable so a
            test drives it deterministically. Defaults to ``time.monotonic``.
    """

    def __init__(
        self,
        *,
        status_keys: Callable[[], set[str]],
        idle_exit_secs: float,
        on_idle_empty: Callable[[], None],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if idle_exit_secs <= 0:
            raise ValueError("idle_exit_secs must be > 0")
        self._status_keys = status_keys
        self._idle_exit_secs = float(idle_exit_secs)
        self._on_idle_empty = on_idle_empty
        self._clock = clock
        #: When the manager last became (or was first observed) empty; ``None``
        #: while a session exists. The empty window is measured from this mark.
        self._empty_since: float | None = None
        #: One-way latch so shutdown fires at most once.
        self._fired = False

    def tick(self) -> None:
        """Sample the manager once; fire the shutdown callback iff it has been
        continuously empty for the window. Idempotent after firing."""
        if self._fired:
            return
        now = self._clock()
        if self._status_keys():
            # A session exists → not idle-empty; reset the empty-since mark so the
            # window must restart from the next time the daemon goes empty.
            self._empty_since = None
            return
        if self._empty_since is None:
            # First observation of emptiness — start the window here.
            self._empty_since = now
            return
        if (now - self._empty_since) >= self._idle_exit_secs:
            self._fired = True
            self._on_idle_empty()


# ── composition root (WPB-07): adapters + server wiring ──────────────────────


def _build_pty_adapter() -> ProviderAdapter:
    """The pty provider for this daemon.

    Production: the **real** interactive Claude pty adapter (WP-004) — a get-or-
    spawn runs the change's interactive ``claude --agent sulis`` in its worktree.
    Test/CI (``SULIS_DAEMON_PTY_CHILD`` set): the shared fake pty child via
    :class:`PtyChildAdapter` — a real subprocess (MEA-09), not a mock, so the
    integration suite exercises the real socket + manager + a real pty without
    the real binary (the WP-009 ``--verbose`` lesson)."""
    child = os.environ.get(_ENV_PTY_CHILD)
    if child:
        # Test seam only: the fake child + its adapter live under tests/lib (on
        # sys.path above). Imported lazily so production never loads test code.
        from session_child_adapters import PtyChildAdapter

        return PtyChildAdapter(Path(child))
    return InteractiveClaudePtyAdapter()


def _build_server(socket_path: str) -> tuple[SocketServer, SessionManager]:
    """Wire a real :class:`SessionManager` (pty provider) + a :class:`SocketServer`
    over ``socket_path`` with the §2.13.4 binding guard **ON**.

    Session-level idle eviction is the engine's job, so ``start_maintenance=True``
    (the daemon's own idle-empty auto-exit is separate; see
    :class:`IdleEmptyExitWatcher`). Returns ``(server, manager)`` so the caller
    can stop both on shutdown. Mirrors the (retired) host's bound-server shape so
    the two share one binding resolver (EP-03) — the host's standalone ``main``
    is gone; this is the single composition root for the engine over the socket.
    """
    manager = SessionManager(
        {"pty": _build_pty_adapter()},
        start_maintenance=True,  # engine's per-session idle eviction ON
    )
    registry = ConnectionBindingRegistry()
    server = SocketServer(
        BindingManager(manager, registry),
        socket_path,
        bound_key_for=registry.resolve,
    )
    return server, manager


# ── the daemon lifecycle ──────────────────────────────────────────────────────


def _acquire_singleton_lock(lock_path: str) -> "int | None":
    """Take the singleton flock (``LOCK_EX | LOCK_NB``) for the daemon's life.

    Returns the open lock fd on success (this process is THE daemon; the fd is
    held for the process's life — ``fcntl.flock`` auto-releases on death, so no
    stale-lock cleanup is needed, ADR-001). Returns ``None`` if another daemon
    already holds the lock (losing the race is normal — the caller confirms the
    live socket and exits 0).

    The lock's parent dir is created ``0o700`` first (the stable-socket dir gate,
    §2.8.1 parity) so a fresh ``~/.sulis`` works without a separate mkdir."""
    parent = Path(lock_path).resolve().parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def _release_singleton_lock(lock_fd: int) -> None:
    """Release + close the singleton lock fd (idempotent best-effort)."""
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
    except OSError:  # pragma: no cover - best-effort
        pass
    try:
        os.close(lock_fd)
    except OSError:  # pragma: no cover - best-effort
        pass


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="The shared session-manager daemon")
    parser.add_argument(
        "--socket",
        default=daemon_client.resolve_default_socket(),
        help="stable AF_UNIX socket path to serve on (default: the stable socket)",
    )
    parser.add_argument(
        "--lock",
        default=resolve_default_lock(),
        help="singleton flock path (default: the stable lock beside the socket)",
    )
    args = parser.parse_args(argv)

    # 1. Singleton arbitration: take the flock BEFORE binding so only the holder
    #    reaches SocketServer.start's unlink+bind (closes the race, ADR-001).
    lock_fd = _acquire_singleton_lock(args.lock)
    if lock_fd is None:
        # Lost the race. The winner is (or is becoming) the daemon. If its socket
        # already answers, this is the normal "another daemon won" path: print
        # READY and exit 0. Else the winner is mid-boot — briefly poll, then exit
        # 0 if it comes up (the caller's ensure-daemon also polls) or non-zero if
        # the lock is held with no live socket (a genuinely wedged daemon).
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if daemon_client.daemon_is_live(args.socket):
                sys.stdout.write(f"READY {args.socket}\n")
                sys.stdout.flush()
                return 0
            time.sleep(0.05)
        sys.stderr.write(
            f"singleton lock held but no live socket at {args.socket} — "
            "a daemon is mid-boot or wedged; ensure-daemon will retry\n"
        )
        return 1

    # 2. This process is THE daemon. Ensure the socket's parent dir exists 0o700
    #    (the §2.8.1 gate; the engine chmods the socket itself 0o600 at bind).
    Path(args.socket).resolve().parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    stop = threading.Event()

    def _stop() -> None:
        """The single clean-stop path (signal-driven OR idle-empty-driven): stop
        the server, shut the manager down, unlink the socket (server.stop does),
        release the lock. Idempotent via the stop Event."""
        stop.set()

    # SIGTERM / SIGINT → the same clean stop. Installed BEFORE binding + READY so
    # a signal arriving the instant a view (or test) sees READY is caught by this
    # handler, never the default disposition (which would kill with -SIGTERM, not
    # exit 0). Signal handlers must be set on the main thread — this is it.
    signal.signal(signal.SIGTERM, lambda *_a: _stop())
    signal.signal(signal.SIGINT, lambda *_a: _stop())

    server, manager = _build_server(args.socket)
    server.start()  # only the lock-holder reaches the engine's unlink+bind

    # 3. Idle-empty auto-exit watcher on a background daemon thread. When the
    #    manager has been empty for the window, it sets the stop Event — the same
    #    clean teardown SIGTERM drives (one stop path, ADR-001).
    watcher = IdleEmptyExitWatcher(
        status_keys=manager.status_keys,
        idle_exit_secs=resolve_idle_exit_secs(),
        on_idle_empty=_stop,
    )

    def _idle_loop() -> None:
        # Interruptible wait (not a bare sleep) so shutdown is prompt.
        while not stop.wait(_IDLE_WATCH_INTERVAL_SECS):
            watcher.tick()

    idle_thread = threading.Thread(
        target=_idle_loop, name="daemon-idle-empty-watch", daemon=True
    )
    idle_thread.start()

    # 4. Signal readiness (both views wait for this before connecting). By now the
    #    socket is bound AND the signal handlers are installed.
    sys.stdout.write(f"READY {args.socket}\n")
    sys.stdout.flush()

    try:
        stop.wait()
    finally:
        server.stop()  # shuts the server down + unlinks the socket
        manager.shutdown()  # stops engine maintenance + closes every session
        _release_singleton_lock(lock_fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
