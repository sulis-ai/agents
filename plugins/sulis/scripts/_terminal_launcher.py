"""Cross-platform terminal launcher for the change-as-primitive flow.

This is the sanctioned launcher for the change-start flow. When the founder
starts a change (``sulis-change start --spawn`` → the ``/sulis:change`` skill),
a VISIBLE launch opens a real terminal window — Terminal.app on macOS,
gnome-terminal / konsole / xterm on Linux — bound to the change via
``SULIS_CHANGE_ID``, with the pre-prompt sidecar so the session self-orients
rather than sitting idle. This is the DEFAULT: no env flag is required to open
the terminal.

By DEFAULT the window now runs the **desktop viewer** (``session_viewer.py``,
WP-005) attached to the change's **shared session** over the daemon's stable
socket — so the window is a VIEW onto the change's *one* session (the same
session the cockpit attaches to), not a standalone ``claude``. This supersedes
the prior CH-01KTK7 standalone-``claude`` path (change CH-01KTKB ADR-003): the
launcher keeps all of its proven cross-platform spawn, env-scrub, origin-hook,
and pre-prompt machinery — only WHAT the window execs changed. The viewer
itself cold-starts the daemon on demand (ensure-daemon → get-or-spawn); the
daemon's interactive pty adapter spawns the session's ``claude`` and reads the
pre-prompt sidecar via ``SULIS_CHANGE_ID``, so the session is still briefed on
its first turn. An explicit chat-style ``entry_command`` is still honoured for
callers that pass one (it remains subject to the injection whitelist); the
viewer is the default.

``SULIS_TERMINAL_OS_WINDOW`` is retained only as an explicit override knob (see
``_os_window_enabled``); it does NOT gate the default-on spawn. The in-cockpit
``<LiveTerminal/>`` is a SEPARATE capability — a pty-mode session rendered in
the browser, reached through the cockpit. It is a different job (watch/use a
session inside the cockpit), not a replacement for popping a focused terminal
at change start; this launcher is not deprecated in favour of it.

Port of `ae_task_executor/terminal_launcher.py` (504 LOC) stripped to the
load-bearing cross-platform spawn path for sulis's single-founder,
single-machine v1 use case. See:

- `plugins/sulis/docs/change-as-primitive-design.md` § "Session binding"
- ADR-001 (port shape — strip + adapt + drop matrix)
- ADR-002 (module placement — underscore-prefixed lib alongside `_wpxlib.py`)
- ADR-003 (pre-prompt delivery — quoted HERE-DOC into `claude`'s positional arg)

Public entry-point: `launch_change_terminal(...)` opens a new terminal in
a change worktree with `SULIS_CHANGE_ID` exported and the desktop viewer
attached to the change's shared session inside it (or, if an explicit
chat-style `entry_command` is passed, that command instead).

The generated launch script begins with a `compgen`-based env-scrub
preamble (MUC-2 env-leak prevention). This line is bash-specific; sulis
assumes bash-or-zsh on macOS and Linux (default shells on both).

Stdlib only (NFR-5): subprocess, platform, shlex, shutil, json, logging.
"""

from __future__ import annotations

import json
import logging
import os
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

# Optional override knob for the OS-window launch. A visible launch opens the
# terminal by DEFAULT (CH-01KTK7) — this flag is NOT required for that. It is
# retained only as an explicit override an operator can set when they want to
# force/annotate the OS-window path; it does not gate the default-on behaviour.
_OS_WINDOW_FLAG = "SULIS_TERMINAL_OS_WINDOW"
_OS_WINDOW_TRUTHY = frozenset({"1", "true", "yes", "on"})

# entry_command whitelist: lower-case letters/digits, spaces, dashes.
_ENTRY_COMMAND_RE = re.compile(r"^[a-z][a-z0-9 \-]+$")

# POSIX env-var name convention.
_ENV_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")

# Carry-over env whitelist for the scrub preamble (MUC-2).
#
# Two hardening properties make this line safe under `set -euo pipefail`
# (the dogfood failure: a real spawn aborted at this line and `claude` never
# started — `compgen -v` lists bash *readonly* vars (EUID/UID/PPID/SHELLOPTS/
# BASH_VERSINFO/...) which `unset` refuses with a non-zero exit):
#   1. The grep `-Ev` pattern excludes the known bash readonly + shell-internal
#      vars from the unset set, so we don't even attempt them.
#   2. `unset -v ... 2>/dev/null || true` makes the line non-fatal regardless:
#      stderr is silenced (no per-var error spam in the spawned window) and the
#      trailing `|| true` guarantees the line cannot abort the script under -e.
# Intent preserved: scrub every non-carry-over env var so the spawned session
# can't inherit the parent's secrets; PATH/HOME/USER/TERM/LANG/LC_* carried over.
_ENV_SCRUB_LINE = (
    "unset -v $(compgen -v | grep -Ev "
    "'^(PATH|HOME|USER|TERM|LANG|LC_.*|EUID|UID|GID|PPID|SHELLOPTS|BASHOPTS|"
    "BASH_VERSINFO|BASH_.*|IFS|PWD|OLDPWD|SHLVL|_)$') 2>/dev/null || true"
)

# Linux terminal-app priority order (matches ae's dispatch; first found wins).
_LINUX_TERMINAL_APPS = ("gnome-terminal", "konsole", "xterm")

# Pre-prompt delivery (ADR-003; sidecar-file delivery since #86).
_PRE_PROMPT_HEREDOC_TAG = "SULIS_PROMPT_EOF"
_PRE_PROMPT_SIDECAR = "pre_prompt.txt"  # co-located with launch.sh in the change dir
_PRE_PROMPT_MAX_BYTES = 50_000

# Desktop viewer (WP-005). By default the launched window runs this — attached
# to the change's shared session over the daemon's stable socket — instead of a
# standalone `claude` (change CH-01KTKB ADR-003). Co-located with this module.
_VIEWER_SCRIPT = "session_viewer.py"


# ─── OS-window override knob ────────────────────────────────────────────────


def _os_window_enabled() -> bool:
    """Return True when the OS-window override flag is set.

    Override knob only — a visible launch opens the terminal by DEFAULT
    (CH-01KTK7), so this is NOT required for the change-start spawn. It is
    retained so an operator can explicitly signal the OS-window path. Truthy
    values: ``1``, ``true``, ``yes``, ``on`` (case-insensitive).
    """
    return os.environ.get(_OS_WINDOW_FLAG, "").strip().lower() in _OS_WINDOW_TRUTHY


# ─── Validators (pure functions, no subprocess) ────────────────────────────


def validate_entry_command(cmd: str) -> tuple[bool, str]:
    """Whitelist: ``^[a-z][a-z0-9 \\-]+$`` (default
    ``claude --dangerously-skip-permissions --agent sulis`` — the spawned
    focused session runs unattended, so it skips interactive permission
    prompts, matching how the founder runs Claude Code).

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

    Since #86 the pre_prompt is delivered via a sidecar file read at runtime
    (``"$(cat <file>)"``), never embedded in the launch script — so its bytes
    are never shell-parsed. There is no heredoc tag to close early and no
    injection surface; the only remaining guard is size:
      - text exceeding ``_PRE_PROMPT_MAX_BYTES`` (UTF-8) — pathological guard
    """
    if text is None:
        return True, ""
    if len(text.encode("utf-8")) > _PRE_PROMPT_MAX_BYTES:
        return False, (
            f"pre_prompt exceeds {_PRE_PROMPT_MAX_BYTES} bytes; "
            f"pass a summary, not the full CONTEXT.md"
        )
    return True, ""


# ─── Shell-script construction ─────────────────────────────────────────────


def _build_viewer_exec_line(
    change_id: str,
    worktree_path: Path,
    scripts_dir: Path,
) -> str:
    """Return the ``exec`` line that runs the desktop viewer (WP-005).

    The window runs ``python3 <scripts>/session_viewer.py --change-id <id>
    --worktree <wt>`` — a VIEW onto the change's shared session, not a
    standalone ``claude`` (change CH-01KTKB ADR-003). The viewer cold-starts the
    daemon on demand (ensure-daemon → get-or-spawn).

    This is built OUTSIDE the chat-style ``_ENTRY_COMMAND_RE`` whitelist (which
    forbids ``/``, ``.``, digits, and ``--flags`` for injection safety on
    operator-typed commands). Like the existing pre-prompt ``cat`` line, every
    argument is ``shlex.quote``-d here, so the path/id bytes are inert to the
    shell — the injection guard is preserved by construction, not by the
    whitelist regex. ``_build_launch_script`` is pure (no file I/O / no mkdir);
    the caller resolves ``scripts_dir`` and ``worktree_path``.
    """
    viewer = scripts_dir / _VIEWER_SCRIPT
    return (
        "exec python3 "
        f"{shlex.quote(str(viewer))} "
        f"--change-id {shlex.quote(change_id)} "
        f"--worktree {shlex.quote(str(worktree_path))}"
    )


def _build_launch_script(
    change_id: str,
    worktree_path: Path,
    entry_command: str | None = None,
    extra_env: dict[str, str] | None = None,
    pre_prompt: str | None = None,
    enable_origin_hook: bool = False,
) -> str:
    """Return the bash script body (string).

    Re-validates inputs as defence in depth (MUC-1). ``extra_env`` values
    are ``shlex.quote``-d before insertion. The script begins with the
    env-scrub preamble (MUC-2) before any ``export``.

    ``entry_command`` selects WHAT the window execs:

    - ``None`` (the DEFAULT) → the desktop viewer attached to the change's
      shared session, built via :func:`_build_viewer_exec_line` (change
      CH-01KTKB ADR-003). The viewer line is path-/flag-shaped and is therefore
      built outside the chat-style whitelist, with each arg ``shlex.quote``-d.
    - a chat-style command string → that command instead (the legacy path),
      still subject to the ``_ENTRY_COMMAND_RE`` injection whitelist.

    When ``pre_prompt`` is set the ``exec`` line is suffixed with a quoted
    ``cat`` of the sidecar file the brief is written to (#86); when None the
    script omits it. The daemon's interactive pty adapter reads the same sidecar
    via ``SULIS_CHANGE_ID``, so the session is briefed regardless of which exec
    path is taken.
    """
    if entry_command is not None:
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

    if entry_command is None:
        # DEFAULT: run the desktop viewer attached to the change's shared
        # session (change CH-01KTKB ADR-003). The brief is NOT passed to the
        # viewer as a CLI arg — the viewer's only args are --change-id /
        # --worktree. The pre_prompt sidecar is still written (below /
        # launch_change_terminal) and SULIS_CHANGE_ID is still exported, so the
        # daemon's interactive pty adapter reads the sidecar and briefs the
        # session's claude on its first turn. The viewer line is path-/flag-
        # shaped, so it is built outside the chat-style whitelist with each arg
        # shlex.quote-d (like the sidecar `cat`). scripts_dir is resolved from
        # this module's location — session_viewer.py is co-located here.
        scripts_dir = Path(__file__).resolve().parent
        exec_line = _build_viewer_exec_line(change_id, worktree_path, scripts_dir)
    elif pre_prompt is not None:
        # Chat-style path with a brief: deliver the pre_prompt via a SIDECAR
        # FILE read at runtime — NOT a heredoc (#86). macOS ships bash 3.2,
        # which mis-parses a quoted heredoc nested inside "$(...)": any
        # apostrophe in the brief is read as an unterminated quote, the script
        # aborts, and claude never starts (silently — the launcher still
        # reports spawned). A `cat` of a file has no heredoc nesting (parses
        # clean under bash 3.2), and the pre_prompt bytes are never shell-parsed
        # — so there is no injection surface either (what the old heredoc's
        # single-quoted tag guarded). Path only — do NOT mkdir here.
        # _build_launch_script is pure (no file I/O); launch_change_terminal
        # creates the dir + writes the sidecar inside its I/O-failure try-block.
        # (Using _change_dir here would mkdir before that try, so an unwritable
        # ~/.sulis would escape as a raw OSError instead of the structured
        # _failed dict.)
        sidecar = Path.home() / ".sulis" / "changes" / change_id / _PRE_PROMPT_SIDECAR
        exec_line = f'exec {entry_command} "$(cat {shlex.quote(str(sidecar))})"'
    else:
        exec_line = f"exec {entry_command}"

    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "# Carry-over env: only PATH, HOME, USER, TERM, LANG, LC_*.",
        _ENV_SCRUB_LINE,
        f'export SULIS_CHANGE_ID="{change_id}"',
    ]
    if enable_origin_hook:
        # WP-P12 (ADR-013) — wire the origin-stamp `prepare-commit-msg` hook for
        # the executor session, so any commit it makes carries the Sulis-Origin
        # trailer. The hook dir is set via GIT_CONFIG_* env (a per-session
        # override; NO `.git/config` mutation, so it leaves the worktree
        # untouched and reversible). SULIS_SCRIPTS_DIR lets the hook locate
        # `_origin_stamp`. The hook itself is a no-op unless SULIS_ORIGIN is set
        # at commit time (the run-ulid + confidence the executor supplies for
        # the autonomous stamp), so wiring it is harmless when no origin is set.
        scripts_dir = Path(__file__).resolve().parent
        hooks_dir = scripts_dir / "hooks"
        lines.append(f"export SULIS_SCRIPTS_DIR={shlex.quote(str(scripts_dir))}")
        lines.append("export GIT_CONFIG_COUNT=1")
        lines.append("export GIT_CONFIG_KEY_0=core.hooksPath")
        lines.append(f"export GIT_CONFIG_VALUE_0={shlex.quote(str(hooks_dir))}")
    if extra_env_block:
        lines.append(extra_env_block)
    lines.append(f'cd "{worktree_path}"')
    lines.append(exec_line)
    return "\n".join(lines) + "\n"


# ─── Platform dispatchers (private) ────────────────────────────────────────


def _spawned(
    pid: int | None,
    terminal_app: str,
    script_path: Path,
    *,
    pid_kind: str = "launcher",
    tty: str | None = None,
) -> dict:
    """Build the structured spawn-success dict.

    ``pid_kind`` flags what ``pid`` actually refers to so callers (``focus``'s
    liveness check) don't trust a known-dead handle:
      - ``"session"``  — pid of the long-lived spawned shell (reliable for
        ``kill -0`` liveness).
      - ``"launcher"`` — pid of the short-lived launcher/helper process
        (osascript / emulator parent) that exits within ~1s. NOT reliable for
        liveness; ``focus`` should prefer ``tty`` when present.
    ``tty`` is the controlling terminal device of the spawned session when it
    could be captured (macOS ``do script`` returns a tab whose ``tty`` we read).
    A real tty is a more useful liveness handle than a dead launcher pid.
    """
    return {
        "status": "spawned",
        "pid": pid,
        "pid_kind": pid_kind,
        "tty": tty,
        "terminal_app_used": terminal_app,
        "script_path": str(script_path),
        "error": None,
    }


def _failed(error: str, script_path: Path) -> dict:
    return {
        "status": "failed",
        "pid": None,
        "pid_kind": None,
        "tty": None,
        "terminal_app_used": None,
        "script_path": str(script_path),
        "error": error,
    }


def _launch_macos(script_path: Path, change_id: str, visible: bool) -> dict:
    """Spawn via ``osascript -e 'tell Terminal to do script ...'``.

    ``do script`` opens a NEW Terminal.app window and runs the command in it.
    Two dogfood fixes vs. the original fire-and-forget Popen:

    1. ``activate`` brings Terminal.app to the foreground so the spawned
       window lands in front of the founder's current app instead of behind it
       (Bug 3). The single AppleScript both opens the tab and activates the app.

    2. We run osascript *synchronously* and read back the new tab's ``tty``
       (Bug 2). ``do script`` returns the tab; ``tty of <tab>`` is its
       controlling terminal device — a stable, long-lived handle. The osascript
       process itself exits within ~1s, so its pid is useless for liveness;
       recording the tty (pid_kind="session", pid=None) gives ``focus`` a real
       thing to check (``ps -t <tty>``) instead of a known-dead pid.

    If the tty can't be parsed (older macOS / unexpected AppleScript output),
    we degrade honestly: pid_kind="launcher", tty=None — flagged, not silently
    misleading. The window still opens and runs ``claude``.
    """
    # `activate` first foregrounds Terminal.app; `do script` opens the tab and
    # returns it; `tty of <tab>` yields the device path we print to stdout.
    applescript = (
        'tell application "Terminal"\n'
        "    activate\n"
        f'    set newTab to do script "bash {script_path}"\n'
        "    return tty of newTab\n"
        "end tell"
    )
    logger.info("spawning macOS terminal for change %s", change_id)
    try:
        completed = subprocess.run(  # noqa: S603
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=15,
        )
        tty = completed.stdout.strip() or None
        # A real Terminal tty looks like /dev/ttys000; anything else is noise.
        if tty is not None and not tty.startswith("/dev/tty"):
            tty = None
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("osascript spawn read-back failed for %s: %s", change_id, exc)
        tty = None

    if tty is not None:
        return _spawned(
            None, "Terminal.app", script_path, pid_kind="session", tty=tty,
        )
    # Honest degrade: we opened the window but couldn't capture a liveness
    # handle. Flag pid_kind="launcher" so focus knows not to trust pid.
    return _spawned(
        None, "Terminal.app", script_path, pid_kind="launcher", tty=None,
    )


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
        # The emulator pid is the launcher process, not the bound session
        # shell: gnome-terminal in particular forks to a daemon and the
        # launched pid exits at once, so kill -0 on it is unreliable. Flag it
        # pid_kind="launcher". Linux emulators foreground themselves on launch,
        # so no explicit activate is needed (Bug 3 is a macOS-only problem).
        return _spawned(proc.pid, app, script_path, pid_kind="launcher")

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
    # Headless spawns the session shell directly: this pid IS the long-lived
    # bound session, so it's a reliable kill -0 liveness handle.
    return _spawned(proc.pid, "headless", script_path, pid_kind="session")


# ─── Session bookkeeping (private) ─────────────────────────────────────────


def _change_dir(change_id: str) -> Path:
    """Return ``~/.sulis/changes/{change_id}/`` (created if absent)."""
    change_dir = Path.home() / ".sulis" / "changes" / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    return change_dir


def _default_change_pre_prompt(change_id: str) -> str:
    """Opening prompt used when a caller spawns a change terminal without one.

    Without an opening turn, ``claude --agent sulis`` comes up correctly bound
    to the change (``SULIS_CHANGE_ID`` exported, cwd = the worktree) but sits
    idle: the agent never reads the env var until the founder types something,
    so it never self-orients. ``sulis-change start --spawn`` avoids this by
    passing a rich brief; the ``focus`` / ``recreate`` re-spawn paths (and any
    direct caller) historically passed ``None`` and hit the idle-session bug
    (#93). Defaulting here makes an auto-starting session the floor for EVERY
    caller — an explicit ``pre_prompt`` still wins.

    Deterministic (a pure function of ``change_id``) so the sidecar write and
    the launch script's ``cat`` of it always agree on the same bytes.
    """
    recon = Path.home() / ".sulis" / "changes" / change_id / "CONTEXT.md"
    return (
        f"You are Sulis, focused on the change bound to this session "
        f"(id: {change_id}). Your working directory is the change worktree. "
        f"Read the pre-spawn recon at {recon} for the change identity, git "
        f"state, and suggested next step — and any .changes/*.HANDOFF.md or "
        f".changes/*.WORKING-SET.md in the worktree — then greet me in "
        f"change-context mode and route to the right stage."
    )


def _write_session_json(
    change_dir: Path,
    change_id: str,
    pid: int | None,
    terminal_app: str | None,
    script_path: Path,
    *,
    pid_kind: str = "launcher",
    tty: str | None = None,
) -> Path:
    """Persist session.json for later reattach (used by ``focus``).

    Records ``pid_kind`` + ``tty`` so the reattach liveness check doesn't trust
    a known-dead launcher pid: when ``pid_kind == "session"`` the pid (or tty)
    is a reliable handle; when ``"launcher"`` the pid exits within ~1s and the
    consumer should fall back to ``tty`` (``ps -t <tty>``) if present, or treat
    the session as unknown rather than dead.
    """
    payload = {
        "change_id": change_id,
        "pid": pid,
        "pid_kind": pid_kind,
        "tty": tty,
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
    entry_command: str | None = None,
    extra_env: dict[str, str] | None = None,
    pre_prompt: str | None = None,
    enable_origin_hook: bool = True,
) -> dict:
    """Spawn a new terminal in the change worktree with SULIS_CHANGE_ID set.

    ``entry_command`` defaults to ``None`` → the window runs the desktop viewer
    attached to the change's shared session (change CH-01KTKB ADR-003). Pass a
    chat-style command string to run that instead (the legacy direct path; it
    is still injection-whitelisted).

    Composes:
        1. Validate all inputs (raises ValueError on bad input)
        2. Build launch.sh via _build_launch_script
        3. Persist launch.sh at ~/.sulis/changes/{change_id}/launch.sh (0o755)
        4. Dispatch to _launch_{macos|linux|headless} by platform + visible
        5. Persist session.json on success (not on failure)
        6. Return the structured dispatcher dict + session_json_path

    Returns:
        {"status", "pid", "pid_kind", "tty", "terminal_app_used",
         "script_path", "session_json_path", "error"}

        ``pid_kind`` flags whether ``pid`` is the long-lived bound session
        ("session") or a short-lived launcher/helper ("launcher", exits ~1s —
        do not trust for liveness); ``tty`` is the session's controlling
        terminal device when capturable (macOS), a more reliable reattach
        handle than a dead launcher pid.

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

    # A VISIBLE launch opens the change's terminal by DEFAULT (CH-01KTK7). This
    # is the sanctioned change-start launcher: `start --spawn` wants a real
    # terminal window to open, briefed on the change — not a pointer elsewhere.
    # No env flag is required. ``SULIS_TERMINAL_OS_WINDOW`` remains only as an
    # explicit override knob (e.g. forcing the OS-window path in environments
    # where it would otherwise be skipped); it does NOT gate the default-on
    # behaviour, so we deliberately do not consult ``_os_window_enabled()`` here.
    # The in-cockpit ``<LiveTerminal/>`` is a SEPARATE browser-rendering
    # capability, reached through the cockpit — not a replacement for popping a
    # focused terminal at change start.

    # Default an opening prompt so the spawned session auto-starts rather than
    # sitting idle at an empty claude prompt (#93). start --spawn passes a rich
    # brief; focus / recreate / direct callers historically passed None. An
    # explicit pre_prompt still wins — we only fill the gap.
    if pre_prompt is None:
        pre_prompt = _default_change_pre_prompt(change_id)

    script_body = _build_launch_script(
        change_id, resolved, entry_command=entry_command,
        extra_env=extra_env, pre_prompt=pre_prompt,
        enable_origin_hook=enable_origin_hook,
    )

    # File-I/O hardening: an unwritable change dir / launch.sh (permission
    # denied, read-only FS, disk full) must surface the module's structured
    # _failed(...) dict — never an unhandled OSError traceback to the founder.
    try:
        change_dir = _change_dir(change_id)
        change_dir.mkdir(parents=True, exist_ok=True)
        script_path = change_dir / "launch.sh"
        # Write the pre_prompt sidecar the exec line reads (#86). The brief
        # lives in a file, never inline in the script, so bash never parses
        # its bytes — apostrophes/quotes/backticks are safe, and it is
        # inspectable.
        if pre_prompt is not None:
            (change_dir / _PRE_PROMPT_SIDECAR).write_text(pre_prompt)
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
                pid_kind=result.get("pid_kind", "launcher"),
                tty=result.get("tty"),
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
