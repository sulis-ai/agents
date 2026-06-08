"""Production session-manager host process (engine owner, binding guard ON).

Contract: terminal contract §2.13.4 (the attach-authorisation binding guard) +
ADR-010 (the terminal is a sanctioned, attach-authorised write path — the guard
turns ON for the cockpit) + ADR-011 (the cockpit owns the shipped engine via a
long-lived spawned Python host process).

This is the **production** sibling of ``apps/cockpit/e2e/terminal-backend.py``:
a long-lived process the cockpit server spawns at boot. It owns the shipped,
contract-frozen :class:`SessionManager` + :class:`SocketServer` over a 0o600
AF_UNIX socket, with the per-change binding guard **ON**
(``SocketServer(manager, socket, bound_key_for=…)``). Unlike the e2e backend it
seeds **no** scrollback banner — that pre-seeding is harness-only (it exists so
the Playwright e2e can assert the "render existing scrollback" guarantee).

It composes the engine; it does not modify it (``_session_manager/`` is frozen).
The only new code here is (1) the per-connection binding resolver that turns the
guard ON, and (2) the no-seed boot + signal-driven shutdown (mirrors
``terminal-backend.py``). It is deliberately decoupled from the cockpit chat
relay: this host owns the engine for the **terminal** via the socket directly.

Usage (invoked by the cockpit server, ADR-011):
    python3 session_manager_host.py --socket /tmp/x.sock

It prints ``READY <socket_path>`` on stdout once the socket is serving, then
runs until killed (SIGTERM/SIGINT) — the cockpit owns its lifetime.

The binding guard (§2.13.4): each AF_UNIX connection is scoped to the single
change ``key`` of its **first** session use on that connection. Because the
shipped :class:`SocketServer` serves each connection on its own handler thread
(``ThreadingMixIn``), connection identity is thread identity — so the resolver
keys the binding by the handler thread and the same-thread ``open`` records it.
Any later guarded method (``attach``/``feed``/``detach``/``resize``) on a
*different* key over the same connection is refused ``NOT_AUTHORIZED`` (the
literal terminal analogue of ADR-004's positive session-to-change binding).
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
from pathlib import Path

# The session manager package + the real pty child/adapter live under
# plugins/sulis/scripts (this file's directory). Mirror terminal-backend.py's
# import wiring so the host runs from any cwd.
_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "tests" / "lib"))

from _session_manager.adapter import SessionSpec  # noqa: E402
from _session_manager.manager import SessionManager  # noqa: E402
from _session_manager.socket_server import SocketServer  # noqa: E402

import fake_claude_child  # noqa: E402
from session_child_adapters import PtyChildAdapter  # noqa: E402


class ConnectionBindingRegistry:
    """Per-connection change binding for the §2.13.4 guard (the resolver state).

    A connection is bound to the single change ``key`` of its **first** session
    use; every subsequent guarded method on a *different* key is refused. The
    shipped :class:`SocketServer` serves one handler thread per connection
    (``ThreadingMixIn``), so the handler thread id identifies the connection —
    :meth:`bind_first` (called on the same thread as the connection's first
    ``open``) records it, and :meth:`resolve` (the ``bound_key_for`` callback)
    reads it back.

    Pure and thread-safe; testable without a live socket (Blue).
    """

    def __init__(self) -> None:
        self._bindings: dict[int, str] = {}
        self._lock = threading.Lock()

    def bind_first(self, key: str, *, thread_id: int | None = None) -> str:
        """Record (idempotently) the change a connection is bound to.

        The first ``key`` seen on a connection thread wins; later calls on the
        same thread keep the original binding (they do not re-bind). Returns the
        binding now in force for the thread."""
        tid = thread_id if thread_id is not None else threading.get_ident()
        with self._lock:
            return self._bindings.setdefault(tid, key)

    def resolve(self, _conn: object, *, thread_id: int | None = None) -> str | None:
        """The ``bound_key_for`` resolver: the change this connection is bound to.

        ``None`` before the connection has opened anything (no guarded method can
        precede the bind on a real client flow). The ``_conn`` socket argument is
        the shipped resolver signature; binding is keyed by handler thread."""
        tid = thread_id if thread_id is not None else threading.get_ident()
        with self._lock:
            return self._bindings.get(tid)


class _BindingManager:
    """A thin pass-through wrapper over :class:`SessionManager` that records the
    per-connection binding on each ``open`` (the only place a connection first
    names its change), then delegates verbatim. It changes no engine behaviour —
    it only observes ``open`` to feed the §2.13.4 guard. Everything else is
    forwarded unchanged via ``__getattr__`` so the frozen manager surface is
    untouched."""

    def __init__(
        self, manager: SessionManager, registry: ConnectionBindingRegistry
    ) -> None:
        self._manager = manager
        self._registry = registry

    def open(self, key: str, spec: SessionSpec):  # noqa: ANN201 - delegates the engine's type
        # Bind this connection (handler thread) to the first change it opens.
        self._registry.bind_first(key)
        return self._manager.open(key, spec)

    def __getattr__(self, name: str):  # noqa: ANN001, ANN201 - transparent delegation
        return getattr(self._manager, name)


def _build_server(
    socket_path: str, *, cwd: str, bound: bool
) -> tuple[SocketServer, SessionManager]:
    """Wire a real :class:`SessionManager` (pty adapter) + a :class:`SocketServer`
    over ``socket_path`` with the binding guard ON (default). No scrollback is
    seeded. Returns ``(server, underlying_manager)`` so the caller can shut both
    down on signal."""
    os.makedirs(cwd, exist_ok=True)
    child = fake_claude_child.write_child(Path(cwd))
    manager = SessionManager({"pty": PtyChildAdapter(child)}, start_maintenance=False)

    if bound:
        registry = ConnectionBindingRegistry()
        server = SocketServer(
            _BindingManager(manager, registry),
            socket_path,
            bound_key_for=registry.resolve,
        )
    else:
        # Guard OFF: only the 0o600 filesystem permission gates (parity escape
        # hatch; production defaults bound).
        server = SocketServer(manager, socket_path)
    return server, manager


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--socket", required=True, help="AF_UNIX socket path to serve on"
    )
    parser.add_argument(
        "--cwd",
        default=None,
        help="working dir for the pty child (default: a tmp dir beside the socket)",
    )
    guard = parser.add_mutually_exclusive_group()
    guard.add_argument(
        "--bound",
        dest="bound",
        action="store_true",
        help="turn the per-change binding guard ON (default, production)",
    )
    guard.add_argument(
        "--no-bound",
        dest="bound",
        action="store_false",
        help="turn the binding guard OFF (filesystem permission only)",
    )
    parser.set_defaults(bound=True)
    args = parser.parse_args(argv)

    cwd = args.cwd or str(Path(args.socket).resolve().parent / "host-cwd")

    server, manager = _build_server(args.socket, cwd=cwd, bound=args.bound)
    server.start()

    # Signal readiness (the cockpit waits for this line before connecting).
    sys.stdout.write(f"READY {args.socket}\n")
    sys.stdout.flush()

    stop = threading.Event()

    def _shutdown(*_a: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        stop.wait()
    finally:
        server.stop()
        manager.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
