"""ADE worktree relocation — the change's worktree co-locates with its state.

A change's working tree now lives at ``~/.sulis/changes/{change_id}/worktree``
(beside its ``state.json`` / ``change.json`` / ``CONTEXT.md``) instead of as a
sibling ``<repo>-change-<slug>/`` directory. This kept confusing both the
non-technical user and git tooling (the stale-worktree pile-up that jammed the
shared ``dev`` branch).

Two behaviours under test:
  1. ``change_worktree_dir(change_id)`` resolves to ``change_dir/worktree``.
  2. ``resolve_current_change`` finds a co-located change by ``change_id`` even
     when driving from an unrelated directory (step 2.5 of the resolver).

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

import os

import pytest

from _change_state import change_dir, change_worktree_dir
from _wpxlib import (
    SULIS_CHANGE_ID_ENV_VAR,
    resolve_current_change,
    write_change_metadata,
)

_CHANGE_ID = "01HYQC71000000000000000000"


@pytest.fixture(autouse=True)
def _home_isolation(tmp_path_factory, monkeypatch):
    """Isolate ~/.sulis via HOME (opt out of the repo-wide SULIS_STATE_DIR)."""
    monkeypatch.delenv("SULIS_STATE_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))


def test_change_worktree_dir_is_under_change_dir():
    """The worktree lives co-located with the change's state dir."""
    assert change_worktree_dir(_CHANGE_ID) == change_dir(_CHANGE_ID) / "worktree"


def test_change_worktree_dir_is_not_a_repo_sibling():
    """Sanity: the new home is under ~/.sulis, not a sibling of any repo."""
    wt = change_worktree_dir(_CHANGE_ID)
    assert ".sulis" in wt.parts and "changes" in wt.parts
    assert wt.name == "worktree"


def test_resolve_finds_colocated_change_from_unrelated_dir(tmp_path, monkeypatch):
    """resolve_current_change resolves a co-located change by change_id (step
    2.5) even when cwd/repo_root is an unrelated, non-git directory."""
    # Lay down a co-located manifest at change_dir/worktree/.changes/.
    primitive, slug = "create", "introduce-payments"
    manifest = (
        change_worktree_dir(_CHANGE_ID) / ".changes" / f"{primitive}-{slug}.yaml"
    )
    write_change_metadata(
        manifest,
        {
            "change_id": _CHANGE_ID,
            "slug": slug,
            "primitive": primitive,
            "branch": f"change/{primitive}-{slug}",
            "worktree_path": str(change_worktree_dir(_CHANGE_ID)),
        },
    )

    monkeypatch.setenv(SULIS_CHANGE_ID_ENV_VAR, _CHANGE_ID)
    # repo_root is an unrelated, empty, non-git dir — steps 1/2/3 cannot match;
    # only the co-located step (2.5) can resolve it.
    unrelated = tmp_path / "somewhere-else"
    unrelated.mkdir()

    result = resolve_current_change(repo_root=unrelated)
    assert result is not None, "co-located change should resolve by change_id"
    assert result.get("change_id") == _CHANGE_ID
    assert result.get("slug") == slug


def test_resolve_returns_none_when_env_unset(tmp_path, monkeypatch):
    """Regression: env unset → None (unchanged behaviour)."""
    monkeypatch.delenv(SULIS_CHANGE_ID_ENV_VAR, raising=False)
    assert resolve_current_change(repo_root=tmp_path) is None
