"""Unit tests for the #56 ship-hardening pure helpers.

`_dedouble_slug` (Part 4) and `_compose_squash_message` (Part 3) live in the
`sulis-change` script (no .py extension), so they're loaded via importlib
from the file path — the same shape other tests use for the extensionless
tools.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SCRIPTS / "sulis-change"))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load_sulis_change()
_dedouble_slug = _mod._dedouble_slug
_compose_squash_message = _mod._compose_squash_message
_remove_shipped_worktree = _mod._remove_shipped_worktree


# ─── Part 2: never delete the worktree the shell is standing in ────────────


def test_remove_refuses_when_cwd_is_the_worktree(tmp_path, monkeypatch):
    """The cwd-ancestor guard fires BEFORE any git/session call — removing the
    worktree the caller is inside would strand their shell in a deleted dir."""
    wt = tmp_path / "wt"
    wt.mkdir()
    monkeypatch.chdir(wt)
    out = _remove_shipped_worktree(tmp_path, "01HID", wt)
    assert out["worktree_removed"] is False
    assert "inside this worktree" in out["worktree_kept_reason"]


def test_remove_refuses_when_cwd_is_below_the_worktree(tmp_path, monkeypatch):
    wt = tmp_path / "wt"
    (wt / "sub" / "deep").mkdir(parents=True)
    monkeypatch.chdir(wt / "sub" / "deep")
    out = _remove_shipped_worktree(tmp_path, "01HID", wt)
    assert out["worktree_removed"] is False
    assert "inside this worktree" in out["worktree_kept_reason"]


# ─── Part 4: slug de-doubling ─────────────────────────────────────────────


def test_dedouble_strips_redundant_primitive_prefix():
    # "fix the login bug" → slug fix-login-bug + primitive fix
    assert _dedouble_slug("fix", "fix-login-bug") == "login-bug"


def test_dedouble_leaves_non_prefixed_slug_untouched():
    assert _dedouble_slug("feat", "introduce-payments") == "introduce-payments"


def test_dedouble_keeps_doubled_when_remainder_would_be_invalid():
    # Stripping 'fix-' from 'fix-login' leaves 'login' (1 word) which fails
    # the 2-5-word slug rule → keep the original rather than emit an invalid
    # slug. Conservative branch.
    assert _dedouble_slug("fix", "fix-login") == "fix-login"


def test_dedouble_only_strips_exact_primitive_prefix():
    # 'fixture-cleanup' starts with 'fix' but NOT 'fix-' — must not strip.
    assert _dedouble_slug("fix", "fixture-cleanup") == "fixture-cleanup"


# ─── Part 3: Conventional-Commit squash message ───────────────────────────


def test_squash_message_subject_is_primitive_colon_slug():
    msg = _compose_squash_message("fix", "tidy-login-form", {})
    assert msg.splitlines()[0] == "fix: tidy-login-form"


def test_squash_message_includes_intent_and_coauthor():
    msg = _compose_squash_message(
        "feat", "introduce-payments",
        {"intent": "Let founders take card payments."})
    lines = msg.splitlines()
    assert lines[0] == "feat: introduce-payments"
    assert "Let founders take card payments." in msg
    assert "Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>" in msg


def test_squash_message_omits_empty_intent_but_keeps_coauthor():
    msg = _compose_squash_message("chore", "bump-deps", {"intent": ""})
    assert msg.splitlines()[0] == "chore: bump-deps"
    assert "Co-Authored-By:" in msg


# ─── #272: refuse to mark an EMPTY change shipped (the stacked-change harm) ──

import subprocess  # noqa: E402

import pytest  # noqa: E402


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)


def _init_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "f.txt").write_text("base")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, base


def test_own_commit_count_zero_for_branch_at_base(tmp_path):
    repo, base = _init_repo(tmp_path)
    _git(repo, "checkout", "-qb", "change/empty")  # at base — zero own commits
    assert _mod._change_own_commit_count(repo, base, "change/empty") == 0


def test_own_commit_count_positive_when_ahead(tmp_path):
    repo, base = _init_repo(tmp_path)
    _git(repo, "checkout", "-qb", "change/work")
    (repo / "g.txt").write_text("x")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "work")
    assert _mod._change_own_commit_count(repo, base, "change/work") == 1


def test_own_commit_count_none_when_base_unknown(tmp_path):
    repo, _ = _init_repo(tmp_path)
    # No base_sha to compare against → undeterminable (never blocks a ship).
    assert _mod._change_own_commit_count(repo, "", "change/work") is None


def test_archive_after_ship_refuses_empty_change(tmp_path, monkeypatch):
    """The #272 guard: a change whose branch has zero commits beyond its base
    is empty — nothing was built — and must NOT be markable as shipped."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "state"))
    import _change_state as cs

    repo, base = _init_repo(tmp_path)
    _git(repo, "checkout", "-qb", "change/fix-empty")  # at base — empty
    cid = "01J0000000000000000000000X"  # valid 26-char ULID
    cs.write_change_record(cid, {
        "change_id": cid, "handle": "CH-01J000", "slug": "empty",
        "primitive": "fix", "branch": "change/fix-empty",
        "base_sha": base, "worktree_path": str(tmp_path / "wt"),
    })
    with pytest.raises(SystemExit):  # emit_error → sys.exit(1)
        _mod._archive_after_ship(repo, cid, "change/fix-empty",
                                 tmp_path / "wt", remove_worktree=False)
    # And it did NOT flip the record to shipped.
    rec = cs.read_change_record(cid) or {}
    assert rec.get("stage") != "shipped"


def test_archive_after_ship_allows_nonempty_change(tmp_path, monkeypatch):
    """A change with real commits of its own ships normally (guard doesn't fire)."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path / "state"))
    import _change_state as cs

    repo, base = _init_repo(tmp_path)
    _git(repo, "checkout", "-qb", "change/fix-real")
    (repo / "g.txt").write_text("x")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "real work")
    cid = "01J0000000000000000000000Y"
    cs.write_change_record(cid, {
        "change_id": cid, "handle": "CH-01J000", "slug": "real",
        "primitive": "fix", "branch": "change/fix-real",
        "base_sha": base, "worktree_path": str(tmp_path / "wt"),
    })
    out = _mod._archive_after_ship(repo, cid, "change/fix-real",
                                   tmp_path / "wt", remove_worktree=False)
    assert out["stage"] == "shipped"
