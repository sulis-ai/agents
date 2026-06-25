"""Tests for ``_session_manager.adapters.agy_pty`` — the interactive Google
Antigravity (``agy``) pty adapter (WP-001, CH-M7WSQ4; TDD §Form/§Armor/§Proof,
PC-001, ADR-001/002/003).

This adapter mirrors the **shape** of :class:`InteractiveClaudePtyAdapter` (the
``ProviderAdapter`` Protocol; ``_BASE_ARGV``; brief-as-trailing-positional read
from the CH-GJ9KQR sidecar; unused ``encode``/``decode``/``turn_complete``;
``classify_failure -> None``) but **does not** reproduce the two Claude-only
behaviours PC-001 confirmed ``agy`` lacks (ADR-002):

- **No Remote Control fragment** — ``agy`` has no ``--remote-control`` flag.
- **No deterministic pre-spawn ``--session-id`` pin** — ``agy`` assigns its own
  conversation ids; resume is by ``--conversation <id>`` / ``--continue``.

The one genuine hardening decision (ADR-003, the Armor gate) is the permission
posture: default ``--sandbox``, **never** blanket ``--dangerously-skip-permissions``;
a default-OFF / opt-in ``SULIS_AGY_SKIP_PERMISSIONS`` knob loosens it deliberately.

These are **unit** conformance + argv-shape tests. The real interactive ``agy``
binary cannot run a prompt-bearing session in CI (real Google auth required); the
prompt round-trip is observed-done at verify time (deferred
``agy-real-session-driver-google``), not asserted here. The read-only binary
introspection lives in ``tests/integration/test_agy_binary_introspection.py``.

Pre-prompt delivery REUSES the launcher's sidecar file
(``_terminal_launcher._PRE_PROMPT_SIDECAR``, #86): the change's brief lives in
``~/.sulis/changes/{change_id}/pre_prompt.txt`` and the adapter reads its bytes,
passing the brief as a single argv element (the manager spawns argv directly with
no shell, so the brief is read here and passed as one literal ``execv`` token —
still never shell-parsed, the property #86 secures). The change id reaches the
adapter via ``spec.brief_change_id`` (CH-GJ9KQR ADR-001), NOT the ambient
``SULIS_CHANGE_ID`` env.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import _terminal_launcher
from _session_manager.adapter import ProviderAdapter, SessionSpec
from _session_manager.adapters.agy_pty import InteractiveAgyPtyAdapter

# Two distinct valid 26-char Crockford-base32 change ULIDs. ``_CHANGE_ID`` is
# the spec's brief target in the single-change cases; ``_OTHER_CHANGE_ID`` is
# the *ambient* change in the regression test, proving the env is ignored.
_CHANGE_ID = "01KTKB8KSD6G2EMZZNPD0TNPHH"
_OTHER_CHANGE_ID = "01KTGYDA7XJDGAMGBEMGXR9YF0"


@pytest.fixture
def adapter() -> InteractiveAgyPtyAdapter:
    return InteractiveAgyPtyAdapter()


def _spec(
    brief_change_id: str | None = None,
    resume_ref: str | None = None,
    cwd: str = "/tmp/worktree",
) -> SessionSpec:
    """An agy pty :class:`SessionSpec` with the given brief target (default none)."""
    return SessionSpec(
        provider="agy",
        cwd=cwd,
        io_mode="pty",
        brief_change_id=brief_change_id,
        resume_ref=resume_ref,
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
    — the proof agy slots into the same seam as the Claude pty adapter."""
    assert isinstance(adapter, ProviderAdapter)


def test_capabilities_declared(adapter):
    """Honest capability flags (§2.7): resume + tools True, partial streaming
    False (a pty is a raw terminal, not a structured chunk stream)."""
    assert adapter.capabilities.supports_resume is True
    assert adapter.capabilities.supports_tools is True
    assert adapter.capabilities.supports_partial_streaming is False


# ── spawn_argv: the interactive shape ─────────────────────────────────────


def test_spawn_argv_is_interactive(adapter):
    """The argv is the INTERACTIVE invocation: ``argv[0] == "agy"``,
    ``--prompt-interactive`` present, ``--add-dir <cwd>`` present with cwd as its
    value; none of the headless ``-p`` / ``--print`` / ``--prompt`` flags
    (PC-001 §4)."""
    argv = adapter.spawn_argv(_spec(brief_change_id=None, cwd="/tmp/worktree"))

    assert argv[0] == "agy"
    assert "--prompt-interactive" in argv
    assert "--add-dir" in argv
    assert argv[argv.index("--add-dir") + 1] == "/tmp/worktree"

    # No headless flags — this is the terminal io-model.
    assert "-p" not in argv
    assert "--print" not in argv
    assert "--prompt" not in argv


def test_default_posture_is_sandbox(adapter, monkeypatch):
    """ADR-003 Armor gate: the default argv carries ``--sandbox`` and does NOT
    carry ``--dangerously-skip-permissions``."""
    monkeypatch.delenv("SULIS_AGY_SKIP_PERMISSIONS", raising=False)
    argv = adapter.spawn_argv(_spec(brief_change_id=None))
    assert "--sandbox" in argv
    assert "--dangerously-skip-permissions" not in argv


def test_skip_permissions_optin_knob(adapter, monkeypatch):
    """ADR-003: ``SULIS_AGY_SKIP_PERMISSIONS=1`` (truthy) flips to the loosened
    posture — ``--dangerously-skip-permissions`` present, ``--sandbox`` absent.
    The knob is default-OFF / opt-in (inverse polarity to the Claude adapter's
    default-ON Remote Control knob)."""
    monkeypatch.setenv("SULIS_AGY_SKIP_PERMISSIONS", "1")
    argv = adapter.spawn_argv(_spec(brief_change_id=None))
    assert "--dangerously-skip-permissions" in argv
    assert "--sandbox" not in argv


def test_appends_brief_when_present(adapter, monkeypatch, tmp_path):
    """With ``spec.brief_change_id`` set and the sidecar present, the brief's
    TEXT is the trailing positional argv element — a single token, read from the
    launcher's sidecar (#86), NEVER a literal ``$(cat …)`` (the manager spawns
    argv directly, no shell)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _seed_sidecar(tmp_path, _CHANGE_ID, body="orient yourself, friend")

    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))

    assert argv[-1] == "orient yourself, friend"
    assert not argv[-1].startswith("$(")
    assert "cat " not in argv[-1]


def test_briefs_from_spec_not_env(adapter, monkeypatch, tmp_path):
    """THE CH-GJ9KQR regression (ADR-001): under the shared daemon the ambient
    ``SULIS_CHANGE_ID`` is constant across sessions. Set ambient env to one
    change (CH_A) and ``spec.brief_change_id`` to a DIFFERENT change (CH_B), each
    with its own sidecar; the spawn briefs from CH_B (the spec) — env IGNORED."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SULIS_CHANGE_ID", _OTHER_CHANGE_ID)
    _seed_sidecar(tmp_path, _OTHER_CHANGE_ID, body="WRONG brief: ambient CH_A")
    _seed_sidecar(tmp_path, _CHANGE_ID, body="CORRECT brief: spec CH_B")

    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))

    assert argv[-1] == "CORRECT brief: spec CH_B"
    assert "WRONG" not in argv[-1]


def test_omits_positional_when_brief_absent(adapter, monkeypatch, tmp_path):
    """``spec.brief_change_id`` set but the sidecar file does not exist — no
    pre-prompt positional is appended (degrade, don't crash). The trailing token
    is NOT a brief body."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))
    assert not any("cat " in token for token in argv)
    # No brief positional: the last token is the --add-dir value (no resume, no
    # model, no brief), never a brief body.
    assert argv[-1] != ""


def test_omits_positional_when_brief_malformed(adapter, monkeypatch, tmp_path):
    """A ``brief_change_id`` that survives ``__post_init__`` (no leading ``-``,
    no control chars) but is NOT a valid change ULID is ignored at resolution
    time — no sidecar resolution, no positional, no crash (ULID validation is
    defence-in-depth before the path join)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # 26 chars but contains 'I','L','O','U' — not Crockford-base32, yet no leading
    # '-' and no control chars, so it passes __post_init__ and reaches the resolver.
    argv = adapter.spawn_argv(_spec(brief_change_id="ILOU" + "0" * 22))
    assert not any("cat " in token for token in argv)


# ── resume mapping (ADR-002 / PC-001 §7) ───────────────────────────────────


def test_resume_maps_to_conversation(adapter):
    """``spec.resume_ref`` set → ``["--conversation", <ref>]`` present; unset →
    no ``--conversation`` (agy resume is conversation-id-based; no pre-spawn pin,
    ADR-002). ``--continue`` is the documented most-recent fallback, not emitted
    here."""
    ref = "agy-conv-1234567890"
    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID, resume_ref=ref))
    assert "--conversation" in argv
    assert argv[argv.index("--conversation") + 1] == ref
    # No Claude-only session-id pin (ADR-002).
    assert "--session-id" not in argv

    argv_no_resume = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))
    assert "--conversation" not in argv_no_resume


def test_does_not_mirror_claude_only_flags(adapter):
    """ADR-002: agy has neither ``--remote-control`` nor ``--session-id``; the
    adapter must NOT emit either (faking a flag the platform rejects is dead
    surface)."""
    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))
    assert "--remote-control" not in argv
    assert "--session-id" not in argv


# ── optional model (PC-001 §6) ─────────────────────────────────────────────


def test_optional_model(adapter, monkeypatch):
    """``SULIS_AGY_MODEL`` set → ``["--model", <value>]`` present; unset →
    ``--model`` absent (agy uses its own default model)."""
    monkeypatch.setenv("SULIS_AGY_MODEL", "gemini-3-pro")
    argv = adapter.spawn_argv(_spec(brief_change_id=None))
    assert "--model" in argv
    assert argv[argv.index("--model") + 1] == "gemini-3-pro"

    monkeypatch.delenv("SULIS_AGY_MODEL", raising=False)
    argv_no_model = adapter.spawn_argv(_spec(brief_change_id=None))
    assert "--model" not in argv_no_model


# ── unused pty methods ────────────────────────────────────────────────────


def test_encode_raises(adapter):
    """``encode`` is unused on the pty path — the manager writes raw bytes to the
    pty master, it does not frame structured turns."""
    with pytest.raises(NotImplementedError):
        adapter.encode("hello")


def test_decode_returns_none(adapter):
    """``decode`` is unused on the pty path — there is no per-line event
    vocabulary; the manager reads raw terminal bytes."""
    assert adapter.decode(b"any line") is None


def test_turn_complete_returns_false(adapter):
    """``turn_complete`` is unused on the pty path — a terminal has no structured
    turn-done signal; the one-in-flight slot model does not apply."""
    fake_event = object()
    assert adapter.turn_complete(fake_event) is False


def test_classify_failure_returns_none(adapter):
    """``classify_failure`` defers to the neutral classifier in Phase 1 (PC-001
    §8) — provider-specific raw-failure detection is the Phase-2 failover seam."""
    fake_error = object()
    assert adapter.classify_failure(fake_error) is None


def test_reauth_raises(adapter):
    """``reauth`` is a Phase-2 seam stub (PC-001 §8) — it raises to stay honest.
    The driver only calls it after ``classify_failure`` yields ``LOGIN_EXPIRED``,
    which this Phase-1 adapter never does."""
    with pytest.raises(NotImplementedError):
        adapter.reauth()


# ── reuse: the launcher's sidecar constant, not a duplicate (EP-03) ────────


def test_reuses_launcher_sidecar_constant(adapter, monkeypatch, tmp_path):
    """The adapter resolves the sidecar at the SAME filename the launcher writes
    (``_terminal_launcher._PRE_PROMPT_SIDECAR``) — proving it reuses the constant
    rather than duplicating the literal (EP-03). Re-point the constant, write the
    brief at the relocated filename, and the adapter reads it from there."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(_terminal_launcher, "_PRE_PROMPT_SIDECAR", "relocated.txt")

    sidecar = tmp_path / ".sulis" / "changes" / _CHANGE_ID / "relocated.txt"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("relocated brief body")

    # The default sidecar name must NOT exist — so a pass can only mean the
    # adapter read from the relocated (constant-driven) path.
    argv = adapter.spawn_argv(_spec(brief_change_id=_CHANGE_ID))
    assert argv[-1] == "relocated brief body"


# ── token order (PC-001 §4) ─────────────────────────────────────────────────


def test_token_order_brief_is_trailing_positional(adapter, monkeypatch, tmp_path):
    """PC-001 §4: the brief is the TRAILING positional — after --add-dir, the
    posture flag, optional model, and any resume flags. With model + resume +
    brief all present, the brief is still last."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SULIS_AGY_MODEL", "gemini-3-pro")
    _seed_sidecar(tmp_path, _CHANGE_ID, body="the brief")

    argv = adapter.spawn_argv(
        _spec(brief_change_id=_CHANGE_ID, resume_ref="agy-conv-9")
    )

    assert argv[0] == "agy"
    assert argv[-1] == "the brief"
    # The brief comes after the conversation flag (resume) and model.
    assert argv.index("--conversation") < len(argv) - 1
    assert argv.index("--model") < len(argv) - 1
