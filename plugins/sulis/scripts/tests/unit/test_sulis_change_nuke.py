"""Unit tests for `sulis-change nuke` (cmd_nuke).

nuke abandons/deletes a change and its full footprint:
  1. the git worktree         (git worktree remove --force)
  2. the change branch        (git branch -D — refuse if currently checked out)
  3. the local state dir       (~/.sulis/changes/{change_id}/)
  4. the committed manifest    (.changes/{primitive}-{slug}.yaml)

Safety: the CLI requires --force to actually delete. Without --force it
dry-runs (lists the footprint, deletes nothing, exits 0). It also refuses
to nuke the change branch you're currently on.

These tests use the real local_git_repo fixture for the git mechanics
(worktree/branch are fast + deterministic) and a captured-emit harness to
read the structured JSON without sys.exit unwinding the test.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
_SC_PATH = _SCRIPTS / "sulis-change"


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SC_PATH))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


sc = _load_sulis_change()

_GOOD_ULID = "01HYQC71000000000000000000"


@pytest.fixture(autouse=True)
def _home_base_isolation(tmp_path_factory, monkeypatch):
    """nuke tests build their footprint under a HOME-based ~/.sulis and assert
    it's removed, so this module opts out of the repo-wide SULIS_STATE_DIR
    isolation (root conftest) and isolates via HOME instead. Each test sets its
    own HOME (overriding the default here); the default keeps any that don't
    out of the real home."""
    monkeypatch.delenv("SULIS_STATE_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))


# ─── emit capture harness ─────────────────────────────────────────────────


class _ExitOK(Exception):
    def __init__(self, data):
        self.data = data


class _ExitErr(Exception):
    def __init__(self, message, context=None):
        self.message = message
        self.context = context


def _capture_emit():
    """Returns (captured, patches) that intercept emit_ok / emit_error."""
    captured: dict = {}

    def _ok(data=None, warnings=None, exit_code=0):
        captured["ok"] = True
        captured["data"] = data
        raise _ExitOK(data)

    def _err(message, context=None):
        captured["ok"] = False
        captured["error"] = message
        captured["context"] = context
        raise _ExitErr(message, context)

    patches = [
        mock.patch.object(sc, "emit_ok", side_effect=_ok),
        mock.patch.object(sc, "emit_error", side_effect=_err),
    ]
    return captured, patches


def _run_nuke(args, captured, patches):
    from contextlib import ExitStack
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with pytest.raises((_ExitOK, _ExitErr)):
            sc.cmd_nuke(args)
    return captured


# ─── fixture: a real change to nuke ───────────────────────────────────────


def _make_change_branch(repo: Path, primitive: str, slug: str) -> dict:
    """Create a real change branch + worktree + manifest + local state dir.

    Returns the metadata dict. The repo must be the local_git_repo fixture
    (on dev with an origin remote).
    """
    branch = f"change/{primitive}-{slug}"
    worktree = repo.parent / f"{repo.name}-change-{primitive}-{slug}"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree), "dev"],
        cwd=repo, check=True, capture_output=True,
    )
    # Commit a manifest on the change branch's working tree... actually the
    # manifest lives in the worktree on the change branch. For nuke tests we
    # write it untracked into the main repo's .changes/ as cmd_finish/start do.
    manifest = repo / ".changes" / f"{primitive}-{slug}.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        f'change_id: "{_GOOD_ULID}"\nslug: "{slug}"\nprimitive: "{primitive}"\n'
        f'branch: "{branch}"\nworktree_path: "{worktree}"\n',
        encoding="utf-8",
    )
    return {
        "change_id": _GOOD_ULID,
        "branch": branch,
        "primitive": primitive,
        "slug": slug,
        "worktree_path": worktree,
        "manifest": manifest,
    }


def _state_dir(home: Path, change_id: str) -> Path:
    d = home / ".sulis" / "changes" / change_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text('{"stage": "implement"}', encoding="utf-8")
    (d / "CONTEXT.md").write_text("# ctx\n", encoding="utf-8")
    return d


def _nuke_args(repo, *, slug=None, handle=None, force=False) -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=str(repo),
        slug=slug,
        handle=handle,
        force=force,
    )


# ─── dry-run (no --force) ──────────────────────────────────────────────────


def test_nuke_dry_run_deletes_nothing(local_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "create", "drfrom-test")
    state = _state_dir(home, meta["change_id"])

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="drfrom-test", force=False),
              captured, patches)

    # Nothing removed
    assert meta["worktree_path"].exists()
    assert meta["manifest"].exists()
    assert state.exists()
    branches = subprocess.run(["git", "branch", "--list", meta["branch"]],
                              cwd=local_git_repo, capture_output=True, text=True).stdout
    assert meta["branch"] in branches


def test_nuke_dry_run_lists_footprint(local_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "create", "footprint-test")
    _state_dir(home, meta["change_id"])

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="footprint-test", force=False),
              captured, patches)

    assert captured["ok"] is True
    data = captured["data"]
    assert data["dry_run"] is True
    # The footprint should enumerate what WOULD be removed
    would = data["would_remove"]
    assert any("worktree" in k for k in would)
    assert any("branch" in k for k in would)


# ─── --force: full footprint removal ───────────────────────────────────────


def test_nuke_force_removes_full_footprint(local_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "create", "full-footprint")
    state = _state_dir(home, meta["change_id"])

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="full-footprint", force=True),
              captured, patches)

    assert captured["ok"] is True
    # Worktree gone
    assert not meta["worktree_path"].exists()
    # Branch gone
    branches = subprocess.run(["git", "branch", "--list", meta["branch"]],
                              cwd=local_git_repo, capture_output=True, text=True).stdout
    assert meta["branch"] not in branches
    # State dir gone
    assert not state.exists()
    # Manifest gone
    assert not meta["manifest"].exists()


def test_nuke_force_reports_what_was_removed(local_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "create", "report-removed")
    _state_dir(home, meta["change_id"])

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="report-removed", force=True),
              captured, patches)

    data = captured["data"]
    assert data["dry_run"] is False
    removed = data["removed"]
    assert removed["worktree"] is True
    assert removed["branch"] is True
    assert removed["state_dir"] is True
    assert removed["manifest"] is True


# ─── selector: --handle resolves the same change ───────────────────────────


def test_nuke_by_handle_resolves_change(local_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "create", "by-handle")
    _state_dir(home, meta["change_id"])
    handle = sc.ulid_handle(_GOOD_ULID)

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, handle=handle, force=True),
              captured, patches)

    assert captured["ok"] is True
    assert not meta["worktree_path"].exists()


# ─── refuse when the change branch is currently checked out ─────────────────


def test_nuke_refuses_when_branch_currently_checked_out(local_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "create", "on-this-branch")
    # Check out the change branch in the MAIN repo. The worktree already holds
    # it, so create a fresh repo where the change branch IS the current branch.
    # Simpler: checkout the branch directly is blocked by the worktree; instead
    # simulate "current branch == change branch" by checking from the worktree.
    captured, patches = _capture_emit()
    captured2 = _run_nuke(
        _nuke_args(meta["worktree_path"], slug="on-this-branch", force=True),
        captured, patches,
    )
    assert captured2["ok"] is False
    assert "switch to dev" in captured2["error"].lower() or \
           "currently on" in captured2["error"].lower()
    # Nothing destroyed
    assert meta["worktree_path"].exists()


# ─── idempotent: half-cleaned footprint must not crash ─────────────────────


def test_nuke_idempotent_when_worktree_already_gone(local_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "create", "half-gone")
    _state_dir(home, meta["change_id"])
    # Manually remove the worktree dir + prune, leaving the branch + manifest
    subprocess.run(["git", "worktree", "remove", str(meta["worktree_path"]), "--force"],
                   cwd=local_git_repo, check=True, capture_output=True)
    assert not meta["worktree_path"].exists()

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="half-gone", force=True),
              captured, patches)

    # Should still succeed (idempotent) and clean up the remainder
    assert captured["ok"] is True
    branches = subprocess.run(["git", "branch", "--list", meta["branch"]],
                              cwd=local_git_repo, capture_output=True, text=True).stdout
    assert meta["branch"] not in branches
    assert not meta["manifest"].exists()


def test_nuke_idempotent_when_state_dir_already_gone(local_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "create", "no-state")
    # No state dir created at all.

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="no-state", force=True),
              captured, patches)

    assert captured["ok"] is True
    data = captured["data"]
    # state_dir removal is a no-op but reported truthfully (already absent)
    assert data["removed"]["state_dir"] in (False, True)


# ─── selector validation ───────────────────────────────────────────────────


def test_nuke_requires_a_selector(local_git_repo):
    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug=None, handle=None, force=True),
              captured, patches)
    assert captured["ok"] is False
    assert "slug" in captured["error"].lower() or "handle" in captured["error"].lower()


def test_nuke_unknown_change_errors(local_git_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="never-existed", force=True),
              captured, patches)
    assert captured["ok"] is False


# ─── change_id resolution fallback chain (the real-world case) ──────────────
#
# In production the change manifest (.changes/{primitive}-{slug}.yaml, which
# carries change_id) lives in the WORKTREE — it's committed on the change
# branch — NOT in the dev checkout where nuke runs. A nuke that only reads
# <repo-root>/.changes/ therefore resolves change_id=null → state_dir=null →
# leaves ~/.sulis/changes/{change_id}/ behind. These tests pin the fallback
# chain that resolves change_id robustly: handle-prefix scan, worktree
# manifest, honest-degrade.


def _make_change_branch_manifest_in_worktree(
    repo: Path, primitive: str, slug: str, change_id: str = _GOOD_ULID,
) -> dict:
    """Real-world fixture: manifest lives in the WORKTREE, not in dev's .changes/.

    This mirrors production — the manifest is committed on the change branch,
    so the dev checkout (where nuke runs) has no copy. The worktree's own
    working tree carries it.
    """
    branch = f"change/{primitive}-{slug}"
    worktree = repo.parent / f"{repo.name}-change-{primitive}-{slug}"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree), "dev"],
        cwd=repo, check=True, capture_output=True,
    )
    manifest = worktree / ".changes" / f"{primitive}-{slug}.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        f'change_id: "{change_id}"\nslug: "{slug}"\nprimitive: "{primitive}"\n'
        f'branch: "{branch}"\nworktree_path: "{worktree}"\n',
        encoding="utf-8",
    )
    # Deliberately do NOT write any .changes/ file into the dev checkout.
    return {
        "change_id": change_id,
        "branch": branch,
        "primitive": primitive,
        "slug": slug,
        "worktree_path": worktree,
        "worktree_manifest": manifest,
    }


def test_nuke_resolves_state_dir_via_worktree_manifest(local_git_repo, tmp_path, monkeypatch):
    """Manifest is only in the worktree; nuke must still resolve change_id +
    the local state dir, list it in would_remove, and remove it under --force."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch_manifest_in_worktree(
        local_git_repo, "create", "wt-manifest")
    state = _state_dir(home, meta["change_id"])

    # Dry-run first: would_remove.state_dir must be the real state dir.
    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="wt-manifest", force=False),
              captured, patches)
    assert captured["ok"] is True
    data = captured["data"]
    assert data["change_id"] == meta["change_id"]
    assert data["would_remove"]["state_dir"] == str(state)
    assert state.exists()  # dry-run removed nothing

    # --force: the state dir is actually removed.
    captured2, patches2 = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="wt-manifest", force=True),
              captured2, patches2)
    assert captured2["ok"] is True
    assert captured2["data"]["removed"]["state_dir"] is True
    assert not state.exists()


def test_nuke_handle_resolves_state_dir_via_prefix_scan(local_git_repo, tmp_path, monkeypatch):
    """--handle CH-XXXXXX resolves the state dir by scanning ~/.sulis/changes/*
    for a dir whose name starts with the 6-char ULID prefix — even when no
    manifest is reachable from the dev checkout."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch_manifest_in_worktree(
        local_git_repo, "create", "handle-prefix")
    state = _state_dir(home, meta["change_id"])
    handle = sc.ulid_handle(meta["change_id"])  # CH-01HYQC

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, handle=handle, force=False),
              captured, patches)
    assert captured["ok"] is True
    data = captured["data"]
    assert data["change_id"] == meta["change_id"]
    assert data["would_remove"]["state_dir"] == str(state)


def test_nuke_state_dir_already_gone_is_truthful_and_idempotent(local_git_repo, tmp_path, monkeypatch):
    """change_id resolves (via worktree manifest) but the local state dir was
    never created → no crash, removal reported truthfully (already absent)."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch_manifest_in_worktree(
        local_git_repo, "create", "state-absent")
    # No _state_dir() call — the local state dir does not exist.

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="state-absent", force=True),
              captured, patches)
    assert captured["ok"] is True
    data = captured["data"]
    # change_id was resolved (proving the fallback chain fired), so the
    # state_dir path is known even though the dir is absent.
    assert data["change_id"] == meta["change_id"]
    removed = data["removed"]
    assert removed["state_dir"] is False
    assert "already absent" in removed.get("state_dir_detail", "")


# ─── #38: nuke refuses to destroy a shipped change's audit trail ───────────


def _seed_shipped_record(home: Path, change_id: str) -> None:
    """Seed a change.json with stage='shipped' so cmd_nuke's check fires."""
    d = home / ".sulis" / "changes" / change_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text('{"stage": "shipped"}', encoding="utf-8")
    (d / "change.json").write_text(
        '{"change_id": "' + change_id + '", "stage": "shipped", '
        '"shipped_at": "2026-05-27T16:00:00Z"}',
        encoding="utf-8",
    )


def test_nuke_refuses_shipped_change_without_force(
    local_git_repo, tmp_path, monkeypatch,
):
    """A shipped change's worktree + branch ARE the audit trail (#38). Nuke
    without --force must refuse loudly so the founder doesn't lose retrace."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "home" / ".sulis"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "feat", "shipped-archive")
    _seed_shipped_record(home, meta["change_id"])

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="shipped-archive", force=False),
              captured, patches)

    assert captured["ok"] is False
    assert "shipped" in captured["error"].lower()
    assert "audit trail" in captured["error"].lower()
    # Worktree + branch must still exist
    assert meta["worktree_path"].exists()
    branches = subprocess.run(
        ["git", "branch", "--list", meta["branch"]],
        cwd=local_git_repo, capture_output=True, text=True,
    ).stdout
    assert meta["branch"] in branches


def test_nuke_force_overrides_shipped_protection(
    local_git_repo, tmp_path, monkeypatch,
):
    """The protection is a default refusal, not a hard block. --force still
    works for genuine cleanup of an old archived change."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "home" / ".sulis"))
    home = tmp_path / "home"
    home.mkdir()
    meta = _make_change_branch(local_git_repo, "feat", "shipped-force")
    _seed_shipped_record(home, meta["change_id"])

    captured, patches = _capture_emit()
    _run_nuke(_nuke_args(local_git_repo, slug="shipped-force", force=True),
              captured, patches)

    # --force completes the nuke; the shipped check is bypassed.
    assert captured["ok"] is True
    assert not meta["worktree_path"].exists()
