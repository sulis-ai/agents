"""Unit tests for the HD-005 GHClient Protocol and RealGHClient adapter.

These tests verify:

1. ``RealGHClient`` satisfies the ``GHClient`` Protocol structurally
   (the Protocol is ``@runtime_checkable`` so ``isinstance`` works).
2. ``_resolve_gh(None)`` returns the module-level default; passing an
   explicit client overrides it.
3. The existing ``_gh_*`` shim helpers delegate to the GHClient surface
   when one is injected (the seam HD-002's TrainTestbed depends on).
4. The legacy ``_gh_*`` symbols remain importable (preserves
   compatibility with tests that monkeypatch them directly, e.g.
   ``test_wpx_train_partial_merge_failure.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import _wpxlib
from _wpxlib import (
    GHClient,
    RealGHClient,
    _default_gh_client,
    _gh_branch_exists,
    _gh_branch_sha,
    _gh_check_runs,
    _gh_merge,
    _gh_ref_sha,
    _resolve_gh,
    is_sha_on_branch,
)


# ─── Test 1: RealGHClient satisfies the Protocol ─────────────────────


def test_real_gh_client_satisfies_protocol():
    """``RealGHClient`` implements every GHClient method.

    Because GHClient is decorated with ``@runtime_checkable``,
    ``isinstance`` performs structural checking. A bare ``object`` does
    not satisfy the Protocol; a ``RealGHClient`` does.
    """
    assert isinstance(RealGHClient(), GHClient)
    assert not isinstance(object(), GHClient)


def test_default_gh_client_is_a_real_gh_client():
    """The module-level default is a RealGHClient — production behaviour
    is unchanged from pre-HD-005.
    """
    assert isinstance(_default_gh_client, RealGHClient)


# ─── Test 2: _resolve_gh dispatch ────────────────────────────────────


def test_resolve_gh_returns_module_default_on_none():
    assert _resolve_gh(None) is _default_gh_client


def test_resolve_gh_returns_explicit_client_when_provided():
    fake = RealGHClient()  # distinct instance, not the default
    assert _resolve_gh(fake) is fake
    assert _resolve_gh(fake) is not _default_gh_client


# ─── Test 3: shim helpers delegate to injected client ────────────────


class _StubClient:
    """Minimal GHClient implementation for shim-delegation assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def _record(self, op: str, *args, **kwargs):
        self.calls.append((op, args, kwargs))

    def check_runs(self, repo, branch):
        self._record("check_runs", repo, branch)
        return {"check_runs": []}

    def branch_sha(self, repo, branch):
        self._record("branch_sha", repo, branch)
        return "a" * 40

    def ref_sha(self, repo, ref):
        self._record("ref_sha", repo, ref)
        return "b" * 40

    def compare(self, repo, base, head):
        self._record("compare", repo, base, head)
        return {"status": "ahead"}

    def merge(self, repo, base, head, commit_message):
        self._record("merge", repo, base, head, commit_message)
        return "c" * 40

    def deploy_runs(self, repo, workflow, commit):
        self._record("deploy_runs", repo, workflow, commit)
        return []

    def delete_branch(self, repo, branch):
        self._record("delete_branch", repo, branch)

    def branch_exists(self, repo, branch):
        self._record("branch_exists", repo, branch)
        return True

    def clone(self, repo, dest):
        self._record("clone", repo, dest)
        return 0, ""


def test_gh_check_runs_delegates_to_injected_client():
    stub = _StubClient()
    result = _gh_check_runs("owner/repo", "main", gh=stub)
    assert result == {"check_runs": []}
    assert stub.calls == [("check_runs", ("owner/repo", "main"), {})]


def test_gh_branch_sha_delegates_to_injected_client():
    stub = _StubClient()
    sha = _gh_branch_sha("owner/repo", "main", gh=stub)
    assert sha == "a" * 40
    assert stub.calls[0][0] == "branch_sha"


def test_gh_ref_sha_delegates_to_injected_client():
    stub = _StubClient()
    sha = _gh_ref_sha("owner/repo", "dev", gh=stub)
    assert sha == "b" * 40
    assert stub.calls[0][0] == "ref_sha"


def test_gh_merge_delegates_to_injected_client():
    stub = _StubClient()
    sha = _gh_merge("owner/repo", base="dev", head="feat/x",
                    commit_message="m", gh=stub)
    assert sha == "c" * 40
    assert stub.calls[0][0] == "merge"


def test_gh_branch_exists_delegates_to_injected_client():
    stub = _StubClient()
    exists = _gh_branch_exists("owner/repo", "main", gh=stub)
    assert exists is True
    assert stub.calls[0][0] == "branch_exists"


def test_is_sha_on_branch_uses_compare_via_injected_client():
    """is_sha_on_branch goes through compare() — verify the call shape."""
    stub = _StubClient()
    # status="ahead" → NOT on branch
    on_branch = is_sha_on_branch("owner/repo", "deadbeef", "dev", gh=stub)
    assert on_branch is False
    assert stub.calls[0][0] == "compare"

    # Configure compare to return identical → IS on branch
    class _IdenticalStub(_StubClient):
        def compare(self, repo, base, head):
            self._record("compare", repo, base, head)
            return {"status": "identical"}

    stub2 = _IdenticalStub()
    assert is_sha_on_branch("owner/repo", "deadbeef", "dev", gh=stub2) is True


# ─── Test 4: legacy seam preserved ────────────────────────────────────


def test_legacy_gh_helpers_still_importable():
    """The pre-HD-005 ``_gh_*`` symbols remain on _wpxlib for
    backward-compat with monkeypatch-based tests.

    Verifies the seam HD-005 promised to preserve.
    """
    # All should be callable attributes of _wpxlib
    assert callable(getattr(_wpxlib, "_gh_check_runs"))
    assert callable(getattr(_wpxlib, "_gh_branch_sha"))
    assert callable(getattr(_wpxlib, "_gh_ref_sha"))
    assert callable(getattr(_wpxlib, "_gh_merge"))
    assert callable(getattr(_wpxlib, "_gh_branch_already_merged"))
    assert callable(getattr(_wpxlib, "_gh_branch_exists"))
    assert callable(getattr(_wpxlib, "_gh_deploy_runs"))
    assert callable(getattr(_wpxlib, "is_sha_on_branch"))
    assert callable(getattr(_wpxlib, "clone_repo_to_temp"))
    assert callable(getattr(_wpxlib, "_merge_squash"))
