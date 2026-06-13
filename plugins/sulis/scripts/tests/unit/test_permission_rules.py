"""WP-003 — permission deny-rules (SC-E2): the BELT to the hook's braces.

ADR-003 keeps the permission rules as a redundant belt: deny ``WebFetch`` +
raw network tools (``Bash(curl:*)``/``Bash(wget:*)``), allow the safe MCP
identities (``mcp__sulis-safe-tools__*``). Neither the rules nor the hook is
claimed sufficient alone — the rules are deny-first (a managed deny always
wins) and the hook is the URL/command validator the docs recommend.

These assertions pin the SHIPPED config (``plugins/sulis/settings.json``) so a
later edit that drops a deny rule or stops allowing the safe path fails CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_PLUGIN = Path(__file__).resolve().parents[3]
_SETTINGS = _PLUGIN / "settings.json"


@pytest.fixture(scope="module")
def permissions() -> dict:
    assert _SETTINGS.is_file(), f"plugin settings missing at {_SETTINGS}"
    data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    perms = data.get("permissions")
    assert isinstance(perms, dict), "settings.json must carry a 'permissions' block"
    return perms


def test_webfetch_denied(permissions):
    """SC-E2: a permission deny-rule hard-blocks ``WebFetch``."""
    deny = permissions.get("deny", [])
    assert "WebFetch" in deny, "WebFetch must be denied (the unsafe open-web fetch)"


def test_raw_network_denied(permissions):
    """Raw ``curl``/``wget`` are denied at the permission layer too (belt)."""
    deny = permissions.get("deny", [])
    assert "Bash(curl:*)" in deny
    assert "Bash(wget:*)" in deny


def test_websearch_denied(permissions):
    """``WebSearch`` (the other raw open-web tool) is denied; the safe path is
    ``safe_search``."""
    deny = permissions.get("deny", [])
    assert "WebSearch" in deny


def test_safe_mcp_allowed(permissions):
    """SC-E2: the safe MCP identities are explicitly allowed — the safe path."""
    allow = permissions.get("allow", [])
    assert any(
        rule == "mcp__sulis-safe-tools__*"
        or rule.startswith("mcp__sulis-safe-tools__")
        for rule in allow
    ), "the safe MCP tools must be allowed"


def test_deny_takes_precedence_documented(permissions):
    """The config does NOT 'allow' WebFetch anywhere — deny must not be
    contradicted by an allow on the same identity (deny-first invariant)."""
    allow = permissions.get("allow", [])
    assert "WebFetch" not in allow
    assert "WebSearch" not in allow
