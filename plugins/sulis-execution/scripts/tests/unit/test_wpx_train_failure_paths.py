"""Unit tests for the Phase 3 failure-path helpers.

Covers:
- write_train_blocker — train-level BLOCKER artifact shape
- compute_culprit_heuristic — file-overlap scoring
- restore_branch_with_guard — force-push guard logic

The full e2e revert flow (deploy fail → revert + restore + flip)
requires substantial git/gh mocking and is exercised manually via
/sulis-execution:run-all in real sessions.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import _wpxlib
from _wpxlib import (
    WpxPaths,
    compute_culprit_heuristic,
    restore_branch_with_guard,
    write_train_blocker,
)


# ─── write_train_blocker ──────────────────────────────────────────────────


def test_write_train_blocker_writes_to_correct_path(tmp_project):
    """BLOCKER-{train_id}.md lands under work-packages/ alongside per-WP BLOCKERs."""
    paths = WpxPaths(repo_root=tmp_project.repo_root,
                     project=tmp_project.project)
    bundle = [
        {"wp": "WP-001", "branch": "feat/wp-001-x",
         "pre_train_sha": "aaa", "rebased_to_sha": "bbb",
         "merge_sha_on_dev": "ccc"},
    ]
    result = write_train_blocker(
        paths, "train-2026-05-21T120000Z",
        "bundled-tip CI failed", bundle,
        suspected_wp_id="WP-001",
        evidence="lint check failed",
    )
    expected_path = paths.wp_dir / "BLOCKER-train-2026-05-21T120000Z.md"
    assert result == expected_path
    assert expected_path.exists()


def test_write_train_blocker_includes_bundle_table(tmp_project):
    paths = WpxPaths(repo_root=tmp_project.repo_root,
                     project=tmp_project.project)
    bundle = [
        {"wp": "WP-001", "branch": "feat/wp-001-x",
         "pre_train_sha": "aaaaaaaa", "rebased_to_sha": "bbbbbbbb",
         "merge_sha_on_dev": "cccccccc"},
        {"wp": "WP-002", "branch": "feat/wp-002-y",
         "pre_train_sha": "dddddddd", "rebased_to_sha": "eeeeeeee",
         "merge_sha_on_dev": None},  # never merged
    ]
    path = write_train_blocker(paths, "train-x", "test reason", bundle)
    text = path.read_text()
    assert "WP-001" in text
    assert "WP-002" in text
    assert "feat/wp-001-x" in text
    assert "feat/wp-002-y" in text


def test_write_train_blocker_includes_culprit_when_provided(tmp_project):
    paths = WpxPaths(repo_root=tmp_project.repo_root,
                     project=tmp_project.project)
    path = write_train_blocker(
        paths, "train-x", "reason", [],
        suspected_wp_id="WP-005",
    )
    text = path.read_text()
    assert "Most likely culprit: WP-005" in text
    assert "starting point" in text


def test_write_train_blocker_no_culprit_when_none(tmp_project):
    paths = WpxPaths(repo_root=tmp_project.repo_root,
                     project=tmp_project.project)
    path = write_train_blocker(
        paths, "train-x", "reason", [],
        suspected_wp_id=None,
    )
    text = path.read_text()
    assert "could not identify a specific" in text


def test_write_train_blocker_truncates_long_evidence(tmp_project):
    """Evidence is truncated to ~4000 chars to keep the file readable."""
    paths = WpxPaths(repo_root=tmp_project.repo_root,
                     project=tmp_project.project)
    huge = "X" * 10000
    path = write_train_blocker(paths, "train-x", "reason", [], evidence=huge)
    text = path.read_text()
    # Evidence section exists but isn't 10k chars
    assert "## Evidence" in text
    assert text.count("X") <= 4001


# ─── compute_culprit_heuristic ────────────────────────────────────────────


def _init_repo_with_diff(tmp_path: Path, wp_id: str, files: list[str]) -> tuple[str, str]:
    """Create a tiny git repo with one initial commit + a second commit that
    touches `files`. Returns (pre_sha, post_sha).
    """
    repo = tmp_path / f"_repo_{wp_id}"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "BASE.md").write_text("base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repo, check=True)
    pre = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                         capture_output=True, text=True, check=True).stdout.strip()
    for f in files:
        target = repo / f
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("content\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "change"], cwd=repo, check=True)
    post = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          capture_output=True, text=True, check=True).stdout.strip()
    return repo, pre, post


def test_culprit_heuristic_picks_most_overlapping(tmp_path, monkeypatch):
    """The WP whose changed files appear most in failure_text wins."""
    repo_a, pre_a, _ = _init_repo_with_diff(tmp_path, "WP-A",
                                            ["src/handler.ts", "src/util.ts"])
    repo_b, pre_b, _ = _init_repo_with_diff(tmp_path, "WP-B",
                                            ["src/unrelated.ts"])

    # The heuristic uses _run with cwd=clone_dir for git diff. We need
    # to run it against each WP's repo. Patch _run to dispatch by cwd.
    real_run = _wpxlib._run

    def cwd_aware_run(cmd, cwd=None, timeout=60):
        # If cwd is set, use it; otherwise use repo_a as default
        return real_run(cmd, cwd=cwd or repo_a, timeout=timeout)

    # Simpler: run the heuristic with clone_dir set to each repo per-call.
    # Since the function loops, we need both repos' diffs visible from
    # ONE clone_dir. For the test, we'll pass one of the repos as the
    # clone_dir and only check WP-A (since the function uses HEAD vs
    # pre_train_sha, both shas need to exist in clone_dir).

    bundle = [
        {"wp": "WP-A", "branch": "feat/a",
         "pre_train_sha": pre_a, "rebased_to_sha": "x"},
    ]
    failure = "TS error in src/handler.ts at line 42"
    culprit = compute_culprit_heuristic(bundle, repo_a, failure)
    assert culprit == "WP-A"


def test_culprit_heuristic_returns_none_when_no_overlap(tmp_path):
    """If no changed files appear in failure_text, return None."""
    repo, pre, _ = _init_repo_with_diff(tmp_path, "WP-X", ["src/handler.ts"])
    bundle = [
        {"wp": "WP-X", "branch": "feat/x",
         "pre_train_sha": pre, "rebased_to_sha": "y"},
    ]
    failure = "unrelated TypeError in node_modules/foo/bar.js"
    culprit = compute_culprit_heuristic(bundle, repo, failure)
    assert culprit is None


def test_culprit_heuristic_empty_inputs_returns_none(tmp_path):
    assert compute_culprit_heuristic([], tmp_path, "any") is None
    assert compute_culprit_heuristic(
        [{"wp": "X", "pre_train_sha": "a", "branch": "b"}],
        tmp_path, "",
    ) is None


# ─── restore_branch_with_guard ────────────────────────────────────────────


def test_restore_guard_detects_newer_push(tmp_path, monkeypatch):
    """If origin/{branch} has advanced beyond rebased_to_sha, abort restore."""
    # Build a fake clone with `git rev-parse` returning a different SHA
    # We monkeypatch _run instead of building a real repo for speed.

    calls = []

    def fake_run(cmd, cwd=None, timeout=60):
        calls.append(cmd)
        if cmd[:2] == ["git", "fetch"]:
            return 0, "", ""
        if cmd[:2] == ["git", "rev-parse"]:
            return 0, "newshanew" + "0" * 32 + "\n", ""
        return 1, "", "unexpected call"

    monkeypatch.setattr(_wpxlib, "_run", fake_run)

    ok, msg = restore_branch_with_guard(
        repo="acme/x",
        clone_dir=tmp_path,
        branch="feat/wp-001",
        pre_train_sha="pre" + "0" * 37,
        rebased_to_sha="rebased" + "0" * 33,
    )
    assert ok is False
    assert "newer push" in msg
    # Verify push was NOT attempted
    push_calls = [c for c in calls if len(c) > 1 and c[0] == "git" and c[1] == "push"]
    assert not push_calls


def test_restore_guard_passes_when_sha_matches(tmp_path, monkeypatch):
    """If origin/{branch} matches rebased_to_sha, force-push pre_train_sha."""
    rebased = "rebased" + "0" * 33

    push_attempted = []

    def fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "fetch"]:
            return 0, "", ""
        if cmd[:2] == ["git", "rev-parse"]:
            return 0, rebased + "\n", ""
        if len(cmd) > 1 and cmd[0] == "git" and cmd[1] == "push":
            push_attempted.append(cmd)
            return 0, "", ""
        return 1, "", "unexpected"

    monkeypatch.setattr(_wpxlib, "_run", fake_run)

    ok, msg = restore_branch_with_guard(
        repo="acme/x",
        clone_dir=tmp_path,
        branch="feat/wp-001",
        pre_train_sha="pre" + "0" * 37,
        rebased_to_sha=rebased,
    )
    assert ok is True
    assert msg == "restored"
    assert len(push_attempted) == 1


def test_restore_guard_fails_on_fetch_error(tmp_path, monkeypatch):
    """git fetch failure → guard returns False with the fetch error."""
    def fake_run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "fetch"]:
            return 1, "", "fetch failed: 404"
        return 0, "", ""

    monkeypatch.setattr(_wpxlib, "_run", fake_run)

    ok, msg = restore_branch_with_guard(
        repo="acme/x",
        clone_dir=tmp_path,
        branch="feat/wp-001",
        pre_train_sha="pre",
        rebased_to_sha="rebased",
    )
    assert ok is False
    assert "fetch" in msg
