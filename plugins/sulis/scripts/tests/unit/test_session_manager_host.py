"""WP-001 (production-terminal-sidecar) — unit tests for the host's binding
resolver + manager wrapper (the §2.13.4 guard's pure, socket-free surface).

The integration suite (tests/integration/test_session_manager_host.py) proves
the host end-to-end over a real socket/process. These unit tests pin the pure
pieces the guard is built from — testable without a live socket (Blue): the
per-connection :class:`ConnectionBindingRegistry` and the ``open``-observing
:class:`_BindingManager`.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS_DIR))

from session_manager_host import (  # noqa: E402
    ConnectionBindingRegistry,
    _BindingManager,
    _build_server,
)


def test_resolve_is_none_before_any_bind() -> None:
    """A connection that has opened nothing is bound to nothing — the guard
    declines every guarded key until the connection's first ``open``."""
    reg = ConnectionBindingRegistry()
    assert reg.resolve(object(), thread_id=1) is None


def test_first_key_binds_and_resolves() -> None:
    """The first ``bind_first`` on a connection sets the binding; ``resolve``
    reads it back for that same connection."""
    reg = ConnectionBindingRegistry()
    assert reg.bind_first("chg_A", thread_id=1) == "chg_A"
    assert reg.resolve(object(), thread_id=1) == "chg_A"


def test_first_key_wins_subsequent_binds_are_idempotent() -> None:
    """A connection is scoped to its FIRST change: a later ``bind_first`` with a
    different key does not re-bind (§2.13.4 — one change per connection)."""
    reg = ConnectionBindingRegistry()
    assert reg.bind_first("chg_A", thread_id=1) == "chg_A"
    assert reg.bind_first("chg_B", thread_id=1) == "chg_A"
    assert reg.resolve(object(), thread_id=1) == "chg_A"


def test_bindings_are_per_connection() -> None:
    """Distinct connections (handler threads) carry independent bindings — one
    connection bound to A never leaks authorisation to another bound to B."""
    reg = ConnectionBindingRegistry()
    reg.bind_first("chg_A", thread_id=1)
    reg.bind_first("chg_B", thread_id=2)
    assert reg.resolve(object(), thread_id=1) == "chg_A"
    assert reg.resolve(object(), thread_id=2) == "chg_B"


def test_resolve_defaults_to_the_calling_thread() -> None:
    """Without an explicit ``thread_id`` the registry keys by the running thread —
    the production path, where ``open`` and the resolver run on the same handler
    thread (the shipped ThreadingMixIn gives one thread per connection)."""
    reg = ConnectionBindingRegistry()
    captured: dict[str, str | None] = {}

    def worker() -> None:
        reg.bind_first("chg_T")
        captured["bound"] = reg.resolve(object())

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=5.0)
    assert captured["bound"] == "chg_T"
    # The main thread, which never bound, sees nothing.
    assert reg.resolve(object()) is None


class _FakeManager:
    """A stand-in for SessionManager: records the keys it was asked to open and
    answers an attribute used to prove transparent delegation."""

    def __init__(self) -> None:
        self.opened: list[str] = []
        self.marker = "delegated"

    def open(self, key: str, spec: object) -> str:
        self.opened.append(key)
        return f"session:{key}"


def test_binding_manager_records_open_then_delegates() -> None:
    """``_BindingManager.open`` binds the connection to the opened key and
    forwards the call to the real manager unchanged."""
    reg = ConnectionBindingRegistry()
    fake = _FakeManager()
    wrapped = _BindingManager(fake, reg)

    result = wrapped.open("chg_A", object())
    assert result == "session:chg_A"
    assert fake.opened == ["chg_A"]
    assert reg.resolve(object()) == "chg_A"


def test_binding_manager_passes_through_other_attributes() -> None:
    """Every non-``open`` attribute is forwarded to the wrapped manager verbatim
    — the frozen engine surface is untouched."""
    reg = ConnectionBindingRegistry()
    fake = _FakeManager()
    wrapped = _BindingManager(fake, reg)
    assert wrapped.marker == "delegated"


def test_build_server_bound_uses_the_guard(tmp_path: Path) -> None:
    """With ``bound=True`` (production default) the server is wired with a
    binding resolver — the guard is ON."""
    socket_path = str(tmp_path / "h.sock")
    server, manager = _build_server(socket_path, cwd=str(tmp_path / "cwd"), bound=True)
    try:
        assert server._bound_key_for is not None
        assert server.socket_path == socket_path
    finally:
        manager.shutdown()


def test_build_server_unbound_has_no_guard(tmp_path: Path) -> None:
    """With ``bound=False`` the server has no resolver — only the 0o600
    filesystem permission gates (the parity escape hatch)."""
    socket_path = str(tmp_path / "h.sock")
    server, manager = _build_server(socket_path, cwd=str(tmp_path / "cwd"), bound=False)
    try:
        assert server._bound_key_for is None
    finally:
        manager.shutdown()
