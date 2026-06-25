"""Unit — the ``thread_context`` MCP tool is wired LIVE + denyable in practice
(CH-GJ9KQR WP-007, WP-005 ADV-1, ADR-005).

WP-005's review flagged: the tool is built + denyable in principle but NOT
wired live. This integration WP closes that — the founder's allow/deny surface
must actually cover it. This test pins the three wiring facts (mirroring the
established ``sulis-safe-tools`` posture):

  1. ``plugins/sulis/.mcp.json`` registers a ``sulis-thread-context`` server,
     invoked the same Python-stdio way as ``sulis-safe-tools`` (``uv run … the
     launcher``) — NOT npx, on the plugin's own env (ADR-002 launcher posture).

  2. ``plugins/sulis/settings.json`` carries the matching permission identity
     ``mcp__sulis-thread-context__*`` in its allow list, so the tool is a
     denyable identity in practice (the founder can withhold it) — the
     availability/deny split WP-005 left half-done.

  3. The launcher script ``plugins/sulis/scripts/sulis-thread-context-mcp``
     exists, is executable, and resolves ``build_server`` from the WP-005 server
     module — it is the ``command`` entry ``.mcp.json`` invokes, carrying no
     logic of its own (mirrors ``sulis-safe-tools-mcp``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from _thread_context_mcp import SERVER_NAME

_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
_MCP_JSON = _PLUGIN_ROOT / ".mcp.json"
_SETTINGS_JSON = _PLUGIN_ROOT / "settings.json"
_LAUNCHER = _PLUGIN_ROOT / "scripts" / "sulis-thread-context-mcp"

_PERMISSION_IDENTITY = f"mcp__{SERVER_NAME}__*"


def test_mcp_json_registers_thread_context_server() -> None:
    """``.mcp.json`` carries a ``sulis-thread-context`` server, invoked the same
    Python-stdio way as ``sulis-safe-tools`` (uv run, the plugin's own env)."""
    config = json.loads(_MCP_JSON.read_text(encoding="utf-8"))
    servers = config["mcpServers"]
    assert SERVER_NAME in servers, f"{SERVER_NAME} not registered in .mcp.json"

    entry = servers[SERVER_NAME]
    # Mirror the safe-tools posture: uv run python launcher (NOT npx).
    assert entry["command"] == "uv"
    args = entry["args"]
    assert "run" in args
    # The launcher is the script the entry invokes (resolved under the plugin).
    assert any("sulis-thread-context-mcp" in a for a in args), args


def test_settings_allows_thread_context_permission_identity() -> None:
    """``settings.json`` carries ``mcp__sulis-thread-context__*`` in its allow
    list — the denyable identity is covered in practice (WP-005 ADV-1)."""
    settings = json.loads(_SETTINGS_JSON.read_text(encoding="utf-8"))
    allow = settings["permissions"]["allow"]
    assert _PERMISSION_IDENTITY in allow, (
        f"{_PERMISSION_IDENTITY} missing from settings allow list {allow}"
    )


def test_launcher_exists_executable_and_resolves_server_entry() -> None:
    """The launcher exists, is executable, and imports the WP-005 server's
    ``main`` entry from the ``_thread_context_mcp`` module (it is the
    ``command`` .mcp.json invokes, carrying no logic of its own)."""
    assert _LAUNCHER.exists(), f"launcher missing: {_LAUNCHER}"
    assert os.access(_LAUNCHER, os.X_OK), "launcher is not executable"
    body = _LAUNCHER.read_text(encoding="utf-8")
    # Thin launcher: imports the server's ``main`` entry from the WP-005 module
    # (the same entry _thread_context_mcp.main / build_server expose).
    assert "_thread_context_mcp" in body
    assert "main" in body
