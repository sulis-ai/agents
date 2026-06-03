"""Integration tests for sulis-change subcommands.

Uses the local_git_repo fixture (real git on a sandbox) to exercise:
- start: branch + worktree created; metadata written
- adopt: three flavours — clean / uncommitted / local-commits
- list: enumerates active changes
- status: reports SHAs + ahead/behind
- finish: merge path cleans up the worktree

All integration tests invoke the script via subprocess (matching the
existing wpx-pipeline / wpx-train test pattern).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import _wpxlib
from _wpxlib import (
    adopt_uncommitted_into_change,
    change_worktree_path,
    compose_change_branch,
    read_change_metadata,
)


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True,
                          text=True, check=True)


def _git(cwd, *args):
    """Run a git command in `cwd`, returning stripped stdout."""
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
    ).stdout.strip()


def _stash_entries(repo: Path) -> list[str]:
    """Return the messages of every stash currently on `repo`'s shared stack."""
    out = _git(repo, "stash", "list")
    return [line for line in out.splitlines() if line.strip()]


# ─── start ──────────────────────────────────────────────────────────────


def test_start_creates_branch_and_worktree(local_git_repo, run_tool):
    """`sulis-change start` creates the change branch, worktree, and metadata."""
    result = run_tool(
        "sulis-change", "start",
        "--repo-root", str(local_git_repo),
        "--slug", "introduce-payments",
        "--primitive", "create",
    )
    assert result.ok, f"start failed: stderr={result.stderr}"
    assert result.data["branch"] == "change/create-introduce-payments"
    assert result.data["primitive"] == "create"
    assert result.data["slug"] == "introduce-payments"

    # The worktree exists
    worktree_dest = Path(result.data["worktree_path"])
    assert worktree_dest.exists()
    assert (worktree_dest / ".git").exists()

    # Metadata was written
    metadata = read_change_metadata(
        worktree_dest / ".changes" / "create-introduce-payments.yaml",
    )
    assert metadata["branch"] == "change/create-introduce-payments"
    assert metadata["primitive"] == "create"


def test_start_pushes_change_branch_to_origin(local_git_repo, run_tool):
    """`sulis-change start` publishes the change branch to origin (#61).

    The integration train merges via the GitHub API, so the change branch
    (the train's --base-branch) MUST exist on origin or the first train run
    404s. `start` therefore pushes the new branch at creation. The
    local_git_repo fixture wires up a bare `origin` remote, so after `start`
    the branch must be a ref in that remote.
    """
    result = run_tool(
        "sulis-change", "start",
        "--repo-root", str(local_git_repo),
        "--slug", "publish-me",
        "--primitive", "feat",
    )
    assert result.ok, f"start failed: stderr={result.stderr}"
    branch = "change/feat-publish-me"
    assert result.data["branch"] == branch

    # The push outcome is reported in the JSON (additive field).
    assert result.data["pushed_to_origin"] is True, (
        f"start did not report pushing the branch: data={result.data}"
    )

    # The branch is a real ref on origin (the bare remote).
    ls_remote = _git(local_git_repo, "ls-remote", "origin",
                     f"refs/heads/{branch}")
    assert ls_remote, (
        f"change branch {branch} is not on origin after start — the train "
        f"will 404 on its first run. ls-remote returned empty."
    )
    assert branch in ls_remote


def test_start_degrades_gracefully_with_no_remote(tmp_path, run_tool):
    """`start` with NO origin remote still succeeds locally and reports
    `pushed_to_origin: false` without crashing (#61 graceful-degrade).

    The push is an enhancement, not a new precondition — an offline / no-remote
    repo must still get its local branch + worktree.
    """
    # A real git repo on the trunk (main), but with NO origin remote configured.
    repo = tmp_path / "_no_remote_repo"
    repo.mkdir()
    _run(["git", "init", "-q", "-b", "main"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    _run(["git", "config", "user.name", "Test"], cwd=repo)
    (repo / "README.md").write_text("# no remote\n")
    _run(["git", "add", "."], cwd=repo)
    _run(["git", "commit", "-q", "-m", "initial"], cwd=repo)

    result = run_tool(
        "sulis-change", "start",
        "--repo-root", str(repo),
        "--slug", "offline-change",
        "--primitive", "feat",
    )
    # Local branch + worktree creation still succeeds (no crash, exit 0).
    assert result.ok, f"start must not crash with no remote: stderr={result.stderr}"
    assert result.returncode == 0
    branch = "change/feat-offline-change"
    assert result.data["branch"] == branch

    # The push could not happen → reported false, not crashed.
    assert result.data["pushed_to_origin"] is False, (
        f"start should report pushed_to_origin=false with no remote: "
        f"data={result.data}"
    )

    # The local branch + worktree genuinely exist.
    worktree_dest = Path(result.data["worktree_path"])
    assert worktree_dest.exists()
    branches = _git(repo, "branch", "--list", branch)
    assert branch in branches


def test_start_rejects_existing_branch(local_git_repo, run_tool):
    """Starting twice with the same slug fails the second time."""
    run_tool("sulis-change", "start",
             "--repo-root", str(local_git_repo),
             "--slug", "feat-thing", "--primitive", "feat")
    result = run_tool("sulis-change", "start",
                      "--repo-root", str(local_git_repo),
                      "--slug", "feat-thing", "--primitive", "feat")
    assert result.returncode == 1
    assert result.json is not None
    assert "already exists" in result.json["error"]


def test_start_validates_primitive(local_git_repo, run_tool):
    """Invalid primitive is rejected with a clear message."""
    result = run_tool("sulis-change", "start",
                      "--repo-root", str(local_git_repo),
                      "--slug", "thing-x", "--primitive", "bogus")
    assert result.returncode == 1
    assert "primitive 'bogus' not in allowed set" in result.json["error"]


def test_start_validates_slug(local_git_repo, run_tool):
    """Invalid slug is rejected."""
    result = run_tool("sulis-change", "start",
                      "--repo-root", str(local_git_repo),
                      "--slug", "single",  # one-word slug
                      "--primitive", "feat")
    assert result.returncode == 1
    assert "kebab-case" in result.json["error"]


# ─── adopt ──────────────────────────────────────────────────────────────


def test_adopt_uncommitted_changes_into_change_branch(local_git_repo, run_tool):
    """Worktree-safe file transfer retrofits uncommitted work."""
    # Make some uncommitted changes on dev
    (local_git_repo / "new-file.md").write_text("WIP design notes\n")

    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(local_git_repo),
        "--slug", "extract-design", "--primitive", "refactor",
    )
    assert result.ok, f"adopt failed: stderr={result.stderr}"
    worktree_dest = Path(result.data["worktree_path"])

    # The uncommitted file should now be in the worktree, not on dev
    assert (worktree_dest / "new-file.md").exists()
    assert not (local_git_repo / "new-file.md").exists()
    assert result.data["uncommitted_count"] == 1


def test_adopt_local_commits_into_change_branch(local_git_repo, run_tool):
    """Cherry-pick path retrofits local commits not yet on origin."""
    # Make a local commit on dev (not pushed)
    (local_git_repo / "feature.md").write_text("feature work\n")
    _run(["git", "add", "feature.md"], cwd=local_git_repo)
    _run(["git", "commit", "-m", "feat: local-only commit"], cwd=local_git_repo)

    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(local_git_repo),
        "--slug", "add-feature", "--primitive", "feat",
        "--remote-ref", "origin/dev",
    )
    assert result.ok, f"adopt failed: stderr={result.stderr}"
    assert result.data["local_commits_count"] == 1

    # The file should be on the change branch worktree
    worktree_dest = Path(result.data["worktree_path"])
    assert (worktree_dest / "feature.md").exists()

    # Local dev should be reset to origin/dev (no feature.md there)
    assert not (local_git_repo / "feature.md").exists()


# ─── adopt: worktree-safety regression (issue #53) ────────────────────────


def test_adopt_does_not_consume_sibling_worktree_stash(local_git_repo):
    """Load-bearing regression for issue #53.

    The shared stash stack is per-repo, so a positional ``git stash pop``
    in a change worktree can grab an UNRELATED sibling worktree's stash.
    This is the DC-04 incident: an adopt run popped a hardening stash
    pushed from a different worktree and dumped its files in as cruft.

    Reproduction (white-box, real git): a sibling worktree's stash is
    interleaved onto the shared stack at the exact moment between the
    adopt's own stash push and its worktree pop — i.e. it lands on TOP
    of the adopt's stash, so the positional pop grabs the WRONG one.
    We model the interleave by wrapping ``git_worktree_add`` (the step
    that runs between push and pop in the buggy code) to push the
    sibling stash. The function under test still uses real git.

    Assertion: after adopt, the sibling stash is STILL on the stack and
    its content is untouched. Against the buggy (positional-pop) code
    this FAILS — the sibling stash is consumed.
    """
    repo = local_git_repo

    # The sibling worktree's parked work (a tracked-file modification +
    # an untracked file). We capture it as a stash-like payload that the
    # interleave hook will push at the hazardous moment.
    real_worktree_add = _wpxlib.git_worktree_add

    def _interleaving_worktree_add(repo_root, branch, dest, base_ref="dev"):
        # Simulate a sibling worktree pushing its own stash onto the
        # shared stack right now (after adopt's push, before adopt's pop).
        (repo / "sibling-unrelated.txt").write_text("SIBLING worktree's work\n")
        _git(repo, "stash", "push", "-u", "-m", "SIBLING-hardening-work")
        return real_worktree_add(repo_root, branch, dest, base_ref)

    _wpxlib.git_worktree_add = _interleaving_worktree_add
    try:
        # The adopt's OWN uncommitted work.
        (repo / "adopt-own.txt").write_text("this change's own work\n")
        branch = compose_change_branch("refactor", "interleave-victim")
        worktree_dest = change_worktree_path(repo, "refactor", "interleave-victim")

        ok, msg = adopt_uncommitted_into_change(
            repo, branch, "dev", worktree_dest, ["adopt-own.txt"],
        )
    finally:
        _wpxlib.git_worktree_add = real_worktree_add

    assert ok, f"adopt should succeed: {msg}"

    # The sibling stash MUST still be on the shared stack, untouched.
    entries = _stash_entries(repo)
    assert any("SIBLING-hardening-work" in e for e in entries), (
        "the sibling worktree's stash was consumed by the adopt — "
        f"cross-worktree contamination (issue #53). stack now: {entries}"
    )

    # And its content must be recoverable intact (still parked, not applied
    # into either tree as cruft).
    assert not (repo / "sibling-unrelated.txt").exists(), (
        "sibling stash content leaked back into the source tree"
    )
    assert not (worktree_dest / "sibling-unrelated.txt").exists(), (
        "sibling stash content leaked into the adopt worktree as cruft"
    )


def test_adopt_preexisting_sibling_stash_survives(local_git_repo, run_tool):
    """A sibling stash already parked on the shared stack before an adopt
    must remain present and unchanged after the adopt completes.

    (Acceptance-criteria phrasing of the regression. After the fix this
    is rock-solid because the adopt path uses no stash at all.)
    """
    repo = local_git_repo

    # Park an unrelated sibling stash on the shared stack first.
    (repo / "sibling.txt").write_text("sibling parked work\n")
    _git(repo, "stash", "push", "-u", "-m", "SIBLING-parked")
    before = _stash_entries(repo)
    assert any("SIBLING-parked" in e for e in before)

    # Now adopt this change's own uncommitted work.
    (repo / "my-work.md").write_text("my own WIP\n")
    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(repo),
        "--slug", "park-safe", "--primitive", "refactor",
    )
    assert result.ok, f"adopt failed: {result.stderr}"

    after = _stash_entries(repo)
    assert any("SIBLING-parked" in e for e in after), (
        f"sibling stash disappeared after adopt. before={before} after={after}"
    )


def test_adopt_transfers_tracked_and_untracked_work(local_git_repo, run_tool):
    """Both a tracked modification and an untracked file must land in the
    new worktree with correct content."""
    repo = local_git_repo

    # Tracked modification: change the committed README.
    (repo / "README.md").write_text("# test repo\nADOPTED tracked edit\n")
    # Untracked new file.
    (repo / "brand-new.txt").write_text("untracked content\n")

    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(repo),
        "--slug", "tracked-untracked", "--primitive", "refactor",
    )
    assert result.ok, f"adopt failed: {result.stderr}"
    worktree_dest = Path(result.data["worktree_path"])

    # Tracked modification carried across with correct content.
    assert (worktree_dest / "README.md").read_text() == (
        "# test repo\nADOPTED tracked edit\n"
    )
    # Untracked file carried across with correct content.
    assert (worktree_dest / "brand-new.txt").exists()
    assert (worktree_dest / "brand-new.txt").read_text() == "untracked content\n"


def test_adopt_preserves_untracked_symlink_fidelity(local_git_repo, run_tool):
    """ADVISORY (symlink fidelity): an untracked symlink must arrive in the
    worktree AS A SYMLINK — not silently followed-and-transmuted into a
    regular file (file target) nor silently dropped (directory target)."""
    repo = local_git_repo

    # Untracked symlink -> a (committed) file. The link points at README.md.
    file_link = repo / "link-to-readme"
    file_link.symlink_to("README.md")

    # Untracked symlink -> a directory. Create a real dir to point at.
    (repo / "subdir").mkdir()
    (repo / "subdir" / "inner.txt").write_text("inside\n")
    _run(["git", "add", "subdir/inner.txt"], cwd=repo)
    _run(["git", "commit", "-qm", "add subdir/inner.txt"], cwd=repo)
    dir_link = repo / "link-to-subdir"
    dir_link.symlink_to("subdir")

    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(repo),
        "--slug", "symlink-fidelity", "--primitive", "refactor",
    )
    assert result.ok, f"adopt failed: {result.stderr}"
    worktree_dest = Path(result.data["worktree_path"])

    # File symlink preserved as a symlink (not transmuted to a regular file).
    moved_file_link = worktree_dest / "link-to-readme"
    assert moved_file_link.is_symlink(), (
        "untracked file-symlink was transmuted into a regular file "
        "(symlink-ness lost)"
    )
    assert os.readlink(moved_file_link) == "README.md"

    # Directory symlink preserved as a symlink (not silently dropped).
    moved_dir_link = worktree_dest / "link-to-subdir"
    assert moved_dir_link.is_symlink(), (
        "untracked directory-symlink was silently dropped at capture"
    )
    assert os.readlink(moved_dir_link) == "subdir"


def test_adopt_leaves_source_tree_clean(local_git_repo, run_tool):
    """After a successful adopt, the source repo working tree has no
    leftover tracked modifications and no moved untracked files."""
    repo = local_git_repo

    (repo / "README.md").write_text("# test repo\nmoved edit\n")
    (repo / "moved-untracked.txt").write_text("moved\n")

    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(repo),
        "--slug", "clean-source", "--primitive", "refactor",
    )
    assert result.ok, f"adopt failed: {result.stderr}"

    # Source tree clean: no porcelain status output at all.
    status = _git(repo, "status", "--porcelain")
    assert status == "", f"source tree not clean after adopt: {status!r}"
    # The moved untracked file is gone from source.
    assert not (repo / "moved-untracked.txt").exists()
    # The tracked file is restored to its committed content.
    assert (repo / "README.md").read_text() == "# test repo\n"


def test_adopt_local_commits_plus_uncommitted_no_stash(local_git_repo, run_tool):
    """Combined case: local-only commits cherry-picked onto the change
    branch AND trailing uncommitted (tracked + untracked) work lands in
    the worktree — with no shared-stack pop consuming a sibling stash."""
    repo = local_git_repo

    # A local-only commit (not on origin/dev).
    (repo / "feature.md").write_text("committed feature work\n")
    _run(["git", "add", "feature.md"], cwd=repo)
    _run(["git", "commit", "-m", "feat: local-only commit"], cwd=repo)

    # Trailing uncommitted work on top: a tracked edit + an untracked file.
    (repo / "feature.md").write_text("committed feature work\nplus WIP edit\n")
    (repo / "wip-extra.txt").write_text("uncommitted extra\n")

    # Park an unrelated sibling stash that must survive. Scope the stash to
    # the sibling file only (a pathspec) so it does NOT swallow this change's
    # own WIP — exactly how a sibling worktree's parked work would look on
    # the shared stack.
    (repo / "sibling2.txt").write_text("sibling parked\n")
    _git(repo, "stash", "push", "-u", "-m", "SIBLING-combined", "--", "sibling2.txt")

    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(repo),
        "--slug", "combined-case", "--primitive", "feat",
        "--remote-ref", "origin/dev",
    )
    assert result.ok, f"adopt failed: {result.stderr}"
    assert result.data["local_commits_count"] == 1
    worktree_dest = Path(result.data["worktree_path"])

    # The cherry-picked commit landed (feature.md exists on the branch).
    assert (worktree_dest / "feature.md").exists()
    # The trailing uncommitted edit + untracked file landed too.
    assert "plus WIP edit" in (worktree_dest / "feature.md").read_text()
    assert (worktree_dest / "wip-extra.txt").exists()
    assert (worktree_dest / "wip-extra.txt").read_text() == "uncommitted extra\n"

    # The sibling stash survives untouched.
    entries = _stash_entries(repo)
    assert any("SIBLING-combined" in e for e in entries), (
        f"sibling stash consumed by combined adopt. stack: {entries}"
    )


# ─── adopt: durable-recovery on combined-path failure (data-loss window) ──


def _force_conflicting_local_commit(repo: Path) -> None:
    """Set up the combined-adopt failure scenario with REAL git.

    Advances origin/dev with one change to README.md, then makes a
    conflicting local-only commit to the SAME lines. Cherry-picking the
    local commit onto the (advanced) remote tip is then guaranteed to
    CONFLICT — which is exactly the cherry-pick-failure leg of the
    combined adopt path. No mocking: the failure is genuine.
    """
    # Seed README with multiple lines so a mid-file edit conflicts cleanly.
    (repo / "README.md").write_text("line1\nline2\nline3\n")
    _run(["git", "commit", "-qam", "seed multi-line readme"], cwd=repo)
    _run(["git", "push", "-q", "origin", "dev"], cwd=repo)

    # Advance origin/dev via a sibling clone: change line2 -> REMOTE.
    other = repo.parent / "_origin_advancer"
    origin = repo.parent / "_origin.git"
    _run(["git", "clone", "-q", str(origin), str(other)], cwd=repo.parent)
    _run(["git", "config", "user.email", "t@e.com"], cwd=other)
    _run(["git", "config", "user.name", "T"], cwd=other)
    (other / "README.md").write_text("line1\nREMOTE-CHANGE\nline3\n")
    _run(["git", "commit", "-qam", "remote advances line2"], cwd=other)
    _run(["git", "push", "-q", "origin", "dev"], cwd=other)

    # Locally: fetch so origin/dev is ahead, then make a conflicting
    # local-only commit touching the SAME line2.
    _run(["git", "fetch", "-q", "origin"], cwd=repo)
    (repo / "README.md").write_text("line1\nLOCAL-CHANGE\nline3\n")
    _run(["git", "commit", "-qam", "local conflicting commit"], cwd=repo)


def test_combined_adopt_cherrypick_failure_is_loud_and_recoverable(
    local_git_repo, run_tool,
):
    """MUST FIX (data-loss window): when the cherry-pick fails in the
    combined path AFTER the source tree has been cleaned, the command
    must (a) fail loudly — non-zero exit / emit_error, never
    success-with-WARN — and (b) leave the founder's uncommitted work
    recoverable in a durable on-disk location surfaced in the error.
    """
    repo = local_git_repo
    _force_conflicting_local_commit(repo)

    # Trailing uncommitted work on top of the local commit: a tracked edit
    # to a different file (so it captures cleanly) + an untracked file.
    (repo / "feature.txt").write_text("WIP tracked work\n")
    _run(["git", "add", "feature.txt"], cwd=repo)
    _run(["git", "commit", "-qm", "add feature.txt placeholder"], cwd=repo)
    _run(["git", "push", "-q", "origin", "HEAD:refs/heads/_throwaway"], cwd=repo)
    # ^ no-op push to a throwaway ref just to keep origin tidy; the local
    #   commit above is now ALSO ahead of origin/dev, which is fine — what
    #   matters is the conflicting commit will fail to cherry-pick.
    (repo / "feature.txt").write_text("WIP tracked work\nUNCOMMITTED EDIT\n")
    (repo / "wip-untracked.txt").write_text("precious untracked WIP\n")

    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(repo),
        "--slug", "cp-fail", "--primitive", "feat",
        "--remote-ref", "origin/dev",
    )

    # (a) Loud failure — NEVER success-with-WARN.
    assert not result.ok, (
        "combined adopt reported success despite a cherry-pick failure "
        f"after source-clean. data={result.data}"
    )
    assert result.returncode != 0, "expected non-zero exit on cherry-pick failure"

    # (b) The founder's uncommitted work is recoverable: the error surfaces
    #     a durable recovery location that still holds the work.
    recovery = result.json.get("context", {}).get("recovery_dir") if result.json else None
    assert recovery, (
        "cherry-pick-failure error did not surface a durable recovery_dir; "
        f"error={result.error!r}"
    )
    recovery_dir = Path(recovery)
    assert recovery_dir.exists(), f"recovery dir missing: {recovery_dir}"

    # The untracked file content is preserved verbatim under the recovery dir.
    recovered_untracked = list(recovery_dir.rglob("wip-untracked.txt"))
    assert recovered_untracked, (
        f"untracked WIP not found under recovery dir {recovery_dir}; "
        f"contents={[p.name for p in recovery_dir.rglob('*')]}"
    )
    assert recovered_untracked[0].read_bytes() == b"precious untracked WIP\n"

    # The tracked delta is preserved as a patch under the recovery dir.
    patch_files = list(recovery_dir.rglob("*.patch"))
    assert patch_files, f"tracked-delta patch not found under {recovery_dir}"
    patch_text = patch_files[0].read_text()
    assert "UNCOMMITTED EDIT" in patch_text, (
        "tracked uncommitted edit not preserved in recovery patch"
    )


def test_combined_adopt_success_cleans_up_durable_recovery(
    local_git_repo, run_tool,
):
    """On the success path, the durable recovery copy must be cleaned up —
    it exists only as a failure safety net, not as cruft left behind."""
    repo = local_git_repo

    # A local-only commit that cherry-picks cleanly (no conflict).
    (repo / "feature.md").write_text("committed feature work\n")
    _run(["git", "add", "feature.md"], cwd=repo)
    _run(["git", "commit", "-qm", "feat: local-only commit"], cwd=repo)

    # Trailing uncommitted work.
    (repo / "feature.md").write_text("committed feature work\nWIP edit\n")
    (repo / "wip-extra.txt").write_text("uncommitted extra\n")

    before = set(_change_recovery_dirs())
    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(repo),
        "--slug", "combined-clean", "--primitive", "feat",
        "--remote-ref", "origin/dev",
    )
    assert result.ok, f"adopt failed: {result.stderr}"

    # No durable recovery dir leaked after a clean success.
    after = set(_change_recovery_dirs())
    leaked = after - before
    assert not leaked, f"durable recovery dir not cleaned up on success: {leaked}"


def _change_recovery_dirs() -> list[Path]:
    """Enumerate any sulis-adopt durable recovery dirs in the temp area."""
    import tempfile as _tf
    tmp = Path(_tf.gettempdir())
    return [p for p in tmp.glob("sulis-adopt-recovery-*") if p.is_dir()]


def test_adopt_rewrite_mode_requires_force(local_git_repo, run_tool):
    """--mode rewrite without --force is rejected."""
    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(local_git_repo),
        "--slug", "rewrite-test", "--primitive", "feat",
        "--mode", "rewrite",
    )
    assert result.returncode == 1
    assert "--force" in result.json["error"]


def test_adopt_with_no_pending_work_creates_branch_forward(local_git_repo, run_tool):
    """Clean tree + no local commits → adopt creates branch forward-only."""
    result = run_tool(
        "sulis-change", "adopt",
        "--repo-root", str(local_git_repo),
        "--slug", "clean-adopt", "--primitive", "feat",
    )
    assert result.ok
    assert result.data["uncommitted_count"] == 0
    assert result.data["local_commits_count"] == 0
    assert "forward-only" in " ".join(result.data["moved"])


# ─── list ───────────────────────────────────────────────────────────────


def test_list_reports_active_changes(local_git_repo, run_tool):
    """`sulis-change list` enumerates change/* branches."""
    run_tool("sulis-change", "start",
             "--repo-root", str(local_git_repo),
             "--slug", "thing-a", "--primitive", "create")
    run_tool("sulis-change", "start",
             "--repo-root", str(local_git_repo),
             "--slug", "thing-b", "--primitive", "refactor")

    result = run_tool("sulis-change", "list",
                      "--repo-root", str(local_git_repo))
    assert result.ok
    assert result.data["active_count"] == 2
    slugs = sorted(c["slug"] for c in result.data["changes"])
    assert slugs == ["thing-a", "thing-b"]

    # Each entry includes worktree_present + primitive
    for c in result.data["changes"]:
        assert c["worktree_present"] is True
        assert c["primitive"] in ("create", "refactor")


def test_list_empty_when_no_changes(local_git_repo, run_tool):
    """No change branches → active_count: 0."""
    result = run_tool("sulis-change", "list",
                      "--repo-root", str(local_git_repo))
    assert result.ok
    assert result.data["active_count"] == 0
    assert result.data["changes"] == []


# ─── status ─────────────────────────────────────────────────────────────


def test_status_reports_sha_and_ahead_behind(local_git_repo, run_tool):
    """`sulis-change status` shows branch SHA, ahead/behind dev."""
    start_result = run_tool("sulis-change", "start",
                            "--repo-root", str(local_git_repo),
                            "--slug", "status-test", "--primitive", "feat")

    # Add a commit on the change branch to make it "ahead of dev".
    # `start` creates the worktree at the co-located path
    # (~/.sulis/changes/{id}/worktree) and returns it as `worktree_path`;
    # use THAT rather than reconstructing the legacy sibling path.
    worktree_dest = Path(start_result.data["worktree_path"])
    (worktree_dest / "marker.txt").write_text("change-branch work\n")
    _run(["git", "add", "marker.txt"], cwd=worktree_dest)
    _run(["git", "commit", "-m", "feat: status test commit"], cwd=worktree_dest)

    result = run_tool("sulis-change", "status",
                      "--repo-root", str(local_git_repo),
                      "--slug", "status-test", "--primitive", "feat")
    assert result.ok
    assert result.data["branch"] == "change/feat-status-test"
    assert result.data["ahead_of_base"] == 1
    assert result.data["behind_base"] == 0
    assert result.data["worktree_present"] is True


# ─── finish ─────────────────────────────────────────────────────────────


def test_finish_merge_removes_worktree_keeps_branch_and_record(local_git_repo,
                                                               run_tool):
    """`finish --merge` ships, then REMOVES the worktree but KEEPS the branch +
    record — #56 Part 2 (refines #38's archive-don't-delete).

    The committed work merges to dev; the change-branch tip is pinned as
    `shipped_sha`; the now-redundant worktree is removed (only regenerable
    `.changes/` metadata was uncommitted in it); the local branch + change
    record stay so the cockpit can retrace and `recreate` can re-materialise.
    """
    start_result = run_tool("sulis-change", "start",
                            "--repo-root", str(local_git_repo),
                            "--slug", "merge-test", "--primitive", "feat")
    change_id = start_result.data["change_id"]

    # `start` returns the co-located worktree path; commit the shippable
    # work there (not the legacy sibling path).
    worktree_dest = Path(start_result.data["worktree_path"])
    (worktree_dest / "merged.txt").write_text("merged content\n")
    _run(["git", "add", "merged.txt"], cwd=worktree_dest)
    _run(["git", "commit", "-m", "feat: merge-test work"], cwd=worktree_dest)

    result = run_tool("sulis-change", "finish",
                      "--repo-root", str(local_git_repo),
                      "--slug", "merge-test", "--primitive", "feat",
                      "--merge")
    assert result.ok, f"finish failed: stderr={result.stderr}"
    assert result.data["outcome"]["mode"] == "merge"

    archived = result.data["archived"]
    assert archived["archived"] is True
    assert archived["stage"] == "shipped"
    assert archived["change_id"] == change_id
    # shipped_sha is pinned (#56 Part 2) — non-empty, a 40-char git sha.
    assert archived["shipped_sha"] and len(archived["shipped_sha"]) == 40
    # The worktree was removed (only sulis metadata was dirty → safe).
    assert archived["worktree_removed"] is True
    assert not worktree_dest.exists(), "worktree must be removed on ship"

    # The local branch + record BOTH remain — the audit trail.
    proc = _run(["git", "branch", "--list", "change/feat-merge-test"],
                cwd=local_git_repo)
    assert "change/feat-merge-test" in proc.stdout, \
        "local change branch must remain after ship"

    # The work is on dev.
    assert (local_git_repo / "merged.txt").exists()


def test_finish_merge_keeps_worktree_when_uncommitted_work_present(
        local_git_repo, run_tool):
    """The worktree is KEPT (never force-discarded) when genuine uncommitted
    work is present — #56 Part 2 safety. Only sulis-managed `.changes/`
    metadata is safe to discard; real founder WIP blocks removal."""
    start_result = run_tool("sulis-change", "start",
                            "--repo-root", str(local_git_repo),
                            "--slug", "wip-test", "--primitive", "feat")
    worktree_dest = Path(start_result.data["worktree_path"])
    # Commit the shippable work...
    (worktree_dest / "shipped.txt").write_text("done\n")
    _run(["git", "add", "shipped.txt"], cwd=worktree_dest)
    _run(["git", "commit", "-m", "feat: wip-test work"], cwd=worktree_dest)
    # ...then leave a genuine uncommitted file behind.
    (worktree_dest / "scratch-notes.txt").write_text("half-finished idea\n")

    result = run_tool("sulis-change", "finish",
                      "--repo-root", str(local_git_repo),
                      "--slug", "wip-test", "--primitive", "feat", "--merge")
    assert result.ok, f"finish failed: stderr={result.stderr}"
    archived = result.data["archived"]
    assert archived["worktree_removed"] is False
    assert "uncommitted work" in archived["worktree_kept_reason"]
    assert worktree_dest.exists(), "worktree must be kept when WIP present"
    assert (worktree_dest / "scratch-notes.txt").exists()


def test_finish_requires_merge_or_pr(local_git_repo, run_tool):
    """`finish` without --merge or --pr is rejected."""
    run_tool("sulis-change", "start",
             "--repo-root", str(local_git_repo),
             "--slug", "nomode-test", "--primitive", "feat")
    result = run_tool("sulis-change", "finish",
                      "--repo-root", str(local_git_repo),
                      "--slug", "nomode-test", "--primitive", "feat")
    assert result.returncode == 1
    assert "--merge" in result.json["error"] or "--pr" in result.json["error"]


# ─── global change store (slice A.5) ──────────────────────────────────────


def _state_changes_dir() -> Path:
    """The changes/ dir under the isolated SULIS_STATE_DIR (set autouse)."""
    return Path(os.environ["SULIS_STATE_DIR"]) / "changes"


def test_start_writes_change_record(local_git_repo, run_tool):
    """`start` writes a full change.json record under the local store."""
    result = run_tool("sulis-change", "start",
                      "--repo-root", str(local_git_repo),
                      "--slug", "record-test", "--primitive", "create",
                      "--intent", "build the thing")
    assert result.ok, f"start failed: stderr={result.stderr}"
    change_id = result.data["change_id"]

    record_path = _state_changes_dir() / change_id / "change.json"
    assert record_path.exists(), "change.json was not written"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["change_id"] == change_id
    assert record["slug"] == "record-test"
    assert record["primitive"] == "create"
    assert record["branch"] == "change/create-record-test"
    assert record["intent"] == "build the thing"
    assert record["base_branch"] == "main"
    assert record["stage"] == "recon"
    assert record["created_at"].endswith("Z")


def test_list_reads_the_records(local_git_repo, run_tool):
    """`list` enumerates from the local records (branch-independent index)."""
    run_tool("sulis-change", "start",
             "--repo-root", str(local_git_repo),
             "--slug", "rec-a", "--primitive", "create")
    run_tool("sulis-change", "start",
             "--repo-root", str(local_git_repo),
             "--slug", "rec-b", "--primitive", "refactor")

    result = run_tool("sulis-change", "list",
                      "--repo-root", str(local_git_repo))
    assert result.ok
    assert result.data["active_count"] == 2
    slugs = sorted(c["slug"] for c in result.data["changes"])
    assert slugs == ["rec-a", "rec-b"]
    # Each entry carries the record fields + the cross-referenced branch flag.
    for c in result.data["changes"]:
        assert c["branch_present"] is True
        assert c["worktree_present"] is True
        assert "change_id" in c
        assert c["stage"] == "recon"


def test_list_flags_record_whose_branch_is_gone(local_git_repo, run_tool):
    """A record whose branch was deleted is listed but branch_present=False."""
    start_result = run_tool("sulis-change", "start",
                            "--repo-root", str(local_git_repo),
                            "--slug", "gone-branch", "--primitive", "feat")
    # Delete the branch + worktree out from under the record (simulating a
    # merged/pruned change whose local record still lingers). The worktree
    # lives at the co-located path `start` returns, not the legacy sibling.
    worktree = Path(start_result.data["worktree_path"])
    subprocess.run(["git", "worktree", "remove", str(worktree), "--force"],
                   cwd=local_git_repo, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-D", "change/feat-gone-branch"],
                   cwd=local_git_repo, check=True, capture_output=True)

    result = run_tool("sulis-change", "list",
                      "--repo-root", str(local_git_repo))
    assert result.ok
    assert result.data["active_count"] == 1
    item = result.data["changes"][0]
    assert item["slug"] == "gone-branch"
    assert item["branch_present"] is False
    assert item["worktree_present"] is False


def test_nuke_resolves_change_id_from_record(local_git_repo, run_tool):
    """nuke resolves the change_id via the local record (no manifest needed)."""
    start = run_tool("sulis-change", "start",
                     "--repo-root", str(local_git_repo),
                     "--slug", "nuke-rec", "--primitive", "feat")
    change_id = start.data["change_id"]

    result = run_tool("sulis-change", "nuke",
                      "--repo-root", str(local_git_repo),
                      "--slug", "nuke-rec")  # dry-run (no --force)
    assert result.ok
    assert result.data["change_id"] == change_id
    assert result.data["change_id_resolution"] == "matched-via-record"


def test_start_does_not_pollute_real_home(local_git_repo, run_tool, monkeypatch):
    """With SULIS_STATE_DIR set, `start` writes ONLY under it — never real HOME.

    Pollution guard: prior to the configurable base, subprocess `start` calls
    inherited the real home and wrote ~20 junk ~/.sulis/changes/* dirs.
    """
    # Point HOME at a sentinel tmp that must stay empty (SULIS_STATE_DIR, set
    # by the autouse fixture, takes precedence in the resolver).
    fake_home = local_git_repo.parent / "_sentinel_home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    result = run_tool("sulis-change", "start",
                      "--repo-root", str(local_git_repo),
                      "--slug", "no-pollute", "--primitive", "feat")
    assert result.ok, f"start failed: stderr={result.stderr}"
    change_id = result.data["change_id"]

    # The record landed under SULIS_STATE_DIR ...
    assert (_state_changes_dir() / change_id / "change.json").exists()
    # ... and NOTHING was written under the (fake) real home's ~/.sulis.
    assert not (fake_home / ".sulis").exists(), \
        "start polluted the real home's ~/.sulis despite SULIS_STATE_DIR"


# ─── #38: mark-shipped subcommand (the gh-PR ship-skill seam) ──────────────


def test_mark_shipped_via_handle_flips_stage(local_git_repo, run_tool):
    """The mark-shipped subcommand is what the change skill calls AFTER
    `gh pr merge` succeeds. It must resolve the change via --handle, flip
    stage='shipped', and persist shipped_at on the change record so the
    cockpit's 'Shipped' section can read it AND cmd_nuke's protection
    fires."""
    start = run_tool("sulis-change", "start",
                     "--repo-root", str(local_git_repo),
                     "--slug", "mark-shipped-test", "--primitive", "feat")
    assert start.ok
    handle = start.data["handle"]

    result = run_tool("sulis-change", "mark-shipped",
                      "--handle", handle,
                      "--repo-root", str(local_git_repo))
    assert result.ok, f"mark-shipped failed: {result.error}; stderr={result.stderr}"
    assert result.data["stage"] == "shipped"
    assert result.data["shipped_at"]  # non-empty ISO timestamp


def test_mark_shipped_requires_an_identifier(local_git_repo, run_tool):
    """Without --change-id / --handle / SULIS_CHANGE_ID, mark-shipped errors
    cleanly (no destructive default)."""
    result = run_tool(
        "sulis-change", "mark-shipped",
        "--repo-root", str(local_git_repo),
        env={"PATH": os.environ.get("PATH", "")},  # no SULIS_CHANGE_ID
    )
    assert not result.ok
    assert "change-id" in (result.error or "") or "handle" in (result.error or "")
