"""WP-P12 — the `prepare-commit-msg` git hook (ADR-013).

The commit-time interception for both write paths: it reads the `SULIS_ORIGIN`
env (set by the executor / by the relay's bridge spawn) and appends the
`Sulis-Origin:` trailer to the in-flight commit message file BEFORE the commit
object is written. No env → no-op (the commit lands unstamped → inferred).

The hook is a thin shell over `_origin_stamp.append_trailer_to_message` /
`parse_origin_env`; this drives the real script end-to-end as a real git hook.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_HOOK = (
    Path(__file__).resolve().parents[2] / "hooks" / "prepare-commit-msg"
)


def _install_hook(repo: Path) -> None:
    """Wire the hook the way it actually ships: point git's `core.hooksPath`
    at the scripts `hooks/` dir, so the hook runs in place with its sibling
    `_origin_stamp` importable."""
    subprocess.run(
        ["git", "-C", str(repo), "config", "core.hooksPath", str(_HOOK.parent)],
        check=True,
    )


def _commit(repo: Path, fname: str, msg: str, env: dict | None = None) -> str:
    (repo / fname).write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", fname], check=True)
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", msg],
        check=True, env=full_env,
    )
    return subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%B"],
        check=True, capture_output=True, text=True,
    ).stdout


def test_hook_exists_and_is_executable():
    assert _HOOK.exists(), f"hook missing: {_HOOK}"
    assert os.access(_HOOK, os.X_OK), "hook must be executable"


def test_hook_stamps_autonomous_trailer_when_env_set(local_git_repo):
    repo = local_git_repo
    _install_hook(repo)
    msg = _commit(
        repo, "a.txt", "feat: autonomous work",
        env={"SULIS_ORIGIN": "autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=0.8"},
    )
    assert (
        "Sulis-Origin: autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=0.8"
        in msg
    )
    assert "feat: autonomous work" in msg


def test_hook_stamps_assisted_trailer_when_env_set(local_git_repo):
    repo = local_git_repo
    _install_hook(repo)
    msg = _commit(
        repo, "b.txt", "fix: assisted",
        env={"SULIS_ORIGIN": "assisted; conversation=sess-9; turn=4"},
    )
    assert "Sulis-Origin: assisted; conversation=sess-9; turn=4" in msg


def test_hook_is_noop_without_env(local_git_repo):
    repo = local_git_repo
    _install_hook(repo)
    msg = _commit(repo, "c.txt", "chore: no origin")
    assert "Sulis-Origin:" not in msg
    assert "chore: no origin" in msg


def test_hook_works_when_copied_into_git_hooks(local_git_repo):
    """Copy-install (into `.git/hooks/`, where the sibling import is gone) still
    stamps, via the `SULIS_SCRIPTS_DIR` locator override."""
    repo = local_git_repo
    hooks_dir = repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    dest = hooks_dir / "prepare-commit-msg"
    dest.write_text(_HOOK.read_text())
    dest.chmod(0o755)
    msg = _commit(
        repo, "e.txt", "feat: copied hook",
        env={
            "SULIS_ORIGIN": "autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=1",
            "SULIS_SCRIPTS_DIR": str(_HOOK.parent.parent),
        },
    )
    assert "Sulis-Origin: autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=1" in msg


def test_hook_is_non_fatal_on_garbage_env(local_git_repo):
    """A malformed SULIS_ORIGIN must not block the commit (graceful degrade)."""
    repo = local_git_repo
    _install_hook(repo)
    msg = _commit(
        repo, "d.txt", "chore: garbage origin",
        env={"SULIS_ORIGIN": "this-is-not-valid"},
    )
    assert "chore: garbage origin" in msg  # commit landed
    assert "Sulis-Origin:" not in msg  # nothing stamped
