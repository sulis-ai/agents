"""Tests for `wpx-worktree create --base-branch` (L-04).

Before L-04, cmd_create hardcoded `origin/dev`: it fetched origin/dev, rev-
parsed origin/dev, and branched the worktree off origin/dev. A CW-04 change
flow (`change/{primitive}-{slug}`) has its work on a LOCAL change branch that
origin may not have yet, so every per-WP worktree needed a manual
`git worktree add -b … origin/change/…` — ~10 hand-fixups during the cockpit
run.

L-04 adds `--base-branch` (default `dev`) and resolves it robustly:
  * a LOCAL branch (a `change/*` branch lives here) → branch off it, NO fetch;
  * any other base → fetch origin/<base>, branch off origin/<base>.

These tests use a real local git repo (git is fast + deterministic) and drive
the CLI through `run_tool`, asserting the worktree's HEAD lands on the right
base.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _head_sha(repo: Path, ref: str) -> str:
    out = subprocess.run(
        ["git", "rev-parse", ref], cwd=repo, capture_output=True, text=True,
    )
    return out.stdout.strip()


def _commit_on_branch(repo: Path, branch: str, filename: str) -> str:
    """Create `branch` off current HEAD, add a commit, return its SHA."""
    subprocess.run(["git", "checkout", "-q", "-b", branch], cwd=repo, check=True)
    (repo / filename).write_text("x\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"on {branch}"], cwd=repo, check=True)
    sha = _head_sha(repo, "HEAD")
    subprocess.run(["git", "checkout", "-q", "dev"], cwd=repo, check=True)
    return sha


def test_create_defaults_to_origin_dev(local_git_repo, run_tool):
    """No --base-branch → branches off origin/dev (the pre-L-04 behaviour,
    pinned so the default path can't regress)."""
    wt = local_git_repo.parent / "wp-001-wt"
    result = run_tool(
        "wpx-worktree", "create",
        "--wp", "WP-001",
        "--project", "p",
        "--branch", "feat/wp-001-x",
        "--worktree-path", str(wt),
        "--repo-root", str(local_git_repo),
    )
    assert result.ok, f"create failed: {result.error}; stderr={result.stderr}"
    assert result.data["base_branch"] == "dev"
    assert result.data["base_ref"] == "origin/dev"
    # Worktree HEAD == origin/dev SHA
    assert _head_sha(wt, "HEAD") == _head_sha(local_git_repo, "origin/dev")


def test_create_off_local_change_branch(local_git_repo, run_tool):
    """--base-branch change/foo-bar falls back to the LOCAL ref when origin
    doesn't have it (the CW-04 mid-change case — no origin push needed).

    The change branch carries a commit that origin does NOT have — fetching
    origin/change/foo-bar fails (no such remote ref), so cmd_create falls back
    to the local branch. Asserting the worktree HEAD equals the local change-
    branch tip proves the fallback works."""
    change_sha = _commit_on_branch(
        local_git_repo, "change/create-foo-bar", "feature.txt",
    )
    # Deliberately do NOT push change/* to origin.
    wt = local_git_repo.parent / "wp-002-wt"
    result = run_tool(
        "wpx-worktree", "create",
        "--wp", "WP-002",
        "--project", "p",
        "--branch", "feat/wp-002-y",
        "--worktree-path", str(wt),
        "--base-branch", "change/create-foo-bar",
        "--repo-root", str(local_git_repo),
    )
    assert result.ok, f"create failed: {result.error}; stderr={result.stderr}"
    assert result.data["base_branch"] == "change/create-foo-bar"
    assert result.data["base_ref"] == "change/create-foo-bar"  # local, not origin/
    assert result.data["dev_sha_at_creation"] == change_sha
    assert _head_sha(wt, "HEAD") == change_sha
