"""Cross-platform terminal launcher for the change-as-primitive flow.

Port of `ae_task_executor/terminal_launcher.py` (504 LOC) stripped to the
load-bearing cross-platform spawn path for sulis's single-founder,
single-machine v1 use case. See:

- `plugins/sulis/docs/change-as-primitive-design.md` § "Session binding"
- ADR-001 (port shape — strip + adapt + drop matrix)
- ADR-002 (module placement — underscore-prefixed lib alongside `_wpxlib.py`)
- ADR-003 (pre-prompt delivery — quoted HERE-DOC into `claude`'s positional arg)

Public entry-point: `launch_change_terminal(...)` opens a new terminal in
a change worktree with `SULIS_CHANGE_ID` exported and a focused
`claude --agent sulis` session inside it.

The generated launch script begins with a `compgen`-based env-scrub
preamble (MUC-2 env-leak prevention). This line is bash-specific; sulis
assumes bash-or-zsh on macOS and Linux (default shells on both).

Stdlib only (NFR-5): subprocess, platform, shlex, shutil, json, logging.
"""

from __future__ import annotations

import json
import logging
import platform
import re
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent))
from _wpxlib import validate_change_ulid  # noqa: E402

logger = logging.getLogger("sulis.terminal_launcher")


# ─── Module-level constants ────────────────────────────────────────────────

# entry_command whitelist: lower-case letters/digits, spaces, dashes.
_ENTRY_COMMAND_RE = re.compile(r"^[a-z][a-z0-9 \-]+$")

# POSIX env-var name convention.
_ENV_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")

# Carry-over env whitelist for the scrub preamble (MUC-2).
_ENV_SCRUB_LINE = (
    "unset $(compgen -v | grep -Ev '^(PATH|HOME|USER|TERM|LANG|LC_.*)$')"
)

# Linux terminal-app priority order (matches ae's dispatch; first found wins).
_LINUX_TERMINAL_APPS = ("gnome-terminal", "konsole", "xterm")

# Pre-prompt delivery (ADR-003).
_PRE_PROMPT_HEREDOC_TAG = "SULIS_PROMPT_EOF"
_PRE_PROMPT_MAX_BYTES = 50_000


# ─── Validators (pure functions, no subprocess) ────────────────────────────


def validate_entry_command(cmd: str) -> tuple[bool, str]:
    """Whitelist: ``^[a-z][a-z0-9 \\-]+$`` (default ``claude --agent sulis``).

    Rejects shell metacharacters (``;``, ``&``, ``$``, backticks, ``|``,
    newlines) that would enable injection at script-generation time.
    """
    if not cmd:
        return False, "entry_command is empty"
    if not _ENTRY_COMMAND_RE.match(cmd):
        return False, (
            f"entry_command {cmd!r} contains characters outside the safe "
            f"whitelist [a-z0-9 -]; injection risk"
        )
    return True, ""


def validate_extra_env_key(key: str) -> tuple[bool, str]:
    """POSIX env-var name convention: ``^[A-Z_][A-Z0-9_]*$``."""
    if not key:
        return False, "env key is empty"
    if not _ENV_KEY_RE.match(key):
        return False, (
            f"env key {key!r} is not a POSIX env-var name "
            f"(uppercase letters, digits, underscores; not leading digit)"
        )
    return True, ""


def validate_worktree_path(path: Path | str) -> tuple[bool, Path]:
    """Resolve ``path``; assert it is an existing directory.

    Returns ``(True, resolved_path)`` or ``(False, resolved_path)`` — the
    resolved path is always returned so callers can include it in errors.
    """
    resolved = Path(path).resolve()
    if not resolved.exists():
        return False, resolved
    if not resolved.is_dir():
        return False, resolved
    return True, resolved


def _validate_pre_prompt(text: str | None) -> tuple[bool, str]:
    """Return ``(True, "")`` if ``text`` is None or safe; else ``(False, reason)``.

    Rejects (per ADR-003 + WP-006):
      - text containing the literal heredoc tag ``SULIS_PROMPT_EOF`` (would
        close the heredoc early — script-injection vector)
      - text exceeding ``_PRE_PROMPT_MAX_BYTES`` (UTF-8) — pathological guard
    """
    if text is None:
        return True, ""
    if _PRE_PROMPT_HEREDOC_TAG in text:
        return False, (
            f"pre_prompt contains the reserved heredoc tag "
            f"{_PRE_PROMPT_HEREDOC_TAG!r}; would close the heredoc early"
        )
    if len(text.encode("utf-8")) > _PRE_PROMPT_MAX_BYTES:
        return False, (
            f"pre_prompt exceeds {_PRE_PROMPT_MAX_BYTES} bytes; "
            f"pass a summary, not the full CONTEXT.md"
        )
    return True, ""


# ─── Shell-script construction ─────────────────────────────────────────────


def _render_heredoc(tag: str, body: str) -> str:
    """Render a quoted HERE-DOC delivering ``body`` as ``claude``'s argv.

    Single-quoting the tag (``<<'TAG'``) disables bash parameter expansion
    and command substitution inside the body (ADR-003). The whole
    substitution is double-quoted so the captured string is one argv
    element including newlines.
    """
    return f'"$(cat <<\'{tag}\'\n{body}\n{tag}\n)"'


def _build_launch_script(
    change_id: str,
    worktree_path: Path,
    entry_command: str = "claude --agent sulis",
    extra_env: dict[str, str] | None = None,
    pre_prompt: str | None = None,
) -> str:
    """Return the bash script body (string).

    Re-validates inputs as defence in depth (MUC-1). ``extra_env`` values
    are ``shlex.quote``-d before insertion. The script begins with the
    env-scrub preamble (MUC-2) before any ``export``.

    When ``pre_prompt`` is set the ``exec`` line delivers it via a quoted
    HERE-DOC (ADR-003); when None the script is byte-identical to the
    no-pre-prompt baseline.
    """
    ok, reason = validate_entry_command(entry_command)
    if not ok:
        raise ValueError(reason)
    ok, reason = validate_change_ulid(change_id)
    if not ok:
        raise ValueError(reason)
    ok, _resolved = validate_worktree_path(worktree_path)
    if not ok:
        raise ValueError(f"worktree_path is not an existing directory: {worktree_path}")
    ok, reason = _validate_pre_prompt(pre_prompt)
    if not ok:
        raise ValueError(reason)

    extra_env_lines: list[str] = []
    for key, value in (extra_env or {}).items():
        ok, reason = validate_extra_env_key(key)
        if not ok:
            raise ValueError(reason)
        extra_env_lines.append(f"export {key}={shlex.quote(value)}")
    extra_env_block = "\n".join(extra_env_lines)

    if pre_prompt is not None:
        exec_line = f"exec {entry_command} {_render_heredoc(_PRE_PROMPT_HEREDOC_TAG, pre_prompt)}"
    else:
        exec_line = f"exec {entry_command}"

    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "# Carry-over env: only PATH, HOME, USER, TERM, LANG, LC_*.",
        _ENV_SCRUB_LINE,
        f'export SULIS_CHANGE_ID="{change_id}"',
    ]
    if extra_env_block:
        lines.append(extra_env_block)
    lines.append(f'cd "{worktree_path}"')
    lines.append(exec_line)
    return "\n".join(lines) + "\n"


# ─── Platform dispatchers (private) ────────────────────────────────────────


def _spawned(pid: int, terminal_app: str, script_path: Path) -> dict:
    return {
        "status": "spawned",
        "pid": pid,
        "terminal_app_used": terminal_app,
        "script_path": str(script_path),
        "error": None,
    }


def _failed(error: str, script_path: Path) -> dict:
    return {
        "status": "failed",
        "pid": None,
        "terminal_app_used": None,
        "script_path": str(script_path),
        "error": error,
    }


def _launch_macos(script_path: Path, change_id: str, visible: bool) -> dict:
    """Spawn via ``osascript -e 'tell Terminal to do script ...'``.

    ``do script`` opens a NEW Terminal.app window and runs the command in
    it. The osascript process exits quickly; Terminal.app continues.
    The returned pid is the osascript process's pid.
    """
    applescript = f'tell application "Terminal" to do script "bash {script_path}"'
    logger.info("spawning macOS terminal for change %s", change_id)
    proc = subprocess.Popen(  # noqa: S603
        ["osascript", "-e", applescript],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return _spawned(proc.pid, "Terminal.app", script_path)


def _launch_linux(script_path: Path, change_id: str, visible: bool) -> dict:
    """Try gnome-terminal → konsole → xterm via ``shutil.which`` (first found).

    NFR-4: when none are on PATH, returns a structured failure dict with an
    actionable error. No silent fallback to headless.
    """
    for app in _LINUX_TERMINAL_APPS:
        if shutil.which(app) is None:
            continue
        if app == "gnome-terminal":
            argv = [app, "--", "bash", str(script_path)]
        elif app == "konsole":
            argv = [app, "-e", "bash", str(script_path)]
        else:  # xterm
            argv = [app, "-e", f"bash {script_path}"]
        logger.info("spawning Linux terminal (%s) for change %s", app, change_id)
        proc = subprocess.Popen(  # noqa: S603
            argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return _spawned(proc.pid, app, script_path)

    logger.warning("no supported Linux terminal app found for change %s", change_id)
    return _failed(
        "no supported terminal app found; install gnome-terminal, konsole, "
        "or xterm — or pass visible=False for headless",
        script_path,
    )


def _launch_headless(script_path: Path, change_id: str) -> dict:
    """Background subprocess invocation. Used when ``visible=False``."""
    logger.info("spawning headless session for change %s", change_id)
    proc = subprocess.Popen(  # noqa: S603
        ["bash", str(script_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    return _spawned(proc.pid, "headless", script_path)


# ─── Session bookkeeping (private) ─────────────────────────────────────────


def _change_dir(change_id: str) -> Path:
    """Return ``~/.sulis/changes/{change_id}/`` (created if absent)."""
    change_dir = Path.home() / ".sulis" / "changes" / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    return change_dir


def _write_session_json(
    change_dir: Path,
    change_id: str,
    pid: int | None,
    terminal_app: str | None,
    script_path: Path,
) -> Path:
    """Persist session.json for later reattach (Phase 6 deferred)."""
    payload = {
        "change_id": change_id,
        "pid": pid,
        "terminal_app_used": terminal_app,
        "script_path": str(script_path),
        "spawned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    session_path = change_dir / "session.json"
    session_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return session_path


def _dispatch_for_platform(visible: bool, platform_name: str):
    """Resolve the dispatcher for the platform + visibility, or None.

    Returns a callable taking ``(script_path, change_id, visible)`` for the
    visible dispatchers, or ``(script_path, change_id)`` for headless.
    None means "unsupported platform with visible=True".
    """
    if not visible:
        return _launch_headless
    if platform_name == "Darwin":
        return _launch_macos
    if platform_name == "Linux":
        return _launch_linux
    return None


# ─── Public entry-point ────────────────────────────────────────────────────


def launch_change_terminal(
    change_id: str,
    worktree_path: Path | str,
    *,
    visible: bool = True,
    entry_command: str = "claude --agent sulis",
    extra_env: dict[str, str] | None = None,
    pre_prompt: str | None = None,
) -> dict:
    """Spawn a new terminal in the change worktree with SULIS_CHANGE_ID set.

    Composes:
        1. Validate all inputs (raises ValueError on bad input)
        2. Build launch.sh via _build_launch_script
        3. Persist launch.sh at ~/.sulis/changes/{change_id}/launch.sh (0o755)
        4. Dispatch to _launch_{macos|linux|headless} by platform + visible
        5. Persist session.json on success (not on failure)
        6. Return the structured dispatcher dict + session_json_path

    Returns:
        {"status", "pid", "terminal_app_used", "script_path",
         "session_json_path", "error"}

    Raises:
        ValueError on invalid change_id, worktree_path, entry_command,
        extra_env, or pre_prompt.
    """
    ok, reason = validate_change_ulid(change_id)
    if not ok:
        raise ValueError(reason)
    ok, resolved = validate_worktree_path(worktree_path)
    if not ok:
        raise ValueError(f"worktree_path is not an existing directory: {worktree_path}")

    script_body = _build_launch_script(
        change_id, resolved, entry_command=entry_command,
        extra_env=extra_env, pre_prompt=pre_prompt,
    )

    # File-I/O hardening: an unwritable change dir / launch.sh (permission
    # denied, read-only FS, disk full) must surface the module's structured
    # _failed(...) dict — never an unhandled OSError traceback to the founder.
    try:
        change_dir = _change_dir(change_id)
        script_path = change_dir / "launch.sh"
        script_path.write_text(script_body)
        script_path.chmod(0o755)
    except OSError as exc:
        target = Path.home() / ".sulis" / "changes" / change_id / "launch.sh"
        result = _failed(
            f"could not write launch script at {target}: {exc.strerror or exc} "
            f"(check the path is writable and the disk is not full)",
            target,
        )
        result["session_json_path"] = ""
        return result

    dispatcher = _dispatch_for_platform(visible, platform.system())
    if dispatcher is None:
        result = _failed(
            f"unsupported platform: {platform.system()}; pass visible=False "
            f"or run on macOS/Linux",
            script_path,
        )
        result["session_json_path"] = ""
        return result

    if dispatcher is _launch_headless:
        result = dispatcher(script_path, change_id)
    else:
        result = dispatcher(script_path, change_id, visible)

    if result["status"] == "spawned":
        # session.json is best-effort reattach bookkeeping (Phase 6 deferred);
        # a write failure must not unwind an already-spawned terminal. Degrade
        # to an empty session_json_path and log, rather than raise.
        try:
            session_path = _write_session_json(
                change_dir, change_id, result["pid"],
                result["terminal_app_used"], script_path,
            )
            result["session_json_path"] = str(session_path)
        except OSError as exc:
            logger.warning(
                "could not write session.json for change %s: %s",
                change_id, exc,
            )
            result["session_json_path"] = ""
    else:
        result["session_json_path"] = ""
    return result
