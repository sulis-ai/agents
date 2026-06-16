"""WP-002 — write-roots resolver: ONE source for file-tools + sandbox (SC-E5).

These tests pin the EXTENSION of ``_file_scope`` (ADR-004): the resolved brain
dir becomes a writable root **only when it is outside the worktree** (a
relocated brain; the default in-worktree brain adds nothing), and a single pure
adapter ``sandbox_write_roots`` emits the SAME rw root set the file-tools scope
check uses — so the two consumers (L2 scope check + L3 sandbox config) cannot
drift.

Invariants pinned here:
  * relocated brain (outside worktree) → a writable root; in-worktree → none;
  * a path under ANOTHER change's ``~/.sulis/changes/{OTHER}/`` is refused;
  * ``~/.sulis/`` itself is NEVER a root (narrowest-root; #130 cross-change);
  * canonical paths (``/tmp``->``/private/tmp``) on the brain root too;
  * SINGLE SOURCE: the rw roots ``within_allowed_scope`` permits for a mutating
    op == the set ``sandbox_write_roots`` emits (drift-impossible), property-
    tested over varied repo_root + brain location.

SULIS_STATE_DIR is redirected to tmp so the change-state roots resolve under
the test dir (mirrors test_file_scope.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_state import change_dir, change_worktree_dir  # noqa: E402
from _file_scope import (  # noqa: E402
    AllowedRoots,
    resolve_allowed_roots,
    sandbox_write_roots,
    within_allowed_scope,
)

_CID = "0123456789ABCDEFGHJKMNPQRS"
_OTHER = "1ABCDEFGHJKMNPQRSTVWXYZ012"

_MUTATING = ("write", "move", "remove")


@pytest.fixture(autouse=True)
def _state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    # Ensure no ambient brain override leaks in from the host environment.
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    return tmp_path


def _mk(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


# ─── relocated brain becomes a writable root; in-worktree brain does not ─────


def test_relocated_brain_added(tmp_path, monkeypatch):
    """A brain resolved OUTSIDE the worktree (relocated) appears as a writable
    root; a write under it is allowed."""
    repo = _mk(tmp_path / "repo")
    relocated = _mk(tmp_path / "relocated-brain")
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(relocated))
    roots = resolve_allowed_roots(_CID, repo_root=repo)
    assert roots.brain_dir == relocated.resolve()
    ok, _ = within_allowed_scope(relocated / "instances" / "x.jsonld", _CID,
                                 operation="write", roots=roots)
    assert ok, "a write under the relocated brain must be allowed"


def test_in_worktree_brain_adds_no_root(tmp_path, monkeypatch):
    """An IN-WORKTREE brain → brain_dir stays None (already covered by the worktree
    root). NOTE: since #346 the DEFAULT brain is the user-level home (OUTSIDE the
    worktree — see test_default_user_level_brain_added); this test explicitly
    configures an in-worktree brain to exercise the containment branch."""
    worktree = _mk(change_worktree_dir(_CID))
    # Force an in-worktree brain via the env override (#127 resolution order).
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(worktree / ".brain" / "instances"))
    roots = resolve_allowed_roots(_CID, repo_root=worktree)
    assert roots.brain_dir is None, (
        "an in-worktree brain must add no extra root (worktree already covers it)"
    )


def test_default_user_level_brain_added(tmp_path):
    """Since #346 the DEFAULT brain is the user-level home
    ({SULIS_STATE_DIR}/.brain/instances), which is OUTSIDE the change worktree, so
    it MUST be added as a writable root — the brain-out-of-worktree case (D5/D7),
    now the live default. (No SULIS_BRAIN_BASE_DIR set: the autouse fixture clears
    it, so brain_base_dir falls to the user-level default under SULIS_STATE_DIR.)"""
    worktree = _mk(change_worktree_dir(_CID))
    roots = resolve_allowed_roots(_CID, repo_root=worktree)
    assert roots.brain_dir is not None, (
        "the user-level default brain is outside the worktree and must be a writable root"
    )
    ok, _ = within_allowed_scope(roots.brain_dir / "x.jsonld", _CID,
                                 operation="write", roots=roots)
    assert ok, "a write under the default user-level brain must be allowed"


def test_brain_dir_permitted_for_all_ops(tmp_path):
    """When set, brain_dir permits all four ops (brain is shared rw)."""
    brain = _mk(tmp_path / "brain")
    roots = AllowedRoots(
        worktree=_mk(change_worktree_dir(_CID)).resolve(),
        git_common_dir=_mk(tmp_path / "gc").resolve(),
        change_state_dir=_mk(change_dir(_CID)).resolve(),
        tools_cache_dir=None,
        creds_dir=None,
        brain_dir=brain.resolve(),
    )
    for op in ("read", *_MUTATING):
        ok, _ = within_allowed_scope(brain / "node.jsonld", _CID,
                                     operation=op, roots=roots)
        assert ok, f"brain_dir should permit {op}"


# ─── a sibling change's state is refused; ~/.sulis is never a root ───────────


def test_sibling_change_refused(tmp_path, monkeypatch):
    """A path under ANOTHER change's ~/.sulis/changes/{OTHER}/ is out of scope,
    even with a relocated brain configured."""
    repo = _mk(tmp_path / "repo")
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(_mk(tmp_path / "brain")))
    roots = resolve_allowed_roots(_CID, repo_root=repo)
    sibling = change_dir(_OTHER) / "state.json"
    for op in _MUTATING:
        ok, reason = within_allowed_scope(sibling, _CID, operation=op, roots=roots)
        assert not ok and "outside" in reason.lower(), (
            f"a sibling change's state must be refused for {op}"
        )


def test_never_whole_sulis(tmp_path, monkeypatch):
    """~/.sulis/ (the state base) itself is NEVER an allowed root — that tree
    holds OTHER changes' state. No root equals or contains the state base."""
    repo = _mk(tmp_path / "repo")
    # Relocate the brain UNDER the state base to make the trap maximally tempting.
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(_mk(tmp_path / "brain")))
    roots = resolve_allowed_roots(_CID, repo_root=repo)
    state_base = tmp_path.resolve()  # SULIS_STATE_DIR == tmp_path

    # A write directly at the state base (would let you reach sibling changes)
    # must be refused.
    ok, _ = within_allowed_scope(state_base / "anything", _CID,
                                 operation="write", roots=roots)
    assert not ok

    # Defensive: no emitted rw root IS the state base, and no emitted root
    # CONTAINS the whole state base (which would reach sibling changes).
    for emitted in sandbox_write_roots(roots):
        rp = Path(emitted).expanduser().resolve()
        assert rp != state_base, f"{rp} must not be the whole ~/.sulis state base"
        try:
            state_base.relative_to(rp)
            contains_base = True
        except ValueError:
            contains_base = False
        assert not contains_base, f"emitted root {rp} must not contain the whole state base"


# ─── canonical paths on the brain root too ───────────────────────────────────


def test_relocated_brain_canonical(tmp_path, monkeypatch):
    """The brain root is canonicalised: a brain reached via a symlinked alias
    (the /tmp->/private/tmp shape) still matches a target through its real
    path."""
    repo = _mk(tmp_path / "repo")
    real_brain = _mk(tmp_path / "real-brain")
    alias = tmp_path / "alias-brain"
    alias.symlink_to(real_brain)
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(alias))
    roots = resolve_allowed_roots(_CID, repo_root=repo)
    # brain_dir is the resolved (canonical) real path, not the alias spelling.
    assert roots.brain_dir == real_brain.resolve()
    ok, _ = within_allowed_scope(real_brain / "x.jsonld", _CID,
                                 operation="write", roots=roots)
    assert ok


def test_misconfigured_brain_at_state_base_refused(tmp_path, monkeypatch):
    """Narrowest-root, defended structurally (not just documented): if the
    brain is (mis)configured to the WHOLE ~/.sulis state base — or any ancestor
    of the per-change ``changes/`` tree — adding it as a root would let a write
    reach EVERY sibling change's state (the #130 cross-change risk ADR-004
    rejects). The resolver must refuse such a brain root (fail-closed), even
    though brain_base_dir faithfully returns the configured path."""
    from _change_state import changes_base

    repo = _mk(tmp_path / "repo")
    state_base = tmp_path.resolve()  # SULIS_STATE_DIR == tmp_path
    # The adversarial misconfiguration: brain == the whole state base.
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(state_base))
    roots = resolve_allowed_roots(_CID, repo_root=repo)
    assert roots.brain_dir is None, (
        "a brain resolving to the state base (or an ancestor of changes/) must "
        "NOT become a root — it would contain sibling changes' state"
    )
    # And a write to a sibling change's state is consequently refused.
    sibling = (changes_base() / _OTHER / "state.json")
    ok, _ = within_allowed_scope(sibling, _CID, operation="write", roots=roots)
    assert not ok


def test_unresolvable_brain_adds_no_root(tmp_path, monkeypatch):
    """Fail-closed: a brain path that cannot be canonicalised contributes no
    root (brain_dir stays None) rather than widening scope."""
    import _file_scope

    repo = _mk(tmp_path / "repo")
    monkeypatch.setattr(_file_scope, "canonical", lambda _t: None)
    roots = resolve_allowed_roots(_CID, repo_root=repo)
    assert roots.brain_dir is None


# ─── SINGLE SOURCE: file-tools rw set == sandbox emit (drift-impossible) ─────


def _mutating_rw_set(roots: AllowedRoots) -> set[Path]:
    """The canonical rw roots the file-tools permit for a mutating op."""
    return {p.resolve() for p in roots.permitted_for("write")}


def test_single_source_emits_strings(tmp_path, monkeypatch):
    """sandbox_write_roots returns sandbox allowWrite path STRINGS (not Paths),
    and the resolved set equals the file-tools mutating rw set."""
    repo = _mk(tmp_path / "repo")
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(_mk(tmp_path / "relocated-brain")))
    roots = resolve_allowed_roots(_CID, repo_root=repo)
    emitted = sandbox_write_roots(roots)
    assert isinstance(emitted, list)
    assert all(isinstance(s, str) for s in emitted)
    emitted_set = {Path(s).expanduser().resolve() for s in emitted}
    assert emitted_set == _mutating_rw_set(roots), (
        "the sandbox allowWrite set must equal the file-tools mutating rw set"
    )


_ULID = st.text(alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ", min_size=26, max_size=26)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(relocate=st.booleans())
def test_single_source_invariant(tmp_path, monkeypatch, relocate):
    """SC-E5 drift-impossible invariant, property-tested over brain location:
    for any configuration, the rw roots within_allowed_scope enforces ==
    the set sandbox_write_roots emits, and NO out-of-scope mutation is allowed.
    """
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    repo = _mk(tmp_path / "repo")
    if relocate:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(_mk(tmp_path / "brain-elsewhere")))
    roots = resolve_allowed_roots(_CID, repo_root=repo)

    # 1. set-equality between the two consumers
    emitted_set = {Path(s).expanduser().resolve() for s in sandbox_write_roots(roots)}
    assert emitted_set == _mutating_rw_set(roots)

    # 2. every emitted root is genuinely writable per the file-tools check
    for root in emitted_set:
        ok, _ = within_allowed_scope(root / "probe", _CID, operation="write", roots=roots)
        assert ok

    # 3. a different change's state dir is never in the emitted set, never writable
    other_state = change_dir(_OTHER).resolve()
    assert other_state not in emitted_set
    ok, _ = within_allowed_scope(other_state / "state.json", _CID,
                                 operation="write", roots=roots)
    assert not ok
