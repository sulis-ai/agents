"""WP-001 (change-owned-terminal-shared-session) — characterisation tests for the
binding classes in their new importable home, ``_session_manager/binding.py``.

TDD §2.1: the daemon (WP-003) needs ``ConnectionBindingRegistry`` and the
``open``-observing binding wrapper, which today live privately inside
``session_manager_host.py``'s module body. WP-001 moves them to a shared module
so both the (retiring) host and the new daemon reuse one binding resolver —
no duplication (EP-03). This is a REORGANISE-Move: behaviour-preserving, so these
characterisation tests pin the *current* behaviour against the imported-from-the-
new-module classes BEFORE the move (EP-07 / Fowler).

The wrapper is renamed ``_BindingManager`` -> ``BindingManager`` as part of the
move (now public-importable); the registry keeps its name. No logic changes.

The pure surface is socket-free and testable without a live socket (Blue); the
host's end-to-end behaviour stays covered by tests/integration/test_session_manager_host.py.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _session_manager.binding import (  # noqa: E402
    BindingManager,
    ConnectionBindingRegistry,
)


# ─── ConnectionBindingRegistry: bind_first idempotency + resolve ──────────────


def test_resolve_is_none_before_any_bind() -> None:
    """``resolve`` returns ``None`` before any bind — a connection that has opened
    nothing is bound to nothing, so the guard declines every guarded key until the
    connection's first ``open``."""
    reg = ConnectionBindingRegistry()
    assert reg.resolve(object(), thread_id=1) is None


def test_first_key_binds_and_resolves() -> None:
    """``resolve`` returns the bound key after the connection's first
    ``bind_first`` — the binding is read back for that same connection."""
    reg = ConnectionBindingRegistry()
    assert reg.bind_first("chg_A", thread_id=1) == "chg_A"
    assert reg.resolve(object(), thread_id=1) == "chg_A"


def test_bind_first_is_idempotent_per_thread_first_key_wins() -> None:
    """``bind_first`` is idempotent per thread: the FIRST key on a connection wins;
    a later ``bind_first`` with a different key does not re-bind
    (§2.13.4 — one change per connection)."""
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


# ─── BindingManager: records the open binding then delegates verbatim ──────────


class _FakeManager:
    """A stand-in for SessionManager: records the keys it was asked to open and
    answers an attribute used to prove transparent delegation."""

    def __init__(self) -> None:
        self.opened: list[str] = []
        self.marker = "delegated"

    def open(self, key: str, spec: object) -> str:
        self.opened.append(key)
        return f"session:{key}"


def test_binding_manager_open_records_binding_then_delegates() -> None:
    """``BindingManager.open`` binds the connection to the opened key and then
    forwards the call to the real manager unchanged."""
    reg = ConnectionBindingRegistry()
    fake = _FakeManager()
    wrapped = BindingManager(fake, reg)

    result = wrapped.open("chg_A", object())
    assert result == "session:chg_A"
    assert fake.opened == ["chg_A"]
    assert reg.resolve(object()) == "chg_A"


def test_binding_manager_passes_through_other_attributes() -> None:
    """Every non-``open`` attribute is forwarded to the wrapped manager verbatim
    via ``__getattr__`` — the frozen engine surface is untouched."""
    reg = ConnectionBindingRegistry()
    fake = _FakeManager()
    wrapped = BindingManager(fake, reg)
    assert wrapped.marker == "delegated"
