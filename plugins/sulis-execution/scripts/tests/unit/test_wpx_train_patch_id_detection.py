"""Unit tests for v0.15.3 — patch-id-already-applied detection.

Tests both the detector (`detect_already_applied_patches`) and the new
`PatchesAlreadyAppliedError` exception raised by `rebase_branch_in_clone`
when patches are already in base history.

These tests use monkeypatching to control `_run` output rather than
running real git operations — fast + deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts dir to path so we can import _wpxlib
SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

import _wpxlib  # noqa: E402
from _wpxlib import (  # noqa: E402
    PatchesAlreadyAppliedError,
    detect_already_applied_patches,
    rebase_branch_in_clone,
)


# ─── detect_already_applied_patches ───────────────────────────────────────


def test_detect_returns_empty_when_no_patches_already_applied(
    tmp_path, monkeypatch,
):
    """`git cherry` returning only `+` lines → empty result list."""
    def fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "cherry"]:
            return 0, "+ abc12345abc12345abc12345abc12345abc12345\n+ def67890def67890def67890def67890def67890\n", ""
        return 1, "", "unexpected"

    monkeypatch.setattr(_wpxlib, "_run", fake_run)
    result = detect_already_applied_patches(tmp_path, "dev", "feat/wp-001")
    assert result == []


def test_detect_returns_already_applied_shas(tmp_path, monkeypatch):
    """`git cherry` returning `- <sha>` lines → those SHAs returned."""
    def fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "cherry"]:
            # Two already-applied, one not-yet-applied
            return 0, (
                "- abc12345abc12345abc12345abc12345abc12345\n"
                "- def67890def67890def67890def67890def67890\n"
                "+ aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            ), ""
        return 1, "", "unexpected"

    monkeypatch.setattr(_wpxlib, "_run", fake_run)
    result = detect_already_applied_patches(tmp_path, "dev", "feat/wp-001")
    assert len(result) == 2
    assert "abc12345abc12345abc12345abc12345abc12345" in result
    assert "def67890def67890def67890def67890def67890" in result


def test_detect_raises_on_git_cherry_failure(tmp_path, monkeypatch):
    """If `git cherry` returns non-zero, propagate as RuntimeError."""
    def fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "cherry"]:
            return 1, "", "fatal: bad revision"
        return 0, "", ""

    monkeypatch.setattr(_wpxlib, "_run", fake_run)
    with pytest.raises(RuntimeError, match="git cherry failed"):
        detect_already_applied_patches(tmp_path, "dev", "feat/wp-001")


def test_detect_handles_empty_output(tmp_path, monkeypatch):
    """Empty `git cherry` output → empty result list (no patches at all)."""
    def fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "cherry"]:
            return 0, "", ""
        return 1, "", ""

    monkeypatch.setattr(_wpxlib, "_run", fake_run)
    assert detect_already_applied_patches(tmp_path, "dev", "feat/wp-001") == []


# ─── PatchesAlreadyAppliedError ───────────────────────────────────────────


def test_exception_carries_branch_and_shas():
    """Error stores branch + base_branch + applied_shas for caller use."""
    exc = PatchesAlreadyAppliedError(
        branch="feat/wp-001",
        base_branch="dev",
        applied_shas=["abc123", "def456"],
    )
    assert exc.branch == "feat/wp-001"
    assert exc.base_branch == "dev"
    assert exc.applied_shas == ["abc123", "def456"]
    assert "2 patch(es)" in str(exc)
    assert "feat/wp-001" in str(exc)
    assert "dev" in str(exc)


def test_exception_is_runtime_error_subclass():
    """Existing rebase-failure handling catches via `except RuntimeError`."""
    exc = PatchesAlreadyAppliedError("feat/x", "dev", ["abc123"])
    assert isinstance(exc, RuntimeError)


# ─── rebase_branch_in_clone integration ───────────────────────────────────


def test_rebase_raises_patches_already_applied_before_attempting_rebase(
    tmp_path, monkeypatch,
):
    """When `git cherry` reports already-applied patches, rebase should
    raise PatchesAlreadyAppliedError BEFORE running `git rebase` (so the
    rebase doesn't silently produce empty output)."""
    rebase_called = []

    def fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "fetch"]:
            return 0, "", ""
        if cmd[:2] == ["git", "rev-parse"]:
            return 0, "preshapreshapreshapreshapreshapresha111\n", ""
        if cmd[:2] == ["git", "cherry"]:
            # Branch has 2 patches; one already in base
            return 0, (
                "- abc12345abc12345abc12345abc12345abc12345\n"
                "+ def67890def67890def67890def67890def67890\n"
            ), ""
        if cmd[:2] == ["git", "rebase"]:
            rebase_called.append(cmd)
            return 0, "", ""
        if cmd[:2] == ["git", "checkout"]:
            return 0, "", ""
        return 1, "", f"unexpected: {cmd}"

    monkeypatch.setattr(_wpxlib, "_run", fake_run)

    with pytest.raises(PatchesAlreadyAppliedError) as exc_info:
        rebase_branch_in_clone(
            tmp_path, "feat/wp-001", "ontoshaontoshaontoshaonto",
            base_branch="dev",
        )
    assert exc_info.value.branch == "feat/wp-001"
    assert exc_info.value.base_branch == "dev"
    assert "abc12345abc12345abc12345abc12345abc12345" in exc_info.value.applied_shas
    # Critical: rebase must NOT have been attempted
    assert rebase_called == []


def test_rebase_proceeds_normally_when_no_patches_already_applied(
    tmp_path, monkeypatch,
):
    """Detection should NOT fire when `git cherry` reports only `+` lines."""
    rebase_called = []
    push_called = []

    def fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "fetch"]:
            return 0, "", ""
        if cmd[:2] == ["git", "rev-parse"]:
            return 0, "preshapreshapreshapreshapreshapresha111\n", ""
        if cmd[:2] == ["git", "cherry"]:
            return 0, "+ aaa\n+ bbb\n", ""
        if cmd[:2] == ["git", "checkout"]:
            return 0, "", ""
        if cmd[:2] == ["git", "rebase"] and cmd[2] != "--abort":
            rebase_called.append(cmd)
            return 0, "", ""
        if cmd[:2] == ["git", "push"]:
            push_called.append(cmd)
            return 0, "", ""
        return 1, "", f"unexpected: {cmd}"

    monkeypatch.setattr(_wpxlib, "_run", fake_run)
    # rev-parse HEAD at end returns the new SHA
    original_fake = fake_run

    def fake_run_with_head(cmd, cwd=None, timeout=60):
        if cmd[:3] == ["git", "rev-parse", "HEAD"]:
            return 0, "newshanewshanewshanewshanewshanewsha\n", ""
        return original_fake(cmd, cwd, timeout)

    monkeypatch.setattr(_wpxlib, "_run", fake_run_with_head)

    result = rebase_branch_in_clone(
        tmp_path, "feat/wp-001", "ontoshaontoshaontoshaonto",
        base_branch="dev",
    )
    assert rebase_called  # rebase was attempted
    assert push_called    # push was attempted
    assert result == "newshanewshanewshanewshanewshanewsha"


def test_rebase_uses_explicit_base_branch_parameter(tmp_path, monkeypatch):
    """`base_branch` parameter should be used in fetch + cherry calls.

    Regression: prior to v0.15.3, `rebase_branch_in_clone` hardcoded
    'dev' even though `wpx-train --base-branch` exists. Detection must
    use the right base branch, not always 'dev'.
    """
    fetch_targets = []
    cherry_args = []

    def fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "fetch"] and len(cmd) > 3:
            # cmd[3] is the refspec like 'dev:refs/remotes/origin/dev'
            fetch_targets.append(cmd[3])
            return 0, "", ""
        if cmd[:2] == ["git", "rev-parse"]:
            return 0, "presha\n", ""
        if cmd[:2] == ["git", "cherry"]:
            cherry_args.append(cmd[2:])
            return 0, "", ""  # empty → no patches already applied
        if cmd[:2] == ["git", "checkout"]:
            return 0, "", ""
        if cmd[:2] == ["git", "rebase"] and cmd[2] != "--abort":
            return 0, "", ""
        if cmd[:2] == ["git", "push"]:
            return 0, "", ""
        if cmd[:3] == ["git", "rev-parse", "HEAD"]:
            return 0, "newsha\n", ""
        return 1, "", f"unexpected: {cmd}"

    monkeypatch.setattr(_wpxlib, "_run", fake_run)

    rebase_branch_in_clone(
        tmp_path, "feat/wp-001", "ontosha",
        base_branch="change/feat-payments",
    )
    # Verify fetch targeted the change branch, not 'dev'
    assert any("change/feat-payments" in t for t in fetch_targets)
    # Verify git cherry compared against change branch
    assert ["origin/change/feat-payments", "origin/feat/wp-001"] in cherry_args
