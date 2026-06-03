"""Integration tests for the worktree-aware ship path (#56).

Covers the harden-ship-worktree-lifecycle change:
- Part 1: ship succeeds when `dev` is checked out in a SIBLING worktree (the
  exact #56 repro — the old code blind-`git checkout dev` in repo_root and
  hit git's same-branch-one-worktree fatal).
- Part 3: the squash-commit message is the Conventional-Commit `{primitive}:
  {slug}` with the change intent + co-author trailer.
- Part 2: `recreate` re-materialises a removed worktree on the kept branch.

Real git on a sandbox (the local_git_repo fixture); the tool is invoked via
the run_tool subprocess fixture, matching the lifecycle test pattern.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True,
                          text=True, check=True)


def _git(cwd, *args) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, check=True).stdout.strip()


# ─── Part 1: ship is worktree-aware (#56 primary) ─────────────────────────


def test_ship_succeeds_when_base_checked_out_in_sibling_worktree(
        local_git_repo, run_tool):
    """The exact #56 repro: the trunk `main` lives in a sibling worktree, not
    repo_root.

    The old ship path did `git checkout main` in repo_root, which git refuses
    when main is checked out elsewhere ('fatal: main is already checked out').
    The worktree-aware path performs the squash-merge in whatever worktree
    holds the base branch instead.
    """
    # Move repo_root OFF main so main is free to live in a sibling worktree.
    _run(["git", "checkout", "-q", "-b", "parking"], cwd=local_git_repo)
    main_holder = local_git_repo.parent / f"{local_git_repo.name}-main-holder"
    _run(["git", "worktree", "add", "-q", str(main_holder), "main"],
         cwd=local_git_repo)

    # Start a change (branches off main) + add a commit on it. `start`
    # returns the co-located worktree path; commit the work there.
    start_result = run_tool("sulis-change", "start",
                            "--repo-root", str(local_git_repo),
                            "--slug", "worktree-aware-ship", "--primitive", "feat")
    change_wt = Path(start_result.data["worktree_path"])
    (change_wt / "feature.txt").write_text("the feature\n")
    _run(["git", "add", "feature.txt"], cwd=change_wt)
    _run(["git", "commit", "-q", "-m", "feat: the feature"], cwd=change_wt)

    # Ship — must NOT hit the #56 fatal.
    result = run_tool("sulis-change", "finish",
                      "--repo-root", str(local_git_repo),
                      "--slug", "worktree-aware-ship", "--primitive", "feat",
                      "--merge")
    assert result.ok, f"ship failed (the #56 regression): {result.stderr}"
    assert result.data["outcome"]["mode"] == "merge"
    # The merge ran in the main-holding worktree, not repo_root.
    assert result.data["outcome"]["merged_in"] == str(main_holder)
    # The work landed on main (verify in the holder).
    assert (main_holder / "feature.txt").exists()


# ─── Part 3: Conventional-Commit squash message ───────────────────────────


def test_squash_commit_message_is_conventional(local_git_repo, run_tool):
    """The squash commit is `{primitive}: {slug}` + intent body + co-author,
    not the old hardcoded `feat(change/...): squash-merge change/...`."""
    start_result = run_tool(
        "sulis-change", "start",
        "--repo-root", str(local_git_repo),
        "--slug", "tidy-the-login-form", "--primitive", "fix",
        "--intent", "Stop the login form double-submitting on Enter.")
    change_wt = Path(start_result.data["worktree_path"])
    (change_wt / "login.txt").write_text("fixed\n")
    _run(["git", "add", "login.txt"], cwd=change_wt)
    _run(["git", "commit", "-q", "-m", "wip"], cwd=change_wt)

    result = run_tool("sulis-change", "finish",
                      "--repo-root", str(local_git_repo),
                      "--slug", "tidy-the-login-form", "--primitive", "fix",
                      "--merge")
    assert result.ok, result.stderr

    msg = _git(local_git_repo, "log", "-1", "--format=%B", "main")
    assert msg.splitlines()[0] == "fix: tidy-the-login-form"
    assert "Stop the login form double-submitting on Enter." in msg
    assert "Co-Authored-By: Claude Opus 4.7" in msg
    # The old hardcoded shape is gone.
    assert "squash-merge" not in msg


# ─── Part 2: recreate ─────────────────────────────────────────────────────


def test_recreate_restores_removed_worktree_on_branch(local_git_repo,
                                                       run_tool):
    """After ship removes the worktree, `recreate` brings it back on the kept
    branch (attached → founder can resume work)."""
    start = run_tool("sulis-change", "start",
                     "--repo-root", str(local_git_repo),
                     "--slug", "recreate-me", "--primitive", "feat")
    handle = start.data["handle"]
    # Commit the work in the worktree `start` created (co-located path).
    start_wt = Path(start.data["worktree_path"])
    (start_wt / "work.txt").write_text("shipped work\n")
    _run(["git", "add", "work.txt"], cwd=start_wt)
    _run(["git", "commit", "-q", "-m", "feat: work"], cwd=start_wt)

    ship = run_tool("sulis-change", "finish",
                    "--repo-root", str(local_git_repo),
                    "--slug", "recreate-me", "--primitive", "feat", "--merge")
    assert ship.data["archived"]["worktree_removed"] is True
    assert not start_wt.exists()

    # Recreate by handle.
    rec = run_tool("sulis-change", "recreate",
                   "--repo-root", str(local_git_repo), "--handle", handle)
    assert rec.ok, rec.stderr
    assert rec.data["recreated"] is True
    assert rec.data["detached"] is False  # on the kept branch
    # `recreate` reports where it re-materialised the worktree.
    change_wt = Path(rec.data["worktree"])
    assert change_wt.exists()
    assert (change_wt / ".git").exists()
    # It's on the change branch, with the shipped work present.
    assert _git(change_wt, "branch", "--show-current") == "change/feat-recreate-me"
    assert (change_wt / "work.txt").exists()


def test_recreate_detaches_at_shipped_sha_when_branch_gone(local_git_repo,
                                                           run_tool):
    """When the branch has been removed, `recreate` falls back to a detached
    worktree at the pinned shipped_sha — the reason we record it (#56 Part 2).
    """
    start = run_tool("sulis-change", "start",
                     "--repo-root", str(local_git_repo),
                     "--slug", "pinned-state", "--primitive", "feat")
    handle = start.data["handle"]
    # Commit the work in the worktree `start` created (co-located path).
    start_wt = Path(start.data["worktree_path"])
    (start_wt / "pinned.txt").write_text("the pinned content\n")
    _run(["git", "add", "pinned.txt"], cwd=start_wt)
    _run(["git", "commit", "-q", "-m", "feat: pinned work"], cwd=start_wt)

    ship = run_tool("sulis-change", "finish",
                    "--repo-root", str(local_git_repo),
                    "--slug", "pinned-state", "--primitive", "feat", "--merge")
    shipped_sha = ship.data["archived"]["shipped_sha"]
    assert not start_wt.exists()

    # Now delete the local branch (simulating later cleanup) — the pinned
    # shipped_sha is the only handle on the exact shipped state.
    _run(["git", "branch", "-D", "change/feat-pinned-state"], cwd=local_git_repo)

    rec = run_tool("sulis-change", "recreate",
                   "--repo-root", str(local_git_repo), "--handle", handle)
    assert rec.ok, rec.stderr
    assert rec.data["recreated"] is True
    assert rec.data["detached"] is True
    assert rec.data["ref"] == shipped_sha
    # `recreate` reports where it re-materialised the worktree.
    change_wt = Path(rec.data["worktree"])
    assert change_wt.exists()
    # The exact shipped content is restored, at the pinned sha.
    assert (change_wt / "pinned.txt").read_text() == "the pinned content\n"
    assert _git(change_wt, "rev-parse", "HEAD") == shipped_sha


def test_recreate_is_noop_when_worktree_present(local_git_repo, run_tool):
    """`recreate` on a change whose worktree still exists is a safe no-op."""
    start = run_tool("sulis-change", "start",
                     "--repo-root", str(local_git_repo),
                     "--slug", "still-here", "--primitive", "feat")
    handle = start.data["handle"]
    rec = run_tool("sulis-change", "recreate",
                   "--repo-root", str(local_git_repo), "--handle", handle)
    assert rec.ok, rec.stderr
    assert rec.data["recreated"] is False
    assert "already exists" in rec.data["reason"]


# ─── Part 4: slug de-doubling ─────────────────────────────────────────────


def test_start_does_not_double_primitive_in_branch(local_git_repo, run_tool):
    """`start --primitive fix --slug fix-the-login-bug` → change/fix-the-login-bug,
    NOT change/fix-fix-the-login-bug (the doubling the founder kept hitting)."""
    result = run_tool("sulis-change", "start",
                      "--repo-root", str(local_git_repo),
                      "--slug", "fix-the-login-bug", "--primitive", "fix")
    assert result.ok, result.stderr
    assert result.data["branch"] == "change/fix-the-login-bug"
    assert result.data["slug"] == "the-login-bug"
    # The worktree lives at the co-located path `start` returns.
    wt = Path(result.data["worktree_path"])
    assert wt.exists()
