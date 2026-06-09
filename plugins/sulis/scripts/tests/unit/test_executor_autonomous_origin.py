"""WP-005 — the executor's autonomous `SULIS_ORIGIN` env-builder (ADR-013).

#216 built the receiving end (the `prepare-commit-msg` hook + the trailer
format + `parse_origin_env`). This WP builds the *sending* side for the
executor (autonomous) write path: a small env-builder the executor's commit
step (Step 7) exports BEFORE it commits, so the already-wired hook stamps the
`Sulis-Origin: autonomous; run=…` trailer onto the very commit it makes.

Design points pinned here:
  - The run-ulid is per-`lifecyclerun`; the export is at COMMIT time (not a
    static launch-script export), so `autonomous_env` takes the run at call time.
  - `confidence` is OPTIONAL — when no per-run scalar exists, build a `run=`-only
    body (do NOT invent a value). The constructor + `format_trailer` already
    support this.
  - Non-fatal (ADR-013): a missing / empty run-ulid → NO export (the helper
    returns an empty env), and the commit proceeds UNSTAMPED. Never abort.
  - No new formatter: the body is the exact bare-body grammar the hook's
    `parse_origin_env` accepts, produced via the existing `format_trailer`.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from _origin_stamp import (  # noqa: E402  (sys.path set up by conftest)
    TRAILER_KEY,
    autonomous_env,
    parse_origin_env,
)

_HOOK = Path(__file__).resolve().parents[2] / "hooks" / "prepare-commit-msg"

_ULID = "01KT500K2JTE2EGW6TPPQ4D4VN"


@pytest.fixture(autouse=True)
def _isolate_sulis_origin(monkeypatch):
    """#245 — clear the ambient `SULIS_ORIGIN` for every test in this file.

    `_commit` snapshots `dict(os.environ)`, so running the suite inside a
    Sulis-assisted session (which exports `SULIS_ORIGIN`) made the
    unstamped-path assertion fail (the hook stamped the session's origin).
    The stamped-path tests pass their own env via `autonomous_env(...)`, which
    re-adds the var after this clear, so they are unaffected.
    """
    monkeypatch.delenv("SULIS_ORIGIN", raising=False)


# ─── the env-builder: run-only ─────────────────────────────────────────────


def test_autonomous_env_run_only_parses_to_autonomous_origin():
    """run-ulid present, no confidence → env value parses back to
    {kind:'autonomous', run:<ulid>} via the hook's own parser."""
    env = autonomous_env(run=_ULID, confidence=None)
    assert "SULIS_ORIGIN" in env
    parsed = parse_origin_env(env["SULIS_ORIGIN"])
    assert parsed == {"kind": "autonomous", "run": _ULID}


def test_autonomous_env_with_confidence_carries_confidence():
    """When a per-run confidence scalar is supplied it round-trips through the
    parser as a float."""
    env = autonomous_env(run=_ULID, confidence=0.8)
    parsed = parse_origin_env(env["SULIS_ORIGIN"])
    assert parsed == {"kind": "autonomous", "run": _ULID, "confidence": 0.8}


def test_autonomous_env_omits_confidence_when_none():
    """confidence=None → a `run=`-only body, no `confidence=` segment
    (do NOT invent a value)."""
    env = autonomous_env(run=_ULID, confidence=None)
    assert "confidence" not in env["SULIS_ORIGIN"]
    assert env["SULIS_ORIGIN"] == f"autonomous; run={_ULID}"


# ─── the env-builder: missing run is non-fatal ─────────────────────────────


@pytest.mark.parametrize("run", ["", None, "   "])
def test_autonomous_env_missing_run_yields_no_export(run):
    """A missing / empty / whitespace run-ulid → NO SULIS_ORIGIN export
    (the helper returns an empty env), so the commit proceeds unstamped
    (degrade to inferred — ADR-013). Never raises."""
    env = autonomous_env(run=run, confidence=None)
    assert env == {}


# ─── grammar conformance: bare body, no new formatter ──────────────────────


def test_autonomous_env_body_is_the_bare_grammar():
    """The exported value is the bare trailer BODY the hook accepts — it does
    NOT carry the `Sulis-Origin: ` key prefix (the hook prepends the key)."""
    env = autonomous_env(run=_ULID, confidence=None)
    assert not env["SULIS_ORIGIN"].lower().startswith(f"{TRAILER_KEY.lower()}:")
    # And it is exactly format_trailer's body (reuse, no re-implementation):
    from _origin_stamp import autonomous_origin, format_trailer

    full = format_trailer(autonomous_origin(run=_ULID, confidence=None))
    expected_body = full[len(f"{TRAILER_KEY}: ") :]
    assert env["SULIS_ORIGIN"] == expected_body


# ─── degradation: real test commit through the wired hook ──────────────────


def _install_hook(repo: Path) -> None:
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


def test_exported_env_round_trips_through_the_hook(local_git_repo):
    """Export the helper's env on a real commit → the wired hook stamps the
    autonomous trailer onto that commit."""
    repo = local_git_repo
    _install_hook(repo)
    env = autonomous_env(run=_ULID, confidence=None)
    msg = _commit(repo, "a.txt", "feat: autonomous work", env=env)
    assert f"Sulis-Origin: autonomous; run={_ULID}" in msg
    assert "feat: autonomous work" in msg


def test_no_export_leaves_the_commit_unstamped(local_git_repo):
    """With no run-ulid the helper returns no env → the commit lands UNSTAMPED
    and no error (graceful degradation to inferred)."""
    repo = local_git_repo
    _install_hook(repo)
    env = autonomous_env(run="", confidence=None)  # {} — nothing exported
    msg = _commit(repo, "b.txt", "chore: no run-ulid", env=env)
    assert "chore: no run-ulid" in msg  # commit landed
    assert "Sulis-Origin:" not in msg  # nothing stamped
