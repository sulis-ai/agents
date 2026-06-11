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


def test_create_defaults_to_origin_main(local_git_repo, run_tool):
    """No --base-branch → branches off origin/main (the trunk default, post
    dev→main cutover; pinned so the default path can't regress)."""
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
    assert result.data["base_branch"] == "main"
    assert result.data["base_ref"] == "origin/main"
    # Worktree HEAD == origin/main SHA
    assert _head_sha(wt, "HEAD") == _head_sha(local_git_repo, "origin/main")


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


def test_create_normalises_origin_prefix(local_git_repo, run_tool):
    """#105 — `--base-branch origin/dev` must resolve identically to `dev`.

    Before the fix: `base_ref = f"origin/{base_branch}"` produced the literal
    `origin/origin/dev`, so `git fetch origin origin/dev` failed (no such ref
    on remote) AND the local fallback `refs/heads/origin/dev` didn't exist,
    yielding 'base branch not found' — even though `origin/dev` is the obvious
    spelling for the same ref. Both spellings must work.
    """
    wt = local_git_repo.parent / "wp-003-wt"
    result = run_tool(
        "wpx-worktree", "create",
        "--wp", "WP-003",
        "--project", "p",
        "--branch", "feat/wp-003-z",
        "--worktree-path", str(wt),
        "--base-branch", "origin/dev",
        "--repo-root", str(local_git_repo),
    )
    assert result.ok, f"create failed: {result.error}; stderr={result.stderr}"
    # Normalised to the bare branch name + the canonical origin/<base> ref
    assert result.data["base_branch"] == "dev"
    assert result.data["base_ref"] == "origin/dev"
    assert _head_sha(wt, "HEAD") == _head_sha(local_git_repo, "origin/dev")


def test_create_normalises_refs_heads_prefix(local_git_repo, run_tool):
    """#105 (defensive) — `--base-branch refs/heads/dev` must also normalise.

    A caller scripting against `git for-each-ref` may pass the full ref name;
    treat it identically to bare `dev`.
    """
    wt = local_git_repo.parent / "wp-004-wt"
    result = run_tool(
        "wpx-worktree", "create",
        "--wp", "WP-004",
        "--project", "p",
        "--branch", "feat/wp-004-w",
        "--worktree-path", str(wt),
        "--base-branch", "refs/heads/dev",
        "--repo-root", str(local_git_repo),
    )
    assert result.ok, f"create failed: {result.error}; stderr={result.stderr}"
    assert result.data["base_branch"] == "dev"
    assert result.data["base_ref"] == "origin/dev"
    assert _head_sha(wt, "HEAD") == _head_sha(local_git_repo, "origin/dev")


# #167 — local-ahead change-branch tip
def _push(repo: Path, branch: str) -> None:
    subprocess.run(["git", "push", "-q", "-u", "origin", branch],
                   cwd=repo, check=True)


def _add_commit(repo: Path, filename: str) -> str:
    (repo / filename).write_text("y\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"add {filename}"],
                   cwd=repo, check=True)
    return _head_sha(repo, "HEAD")


def test_create_prefers_local_change_branch_tip_when_ahead_of_origin(
    local_git_repo, run_tool,
):
    """#167 — every executor in CH-01KT61 hit it: the change branch was
    integrated LOCALLY (prior WPs merged in) but not yet pushed; the create
    cut from the stale `origin/change/<branch>`, missing those merges. Now
    cmd_create must prefer the local change-branch tip when it is ahead of
    or equal to origin (the executor-hot-path case)."""
    # Set up: create change branch locally + push (origin gets initial SHA),
    # then add a local-only commit (local-ahead-of-origin).
    subprocess.run(
        ["git", "checkout", "-q", "-b", "change/create-add-payments"],
        cwd=local_git_repo, check=True,
    )
    (local_git_repo / "wp-prior.txt").write_text("first\n")
    subprocess.run(["git", "add", "."], cwd=local_git_repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "prior WP integrated"],
        cwd=local_git_repo, check=True,
    )
    _push(local_git_repo, "change/create-add-payments")
    origin_sha = _head_sha(local_git_repo, "HEAD")
    # Locally-only commit (the integrated-but-not-pushed prior WP)
    local_sha = _add_commit(local_git_repo, "wp-next.txt")
    assert local_sha != origin_sha
    # Back to dev for cleanliness
    subprocess.run(["git", "checkout", "-q", "dev"], cwd=local_git_repo, check=True)

    wt = local_git_repo.parent / "wp-005-wt"
    result = run_tool(
        "wpx-worktree", "create",
        "--wp", "WP-005",
        "--project", "p",
        "--branch", "feat/wp-005-foo",
        "--worktree-path", str(wt),
        "--base-branch", "change/create-add-payments",
        "--repo-root", str(local_git_repo),
    )
    assert result.ok, f"create failed: {result.error}; stderr={result.stderr}"
    # Local tip is the source of truth — the worktree must carry the
    # locally-integrated WP, not stop at origin's stale tip.
    assert result.data["base_ref"] == "change/create-add-payments", (
        f"expected the LOCAL ref to win; got {result.data['base_ref']!r}"
    )
    assert _head_sha(wt, "HEAD") == local_sha


def test_create_uses_origin_when_origin_change_branch_is_ahead(
    local_git_repo, run_tool,
):
    """Symmetric regression — when origin is ahead of local (someone else
    pushed), the create must still use `origin/<branch>` so the worktree
    cuts off the freshest shared tip."""
    # Set up: create change branch, push, then ADVANCE origin via a second
    # clone — local stays behind.
    subprocess.run(
        ["git", "checkout", "-q", "-b", "change/create-other-foo"],
        cwd=local_git_repo, check=True,
    )
    (local_git_repo / "seed.txt").write_text("x\n")
    subprocess.run(["git", "add", "."], cwd=local_git_repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"],
        cwd=local_git_repo, check=True,
    )
    _push(local_git_repo, "change/create-other-foo")

    # Advance origin by pushing a new commit from a side clone.
    side = local_git_repo.parent / "_side_clone"
    subprocess.run(
        ["git", "clone", "-q", str(local_git_repo.parent / "_origin.git"),
         str(side)], check=True,
    )
    subprocess.run(["git", "config", "user.email", "side@example.com"],
                   cwd=side, check=True)
    subprocess.run(["git", "config", "user.name", "Side"], cwd=side, check=True)
    subprocess.run(
        ["git", "checkout", "-q", "-b", "change/create-other-foo",
         "origin/change/create-other-foo"],
        cwd=side, check=True,
    )
    (side / "advance.txt").write_text("y\n")
    subprocess.run(["git", "add", "."], cwd=side, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "advance origin"],
        cwd=side, check=True,
    )
    subprocess.run(
        ["git", "push", "-q", "origin", "change/create-other-foo"],
        cwd=side, check=True,
    )
    # Local hasn't fetched yet — wpx-worktree's fetch will pull the new tip
    # into origin/<branch> and the resolver must prefer origin (it's ahead).
    subprocess.run(["git", "checkout", "-q", "dev"], cwd=local_git_repo, check=True)

    wt = local_git_repo.parent / "wp-006-wt"
    result = run_tool(
        "wpx-worktree", "create",
        "--wp", "WP-006",
        "--project", "p",
        "--branch", "feat/wp-006-foo",
        "--worktree-path", str(wt),
        "--base-branch", "change/create-other-foo",
        "--repo-root", str(local_git_repo),
    )
    assert result.ok, f"create failed: {result.error}; stderr={result.stderr}"
    assert result.data["base_ref"] == "origin/change/create-other-foo", (
        f"origin was ahead; expected origin/<branch>; got "
        f"{result.data['base_ref']!r}"
    )
    assert _head_sha(wt, "HEAD") == _head_sha(
        local_git_repo, "origin/change/create-other-foo",
    )


def test_create_relative_worktree_path_anchors_to_repo_root_not_cwd(
    local_git_repo, run_tool, monkeypatch, tmp_path,
):
    """#309 — a RELATIVE --worktree-path must resolve against --repo-root (the
    TARGET change's repo), NOT the process cwd. A run-all executor passes
    `../wp-NNN-worktree`; if it anchored to the calling session's cwd (bound to
    a DIFFERENT change), the worktree would land under the wrong change's
    parent. Run from an unrelated deep cwd and assert the worktree lands beside
    the repo-root, never beside the cwd."""
    # Simulate the calling session's cwd bound to a different change, at a
    # different depth so the right/wrong resolutions are distinct paths.
    other_cwd = tmp_path / "_other_change" / "deep" / "cwd"
    other_cwd.mkdir(parents=True)
    monkeypatch.chdir(other_cwd)

    result = run_tool(
        "wpx-worktree", "create",
        "--wp", "WP-009",
        "--project", "p",
        "--branch", "feat/wp-009-rel",
        "--worktree-path", "../wp-009-rel-worktree",  # RELATIVE
        "--repo-root", str(local_git_repo),
    )
    assert result.ok, f"create failed: {result.error}; stderr={result.stderr}"

    # Correct: anchored to repo-root → local_git_repo.parent / wp-009-rel-worktree
    expected = (local_git_repo.parent / "wp-009-rel-worktree").resolve()
    # Wrong (pre-fix): anchored to cwd → other_cwd.parent / wp-009-rel-worktree
    wrong = (other_cwd.parent / "wp-009-rel-worktree").resolve()

    assert Path(result.data["worktree_path"]).resolve() == expected, (
        f"relative worktree path must anchor to repo-root; got "
        f"{result.data['worktree_path']}"
    )
    assert expected.exists()
    assert not wrong.exists(), (
        f"worktree leaked under the cwd-anchored path {wrong} (the #309 bug)"
    )
