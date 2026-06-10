"""Unit tests for the ship-integrity guard (task #111).

`sulis-change mark-shipped` MUST refuse to flip a change to stage='shipped'
unless the change is confirmed merged to `main`. The harm (CH-7BF1VZ, #110):
a change was marked shipped + its branch deleted while the squash-merge never
landed → 'shipped' was a lie and the work was nearly lost.

A SQUASH merge creates a brand-new commit on `main` with NO ancestry link
back to the change-branch tip, so `git merge-base --is-ancestor <branchtip>
origin/main` can NEVER confirm a squash-merged change. The authoritative
signal is a merged PR (`gh pr list --head <branch> --base main --state
merged`), whose `mergeCommit` is the true shipped state. A manual merge is
confirmed instead by `--merge-sha <sha>` being an ancestor of `origin/main`.

The gh/git calls are routed through an injectable `run` seam (default `_run`)
so these tests never touch the network — the same stubbing shape the other
`test_sulis_change_*` tests use.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SCRIPTS / "sulis-change"))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load_sulis_change()


def _fake_run(responses):
    """Build a `run` stub returning queued (rc, out, err) tuples keyed by a
    substring match on the joined command. `responses` is a list of
    (needle, (rc, out, err)) pairs; first matching needle wins."""

    def run(cmd, cwd=None, timeout=60):
        joined = " ".join(cmd)
        for needle, result in responses:
            if needle in joined:
                return result
        return (1, "", f"unexpected command: {joined}")

    return run


def _passthrough_except(mod, responses):
    """Like `_fake_run`, but un-matched commands fall through to the REAL
    `_run` (captured now, before monkeypatch swaps it) so the surrounding
    git probes (rev-list/rev-parse for the #272 empty-change guard) run for
    real against the seeded repo."""
    real = mod._run

    def run(cmd, cwd=None, timeout=60):
        joined = " ".join(cmd)
        for needle, result in responses:
            if needle in joined:
                return result
        return real(cmd, cwd=cwd, timeout=timeout)

    return run


# ─── _confirm_merged_to_main: the RED-proven core ──────────────────────────


def test_confirm_returns_none_when_no_merged_pr_and_no_merge_sha():
    """No merged PR for the branch + no --merge-sha → NOT confirmed (None)."""
    run = _fake_run([("gh pr list", (0, "[]", ""))])
    assert _mod._confirm_merged_to_main(
        Path("/repo"), "change/fix-x", merge_sha=None, run=run,
    ) is None


def test_confirm_returns_merge_commit_from_merged_pr():
    """A merged PR into main is authoritative → returns its mergeCommit oid."""
    pr_json = json.dumps([
        {"number": 7, "mergeCommit": {"oid": "abc123def"},
         "mergedAt": "2026-06-09T10:00:00Z"},
    ])
    run = _fake_run([("gh pr list", (0, pr_json, ""))])
    assert _mod._confirm_merged_to_main(
        Path("/repo"), "change/fix-x", merge_sha=None, run=run,
    ) == "abc123def"


def test_confirm_accepts_merge_sha_when_ancestor_of_origin_main():
    """--merge-sha confirmed when it is an ancestor of origin/main."""
    run = _fake_run([
        ("gh pr list", (0, "[]", "")),                  # no PR — fall to sha
        ("merge-base --is-ancestor", (0, "", "")),        # is an ancestor
    ])
    assert _mod._confirm_merged_to_main(
        Path("/repo"), "change/fix-x", merge_sha="deadbeef", run=run,
    ) == "deadbeef"


def test_confirm_refuses_merge_sha_when_not_ancestor_of_origin_main():
    """--merge-sha NOT an ancestor of origin/main → NOT confirmed (None)."""
    run = _fake_run([
        ("gh pr list", (0, "[]", "")),
        ("merge-base --is-ancestor", (1, "", "")),        # not an ancestor
    ])
    assert _mod._confirm_merged_to_main(
        Path("/repo"), "change/fix-x", merge_sha="deadbeef", run=run,
    ) is None


# ─── cmd_mark_shipped: end-to-end guard behaviour ──────────────────────────


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True,
                          text=True)


def _seed_change(tmp_path, monkeypatch, *, branch="change/fix-x", slug="fix-x",
                 with_repo=False):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "state"))
    import _change_state as cs
    cid = "01J0000000000000000000111X"
    base_sha = ""
    if with_repo:
        # A real repo with a non-empty change branch so the #272 empty-change
        # guard inside _archive_after_ship doesn't fire.
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "t@t")
        _git(repo, "config", "user.name", "t")
        (repo / "f.txt").write_text("base")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "base")
        base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
        _git(repo, "checkout", "-qb", branch)
        (repo / "g.txt").write_text("x")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "work")
    cs.write_change_record(cid, {
        "change_id": cid, "handle": "CH-01J111", "slug": slug,
        "primitive": "fix", "branch": branch,
        "base_sha": base_sha, "worktree_path": str(tmp_path / "wt"),
    })
    monkeypatch.setenv("SULIS_CHANGE_ID", cid)
    return cid, cs


def _args(repo_root, **over):
    import argparse
    ns = argparse.Namespace(
        change_id=None, handle=None, repo_root=str(repo_root),
        merge_sha=None, force=False,
    )
    for k, v in over.items():
        setattr(ns, k, v)
    return ns


def test_mark_shipped_refuses_when_not_merged(tmp_path, monkeypatch, capsys):
    """RED core: unmerged + no --merge-sha → refuse, non-zero, stage NOT flipped."""
    cid, cs = _seed_change(tmp_path, monkeypatch, with_repo=True)
    monkeypatch.setattr(_mod, "_run", _fake_run([("gh pr list", (0, "[]", ""))]))
    with pytest.raises(SystemExit) as ei:
        _mod.cmd_mark_shipped(_args(tmp_path / "repo"))
    assert ei.value.code != 0
    rec = cs.read_change_record(cid) or {}
    assert rec.get("stage") != "shipped"


def test_mark_shipped_succeeds_and_pins_merge_commit(tmp_path, monkeypatch):
    """Confirmed merged PR → flip shipped, pin shipped_sha to the MERGE COMMIT."""
    cid, cs = _seed_change(tmp_path, monkeypatch, with_repo=True)
    pr_json = json.dumps([{"number": 9, "mergeCommit": {"oid": "MERGEsha999"},
                           "mergedAt": "2026-06-09T10:00:00Z"}])
    # gh pr list confirms merged; git rev-list (empty-change guard) runs real.
    monkeypatch.setattr(_mod, "_run",
                        _passthrough_except(_mod, [("gh pr list", (0, pr_json, ""))]))
    # Skip the worktree-removal side effect (no real worktree on disk).
    monkeypatch.setattr(_mod, "_remove_shipped_worktree", lambda *a, **k: {})
    with pytest.raises(SystemExit) as ei:
        _mod.cmd_mark_shipped(_args(tmp_path / "repo"))
    assert ei.value.code == 0
    rec = cs.read_change_record(cid) or {}
    assert rec.get("stage") == "shipped"
    assert rec.get("shipped_sha") == "MERGEsha999"


def test_mark_shipped_force_overrides_and_records_note(tmp_path, monkeypatch, capsys):
    """--force ships despite no merge, and RECORDS the override."""
    cid, cs = _seed_change(tmp_path, monkeypatch, with_repo=True)
    monkeypatch.setattr(_mod, "_run",
                        _passthrough_except(_mod, [("gh pr list", (0, "[]", ""))]))
    monkeypatch.setattr(_mod, "_remove_shipped_worktree", lambda *a, **k: {})
    with pytest.raises(SystemExit) as ei:
        _mod.cmd_mark_shipped(_args(tmp_path / "repo", force=True))
    assert ei.value.code == 0
    rec = cs.read_change_record(cid) or {}
    assert rec.get("stage") == "shipped"
    # The override is recorded — on the record and/or stderr.
    err = capsys.readouterr().err
    assert rec.get("ship_override") or "force" in err.lower()
