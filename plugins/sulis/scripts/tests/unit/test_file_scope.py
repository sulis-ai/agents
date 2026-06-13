"""L2 scope-resolver (WP-004) — multi-root, canonical, fail-closed scope decision.

These tests pin the DECISION layer (the resolver) for SC-L2.1 (in-scope ops
succeed), SC-L2.2 (out-of-scope read refused, incl. the /tmp->/private/tmp
canonical footgun), SC-L2.3 (out-of-scope write/move/remove refused — the #130
cross-worktree-deletion replay), and SC-L2.4 (traversal / symlink escape). The
tool-level I/O (success/refusal end-to-end) lands in WP-005.

The hypothesis property pins the SAFETY INVARIANT: no path outside every
allowed root is ever ok=True. SULIS_STATE_DIR is redirected to tmp so the
change-state roots resolve under the test dir.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_state import change_dir, change_worktree_dir  # noqa: E402
from _file_scope import (  # noqa: E402
    AllowedRoots,
    resolve_allowed_roots,
    within_allowed_scope,
)

_CID = "0123456789ABCDEFGHJKMNPQRS"
_OTHER = "1ABCDEFGHJKMNPQRSTVWXYZ012"

_OPERATIONS = ("read", "write", "move", "remove")


@pytest.fixture(autouse=True)
def _state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    return tmp_path


def _mk(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture()
def roots(tmp_path) -> AllowedRoots:
    """A fully-populated allowlist with every root materialised on disk.

    git-common-dir + tools-cache + creds are stood up under tmp so the
    canonical .resolve() of each is a real, distinct directory.
    """
    worktree = _mk(change_worktree_dir(_CID))
    git_common = _mk(tmp_path / "git-common" / ".git")
    state = _mk(change_dir(_CID))
    tools_cache = _mk(tmp_path / "tools-cache")
    creds = _mk(tmp_path / "creds")
    return AllowedRoots(
        worktree=worktree.resolve(),
        git_common_dir=git_common.resolve(),
        change_state_dir=state.resolve(),
        tools_cache_dir=tools_cache.resolve(),
        creds_dir=creds.resolve(),
    )


# ─── SC-L2.1 — in-scope ops succeed ─────────────────────────────────────────


@pytest.mark.parametrize("operation", _OPERATIONS)
@pytest.mark.parametrize("root_attr", ["worktree", "git_common_dir", "change_state_dir", "tools_cache_dir"])
def test_in_scope_all_ops_allowed(roots, operation, root_attr):
    root = getattr(roots, root_attr)
    target = root / "some" / "file.txt"
    ok, _ = within_allowed_scope(target, _CID, operation=operation, roots=roots)
    assert ok, f"{operation} under {root_attr} should be allowed"


def test_creds_read_allowed(roots):
    target = roots.creds_dir / "token"
    ok, _ = within_allowed_scope(target, _CID, operation="read", roots=roots)
    assert ok


@pytest.mark.parametrize("operation", ["write", "move", "remove"])
def test_creds_write_move_remove_refused(roots, operation):
    target = roots.creds_dir / "token"
    ok, reason = within_allowed_scope(target, _CID, operation=operation, roots=roots)
    assert not ok and "read" in reason.lower()


# ─── SC-L2.2 — out-of-scope read refused (incl. canonical footgun) ──────────


def test_ssh_dir_read_refused(roots):
    ok, _ = within_allowed_scope(Path.home() / ".ssh" / "id_rsa", _CID,
                                 operation="read", roots=roots)
    assert not ok


def test_sibling_change_worktree_read_refused(roots):
    sibling = change_worktree_dir(_OTHER) / "wp-006-worktree"
    ok, reason = within_allowed_scope(sibling, _CID, operation="read", roots=roots)
    assert not ok and "outside" in reason.lower()


def test_canonical_tmp_private_tmp_resolves_correctly(roots, monkeypatch):
    """The /tmp->/private/tmp footgun: an allowlist root given as an un-resolved
    /tmp path must still match a target handed in as a /tmp path, because BOTH
    sides are canonicalised. We assert the resolver canonicalises: a target
    expressed via a symlinked root resolves into scope.
    """
    # Stand up a symlinked alias to the worktree (the /tmp->/private/tmp shape:
    # a path that resolves to a different real path). A target reached through
    # the alias must still be judged in-scope, because resolve() canonicalises.
    alias_parent = roots.worktree.parent / "alias"
    alias_parent.symlink_to(roots.worktree)
    target_via_alias = alias_parent / "file.txt"
    ok, _ = within_allowed_scope(target_via_alias, _CID, operation="read", roots=roots)
    assert ok, "a target reached via a symlinked alias of an in-scope root is in-scope"


def test_canonical_unresolved_root_still_contains(tmp_path):
    """An AllowedRoots built from an UN-resolved root that points through a
    symlink still contains a target given through the real path — both sides
    are canonicalised inside the resolver (defence even if a caller forgets to
    .resolve() a root).
    """
    real = _mk(tmp_path / "real-root")
    link = tmp_path / "link-root"
    link.symlink_to(real)
    roots = AllowedRoots(
        worktree=link,  # deliberately NOT .resolve()-d
        git_common_dir=_mk(tmp_path / "gc"),
        change_state_dir=_mk(tmp_path / "st"),
        tools_cache_dir=None,
        creds_dir=None,
    )
    ok, _ = within_allowed_scope(real / "f.txt", _CID, operation="read", roots=roots)
    assert ok


# ─── SC-L2.3 — out-of-scope write/move/remove refused (#130 replay) ─────────


@pytest.mark.parametrize("operation", ["write", "move", "remove"])
def test_sibling_worktree_mutation_refused(roots, operation):
    # The #130 incident: a wp-006 worktree belonging to ANOTHER change, passed
    # to a destructive op. Must be refused at the decision layer.
    sibling = _mk(change_worktree_dir(_OTHER) / "wp-006-worktree")
    ok, reason = within_allowed_scope(sibling, _CID, operation=operation, roots=roots)
    assert not ok and "outside" in reason.lower()
    assert sibling.exists()  # decision layer never touches the FS


# ─── SC-L2.4 — traversal / symlink escape refused ───────────────────────────


def test_traversal_escape_refused(roots):
    sneaky = roots.worktree / ".." / ".." / _OTHER / "wp-006-worktree"
    for op in _OPERATIONS:
        ok, _ = within_allowed_scope(sneaky, _CID, operation=op, roots=roots)
        assert not ok


def test_symlink_escape_refused(roots, tmp_path):
    outside = _mk(tmp_path / "outside-target")
    link = roots.worktree / "escape"
    link.symlink_to(outside)  # inside-looking, resolves outside
    for op in _OPERATIONS:
        ok, _ = within_allowed_scope(link, _CID, operation=op, roots=roots)
        assert not ok


# ─── fail-closed ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_cid", ["", None, "not-a-ulid"])
def test_invalid_change_id_fails_closed(roots, bad_cid):
    ok, _ = within_allowed_scope(roots.worktree / "f", bad_cid,
                                 operation="read", roots=roots)
    assert not ok


def test_unknown_operation_fails_closed(roots):
    ok, reason = within_allowed_scope(roots.worktree / "f", _CID,
                                      operation="execute", roots=roots)
    assert not ok and "operation" in reason.lower()


def test_unresolvable_path_fails_closed(roots, monkeypatch):
    class _Boom:
        def __fspath__(self):  # Path(target) -> resolve() will blow up
            raise OSError("unresolvable")

    ok, _ = within_allowed_scope(_Boom(), _CID, operation="read", roots=roots)
    assert not ok


def test_no_matching_root_refused(roots, tmp_path):
    elsewhere = _mk(tmp_path / "completely" / "elsewhere")
    ok, _ = within_allowed_scope(elsewhere / "f", _CID, operation="read", roots=roots)
    assert not ok


def test_none_optional_roots_are_not_allowed(tmp_path):
    """tools_cache_dir/creds_dir = None contribute no allowlist entry; a path
    that would have matched them is refused."""
    roots = AllowedRoots(
        worktree=_mk(change_worktree_dir(_CID)).resolve(),
        git_common_dir=_mk(tmp_path / "gc").resolve(),
        change_state_dir=_mk(change_dir(_CID)).resolve(),
        tools_cache_dir=None,
        creds_dir=None,
    )
    # A creds-shaped path is now just an out-of-scope path.
    ok, _ = within_allowed_scope(tmp_path / "creds" / "token", _CID,
                                 operation="read", roots=roots)
    assert not ok


# ─── resolve_allowed_roots ──────────────────────────────────────────────────


def test_resolve_allowed_roots_canonicalises(tmp_path, monkeypatch):
    repo_root = _mk(tmp_path / "repo")
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    # worktree + state come from _change_state and are canonical (.resolve()-d)
    assert roots.worktree == change_worktree_dir(_CID).resolve()
    assert roots.change_state_dir == change_dir(_CID).resolve()
    # every populated root is absolute + canonical (== its own resolve())
    for attr in ("worktree", "git_common_dir", "change_state_dir"):
        p = getattr(roots, attr)
        assert p is not None and p == p.resolve()


def test_resolve_allowed_roots_invalid_cid_fails_closed(tmp_path):
    with pytest.raises((ValueError, RuntimeError)):
        resolve_allowed_roots("not-a-ulid", repo_root=tmp_path)


def test_resolve_allowed_roots_git_common_dir_from_real_repo(tmp_path):
    import subprocess

    repo = _mk(tmp_path / "repo")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    roots = resolve_allowed_roots(_CID, repo_root=repo)
    # git rev-parse --git-common-dir resolves to the repo's .git, canonicalised.
    assert roots.git_common_dir == (repo / ".git").resolve()


def test_resolve_allowed_roots_git_unavailable_falls_back(tmp_path, monkeypatch):
    # A non-git dir: git rev-parse fails → fallback to repo_root/.git (still an
    # in-repo path, never wider scope).
    repo = _mk(tmp_path / "not-a-repo")
    roots = resolve_allowed_roots(_CID, repo_root=repo)
    assert roots.git_common_dir == (repo / ".git").resolve()


def test_resolve_allowed_roots_passes_through_optional_roots(tmp_path):
    tools = _mk(tmp_path / "tc")
    creds = _mk(tmp_path / "cr")
    roots = resolve_allowed_roots(_CID, repo_root=_mk(tmp_path / "repo"),
                                  tools_cache_dir=tools, creds_dir=creds)
    assert roots.tools_cache_dir == tools.resolve()
    assert roots.creds_dir == creds.resolve()


# ─── within_allowed_scope: on-the-fly allowlist build ───────────────────────


def test_builds_allowlist_when_roots_omitted(tmp_path, monkeypatch):
    # roots=None + repo_root given → builds via resolve_allowed_roots; a target
    # in the change worktree is in-scope.
    repo = _mk(tmp_path / "repo")
    target = _mk(change_worktree_dir(_CID)) / "file.txt"
    ok, _ = within_allowed_scope(target, _CID, operation="read", repo_root=repo)
    assert ok


def test_no_roots_and_no_repo_root_fails_closed():
    ok, reason = within_allowed_scope("/anywhere", _CID, operation="read")
    assert not ok and "repo_root" in reason


def test_build_failure_fails_closed(tmp_path, monkeypatch):
    # Force resolve_allowed_roots to raise → within_allowed_scope refuses.
    import _file_scope

    def _boom(*a, **k):
        raise OSError("git exploded")

    monkeypatch.setattr(_file_scope, "resolve_allowed_roots", _boom)
    ok, reason = within_allowed_scope("/x", _CID, operation="read",
                                      repo_root=tmp_path)
    assert not ok and "cannot build allowlist" in reason


# ─── the safety invariant (property-based) ──────────────────────────────────

_ULID = st.text(alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ", min_size=26, max_size=26)
_SEG = st.text(alphabet="abcdefghijkmnpqrstuvwxyz0123456789-", min_size=1, max_size=12)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(other=_ULID, seg=_SEG, op=st.sampled_from(_OPERATIONS))
def test_path_outside_every_root_is_never_allowed(roots, other, seg, op):
    # INVARIANT: a path under a DIFFERENT change's worktree (outside every
    # allowed root for change _CID) is never allowed, for any operation.
    assume(other != _CID)
    target = change_worktree_dir(other) / f"{seg}-worktree"
    ok, _ = within_allowed_scope(target, _CID, operation=op, roots=roots)
    assert ok is False


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(seg=_SEG)
def test_in_worktree_read_always_allowed(roots, seg):
    # INVARIANT: a plain child of the worktree root is always readable.
    target = roots.worktree / f"{seg}.txt"
    ok, _ = within_allowed_scope(target, _CID, operation="read", roots=roots)
    assert ok is True
