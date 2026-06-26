"""Provider-on-open resolution (CH-G3Y4RM WP-002, ADR-003).

ADR-003 replaces the hardcoded ``{provider:"pty"}`` at
``apps/cockpit/server/index.ts:275`` with a per-scope resolver: the picker's
choice if set, ELSE the scope's remembered ``participant_context.provider``,
ELSE the safe default ``pty``. Unknown/absent provider falls back to ``pty``
(Claude) — the daemon's ``UNKNOWN_PROVIDER`` is the backstop, but the resolver
NEVER hands a free-form string downstream; it only ever yields one of the two
registered keys.

This file pins the resolution function itself (the new, boring, one-function
fallback order — WP-002 Definition of Done > Blue: "one function with explicit
fallback order, no implicit magic"). The TypeScript side (``resolveChange``)
threads the choice into ``SessionSpec.provider`` and the daemon registry maps
it to an adapter; that wiring is exercised by the cockpit-side test
(``chatRoutes.test.ts``) and the shipped daemon adapter registry. Here we pin
the pure resolution so the fallback order is verified independently of HTTP.

The two registered keys (the closed union — `pty` = Claude, `agy` =
Antigravity) match the daemon adapter registry (session_manager_daemon.py:638).
"""

from __future__ import annotations

from pathlib import Path

from _session_manager.chat_scope_store import (
    REGISTERED_PROVIDERS,
    remember_provider,
    resolve_provider,
)

_SCOPE = "product:dna:product:01HZX9"
_THREAD = "chat"


def test_registered_providers_is_the_closed_union() -> None:
    """The closed provider union is exactly the two registered daemon keys
    (ADR-003 — the picker selects one of these; no free-form)."""
    assert REGISTERED_PROVIDERS == ("pty", "agy")


def test_picked_provider_wins(tmp_path: Path) -> None:
    """An explicit picked provider is used as-is (highest precedence)."""
    assert resolve_provider(_SCOPE, picked="agy", chat_root=tmp_path) == "agy"
    assert resolve_provider(_SCOPE, picked="pty", chat_root=tmp_path) == "pty"


def test_remembered_provider_used_when_none_picked(tmp_path: Path) -> None:
    """With no picked provider, the scope's remembered choice is used (ADR-003
    middle tier)."""
    remember_provider(_SCOPE, "agy", _THREAD, chat_root=tmp_path)
    assert resolve_provider(_SCOPE, picked=None, chat_root=tmp_path) == "agy"


def test_pty_fallback_when_nothing_picked_or_remembered(tmp_path: Path) -> None:
    """No picked AND no remembered choice -> the safe default ``pty`` (ADR-003
    backstop; preserves today's behaviour for a fresh scope)."""
    assert resolve_provider(_SCOPE, picked=None, chat_root=tmp_path) == "pty"


def test_unknown_picked_provider_falls_back_to_pty(tmp_path: Path) -> None:
    """An unknown/absent provider key falls back to ``pty`` — the resolver never
    forwards a free-form string to the daemon (ADR-003; the daemon's
    UNKNOWN_PROVIDER stays the last-resort backstop)."""
    assert resolve_provider(_SCOPE, picked="gemini", chat_root=tmp_path) == "pty"
    assert resolve_provider(_SCOPE, picked="", chat_root=tmp_path) == "pty"


def test_unknown_remembered_provider_falls_back_to_pty(tmp_path: Path) -> None:
    """If a corrupt/legacy remembered value is not a registered key, it is
    ignored and the resolver falls back to ``pty`` (defensive — the daemon
    backstop is never relied on for user-facing failure)."""
    remember_provider(_SCOPE, "gemini", _THREAD, chat_root=tmp_path)
    assert resolve_provider(_SCOPE, picked=None, chat_root=tmp_path) == "pty"
