"""Per-connection change-binding primitives for the §2.13.4 attach-authorisation
guard — the importable home shared by the (retiring) ``session_manager_host`` and
the new shared daemon (TDD §2.1, ADR-001, WP-001).

These two classes were originally defined inline in ``session_manager_host.py``.
WP-001 moves them here, unchanged, so both the host shim and the daemon (WP-003)
reuse one binding resolver — no duplication (EP-03). ``_BindingManager`` is
renamed :class:`BindingManager` (now public-importable); the registry keeps its
name. Pure logic; behaviour-preserving move.

The guard (§2.13.4): each AF_UNIX connection is scoped to the single change
``key`` of its **first** session use on that connection. The shipped
:class:`~_session_manager.socket_server.SocketServer` serves each connection on
its own handler thread (``ThreadingMixIn``), so connection identity is thread
identity — the resolver keys the binding by the handler thread and the same-thread
``open`` records it. Any later guarded method (``attach``/``feed``/``detach``/
``resize``) on a *different* key over the same connection is refused
``NOT_AUTHORIZED``.

This module imports nothing from the chat relay or the ``platform`` communication
service — terminal-only, per the change's independence directive.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing-only; no runtime engine coupling
    from _session_manager.adapter import SessionSpec
    from _session_manager.manager import SessionManager


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


class BindingManager:
    """A thin pass-through wrapper over :class:`SessionManager` that records the
    per-connection binding on each ``open`` (the only place a connection first
    names its change), then delegates verbatim. It changes no engine behaviour —
    it only observes ``open`` to feed the §2.13.4 guard. Everything else is
    forwarded unchanged via ``__getattr__`` so the frozen manager surface is
    untouched.

    Renamed from ``_BindingManager`` in WP-001 (now public-importable so the
    shared daemon can reuse it)."""

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
