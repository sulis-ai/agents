"""Cancellation-idempotency tests for the discover-project skill.

UC-005 / MUC-002: a SIGINT mid-flow leaves no partial state. The
discovery flow's atomic-write contract (write-to-tmp + fsync +
``os.replace``) plus the SIGINT handler's `.tmp` sweep on receipt
plus the pre-flight sweep at the next session's startup compose to
the "no partial entity persists" invariant.

Two tests (WP-010 §Definition of Done — Red):

1. ``test_sigint_during_ask_phase_leaves_no_partial_state``: simulate
   a SIGINT delivered while the composition root is gathering the
   founder's answers in the Ask phase. Assert ``.sulis/projects/``
   contains no ``.jsonld`` and no ``.tmp`` files.
2. ``test_re_run_after_cancellation_is_first_time_outcome``: after a
   simulated cancellation, the next discovery run produces the same
   outcome a first-time run would (NFR-003 deterministic re-run).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from _discovery import run_discovery_headless
from _discovery.inferrer import NullConfigurationInferrer
from _discovery.minter import stale_tmp_sweep
from _discovery.verifier import DriftVerifyResult


def _fake_verify_pass(entity_path: Path) -> DriftVerifyResult:
    """No-op verifier for cancellation tests. The Verify-phase contract
    against the real drift detector is exercised in
    ``test_discovery_verifier.py``; here we focus on cancellation
    semantics, not drift behaviour."""
    return DriftVerifyResult(ok=True, exit_code=0, stderr="")


def _make_minimal_git_repo(
    path: Path,
    *,
    remote_url: str = "git@github.com:acme/cancel-test.git",
) -> None:
    """Initialise ``path`` as a minimal git repo with one commit + remote.

    Hand-rolled local helper rather than importing the e2e module's
    fixture — keeps the cancellation tests' dependency surface minimal
    (this file is invoked by `os.fork()`-style subprocess shapes in
    CI, and we don't want a heavy import graph).
    """
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=path, check=True, timeout=10,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path, check=True, timeout=10,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test Runner"],
        cwd=path, check=True, timeout=10,
    )
    (path / "README.md").write_text("# fixture\n")
    subprocess.run(
        ["git", "add", "-A"], cwd=path, check=True, timeout=10,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=path, check=True, timeout=10,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", remote_url],
        cwd=path, check=True, timeout=10,
    )


def _patch_consuming_repo_root(
    monkeypatch: pytest.MonkeyPatch, root: Path,
) -> None:
    from _discovery import minter as minter_module
    monkeypatch.setattr(
        minter_module, "consuming_repo_root", lambda: root.resolve(),
    )


# ===========================================================================
# Test 1 — SIGINT during Ask phase leaves no partial state
# ===========================================================================


def test_sigint_during_ask_phase_leaves_no_partial_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A KeyboardInterrupt mid-Ask leaves zero `.jsonld` + zero `.tmp`
    files in ``.sulis/projects/``.

    Implementation: the composition root accepts an `ask_phase_cancels`
    flag for testing — when True, the Ask phase raises
    KeyboardInterrupt mid-flow (mimicking a real Ctrl-C). The test
    asserts the post-cancel state.
    """
    repo = tmp_path / "cancel-test"
    repo.mkdir()
    _make_minimal_git_repo(repo)
    _patch_consuming_repo_root(monkeypatch, repo)

    projects_dir = repo / ".sulis" / "projects"

    with pytest.raises(KeyboardInterrupt):
        run_discovery_headless(
            repo_path=repo,
            inferrer=NullConfigurationInferrer(),
            answers={"name": "cancel-test"},
            ask_phase_cancels=True,  # test-only knob
            verifier_fn=_fake_verify_pass,
        )

    # No .jsonld present after cancellation.
    if projects_dir.exists():
        assert list(projects_dir.glob("*.jsonld")) == []
        # And no stale .tmp files either (the pre-flight sweep at the
        # next discovery run would clean these, but the contract per
        # TDD §Armor §Atomic write semantics says cancellation BEFORE
        # the atomic rename writes nothing visible).
        assert list(projects_dir.glob("*.tmp")) == []


# ===========================================================================
# Test 2 — Re-run after cancellation is first-time outcome
# ===========================================================================


def test_re_run_after_cancellation_is_first_time_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After a cancelled run, the next run produces the same outcome a
    first-time run would. NFR-003 (deterministic re-run)."""
    repo = tmp_path / "re-run"
    repo.mkdir()
    _make_minimal_git_repo(repo)
    _patch_consuming_repo_root(monkeypatch, repo)

    # First run: cancelled mid-Ask.
    with pytest.raises(KeyboardInterrupt):
        run_discovery_headless(
            repo_path=repo,
            inferrer=NullConfigurationInferrer(),
            answers={"name": "re-run"},
            ask_phase_cancels=True,
            verifier_fn=_fake_verify_pass,
        )

    # Simulate a stale .tmp from an earlier cancelled atomic-write —
    # not the in-flow Ask cancel above, but a previous session whose
    # SIGINT landed during write_text→os.replace. The pre-flight sweep
    # should remove it.
    projects_dir = repo / ".sulis" / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    stale = projects_dir / "re-run.jsonld.tmp"
    stale.write_text("partial garbage")
    assert stale.exists()

    # Second run: completes successfully.
    result = run_discovery_headless(
        repo_path=repo,
        inferrer=NullConfigurationInferrer(),
        answers={
            "name": "re-run",
            "type": "library",
            "version_files": ["README.md"],
            "description": "Second-run outcome.",
            "belongs_to_product_ref": "acme-product",
            "branch_policy": "trunk-based",
        },
        verifier_fn=_fake_verify_pass,
    )

    assert result.ok is True
    # Stale .tmp was swept; the new entity is at the expected path.
    assert not stale.exists()
    assert result.entity_path == projects_dir / "re-run.jsonld"
    assert result.entity_path.exists()

    proj = json.loads(result.entity_path.read_text())["projects"][0]
    assert proj["name"] == "re-run"


# ===========================================================================
# Test 3 — Direct contract test on stale_tmp_sweep + install_sigint_handler
# ===========================================================================


def test_stale_tmp_sweep_removes_dot_tmp_files(tmp_path: Path) -> None:
    """Direct contract check on stale_tmp_sweep (the pre-flight sweep
    primitive). Used by the composition root at session startup AND by
    the SIGINT handler."""
    projects_dir = tmp_path / ".sulis" / "projects"
    projects_dir.mkdir(parents=True)
    (projects_dir / "foo.jsonld.tmp").write_text("partial")
    (projects_dir / "bar.jsonld.tmp").write_text("partial")
    (projects_dir / "keep.jsonld").write_text("{}")

    removed = stale_tmp_sweep(projects_dir)

    assert removed == 2
    assert list(projects_dir.glob("*.tmp")) == []
    assert (projects_dir / "keep.jsonld").exists()
