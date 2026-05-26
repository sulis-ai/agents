"""Unit tests for _change_context.py (WP-005 — pre-spawn recon writer).

write_change_context gathers change identity + git state + a primitive-
specific next-step hint and writes ~/.sulis/changes/{change_id}/CONTEXT.md.
Pure-read: it never modifies the repo. Git helpers are mocked so the tests
do not depend on a real repo's state.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

import _change_context as cc


_GOOD_ULID = "01HYQC71000000000000000000"


def _metadata(primitive: str = "create") -> dict:
    return {
        "change_id": _GOOD_ULID,
        "handle": "CH-01HYQC",
        "slug": "introduce-payments",
        "primitive": primitive,
        "branch": f"change/{primitive}-introduce-payments",
    }


def _patch_git():
    """Patch the three private git helpers to known values."""
    return (
        mock.patch.object(cc, "_head_sha", return_value="aaaa111"),
        mock.patch.object(cc, "_base_sha", return_value="bbbb222"),
        mock.patch.object(cc, "_ahead_behind", return_value=(3, 1)),
    )


def test_write_change_context_creates_file_at_expected_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab:
        path = cc.write_change_context(_GOOD_ULID, _metadata(), tmp_path)
    expected = tmp_path / ".sulis" / "changes" / _GOOD_ULID / "CONTEXT.md"
    assert path == expected
    assert path.exists()


def test_write_change_context_returns_absolute_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab:
        path = cc.write_change_context(_GOOD_ULID, _metadata(), tmp_path)
    assert path.is_absolute()


def test_write_change_context_includes_change_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    md = _metadata()
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab:
        path = cc.write_change_context(_GOOD_ULID, md, tmp_path)
    text = path.read_text()
    assert md["change_id"] in text
    assert md["handle"] in text
    assert md["slug"] in text
    assert md["primitive"] in text
    assert md["branch"] in text


def test_write_change_context_includes_git_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab:
        path = cc.write_change_context(_GOOD_ULID, _metadata(), tmp_path)
    text = path.read_text()
    assert "aaaa111" in text  # HEAD sha
    assert "bbbb222" in text  # base sha
    assert "3" in text and "1" in text  # ahead / behind


def test_write_change_context_includes_next_step_hint_for_create(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab:
        path = cc.write_change_context(_GOOD_ULID, _metadata("create"), tmp_path)
    assert "/sulis:specify" in path.read_text()


def test_write_change_context_includes_next_step_hint_for_fix(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab:
        path = cc.write_change_context(_GOOD_ULID, _metadata("fix"), tmp_path)
    assert "/sulis:analyse-codebase" in path.read_text()


def test_write_change_context_defaults_hint_for_unknown_primitive(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab:
        path = cc.write_change_context(_GOOD_ULID, _metadata("weirdo"), tmp_path)
    assert "/sulis:status" in path.read_text()


def test_write_change_context_does_not_modify_repo(tmp_path, monkeypatch):
    """Capture git status --porcelain before/after; assert identical."""
    monkeypatch.setenv("HOME", str(tmp_path))
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "dev"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    (repo / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)

    def _status() -> str:
        return subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo,
            capture_output=True, text=True, check=True,
        ).stdout

    before = _status()
    # Use real git helpers here (no mock) — they must be pure-read.
    cc.write_change_context(_GOOD_ULID, _metadata(), repo)
    after = _status()
    assert before == after


def test_write_change_context_creates_parent_dir_if_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert not (tmp_path / ".sulis").exists()
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab:
        path = cc.write_change_context(_GOOD_ULID, _metadata(), tmp_path)
    assert path.parent.exists()


# ─── Hardening: file-I/O guards (best-effort recon degrades to None) ──────


def test_write_change_context_returns_none_when_write_text_raises(tmp_path, monkeypatch):
    """An unwritable CONTEXT.md must degrade to None, not propagate a traceback.

    Recon is best-effort; a write failure must not crash `sulis-change start`.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab, \
            mock.patch.object(cc.Path, "write_text",
                              side_effect=PermissionError(13, "Permission denied")):
        result = cc.write_change_context(_GOOD_ULID, _metadata(), tmp_path)
    assert result is None


def test_write_change_context_returns_none_when_mkdir_raises(tmp_path, monkeypatch):
    """An unwritable ~/.sulis/changes dir must degrade to None, not raise."""
    monkeypatch.setenv("HOME", str(tmp_path))
    p_head, p_base, p_ab = _patch_git()
    with p_head, p_base, p_ab, \
            mock.patch.object(cc.Path, "mkdir",
                              side_effect=OSError(30, "Read-only file system")):
        result = cc.write_change_context(_GOOD_ULID, _metadata(), tmp_path)
    assert result is None


def test_primitive_hints_cover_all_change_primitives():
    """Hint table covers all 22 primitives + 3 CC fallbacks."""
    from _wpxlib import ALLOWED_CHANGE_PRIMITIVES
    for p in ALLOWED_CHANGE_PRIMITIVES:
        assert p in cc._PRIMITIVE_NEXT_STEP_HINTS, f"missing hint for {p}"
