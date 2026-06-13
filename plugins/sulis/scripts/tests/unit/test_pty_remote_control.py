"""WP-001 (CH-HK5D5M) — Remote Control on by default in the interactive PTY
spawn argv.

Maps to ``.changes/feat-remote-control-spawned-sessions.SPEC.md`` Scope /
Acceptance. The single load-bearing seam is
``_session_manager.adapters.claude_pty.InteractiveClaudePtyAdapter.spawn_argv``:
a spawned interactive change session must come up with Claude Code's Remote
Control already enabled (``claude --remote-control [name]``, interactive-only
per ``claude --help`` v2.1.177), named after the change so it is identifiable in
the founder's Remote Control list, with an env-var opt-out (default-ON).

Verification posture (pure-function argv assertion, Shape 1): the real
interactive ``claude`` cannot run in CI (the WP-009 ``--verbose`` lesson recorded
in ``claude.py``), so these tests assert directly against ``spawn_argv(spec)`` —
no real ``claude`` spawn. Follows the existing pure-argv adapter-test style
(``test_claude_adapter.py::TestSpawnArgv``,
``test_terminal_launcher.py::test_os_window_*``).

Tests (RED first, per the WP Definition of Done):
    test_pty_remote_control.py::test_remote_control_present_by_default          (a)
    test_pty_remote_control.py::test_remote_control_named_after_change          (b)
    test_pty_remote_control.py::test_remote_control_bare_when_no_change_ref     (b2)
    test_pty_remote_control.py::test_remote_control_absent_when_opt_out_falsey  (c)
    test_pty_remote_control.py::test_remote_control_present_when_truthy_or_unset (c)
    test_pty_remote_control.py::test_headless_adapter_never_carries_remote_control (d)
"""

from __future__ import annotations

import pytest

from _session_manager.adapter import SessionSpec
from _session_manager.adapters.claude import ClaudeAdapter
from _session_manager.adapters.claude_pty import InteractiveClaudePtyAdapter

# A real change-ULID-shaped value so ``validate_change_ulid`` passes and the
# adapter derives a deterministic handle name. This is the change this WP ships
# under; its display handle is ``CH-HK5D5M`` (``ulid_handle`` of positions
# 10-15). Using the live value keeps the expected name honest against the real
# handle derivation rather than a hand-mocked string.
_CHANGE_ULID = "01KV0JP9J1HK5D5M27KZZGZAEK"
_EXPECTED_HANDLE = "CH-HK5D5M"

# The opt-out knob this WP introduces (default-ON; falsey value opts a spawn
# out). Named here so the tests pin the env-var contract independently of the
# implementation module's constant.
_OPT_OUT_ENV = "SULIS_SESSION_REMOTE_CONTROL"
_FLAG = "--remote-control"


@pytest.fixture
def pty_adapter() -> InteractiveClaudePtyAdapter:
    return InteractiveClaudePtyAdapter()


@pytest.fixture(autouse=True)
def _clear_opt_out(monkeypatch) -> None:
    """Default the opt-out env var to UNSET for every test, so a test that wants
    a specific value sets it explicitly and the default-on cases see a clean
    environment (the developer/CI process must not leak a stray value in)."""
    monkeypatch.delenv(_OPT_OUT_ENV, raising=False)


# ── (a) default-on ─────────────────────────────────────────────────────────


def test_remote_control_present_by_default(
    pty_adapter: InteractiveClaudePtyAdapter,
) -> None:
    """With the opt-out env var unset, ``--remote-control`` is present in the
    argv for a plain spec (Acceptance: Remote Control on from the first turn)."""
    argv = pty_adapter.spawn_argv(SessionSpec(provider="claude", cwd="/w"))
    assert _FLAG in argv, f"expected {_FLAG!r} in default argv, got {argv!r}"


# ── (b) change-named ───────────────────────────────────────────────────────


def test_remote_control_named_after_change(
    pty_adapter: InteractiveClaudePtyAdapter,
) -> None:
    """With a valid ``brief_change_id``, ``--remote-control`` is present AND the
    next argv element is the change-derived name (the handle the founder sees in
    their Remote Control list), not another flag."""
    spec = SessionSpec(provider="claude", cwd="/w", brief_change_id=_CHANGE_ULID)
    argv = pty_adapter.spawn_argv(spec)
    assert _FLAG in argv, f"expected {_FLAG!r} in argv, got {argv!r}"
    name = argv[argv.index(_FLAG) + 1]
    assert name == _EXPECTED_HANDLE, (
        f"expected change-derived name {_EXPECTED_HANDLE!r} after {_FLAG!r}, "
        f"got {name!r}"
    )
    assert not name.startswith("-"), (
        f"the element after {_FLAG!r} must be a name, not a flag; got {name!r}"
    )


# ── (b2) bare when no change ref ───────────────────────────────────────────


def test_remote_control_bare_when_no_change_ref(
    pty_adapter: InteractiveClaudePtyAdapter,
) -> None:
    """With no ``brief_change_id`` (and no ``resume_ref``), ``--remote-control``
    is present in the bare form — it is either the last argv element or
    immediately followed by a flag/positional that is NOT a name argument the
    flag consumed (the CLI auto-names with its hostname prefix)."""
    argv = pty_adapter.spawn_argv(SessionSpec(provider="claude", cwd="/w"))
    assert _FLAG in argv, f"expected {_FLAG!r} in argv, got {argv!r}"
    idx = argv.index(_FLAG)
    # Bare form: nothing follows, or what follows starts with '-' (another flag),
    # i.e. no name token was consumed by --remote-control.
    if idx + 1 < len(argv):
        following = argv[idx + 1]
        assert following.startswith("-"), (
            f"with no change ref, {_FLAG!r} must be bare (no name argument); "
            f"found a following non-flag token {following!r} in {argv!r}"
        )


def test_remote_control_bare_when_change_id_malformed(
    pty_adapter: InteractiveClaudePtyAdapter,
) -> None:
    """A ``brief_change_id`` that passes the spec's shape guard (no leading
    ``-``, no control chars) but is NOT a valid change ULID must degrade to the
    bare ``--remote-control`` rather than naming the session with a bad handle —
    mirroring ``_conversation_flags`` / ``_read_pre_prompt``'s ignore-on-bad-id
    defence-in-depth (the ULID validation is reused, not re-implemented)."""
    spec = SessionSpec(provider="claude", cwd="/w", brief_change_id="not-a-real-ulid")
    argv = pty_adapter.spawn_argv(spec)
    assert _FLAG in argv, f"expected {_FLAG!r} in argv, got {argv!r}"
    idx = argv.index(_FLAG)
    if idx + 1 < len(argv):
        following = argv[idx + 1]
        assert following.startswith("-"), (
            f"a malformed change id must yield bare {_FLAG!r} (no name); found "
            f"following token {following!r} in {argv!r}"
        )


# ── (c) opt-out / opt-in polarity ──────────────────────────────────────────


@pytest.mark.parametrize("falsey", ["0", "false", "FALSE", "no", "off"])
def test_remote_control_absent_when_opt_out_falsey(
    pty_adapter: InteractiveClaudePtyAdapter, monkeypatch, falsey: str
) -> None:
    """Setting the opt-out env var to a falsey value (case-insensitive) produces
    an argv with NO ``--remote-control`` flag (Acceptance: opt-out cleanly
    removes it). Mirrors ``test_os_window_disabled_by_falsey_flag``."""
    monkeypatch.setenv(_OPT_OUT_ENV, falsey)
    argv = pty_adapter.spawn_argv(SessionSpec(provider="claude", cwd="/w"))
    assert _FLAG not in argv, (
        f"opt-out value {falsey!r} must remove {_FLAG!r}; got {argv!r}"
    )


@pytest.mark.parametrize("truthy", ["1", "true", "yes", "on", ""])
def test_remote_control_present_when_truthy_or_unset(
    pty_adapter: InteractiveClaudePtyAdapter, monkeypatch, truthy: str
) -> None:
    """A truthy or empty value keeps ``--remote-control`` PRESENT (default-ON:
    only an explicit falsey value opts out). ``""`` is the unset-equivalent.
    Mirrors ``test_os_window_enabled_by_truthy_flag`` with inverted polarity."""
    monkeypatch.setenv(_OPT_OUT_ENV, truthy)
    argv = pty_adapter.spawn_argv(SessionSpec(provider="claude", cwd="/w"))
    assert _FLAG in argv, (
        f"value {truthy!r} must keep {_FLAG!r} present (default-ON); got {argv!r}"
    )


# ── (d) headless regression guard ──────────────────────────────────────────


@pytest.mark.parametrize("env_value", [None, "1", "true"])
def test_headless_adapter_never_carries_remote_control(
    monkeypatch, env_value: str | None
) -> None:
    """The headless chat adapter (``claude.py``, ``-p``/stream-json) NEVER
    carries ``--remote-control`` — with the opt-out env var unset AND set truthy.

    Pins the non-goal: Remote Control is an interactive-only feature; the flag
    must not leak to the print-mode adapter. ``claude.py`` is read-only here
    (out of this WP's modify scope)."""
    if env_value is None:
        monkeypatch.delenv(_OPT_OUT_ENV, raising=False)
    else:
        monkeypatch.setenv(_OPT_OUT_ENV, env_value)
    headless = ClaudeAdapter()
    argv = headless.spawn_argv(SessionSpec(provider="claude", cwd="/w"))
    assert _FLAG not in argv, (
        f"headless adapter must never carry {_FLAG!r} (interactive-only); got {argv!r}"
    )
    # And with a resume_ref too — the flag must not appear on any headless path.
    argv_resumed = headless.spawn_argv(
        SessionSpec(provider="claude", cwd="/w", resume_ref="sess-abc")
    )
    assert _FLAG not in argv_resumed, (
        f"headless adapter must never carry {_FLAG!r} even when resuming; "
        f"got {argv_resumed!r}"
    )
