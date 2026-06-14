"""Defence-in-depth: the recreate fallback worktree path disambiguates by
``change_id`` (HD-005).

``change_worktree_path`` composes the *legacy* sibling worktree directory
that ``sulis-change recreate`` falls back to when git reports a change's
branch checked out nowhere. The legacy composition keys purely on
``{primitive}-{slug}`` — so two distinct changes that happen to share a
primitive and slug resolve to the *same* sibling directory. Live data shows
zero such collisions today (low realised risk), but it is the last
structural way two changes could share a working tree (Scenario 3), so this
is opportunistic defence-in-depth.

The fix: ``change_worktree_path`` accepts an optional ``change_id``. When
supplied, it returns the id-keyed co-located worktree dir
(``change_worktree_dir(change_id)``) — which is unique per change by
construction — so two changes sharing ``{primitive}-{slug}`` can never
resolve to the same fallback path. When ``change_id`` is omitted the legacy
two-argument behaviour is preserved byte-for-byte (backward compatibility
for callers and for legacy slug-keyed changes that predate id-keyed
worktrees).

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _change_state import change_worktree_dir
from _wpxlib import change_worktree_path


@pytest.fixture(autouse=True)
def _isolated_state_base(tmp_path, monkeypatch):
    """Point the Sulis state base at a tmp dir so ``change_worktree_dir``
    resolves under the test sandbox (never the real ``~/.sulis``)."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "state"))


# ─── Characterisation (REORGANISE → pin current behaviour first) ──────────


def test_change_worktree_path_pins_current_slug_composition(tmp_path):
    """Pins the existing legacy fallback: a ``{primitive}-{slug}`` sibling of
    the repo. This is the behaviour we must preserve when ``change_id`` is
    not supplied."""
    repo = tmp_path / "myrepo"
    repo.mkdir()

    dest = change_worktree_path(repo, "create", "introduce-payments")

    assert dest == tmp_path / "myrepo-change-create-introduce-payments"


# ─── Behaviour change (fails today; passes after the fix) ─────────────────


def test_change_worktree_path_distinct_ids_distinct_paths(tmp_path):
    """Two changes that share primitive + slug but differ in ``change_id``
    MUST resolve to distinct fallback worktree paths. Without the fix both
    resolve to the same slug-keyed sibling — the collision this WP closes."""
    repo = tmp_path / "myrepo"
    repo.mkdir()

    id_a = "01KTV4SS9N8BP0XN8GCQAXT6PC"
    id_b = "01KTMFZ76WPCD213DC9JX7JYNX"

    dest_a = change_worktree_path(repo, "create", "introduce-payments",
                                  change_id=id_a)
    dest_b = change_worktree_path(repo, "create", "introduce-payments",
                                  change_id=id_b)

    assert dest_a != dest_b


def test_change_worktree_path_id_keyed_uses_colocated_dir(tmp_path):
    """When ``change_id`` is supplied the path IS the id-keyed co-located
    worktree dir — the canonical, per-change-unique home."""
    repo = tmp_path / "myrepo"
    repo.mkdir()
    change_id = "01KTV4SS9N8BP0XN8GCQAXT6PC"

    dest = change_worktree_path(repo, "create", "introduce-payments",
                                change_id=change_id)

    assert dest == change_worktree_dir(change_id)


# ─── Backward compatibility (legacy slug-keyed callers unchanged) ─────────


def test_change_worktree_path_no_id_is_backward_compatible(tmp_path):
    """Omitting ``change_id`` (or passing ``None``) keeps the exact legacy
    slug-keyed sibling path — legacy changes with no co-located worktree
    still recreate at their historic location."""
    repo = tmp_path / "myrepo"
    repo.mkdir()

    implicit = change_worktree_path(repo, "fix", "tidy-logs")
    explicit_none = change_worktree_path(repo, "fix", "tidy-logs",
                                         change_id=None)

    assert implicit == tmp_path / "myrepo-change-fix-tidy-logs"
    assert explicit_none == implicit


def test_change_worktree_path_blank_id_is_backward_compatible(tmp_path):
    """A blank ``change_id`` degrades to the legacy path rather than
    composing a nonsensical co-located dir for the empty id."""
    repo = tmp_path / "myrepo"
    repo.mkdir()

    dest = change_worktree_path(repo, "fix", "tidy-logs", change_id="")

    assert dest == tmp_path / "myrepo-change-fix-tidy-logs"
    assert isinstance(dest, Path)
