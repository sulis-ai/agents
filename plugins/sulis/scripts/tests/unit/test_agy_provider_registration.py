"""Additive provider registration for the agy adapter (WP-001, CH-M7WSQ4;
ADR-001, TDD §Form, DoD Green + Blue).

The daemon composition root (``session_manager_daemon._build_server``) builds the
``SessionManager``'s ``{provider: adapter}`` dict. This change adds two NEW keys
— ``"agy"`` and its alias ``"antigravity"`` — pointing at a single
``InteractiveAgyPtyAdapter`` instance, leaving the Claude ``"pty"`` key
**byte-for-byte unchanged** (ADR-001, acceptance #4).

- Green: ``"agy"`` and ``"antigravity"`` resolve to ``InteractiveAgyPtyAdapter``.
- Blue (no-regression): ``"pty"`` STILL resolves to ``InteractiveClaudePtyAdapter``
  after the additive edit — the Claude path is unaffected.

The registry is read from ``manager._adapters`` after ``_build_server`` wires it;
the server is stopped immediately (we only inspect the composed dict, we never
drive a session).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import session_manager_daemon  # noqa: E402
from _session_manager.adapters.agy_pty import InteractiveAgyPtyAdapter  # noqa: E402
from _session_manager.adapters.claude_pty import (  # noqa: E402
    InteractiveClaudePtyAdapter,
)


def _adapters(tmp_path: Path) -> dict:
    """Build the daemon server, return a copy of the composed adapter registry,
    and stop the server (we only inspect the dict, never drive a session)."""
    socket_path = str(tmp_path / "daemon.sock")
    server, manager = session_manager_daemon._build_server(socket_path)
    try:
        return dict(manager._adapters)
    finally:
        server.stop()


def test_agy_keys_resolve_to_agy_adapter(tmp_path: Path) -> None:
    """Green: both ``"agy"`` and the ``"antigravity"`` alias resolve to an
    ``InteractiveAgyPtyAdapter`` — and to the SAME instance (one adapter, two
    keys, per ADR-001)."""
    adapters = _adapters(tmp_path)
    assert isinstance(adapters["agy"], InteractiveAgyPtyAdapter)
    assert isinstance(adapters["antigravity"], InteractiveAgyPtyAdapter)
    assert adapters["agy"] is adapters["antigravity"]


def test_claude_path_registration_intact(tmp_path: Path) -> None:
    """Blue no-regression (ADR-001, acceptance #4): after the additive edit the
    ``"pty"`` key STILL resolves to ``InteractiveClaudePtyAdapter`` — the Claude
    path is byte-for-byte unaffected."""
    adapters = _adapters(tmp_path)
    assert isinstance(adapters["pty"], InteractiveClaudePtyAdapter)
