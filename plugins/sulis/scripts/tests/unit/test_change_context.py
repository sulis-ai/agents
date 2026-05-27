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

import pytest

import _change_context as cc


_GOOD_ULID = "01HYQC71000000000000000000"


@pytest.fixture(autouse=True)
def _home_base_isolation(tmp_path_factory, monkeypatch):
    """This module asserts the ~/.sulis HOME-fallback CONTEXT.md path, so it
    opts out of the repo-wide SULIS_STATE_DIR isolation (root conftest) and
    isolates via HOME instead. Tests that set their own HOME override the
    default set here."""
    monkeypatch.delenv("SULIS_STATE_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))


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


# ─── #26: enrich CONTEXT.md with intent + linked issue + code-area pointers ──


def test_intent_section_renders_when_metadata_has_intent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    meta = _metadata("fix")
    meta["intent"] = "fix the silent-corrupt-record nuke bypass (closes #22)"
    with mock.patch.object(cc, "_resolve_linked_issues", return_value=[]), \
         mock.patch.object(cc, "_locate_code_areas", return_value=[]), \
         _patch_git()[0], _patch_git()[1], _patch_git()[2]:
        cc.write_change_context(_GOOD_ULID, meta, repo_root=tmp_path / "repo")
    body = (tmp_path / ".sulis" / "changes" / _GOOD_ULID / "CONTEXT.md").read_text()
    assert "## Intent" in body
    assert "fix the silent-corrupt-record nuke bypass" in body


def test_intent_section_omitted_when_metadata_lacks_intent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    meta = _metadata("fix")  # no intent key
    with mock.patch.object(cc, "_resolve_linked_issues", return_value=[]), \
         mock.patch.object(cc, "_locate_code_areas", return_value=[]), \
         _patch_git()[0], _patch_git()[1], _patch_git()[2]:
        cc.write_change_context(_GOOD_ULID, meta, repo_root=tmp_path / "repo")
    body = (tmp_path / ".sulis" / "changes" / _GOOD_ULID / "CONTEXT.md").read_text()
    assert "## Intent" not in body


def test_linked_issue_section_renders_when_gh_resolves(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    meta = _metadata("fix")
    meta["intent"] = "fix the silent-corrupt-record nuke bypass (closes #22)"
    issue = {
        "number": 22,
        "title": "nuke shipped-protection silently bypasses if change.json is unreadable",
        "labels": ["enhancement", "lesson"],
        "body": "Surfaced by Tier 4 of code-health…",
        "url": "https://github.com/sulis-ai/agents/issues/22",
    }
    with mock.patch.object(cc, "_resolve_linked_issues", return_value=[issue]), \
         mock.patch.object(cc, "_locate_code_areas", return_value=[]), \
         _patch_git()[0], _patch_git()[1], _patch_git()[2]:
        cc.write_change_context(_GOOD_ULID, meta, repo_root=tmp_path / "repo")
    body = (tmp_path / ".sulis" / "changes" / _GOOD_ULID / "CONTEXT.md").read_text()
    assert "## Linked issue" in body
    assert "#22" in body
    assert "nuke shipped-protection silently bypasses" in body
    assert "Surfaced by Tier 4" in body
    # Labels surfaced too — useful signal for the spawned Sulis
    assert "enhancement" in body or "lesson" in body


def test_linked_issue_section_handles_multiple_refs(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    meta = _metadata("fix")
    meta["intent"] = "fix both #22 and #23 in one go"
    issues = [
        {"number": 22, "title": "twenty-two", "labels": [], "body": "b22", "url": ""},
        {"number": 23, "title": "twenty-three", "labels": [], "body": "b23", "url": ""},
    ]
    with mock.patch.object(cc, "_resolve_linked_issues", return_value=issues), \
         mock.patch.object(cc, "_locate_code_areas", return_value=[]), \
         _patch_git()[0], _patch_git()[1], _patch_git()[2]:
        cc.write_change_context(_GOOD_ULID, meta, repo_root=tmp_path / "repo")
    body = (tmp_path / ".sulis" / "changes" / _GOOD_ULID / "CONTEXT.md").read_text()
    assert "#22" in body
    assert "#23" in body
    assert "twenty-two" in body
    assert "twenty-three" in body


def test_linked_issue_section_omitted_when_resolution_fails(tmp_path, monkeypatch):
    """gh unavailable / unauthenticated / network error → resolver returns []."""
    monkeypatch.setenv("HOME", str(tmp_path))
    meta = _metadata("fix")
    meta["intent"] = "fix #22"
    with mock.patch.object(cc, "_resolve_linked_issues", return_value=[]), \
         mock.patch.object(cc, "_locate_code_areas", return_value=[]), \
         _patch_git()[0], _patch_git()[1], _patch_git()[2]:
        cc.write_change_context(_GOOD_ULID, meta, repo_root=tmp_path / "repo")
    body = (tmp_path / ".sulis" / "changes" / _GOOD_ULID / "CONTEXT.md").read_text()
    assert "## Linked issue" not in body


def test_code_area_pointers_render_when_grep_finds_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    meta = _metadata("fix")
    meta["intent"] = "fix `cmd_nuke` and `read_change_record` in `_change_state.py`"
    pointers = [
        "plugins/sulis/scripts/sulis-change",
        "plugins/sulis/scripts/_change_state.py",
    ]
    with mock.patch.object(cc, "_resolve_linked_issues", return_value=[]), \
         mock.patch.object(cc, "_locate_code_areas", return_value=pointers), \
         _patch_git()[0], _patch_git()[1], _patch_git()[2]:
        cc.write_change_context(_GOOD_ULID, meta, repo_root=tmp_path / "repo")
    body = (tmp_path / ".sulis" / "changes" / _GOOD_ULID / "CONTEXT.md").read_text()
    assert "## Code-area pointers" in body
    assert "plugins/sulis/scripts/sulis-change" in body
    assert "plugins/sulis/scripts/_change_state.py" in body


def test_code_area_pointers_section_omitted_when_no_matches(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    meta = _metadata("fix")
    meta["intent"] = "fix something somewhere"
    with mock.patch.object(cc, "_resolve_linked_issues", return_value=[]), \
         mock.patch.object(cc, "_locate_code_areas", return_value=[]), \
         _patch_git()[0], _patch_git()[1], _patch_git()[2]:
        cc.write_change_context(_GOOD_ULID, meta, repo_root=tmp_path / "repo")
    body = (tmp_path / ".sulis" / "changes" / _GOOD_ULID / "CONTEXT.md").read_text()
    assert "## Code-area pointers" not in body


def test_section_order_intent_then_issue_then_pointers_then_hint(tmp_path, monkeypatch):
    """The spec mandates a fixed render order — Intent → Linked issue →
    Pointers → Suggested next step — so the spawned Sulis can rely on
    'last section is the hint' to read the actionable thing last."""
    monkeypatch.setenv("HOME", str(tmp_path))
    meta = _metadata("fix")
    meta["intent"] = "fix `cmd_nuke` per #22"
    issue = {"number": 22, "title": "t", "labels": [], "body": "b", "url": ""}
    with mock.patch.object(cc, "_resolve_linked_issues", return_value=[issue]), \
         mock.patch.object(cc, "_locate_code_areas",
                            return_value=["plugins/sulis/scripts/sulis-change"]), \
         _patch_git()[0], _patch_git()[1], _patch_git()[2]:
        cc.write_change_context(_GOOD_ULID, meta, repo_root=tmp_path / "repo")
    body = (tmp_path / ".sulis" / "changes" / _GOOD_ULID / "CONTEXT.md").read_text()
    intent_at = body.find("## Intent")
    issue_at = body.find("## Linked issue")
    pointers_at = body.find("## Code-area pointers")
    hint_at = body.find("## Suggested next step")
    assert -1 < intent_at < issue_at < pointers_at < hint_at, (
        f"order wrong: intent={intent_at} issue={issue_at} "
        f"pointers={pointers_at} hint={hint_at}"
    )


# ─── helper-level tests for the pure parts ─────────────────────────────────


def test_extract_issue_refs_finds_all_NN_tokens():
    refs = cc._extract_issue_refs("fix #22 and also #23, but not #notanumber")
    assert refs == [22, 23]


def test_extract_issue_refs_dedupes_and_preserves_order():
    refs = cc._extract_issue_refs("first #5 then #5 again then #1")
    assert refs == [5, 1]


def test_extract_issue_refs_empty_when_no_hashes():
    assert cc._extract_issue_refs("plain text with no hash refs") == []


def test_extract_code_tokens_picks_backtick_quoted_strings():
    tokens = cc._extract_code_tokens(
        "fix `cmd_nuke` and `read_change_record` in `_change_state.py`"
    )
    # Order preserved; deduped
    assert tokens == ["cmd_nuke", "read_change_record", "_change_state.py"]


def test_extract_code_tokens_ignores_short_tokens():
    """Single-char or two-char backticked tokens are likely noise."""
    tokens = cc._extract_code_tokens("see `a` and `ab` and `abc` and `cmd_nuke`")
    # Threshold: drop tokens shorter than 3 chars (config / domain heuristic)
    assert "a" not in tokens
    assert "ab" not in tokens
    assert "abc" in tokens
    assert "cmd_nuke" in tokens
