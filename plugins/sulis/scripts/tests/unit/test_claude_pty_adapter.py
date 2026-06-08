"""Tests for ``_session_manager.adapters.claude_pty`` — the interactive Claude
pty adapter (WP-004, TDD §2.4 / this change's ADR-001).

The shipped :class:`ClaudeAdapter` is the headless ``-p`` stream-json *chat*
io-model. This adapter is its pty sibling: it runs the **real interactive**
``claude --dangerously-skip-permissions --agent sulis`` whose master pty the
manager reads directly (no decode). ``encode`` / ``decode`` / ``turn_complete``
are unused on the pty path (the manager reads raw bytes, not decoded events),
exactly as the ``PtyChildAdapter`` test sibling does.

These are **unit** conformance + argv-shape tests. The real interactive
``claude`` binary cannot run in CI (the WP-009 ``--verbose`` lesson), so the
real-pty round-trip is observed-done in WP-003, not asserted here.

Pre-prompt delivery REUSES the launcher's sidecar file
(``_terminal_launcher._PRE_PROMPT_SIDECAR``, #86): the change's brief lives in
``~/.sulis/changes/{change_id}/pre_prompt.txt`` and the adapter reads its bytes
and passes the brief as a single argv element. (The launcher uses a shell
``"$(cat …)"`` because it writes a bash script; the manager spawns this
adapter's argv directly with no shell, so the brief must be read here and
passed as one literal argv token — still never shell-parsed, the property #86
secures.)

**The change id reaches the adapter via ``spec.brief_change_id`` (this change's
ADR-001) — NOT the ambient ``SULIS_CHANGE_ID`` process environment.** Under the
shared daemon, the ambient env is constant across every session it spawns, so
briefing from the env briefs every session for the daemon's start-time change
(the bug ADR-001 corrects). The brief target is now a per-session field on the
``SessionSpec`` the adapter already receives; the env is no longer consulted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import _terminal_launcher
from _session_manager.adapter import ProviderAdapter, SessionSpec
from _session_manager.adapters.claude_pty import InteractiveClaudePtyAdapter

# Two distinct valid 26-char Crockford-base32 change ULIDs. ``_CHANGE_ID`` is
# the spec's brief target in the single-change cases; ``_OTHER_CHANGE_ID`` is
# the *ambient* change in the regression test, proving the env is ignored.
_CHANGE_ID = "01KTKB8KSD6G2EMZZNPD0TNPHH"
_OTHER_CHANGE_ID = "01KTGYDA7XJDGAMGBEMGXR9YF0"


@pytest.fixture
def adapter() -> InteractiveClaudePtyAdapter:
    return InteractiveClaudePtyAdapter()


def _spec(brief_change_id: str | None = None) -> SessionSpec:
    """A pty :class:`SessionSpec` with the given brief target (default none)."""
    return SessionSpec(
        provider="pty",
        cwd="/tmp/worktree",
        io_mode="pty",
        brief_change_id=brief_change_id,
    )


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


def test_spawn_argv_is_interactive(adapter):
    """The argv is the INTERACTIVE invocation: ``--agent sulis`` and
    ``--dangerously-skip-permissions`` present; none of the headless
    stream-json flags (``-p`` / ``--output-format`` / ``stream-json``)."""
    argv = adapter.spawn_argv(_spec(brief_change_id=None))

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


def test_spawn_argv_omits_positional_when_no_brief_change_id(adapter):
    """With ``spec.brief_change_id is None`` (the frozen-caller default) there
    is no sidecar to resolve — the argv is the bare interactive invocation, no
    positional."""
    argv = adapter.spawn_argv(_spec(brief_change_id=None))
    assert not any("cat " in token for token in argv)
    assert argv[-1] == "sulis"


def test_spawn_argv_omits_positional_when_sidecar_absent(
    adapter, monkeypatch, tmp_path
):
    """``spec.brief_change_id`` set but the sidecar file does not exist — no
    positional is appended (a session with no briefed pre-prompt)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))
    assert not any("cat " in token for token in argv)
    assert argv[-1] == "sulis"


def test_spawn_argv_appends_preprompt_brief_when_present(
    adapter, monkeypatch, tmp_path
):
    """With ``spec.brief_change_id`` set and the sidecar present, the argv
    carries the brief's TEXT as a single positional argv element — read from the
    launcher's sidecar (#86). The manager spawns argv directly (no shell), so
    the brief is read here, not deferred to a shell ``$(cat …)``."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _seed_sidecar(tmp_path, _CHANGE_ID, body="orient yourself, friend")

    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))

    # The brief is the final argv element — a single token (never split, never
    # shell-parsed: it is one execv arg the kernel hands claude verbatim).
    assert argv[-1] == "orient yourself, friend"
    # NOT a literal shell command-substitution string (the bug a direct-execv
    # spawn would surface if we emitted ``$(cat …)``).
    assert not argv[-1].startswith("$(")
    assert "cat " not in argv[-1]


def test_briefs_from_spec_not_env(adapter, monkeypatch, tmp_path):
    """THE REGRESSION the bug evaded (ADR-001). Under the shared daemon the
    ambient ``SULIS_CHANGE_ID`` is constant across sessions, so briefing from
    the env briefs every session for the daemon's start-time change. Set the
    ambient env to one change (``CH_A``) and ``spec.brief_change_id`` to a
    DIFFERENT change (``CH_B``), each with its own sidecar; assert the spawn
    briefs from CH_B (the spec) — the env is IGNORED.

    The old code briefed from CH_A here (env wins); this asserts the corrected
    behaviour (spec wins, env irrelevant)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # Ambient env points at CH_A with its own (distinct) brief...
    monkeypatch.setenv("SULIS_CHANGE_ID", _OTHER_CHANGE_ID)
    _seed_sidecar(tmp_path, _OTHER_CHANGE_ID, body="WRONG brief: ambient CH_A")
    # ...but the per-session spec points at CH_B with the correct brief.
    _seed_sidecar(tmp_path, _CHANGE_ID, body="CORRECT brief: spec CH_B")

    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))

    # The spec wins: the brief is CH_B's, never the ambient CH_A's.
    assert argv[-1] == "CORRECT brief: spec CH_B"
    assert "WRONG" not in argv[-1]


def test_spawn_argv_rejects_malformed_change_id(adapter, monkeypatch, tmp_path):
    """A ``spec.brief_change_id`` that survives ``__post_init__`` (no leading
    ``-``, no control chars) but is not a valid change ULID is ignored at
    resolution time (no sidecar resolution, no positional) rather than building
    a path from it — ULID validation is retained as defence-in-depth before the
    path join."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # 26 chars but not Crockford-base32 (contains 'I', 'L', 'O', 'U') -> not a
    # valid ULID, yet it has no leading '-' and no control chars so it passes
    # __post_init__ and reaches the resolver.
    argv = adapter.spawn_argv(_spec(brief_change_id="ILOU" + "0" * 22))
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


def test_reuses_launcher_sidecar_constant(adapter, monkeypatch, tmp_path):
    """The adapter resolves the sidecar at the SAME filename the launcher
    writes (``_terminal_launcher._PRE_PROMPT_SIDECAR``) — proving it reuses
    the constant rather than duplicating the literal (EP-03). Re-point the
    constant, write the brief at the relocated filename, and the adapter
    reads it from there (it followed the constant, not a hardcoded name)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(_terminal_launcher, "_PRE_PROMPT_SIDECAR", "relocated.txt")

    sidecar = tmp_path / ".sulis" / "changes" / _CHANGE_ID / "relocated.txt"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("relocated brief body")

    # The default sidecar name must NOT exist — so a pass can only mean the
    # adapter read from the relocated (constant-driven) path.
    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))
    assert argv[-1] == "relocated brief body"


# ── SessionSpec.brief_change_id shape guard (__post_init__) ─────────────────


def test_session_spec_rejects_brief_change_id_leading_dash():
    """``brief_change_id`` flows into a filesystem path; ``__post_init__``
    rejects a leading ``-`` (mirroring the ``resume_ref`` guard) so it can never
    be mistaken for a flag."""
    with pytest.raises(ValueError):
        SessionSpec(provider="pty", cwd="/tmp", brief_change_id="-evil")


def test_session_spec_rejects_brief_change_id_control_char():
    """``__post_init__`` rejects a control character / newline in
    ``brief_change_id`` so it can never split or smuggle across a path or line
    boundary."""
    with pytest.raises(ValueError):
        SessionSpec(provider="pty", cwd="/tmp", brief_change_id="ab\ncd")


def test_session_spec_brief_change_id_defaults_none():
    """``brief_change_id`` is additive + defaulted (the ``io_mode`` precedent):
    a frozen caller that constructs a spec without it gets ``None`` and is
    byte-for-byte unchanged."""
    spec = SessionSpec(provider="pty", cwd="/tmp")
    assert spec.brief_change_id is None
