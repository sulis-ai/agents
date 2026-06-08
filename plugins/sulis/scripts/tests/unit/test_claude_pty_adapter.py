"""Tests for ``_session_manager.adapters.claude_pty`` — the interactive Claude
pty adapter (WP-004, TDD §2.4 / ADR-004).

The shipped :class:`ClaudeAdapter` is the headless ``-p`` stream-json *chat*
io-model. This adapter is its pty sibling: it runs the **real interactive**
``claude --dangerously-skip-permissions --agent sulis`` whose master pty the
manager reads directly (no decode). ``encode`` / ``decode`` / ``turn_complete``
are unused on the pty path (the manager reads raw bytes, not decoded events),
exactly as the ``PtyChildAdapter`` test sibling does.

These are **unit** conformance + argv-shape tests. The real interactive
``claude`` binary cannot run in CI (the WP-009 ``--verbose`` lesson), so the
real-pty round-trip is observed-done in WP-007, not asserted here.

Pre-prompt delivery REUSES the launcher's sidecar file
(``_terminal_launcher._PRE_PROMPT_SIDECAR``, #86): the change's brief lives in
``~/.sulis/changes/{change_id}/pre_prompt.txt`` and the adapter reads its bytes
and passes the brief as a single argv element. (The launcher uses a shell
``"$(cat …)"`` because it writes a bash script; the manager spawns this
adapter's argv directly with no shell, so the brief must be read here and
passed as one literal argv token — still never shell-parsed, the property #86
secures.) The change id reaches the adapter via the ``SULIS_CHANGE_ID`` process
environment the daemon sets (ADR-004) — NOT a new ``SessionSpec`` field, so the
frozen spec is untouched (the contract-note-preferred path).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import _terminal_launcher
from _session_manager.adapter import ProviderAdapter, SessionSpec
from _session_manager.adapters.claude_pty import InteractiveClaudePtyAdapter

# A valid 26-char Crockford-base32 change ULID for the sidecar-resolution tests.
_CHANGE_ID = "01KTKB8KSD6G2EMZZNPD0TNPHH"


@pytest.fixture
def adapter() -> InteractiveClaudePtyAdapter:
    return InteractiveClaudePtyAdapter()


@pytest.fixture
def spec() -> SessionSpec:
    return SessionSpec(provider="pty", cwd="/tmp/worktree", io_mode="pty")


def _seed_sidecar(home: Path, change_id: str, body: str = "brief") -> Path:
    """Write a pre-prompt sidecar under a fake ``$HOME`` at the launcher's
    canonical path, returning the sidecar path."""
    sidecar = (
        home / ".sulis" / "changes" / change_id / _terminal_launcher._PRE_PROMPT_SIDECAR
    )
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(body)
    return sidecar


# ── conformance ───────────────────────────────────────────────────────────


def test_conforms_to_provider_adapter_protocol(adapter):
    """The adapter is a structural :class:`ProviderAdapter` (runtime-checkable)
    — the proof a pty provider slots into the same seam as the chat adapter."""
    assert isinstance(adapter, ProviderAdapter)


def test_capabilities_declared(adapter):
    """Honest capability flags (§2.7): resume + tools, no partial streaming
    (a pty is a raw terminal, not a structured chunk stream)."""
    assert adapter.capabilities.supports_resume is True
    assert adapter.capabilities.supports_tools is True
    assert adapter.capabilities.supports_partial_streaming is False


# ── spawn_argv: the interactive shape ─────────────────────────────────────


def test_spawn_argv_is_interactive(adapter, spec, monkeypatch):
    """The argv is the INTERACTIVE invocation: ``--agent sulis`` and
    ``--dangerously-skip-permissions`` present; none of the headless
    stream-json flags (``-p`` / ``--output-format`` / ``stream-json``)."""
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    argv = adapter.spawn_argv(spec)

    assert argv[0] == "claude"
    assert "--agent" in argv
    assert argv[argv.index("--agent") + 1] == "sulis"
    assert "--dangerously-skip-permissions" in argv

    # No headless / stream-json flags — this is the terminal io-model.
    assert "-p" not in argv
    assert "--print" not in argv
    assert "--output-format" not in argv
    assert "--input-format" not in argv
    assert "stream-json" not in argv


def test_spawn_argv_omits_positional_when_no_change_id(adapter, spec, monkeypatch):
    """With no ``SULIS_CHANGE_ID`` in the environment there is no sidecar to
    resolve — the argv is the bare interactive invocation, no positional."""
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    argv = adapter.spawn_argv(spec)
    assert not any("cat " in token for token in argv)
    assert argv[-1] == "sulis"


def test_spawn_argv_omits_positional_when_sidecar_absent(
    adapter, spec, monkeypatch, tmp_path
):
    """``SULIS_CHANGE_ID`` set but the sidecar file does not exist — no
    positional is appended (a session with no briefed pre-prompt)."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _CHANGE_ID)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    argv = adapter.spawn_argv(spec)
    assert not any("cat " in token for token in argv)
    assert argv[-1] == "sulis"


def test_spawn_argv_appends_preprompt_brief_when_present(
    adapter, spec, monkeypatch, tmp_path
):
    """With ``SULIS_CHANGE_ID`` set and the sidecar present, the argv carries
    the brief's TEXT as a single positional argv element — read from the
    launcher's sidecar (#86). The manager spawns argv directly (no shell), so
    the brief is read here, not deferred to a shell ``$(cat …)``."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _CHANGE_ID)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _seed_sidecar(tmp_path, _CHANGE_ID, body="orient yourself, friend")

    argv = adapter.spawn_argv(spec)

    # The brief is the final argv element — a single token (never split, never
    # shell-parsed: it is one execv arg the kernel hands claude verbatim).
    assert argv[-1] == "orient yourself, friend"
    # NOT a literal shell command-substitution string (the bug a direct-execv
    # spawn would surface if we emitted ``$(cat …)``).
    assert not argv[-1].startswith("$(")
    assert "cat " not in argv[-1]


def test_spawn_argv_rejects_malformed_change_id(adapter, spec, monkeypatch, tmp_path):
    """A ``SULIS_CHANGE_ID`` that is not a valid change ULID is ignored (no
    sidecar resolution, no positional) rather than building a path from
    attacker-influenced input — defence in depth for an env-sourced value."""
    monkeypatch.setenv("SULIS_CHANGE_ID", "../../etc/passwd")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    argv = adapter.spawn_argv(spec)
    assert not any("cat " in token for token in argv)
    assert argv[-1] == "sulis"


# ── unused pty methods ────────────────────────────────────────────────────


def test_encode_raises(adapter):
    """``encode`` is unused on the pty path — the manager writes raw bytes to
    the pty master, it does not frame structured turns."""
    with pytest.raises(NotImplementedError):
        adapter.encode("hello")


def test_decode_returns_none(adapter):
    """``decode`` is unused on the pty path — there is no per-line event
    vocabulary; the manager reads raw terminal bytes."""
    assert adapter.decode(b"any line") is None


def test_turn_complete_returns_false(adapter):
    """``turn_complete`` is unused on the pty path — a terminal has no
    structured turn-done signal; the one-in-flight slot model does not apply."""
    fake_event = object()
    assert adapter.turn_complete(fake_event) is False


# ── reuse: the launcher's sidecar constant, not a duplicate ────────────────


def test_reuses_launcher_sidecar_constant(adapter, spec, monkeypatch, tmp_path):
    """The adapter resolves the sidecar at the SAME filename the launcher
    writes (``_terminal_launcher._PRE_PROMPT_SIDECAR``) — proving it reuses
    the constant rather than duplicating the literal (EP-03). Re-point the
    constant, write the brief at the relocated filename, and the adapter
    reads it from there (it followed the constant, not a hardcoded name)."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _CHANGE_ID)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(_terminal_launcher, "_PRE_PROMPT_SIDECAR", "relocated.txt")

    sidecar = tmp_path / ".sulis" / "changes" / _CHANGE_ID / "relocated.txt"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("relocated brief body")

    # The default sidecar name must NOT exist — so a pass can only mean the
    # adapter read from the relocated (constant-driven) path.
    argv = adapter.spawn_argv(spec)
    assert argv[-1] == "relocated brief body"
