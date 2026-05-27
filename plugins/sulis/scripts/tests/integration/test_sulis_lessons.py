"""Integration tests for `sulis-lessons capture` (#43).

Drives the real CLI via subprocess with a fake `gh` on PATH (mock_gh). The
deterministic triage/dedup is unit-tested in test_lessons.py; here we prove the
gh orchestration: actionable + new → an issue is created; actionable + already
open → deduped; non-actionable → skipped; gh unavailable → clean degrade.
"""

from __future__ import annotations

import json
from pathlib import Path


def _write_lessons(tmp_path: Path, lessons: list[dict]) -> Path:
    p = tmp_path / "lessons.json"
    p.write_text(json.dumps(lessons), encoding="utf-8")
    return p


def test_capture_creates_dedups_and_skips(tmp_path, run_tool, mock_gh):
    lessons = [
        {"id": "L-01", "title": "brand new lesson", "body": "root cause",
         "disposition": "SEA"},
        {"id": "L-02", "title": "already raised", "body": "x",
         "disposition": "TASK"},
        {"id": "L-03", "title": "trivial fixed inline", "body": "x",
         "disposition": "FIX-NOW"},
    ]
    f = _write_lessons(tmp_path, lessons)
    mock_gh([
        {"match": "auth status", "stdout": "Logged in"},
        # the existing open lesson issue carries the prefixed title
        {"match": "issue list",
         "stdout": json.dumps([{"title": "lesson: already raised"}])},
        {"match": "label create", "stdout": "label created"},
        {"match": "issue create",
         "stdout": "https://github.com/o/r/issues/42\n"},
    ])
    result = run_tool("sulis-lessons", "capture", "--lessons-file", str(f),
                      "--repo", "o/r")
    assert result.ok, f"capture failed: {result.error}; {result.stderr[-300:]}"
    data = result.data
    assert data["degraded"] is False
    assert [c["title"] for c in data["created"]] == ["brand new lesson"]
    assert data["created"][0]["url"].endswith("/issues/42")
    assert data["duplicates"] == ["already raised"]
    assert data["skipped"] == ["trivial fixed inline"]


def test_capture_dry_run_creates_nothing(tmp_path, run_tool, mock_gh):
    lessons = [{"id": "L-01", "title": "a lesson", "body": "x",
                "disposition": "SEA"}]
    f = _write_lessons(tmp_path, lessons)
    mock_gh([
        {"match": "auth status", "stdout": "Logged in"},
        {"match": "issue list", "stdout": "[]"},
        # If the CLI tried to create on a dry run, this would be the only
        # create response — its ABSENCE from `created` proves it didn't.
        {"match": "issue create", "stdout": "https://x/issues/1\n"},
    ])
    result = run_tool("sulis-lessons", "capture", "--lessons-file", str(f),
                      "--repo", "o/r", "--dry-run")
    assert result.ok
    assert result.data["dry_run"] is True
    assert result.data["would_create"] == ["a lesson"]
    assert "created" not in result.data


def test_capture_degrades_when_gh_unavailable(tmp_path, run_tool, mock_gh):
    lessons = [{"id": "L-01", "title": "a lesson", "body": "x",
                "disposition": "SEA"}]
    f = _write_lessons(tmp_path, lessons)
    # gh auth status fails → not authenticated / unavailable.
    mock_gh([{"match": "auth status", "stderr": "not logged in", "exit_code": 1}])
    result = run_tool("sulis-lessons", "capture", "--lessons-file", str(f))
    assert result.ok, f"degrade should still emit ok JSON: {result.stderr[-300:]}"
    assert result.data["degraded"] is True
    assert result.data["created"] == []
    assert result.data["would_create"] == ["a lesson"]


def test_capture_missing_lessons_file_errors(tmp_path, run_tool, mock_gh):
    mock_gh([{"match": "auth status", "stdout": "Logged in"}])
    result = run_tool("sulis-lessons", "capture",
                      "--lessons-file", str(tmp_path / "nope.json"))
    assert not result.ok
    assert "not found" in (result.error or "")


# ─── #23: gh issue list dedup query uses --search (immediate), not --label ──


def test_capture_dedup_uses_search_query_not_label_filter(
    tmp_path, run_tool, mock_gh,
):
    """gh's `--label` filter uses the eventually-consistent REST API search
    index; `--search` uses the GraphQL backend that's immediate. The dedup
    scan after creating an issue in another tab/process must see the issue,
    not miss it for ~minutes (#23).

    Strategy: the stub responds ONLY to `--search`. If sulis-lessons still
    uses `--label`, that argv won't include `--search`, the stub falls
    through, the dedup query returns nothing, and the test sees the lesson
    as NOT a duplicate. After the fix, the stub matches `--search`, returns
    the existing-lesson stub, and dedup correctly flags the duplicate.
    """
    lessons = [{"id": "L-01", "title": "already raised", "body": "x",
                "disposition": "SEA"}]
    f = _write_lessons(tmp_path, lessons)
    mock_gh([
        {"match": "auth status", "stdout": "Logged in"},
        # Only matches the new --search form — not the legacy --label filter:
        {"match": "--search",
         "stdout": json.dumps([{"title": "lesson: already raised"}])},
        # Bare 'issue create' fallback so a regression doesn't silently create:
        {"match": "issue create",
         "stdout": "https://github.com/o/r/issues/42\n"},
    ])
    result = run_tool("sulis-lessons", "capture",
                      "--lessons-file", str(f), "--repo", "o/r")
    assert result.ok, f"capture failed: {result.error}"
    # If the --search query was used → dedup found the existing issue →
    # to_create is empty + duplicates has 'already raised'.
    assert result.data["created"] == [], (
        f"expected dedup to flag the issue as a duplicate via --search, "
        f"but {len(result.data['created'])} issue(s) were created — the "
        f"CLI is probably still using --label (the legacy eventually-"
        f"consistent form). created={result.data['created']}"
    )
    assert result.data["duplicates"] == ["already raised"]


