"""The browser-proving toolchain is wired into the plugin's install + MCP config.

Pins that (a) the Playwright MCP is declared as a dependent MCP server, and
(b) the installer has an opt-in `browser` layer that installs the playwright
extra + chromium — graceful/optional, matching the code-health layer's ethos.
Without these, /sulis:prove's agent-driven + deterministic browser paths have no
supported way to be set up.
"""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
_PLUGIN = _ROOT / "plugins" / "sulis"
_MCP = _PLUGIN / ".mcp.json"
_INSTALL = _PLUGIN / "scripts" / "install-sulis.sh"


def test_playwright_declared_as_dependent_mcp_server() -> None:
    d = json.loads(_MCP.read_text(encoding="utf-8"))
    servers = d.get("mcpServers", {})
    assert "playwright" in servers, "the Playwright MCP must be a declared dependent server"
    pw = servers["playwright"]
    assert pw.get("command") == "npx"
    assert any("@playwright/mcp" in a for a in pw.get("args", []))
    # the existing one isn't clobbered
    assert "mobbin" in servers


def test_installer_has_opt_in_browser_layer() -> None:
    t = _INSTALL.read_text(encoding="utf-8")
    assert "--with-browser" in t, "installer needs an opt-in browser layer flag"
    assert "LAYER_BROWSER" in t
    assert "install_browser_layer" in t and "audit_browser_layer" in t


def test_browser_layer_installs_playwright_extra_and_chromium() -> None:
    t = _INSTALL.read_text(encoding="utf-8")
    assert "uv sync --extra browser" in t, "must install the playwright extra"
    assert "playwright install chromium" in t, "must install the chromium binary"


def test_browser_layer_is_optional_not_required() -> None:
    # graceful-degrade: the layer must not fail the install (matches code-health).
    t = _INSTALL.read_text(encoding="utf-8")
    assert "never counts toward" in t.lower() or "degrade" in t.lower()
    # not pulled by --all (heavy + opt-in)
    assert "NOT\n#" in t or "NOT" in t  # the --all help notes browser is excluded
