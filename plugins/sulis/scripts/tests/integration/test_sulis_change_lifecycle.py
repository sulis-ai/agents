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

import pytest

from _wpxlib import change_worktree_path, read_change_metadata


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True,
                          text=True, check=True)


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
    """Stash + worktree + unstash retrofits uncommitted work."""
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
    run_tool("sulis-change", "start",
             "--repo-root", str(local_git_repo),
             "--slug", "status-test", "--primitive", "feat")

    # Add a commit on the change branch to make it "ahead of dev"
    worktree_dest = local_git_repo.parent / f"{local_git_repo.name}-change-feat-status-test"
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


def test_finish_merge_cleans_up_worktree_and_branch(local_git_repo, run_tool):
    """`finish --merge` squash-merges to dev and removes the worktree."""
    # Start a change
    run_tool("sulis-change", "start",
             "--repo-root", str(local_git_repo),
             "--slug", "merge-test", "--primitive", "feat")

    # Add a commit on the change branch
    worktree_dest = local_git_repo.parent / f"{local_git_repo.name}-change-feat-merge-test"
    (worktree_dest / "merged.txt").write_text("merged content\n")
    _run(["git", "add", "merged.txt"], cwd=worktree_dest)
    _run(["git", "commit", "-m", "feat: merge-test work"], cwd=worktree_dest)

    # Finish with --merge
    result = run_tool("sulis-change", "finish",
                      "--repo-root", str(local_git_repo),
                      "--slug", "merge-test", "--primitive", "feat",
                      "--merge")
    assert result.ok, f"finish failed: stderr={result.stderr}"
    assert result.data["outcome"]["mode"] == "merge"
    assert result.data["cleanup"]["branch_deleted"] is True, \
        f"cleanup detail: {result.data['cleanup']}"

    # The worktree is gone
    assert not worktree_dest.exists()

    # The work is on dev
    assert (local_git_repo / "merged.txt").exists()


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
    assert record["base_branch"] == "dev"
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
    run_tool("sulis-change", "start",
             "--repo-root", str(local_git_repo),
             "--slug", "gone-branch", "--primitive", "feat")
    # Delete the branch + worktree out from under the record (simulating a
    # merged/pruned change whose local record still lingers).
    worktree = local_git_repo.parent / f"{local_git_repo.name}-change-feat-gone-branch"
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
