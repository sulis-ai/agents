"""Unit tests for WP-006 — re-point the desktop launcher to run the viewer.

ADR-003 / TDD §6. `launch_change_terminal` used to open a Terminal window
running `claude --agent sulis` DIRECTLY (the CH-01KTK7 standalone path). This
WP changes WHAT runs in the window — the desktop viewer (`session_viewer.py`,
WP-005) attached to the change's shared session via the daemon — while keeping
ALL the proven cross-platform spawn, env-scrub, origin-hook, and pre-prompt
machinery.

The viewer invocation is built via a dedicated `_build_viewer_exec_line`
(`shlex.quote`-d, mirroring the existing sidecar `cat` line) that is NOT subject
to the chat-style `_ENTRY_COMMAND_RE` whitelist (which forbids `/`, `.`, digits,
and `--flags`). The whitelist is preserved unchanged for the explicit chat-style
`entry_command` path that existing callers may still pass.

Subprocess + platform are mocked throughout — no real terminal is spawned.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest import mock

import pytest

import _terminal_launcher as tl


# A valid 26-char Crockford-base32 ULID for tests (matches the sibling suite).
_GOOD_ULID = "01HYQC71000000000000000000"


# ─── The default window now runs the viewer, not raw claude ────────────────


def test_default_exec_line_runs_viewer_not_claude(tmp_path):
    """The DEFAULT generated launch script execs the desktop viewer attached to
    the change's session — NOT a bare `claude`. (ADR-003: the window is a VIEW
    onto the change's one shared session, not a standalone claude.)"""
    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    assert "session_viewer.py" in script, (
        f"default launch script must exec the viewer; script was:\n{script}"
    )
    # The change-id and worktree are passed through to the viewer so it can
    # attach the right session and set the pty cwd on get-or-spawn.
    assert "--change-id" in script
    assert "--worktree" in script
    assert _GOOD_ULID in script
    # It must NOT be the old direct-claude path.
    assert "exec claude " not in script
    assert "--agent sulis" not in script


def test_build_viewer_exec_line_targets_colocated_viewer(tmp_path):
    """`_build_viewer_exec_line` execs `python3 <scripts>/session_viewer.py`
    co-located with the launcher module, with the change-id + worktree."""
    scripts_dir = Path(tl.__file__).resolve().parent
    line = tl._build_viewer_exec_line(_GOOD_ULID, tmp_path, scripts_dir)
    assert line.startswith("exec ")
    assert "python3" in line
    assert str(scripts_dir / "session_viewer.py") in line
    assert "--change-id" in line
    assert _GOOD_ULID in line
    assert "--worktree" in line
    assert str(tmp_path) in line


# ─── Regression: the preserved machinery is untouched on the viewer path ───


def test_viewer_exec_preserves_env_scrub_change_id_and_cd(tmp_path):
    """The env-scrub preamble, `SULIS_CHANGE_ID` export, and `cd <worktree>`
    are ALL still present on the (now-default) viewer path."""
    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    # env-scrub preamble (MUC-2) — unchanged.
    assert "compgen -v | grep -Ev" in script
    assert "PATH|HOME|USER|TERM|LANG|LC_.*" in script
    assert "2>/dev/null || true" in script
    # SULIS_CHANGE_ID export — the daemon-spawned claude reads this to find the
    # pre_prompt sidecar, so it MUST survive the re-point.
    assert f'export SULIS_CHANGE_ID="{_GOOD_ULID}"' in script
    # cd <worktree> then exec, in that order.
    cd_idx = script.index('cd "')
    exec_idx = script.index("exec ")
    assert cd_idx < exec_idx


def test_viewer_path_preserves_origin_hook(tmp_path):
    """The WP-P12 origin-hook wiring still composes on the viewer path."""
    script = tl._build_launch_script(_GOOD_ULID, tmp_path, enable_origin_hook=True)
    assert "GIT_CONFIG_COUNT" in script
    assert "core.hooksPath" in script
    assert "export SULIS_SCRIPTS_DIR=" in script
    # exports land AFTER the env-scrub (which would otherwise strip them).
    assert script.index("compgen -v") < script.index("GIT_CONFIG_COUNT")


def test_viewer_path_still_writes_pre_prompt_sidecar(tmp_path, monkeypatch):
    """The pre_prompt sidecar is STILL written verbatim on the viewer path, and
    SULIS_CHANGE_ID is still exported. The viewer does NOT take the brief as a
    CLI arg — the daemon's interactive pty adapter reads the sidecar via
    SULIS_CHANGE_ID and feeds it to the session's claude as its first turn
    (briefed-on-spawn). So the launch script must (a) write the sidecar and
    (b) export SULIS_CHANGE_ID, but it does NOT cat the brief onto the viewer
    exec line (that would pass argparse an unexpected positional)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    spawned = {
        "status": "spawned", "pid": None, "pid_kind": "session",
        "tty": "/dev/ttys009", "terminal_app_used": "Terminal.app",
        "script_path": "", "error": None,
    }
    body = "render each change's contract -- apostrophe, \"quote\", `tick`"
    with mock.patch.object(tl.platform, "system", return_value="Darwin"), \
            mock.patch.object(tl, "_launch_macos",
                              side_effect=lambda sp, cid, vis: {**spawned, "script_path": str(sp)}):
        result = tl.launch_change_terminal(_GOOD_ULID, tmp_path, pre_prompt=body)
    # (a) the sidecar carrying the brief is still written, byte-for-byte.
    sidecar = tl._change_dir(_GOOD_ULID) / tl._PRE_PROMPT_SIDECAR
    assert sidecar.read_text() == body, "pre_prompt sidecar must still be written verbatim"
    # (b) SULIS_CHANGE_ID is exported so the daemon's pty adapter can locate it.
    script = Path(result["script_path"]).read_text()
    assert f'export SULIS_CHANGE_ID="{_GOOD_ULID}"' in script
    # The viewer exec line runs the viewer (no positional brief arg).
    assert "session_viewer.py" in script
    assert '"$(cat ' not in script, (
        "viewer takes the brief via the daemon, not as a positional CLI arg"
    )


# ─── Injection guard: viewer args are shlex-quoted ─────────────────────────


def test_build_viewer_exec_line_shlex_quotes_args(tmp_path):
    """The viewer exec args are `shlex.quote`-d so a worktree path with shell
    metacharacters cannot break out of the exec line (injection guard, mirroring
    the existing sidecar `cat` construction)."""
    scripts_dir = Path(tl.__file__).resolve().parent
    nasty = tmp_path / "a dir; rm -rf $(echo evil)"
    nasty.mkdir()
    line = tl._build_viewer_exec_line(_GOOD_ULID, nasty, scripts_dir)
    # The dangerous worktree path is single-quoted, so the shell never expands
    # the `$(...)` or runs the `;`-chained command.
    assert "'" in line
    assert shutil.which  # sanity, keeps import used
    # bash must parse the line without splitting on the metacharacters.
    bash = shutil.which("bash")
    if bash is not None:
        wrapper = f"f() {{ :; }}\nexec() {{ printf '%s' \"$*\"; }}\n{line}\n"
        sh = tmp_path / "probe.sh"
        sh.write_text(wrapper)
        r = subprocess.run([bash, "-n", str(sh)], capture_output=True, text=True)
        assert r.returncode == 0, f"viewer exec line is not parseable: {r.stderr}"


def test_build_viewer_exec_line_does_not_use_entry_command_whitelist(tmp_path):
    """The viewer line contains `/`, `.`, and `--flags` — all FORBIDDEN by the
    chat-style `_ENTRY_COMMAND_RE`. Building it must NOT route through
    `validate_entry_command`; if it did, the launcher would reject its own
    viewer invocation. (The whitelist stays intact for the chat-style path.)"""
    scripts_dir = Path(tl.__file__).resolve().parent
    line = tl._build_viewer_exec_line(_GOOD_ULID, tmp_path, scripts_dir)
    # The constructed line is exactly the kind of string the whitelist rejects.
    payload = line[len("exec "):]
    ok, _ = tl.validate_entry_command(payload)
    assert ok is False, "the viewer line is intentionally outside the chat whitelist"
    # And the whitelist itself is unchanged — still rejects path-shaped commands.
    ok, _ = tl.validate_entry_command("python3 /x/session_viewer.py")
    assert ok is False


# ─── The explicit chat-style entry_command path is still supported ─────────


def test_explicit_entry_command_still_supported(tmp_path):
    """An explicit chat-style `entry_command` (whitelist-valid) is still honoured
    for callers that want it — the viewer is only the DEFAULT."""
    script = tl._build_launch_script(
        _GOOD_ULID, tmp_path,
        entry_command="claude --dangerously-skip-permissions --agent sulis",
    )
    # The id is set on claude's OWN process via `env` (#107) so an inherited
    # stale SULIS_CHANGE_ID can't re-shadow it; the claude command itself is
    # otherwise unchanged.
    assert (
        f"exec env SULIS_CHANGE_ID={_GOOD_ULID} "
        "claude --dangerously-skip-permissions --agent sulis"
    ) in script
    assert "session_viewer.py" not in script


def test_explicit_entry_command_still_validated(tmp_path):
    """The explicit chat-style path still runs the injection guard."""
    with pytest.raises(ValueError):
        tl._build_launch_script(
            _GOOD_ULID, tmp_path, entry_command="claude; rm -rf /",
        )


# ─── The generated viewer script parses + runs under bash 3.2 ──────────────


def test_generated_viewer_script_parses_under_bash(tmp_path):
    """The default (viewer) launch script must parse under bash (macOS 3.2),
    including with tricky pre_prompt chars in the sidecar path region."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash not available")
    body = ("render each change's data contract; say \"hi\"; `tick`; "
            "$HOME; it's done -> next")
    script = tl._build_launch_script(_GOOD_ULID, tmp_path, pre_prompt=body)
    sh = tmp_path / "launch.sh"
    sh.write_text(script)
    r = subprocess.run([bash, "-n", str(sh)], capture_output=True, text=True)
    assert r.returncode == 0, f"viewer launch.sh has a syntax error: {r.stderr}"


def test_generated_viewer_script_runs_to_exec_under_bash(tmp_path, monkeypatch):
    """The viewer launch script must run to its exec line under bash without the
    env-scrub `set -e` aborting (the dogfood readonly-var bug). We point the
    viewer at a stub `python3` on PATH that prints a marker and exits 0, proving
    the exec line is reached and the env-scrub does not abort first."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash not available")
    # Stub python3 on PATH: prints a marker for any argv, exits 0.
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub = stub_dir / "python3"
    stub.write_text("#!/usr/bin/env bash\nprintf reached-viewer-exec\nexit 0\n")
    stub.chmod(0o755)
    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    sh = tmp_path / "launch.sh"
    sh.write_text(script)
    env = dict(PATH=f"{stub_dir}:/usr/bin:/bin", HOME=str(tmp_path))
    r = subprocess.run(
        [bash, str(sh)], capture_output=True, text=True, cwd=str(tmp_path), env=env,
    )
    assert r.returncode == 0, (
        f"viewer script aborted (exit {r.returncode}); stderr={r.stderr!r}"
    )
    assert "reached-viewer-exec" in r.stdout, (
        f"viewer exec line not reached; stdout={r.stdout!r} stderr={r.stderr!r}"
    )


# ─── The module is documented as a VIEW onto the shared session ────────────


def test_module_docstring_describes_view_onto_shared_session():
    """The module docstring must describe the window as a VIEW onto the change's
    shared session (ADR-003 supersession of CH-01KTK7), not a standalone claude."""
    src = Path(tl.__file__).read_text()
    head = src[:2000].lower()
    assert "viewer" in head or "view onto" in head, (
        "module docstring must describe the desktop-viewer re-point"
    )


# ─── WP-001 (CH-3FNT33): resolve the INSTALLED scripts dir for the spawn ───
#
# `_terminal_launcher.py` used to self-locate the spawned window's sibling
# scripts from its OWN file (`Path(__file__).resolve().parent`) at two sites —
# the viewer exec line (line 303) and the origin-hook exports (line 350). When
# the launcher runs from a change WORKTREE (the dogfood case), `__file__` is the
# worktree copy, so the spawned window execs worktree code. WP-001 redirects both
# sites at the INSTALLED plugin scripts dir via one named resolver
# `_resolve_installed_scripts_dir()`. These tests build a FAKE cache under
# `tmp_path` and monkeypatch `default_cache_root` at it — the developer's real
# ~/.claude is never touched.


def _make_fake_cache(tmp_path, versions):
    """Materialise `<tmp>/sulis-ai-agents/sulis/<ver>/scripts` for each version.

    Mirrors the real plugin-cache layout (`_prune_cache._SULIS_SUBPATH` =
    ("sulis-ai-agents", "sulis")). Returns the cache ROOT (the dir
    `default_cache_root` should be monkeypatched to return). Each version gets a
    concrete `scripts` subdir, so the resolver's "scripts dir exists" guard is
    satisfied.
    """
    cache_root = tmp_path / "cache"
    sulis_dir = cache_root.joinpath(*tl._prune_cache._SULIS_SUBPATH)
    for ver in versions:
        (sulis_dir / ver / "scripts").mkdir(parents=True, exist_ok=True)
    return cache_root


def test_explicit_scripts_dir_equals_install_on_single_version_machine(
    tmp_path, monkeypatch
):
    """Characterisation (EP-07 — pin behaviour before the refactor).

    On a single-version installed machine the EXPLICITLY-resolved scripts dir
    EQUALS the install: with a fake cache holding exactly one version whose
    `scripts` dir exists (and no override), `_resolve_installed_scripts_dir()`
    returns that `…/<ver>/scripts`. This is the "no behavioural change other than
    explicit resolution" Constraint — on such a machine the resolution and the
    install coincide."""
    monkeypatch.delenv("SULIS_SPAWN_SCRIPTS_DIR", raising=False)
    cache_root = _make_fake_cache(tmp_path, ["0.42.0"])
    monkeypatch.setattr(tl._prune_cache, "default_cache_root", lambda: cache_root)
    resolved = tl._resolve_installed_scripts_dir()
    expected = cache_root.joinpath(*tl._prune_cache._SULIS_SUBPATH) / "0.42.0" / "scripts"
    assert resolved == expected.resolve()


def test_resolver_picks_numerically_newest_cached_install(tmp_path, monkeypatch):
    """(AC-3) With several versions cached the resolver returns the NUMERICALLY
    newest `…/<max>/scripts` — `0.126.0` over `0.98.0`, NOT the lexical winner.
    Proves `_version_pick` (numeric) is used, never a text sort."""
    monkeypatch.delenv("SULIS_SPAWN_SCRIPTS_DIR", raising=False)
    cache_root = _make_fake_cache(tmp_path, ["0.98.0", "0.126.0"])
    monkeypatch.setattr(tl._prune_cache, "default_cache_root", lambda: cache_root)
    resolved = tl._resolve_installed_scripts_dir()
    sulis_dir = cache_root.joinpath(*tl._prune_cache._SULIS_SUBPATH)
    assert resolved == (sulis_dir / "0.126.0" / "scripts").resolve()
    # The lexical winner (0.98.0 — '9' > '1') must NOT be chosen.
    assert resolved != (sulis_dir / "0.98.0" / "scripts").resolve()


def test_resolver_honours_spawn_scripts_dir_override(tmp_path, monkeypatch):
    """(AC-4) `SULIS_SPAWN_SCRIPTS_DIR` set to an EXISTING dir wins over the cache
    pick. A set-but-MISSING override falls through to the cache pick (not a hard
    fail)."""
    cache_root = _make_fake_cache(tmp_path, ["0.126.0"])
    monkeypatch.setattr(tl._prune_cache, "default_cache_root", lambda: cache_root)
    sulis_dir = cache_root.joinpath(*tl._prune_cache._SULIS_SUBPATH)

    # (a) override points at an existing dir → it wins over the cache pick.
    override = tmp_path / "dev-scripts"
    override.mkdir()
    monkeypatch.setenv("SULIS_SPAWN_SCRIPTS_DIR", str(override))
    assert tl._resolve_installed_scripts_dir() == override.resolve()

    # (b) override set but the dir is MISSING → fall through to the cache pick.
    monkeypatch.setenv("SULIS_SPAWN_SCRIPTS_DIR", str(tmp_path / "does-not-exist"))
    assert tl._resolve_installed_scripts_dir() == (
        sulis_dir / "0.126.0" / "scripts"
    ).resolve()


def test_resolver_falls_back_to_module_dir_with_no_install_no_override(
    tmp_path, monkeypatch
):
    """(AC-5) No override + no cached install → resolver returns
    `Path(tl.__file__).resolve().parent` (today's behaviour). Never raises,
    never returns an empty path."""
    monkeypatch.delenv("SULIS_SPAWN_SCRIPTS_DIR", raising=False)
    # Empty cache root (no sulis-ai-agents/sulis tree at all).
    empty_root = tmp_path / "empty-cache"
    empty_root.mkdir()
    monkeypatch.setattr(tl._prune_cache, "default_cache_root", lambda: empty_root)
    resolved = tl._resolve_installed_scripts_dir()
    assert resolved == Path(tl.__file__).resolve().parent
    assert str(resolved)  # non-empty


def test_resolver_falls_back_when_cache_present_but_scripts_dir_missing(
    tmp_path, monkeypatch
):
    """(AC-5, guard) A cache version dir can be mid-install with NO `scripts`
    subdir; requiring the concrete `scripts` dir to exist keeps the resolver from
    baking a non-existent path into the spawn — it falls through to `__file__`."""
    monkeypatch.delenv("SULIS_SPAWN_SCRIPTS_DIR", raising=False)
    cache_root = tmp_path / "cache"
    sulis_dir = cache_root.joinpath(*tl._prune_cache._SULIS_SUBPATH)
    (sulis_dir / "0.126.0").mkdir(parents=True)  # version dir but NO scripts/
    monkeypatch.setattr(tl._prune_cache, "default_cache_root", lambda: cache_root)
    resolved = tl._resolve_installed_scripts_dir()
    assert resolved == Path(tl.__file__).resolve().parent


def test_viewer_exec_line_targets_installed_cache_scripts(tmp_path, monkeypatch):
    """(AC-1) The DEFAULT launch script's viewer exec line runs
    `python3 <cache>/…/<max>/scripts/session_viewer.py` — the CACHE path, NOT
    `Path(tl.__file__).parent/session_viewer.py`."""
    monkeypatch.delenv("SULIS_SPAWN_SCRIPTS_DIR", raising=False)
    cache_root = _make_fake_cache(tmp_path, ["0.98.0", "0.126.0"])
    monkeypatch.setattr(tl._prune_cache, "default_cache_root", lambda: cache_root)
    sulis_dir = cache_root.joinpath(*tl._prune_cache._SULIS_SUBPATH)
    cache_viewer = sulis_dir / "0.126.0" / "scripts" / "session_viewer.py"

    script = tl._build_launch_script(_GOOD_ULID, tmp_path)
    assert str(cache_viewer.resolve()) in script, (
        f"viewer exec line must target the installed cache scripts; script:\n{script}"
    )
    # The module-dir viewer path must NOT be what's exec'd.
    module_viewer = Path(tl.__file__).resolve().parent / "session_viewer.py"
    assert str(module_viewer) not in script


def test_resolved_path_still_shlex_quoted_in_script(tmp_path, monkeypatch):
    """(AC-6) Point the override at a dir whose name contains shell
    metacharacters; the emitted viewer exec line and the origin-hook exports
    single-quote it, and the generated script parses under `bash -n`. The
    resolver changes WHICH path is quoted, not the quoting."""
    monkeypatch.delenv("SULIS_SPAWN_SCRIPTS_DIR", raising=False)
    nasty = tmp_path / "a dir; $(echo evil)"
    nasty.mkdir()
    monkeypatch.setenv("SULIS_SPAWN_SCRIPTS_DIR", str(nasty))

    script = tl._build_launch_script(_GOOD_ULID, tmp_path, enable_origin_hook=True)
    # The dangerous path is single-quoted everywhere it appears (viewer exec +
    # SULIS_SCRIPTS_DIR + GIT_CONFIG_VALUE_0 hooks dir).
    assert f"'{nasty.resolve()}/session_viewer.py'" in script
    assert f"export SULIS_SCRIPTS_DIR='{nasty.resolve()}'" in script
    assert f"GIT_CONFIG_VALUE_0='{nasty.resolve()}/hooks'" in script

    bash = shutil.which("bash")
    if bash is not None:
        sh = tmp_path / "launch.sh"
        sh.write_text(script)
        r = subprocess.run([bash, "-n", str(sh)], capture_output=True, text=True)
        assert r.returncode == 0, f"generated script is not parseable: {r.stderr}"
