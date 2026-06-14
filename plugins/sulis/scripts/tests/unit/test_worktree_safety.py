"""Worktree-removal scope guard (#130) — the destructive cross-change near-miss.

Example tests cover the named failure modes; the hypothesis property pins the
SAFETY INVARIANT: no path outside the named change's scope is ever allowed.
SULIS_STATE_DIR is redirected to tmp so change_dir() resolves under the test dir.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

_SCRIPTS = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_state import change_dir  # noqa: E402
from _worktree_safety import within_change_scope  # noqa: E402

_CID = "0123456789ABCDEFGHJKMNPQRS"
_OTHER = "1ABCDEFGHJKMNPQRSTVWXYZ012"


@pytest.fixture(autouse=True)
def _state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    return tmp_path


def _wt(change_id: str, name: str = "wp-006-worktree") -> Path:
    d = change_dir(change_id) / name
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─── the named failure modes ────────────────────────────────────────────────


def test_in_scope_worktree_allowed():
    ok, _ = within_change_scope(_wt(_CID), _CID)
    assert ok


def test_cross_change_worktree_refused():
    # The incident: a wp-006 worktree belonging to ANOTHER change.
    ok, reason = within_change_scope(_wt(_OTHER), _CID)
    assert not ok and "outside change" in reason


def test_out_of_scope_path_refused(tmp_path):
    ok, _ = within_change_scope(tmp_path / "somewhere" / "else", _CID)
    assert not ok


def test_change_base_itself_refused():
    # Removing the change's whole dir via worktree-remove is not a worktree op.
    change_dir(_CID).mkdir(parents=True, exist_ok=True)
    ok, _ = within_change_scope(change_dir(_CID), _CID)
    assert not ok


def test_path_traversal_escape_refused():
    # A `..` that climbs out of the change scope resolves outside → refused.
    sneaky = change_dir(_CID) / ".." / _OTHER / "wp-006-worktree"
    ok, _ = within_change_scope(sneaky, _CID)
    assert not ok


def test_symlink_escape_refused(tmp_path):
    outside = tmp_path / "outside-target"
    outside.mkdir()
    change_dir(_CID).mkdir(parents=True, exist_ok=True)
    link = change_dir(_CID) / "escape"
    link.symlink_to(outside)              # inside-looking, resolves outside
    ok, _ = within_change_scope(link, _CID)
    assert not ok


def test_missing_or_invalid_change_id_fails_closed():
    assert not within_change_scope(_wt(_CID), "")[0]
    assert not within_change_scope(_wt(_CID), None)[0]
    assert not within_change_scope(_wt(_CID), "not-a-ulid")[0]


def test_current_directory_refused():
    wt = _wt(_CID)
    ok, reason = within_change_scope(wt, _CID, cwd=wt)
    assert not ok and "current directory" in reason


def test_ancestor_of_cwd_refused():
    wt = _wt(_CID)
    inner = wt / "src"
    inner.mkdir()
    ok, _ = within_change_scope(wt, _CID, cwd=inner)   # removing an ancestor of cwd
    assert not ok


# ─── the safety invariant (property-based) ──────────────────────────────────

_ULID = st.text(alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ", min_size=26, max_size=26)
_SEG = st.text(alphabet="abcdefghijkmnpqrstuvwxyz0123456789-", min_size=1, max_size=12)


# The autouse _state_dir fixture sets SULIS_STATE_DIR once per test (same value
# across all generated examples — no per-example reset needed, so the
# function-scoped-fixture health check is correctly suppressed).
def test_git_worktree_remove_refuses_cross_change_before_touching_git():
    # The wired primitive: a cross-change dest + the owning change_id → refused
    # BEFORE any git command runs, and the victim worktree is left intact.
    from _wpxlib import git_worktree_remove

    victim = _wt(_OTHER)                       # another change's worktree
    ok, reason = git_worktree_remove(Path.cwd(), victim, force=True, change_id=_CID)
    assert not ok and "scope-guard" in reason
    assert victim.exists()                     # untouched


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(cid=_ULID, other=_ULID, seg=_SEG)
def test_cross_change_is_never_allowed(cid, other, seg):
    # INVARIANT: a path under a DIFFERENT change's dir is never allowed.
    assume(cid != other)
    target = change_dir(other) / f"{seg}-worktree"
    ok, _ = within_change_scope(target, cid)
    assert ok is False


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(cid=_ULID, seg=_SEG)
def test_in_scope_is_always_allowed(cid, seg):
    # INVARIANT: a plain child of the change's own dir is always allowed.
    target = change_dir(cid) / f"{seg}-worktree"
    ok, _ = within_change_scope(target, cid)
    assert ok is True
