"""Integration tests for `sulis-issues capture` against the lesson descriptor.

Drives the real CLI via subprocess with a fake `gh` on PATH (mock_gh). The
deterministic triage/dedup is unit-tested in test_issues_engine.py +
test_issue_descriptors.py; here we prove the gh orchestration:
actionable + new → an issue is created; actionable + already open →
deduped; non-actionable → skipped; gh unavailable → clean degrade.

History: this file replaces ``test_sulis_lessons.py``. Every assertion is
preserved; only the CLI invocation changed
(``sulis-lessons capture --items-file X`` →
``sulis-issues capture --descriptor lesson --items-file X``).
"""

from __future__ import annotations

import json
from pathlib import Path


def _write_items(tmp_path: Path, items: list[dict]) -> Path:
    p = tmp_path / "items.json"
    p.write_text(json.dumps(items), encoding="utf-8")
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
    f = _write_items(tmp_path, lessons)
    mock_gh([
        {"match": "auth status", "stdout": "Logged in"},
        # the existing open lesson issue carries the prefixed title
        {"match": "issue list",
         "stdout": json.dumps([{"title": "lesson: already raised"}])},
        {"match": "label create", "stdout": "label created"},
        {"match": "issue create",
         "stdout": "https://github.com/o/r/issues/42\n"},
    ])
    result = run_tool("sulis-issues", "capture", "--descriptor", "lesson", "--items-file", str(f),
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
    f = _write_items(tmp_path, lessons)
    mock_gh([
        {"match": "auth status", "stdout": "Logged in"},
        {"match": "issue list", "stdout": "[]"},
        # If the CLI tried to create on a dry run, this would be the only
        # create response — its ABSENCE from `created` proves it didn't.
        {"match": "issue create", "stdout": "https://x/issues/1\n"},
    ])
    result = run_tool("sulis-issues", "capture", "--descriptor", "lesson", "--items-file", str(f),
                      "--repo", "o/r", "--dry-run")
    assert result.ok
    assert result.data["dry_run"] is True
    assert result.data["would_create"] == ["a lesson"]
    assert "created" not in result.data


def test_capture_degrades_when_gh_unavailable(tmp_path, run_tool, mock_gh):
    lessons = [{"id": "L-01", "title": "a lesson", "body": "x",
                "disposition": "SEA"}]
    f = _write_items(tmp_path, lessons)
    # gh auth status fails → not authenticated / unavailable.
    mock_gh([{"match": "auth status", "stderr": "not logged in", "exit_code": 1}])
    result = run_tool("sulis-issues", "capture", "--descriptor", "lesson", "--items-file", str(f))
    assert result.ok, f"degrade should still emit ok JSON: {result.stderr[-300:]}"
    assert result.data["degraded"] is True
    assert result.data["created"] == []
    assert result.data["would_create"] == ["a lesson"]


def test_capture_missing_lessons_file_errors(tmp_path, run_tool, mock_gh):
    mock_gh([{"match": "auth status", "stdout": "Logged in"}])
    result = run_tool("sulis-issues", "capture", "--descriptor", "lesson",
                      "--items-file", str(tmp_path / "nope.json"))
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
    f = _write_items(tmp_path, lessons)
    mock_gh([
        {"match": "auth status", "stdout": "Logged in"},
        # Only matches the new --search form — not the legacy --label filter:
        {"match": "--search",
         "stdout": json.dumps([{"title": "lesson: already raised"}])},
        # Bare 'issue create' fallback so a regression doesn't silently create:
        {"match": "issue create",
         "stdout": "https://github.com/o/r/issues/42\n"},
    ])
    result = run_tool("sulis-issues", "capture", "--descriptor", "lesson",
                      "--items-file", str(f), "--repo", "o/r")
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


# ─── FEEDBACK descriptor: end-to-end via the same CLI ─────────────────────────


def test_capture_feedback_creates_issue_via_same_cli(
    tmp_path, run_tool, mock_gh,
):
    """The same `sulis-issues capture` CLI handles the feedback descriptor
    end-to-end — no separate tool needed. Pins that the dedup query
    targets the feedback base label (`label:feedback is:open`) AND that
    the result envelope tags the descriptor name. The gh argv label
    construction (`--label feedback --label bug` for a bug-disposition
    item) is already covered by ``test_feedback_disposition_sub_labels``
    in test_issue_descriptors.py."""
    items = [{"id": "FB-01", "title": "dashboard liveness wrong",
              "body": "redacted founder body",
              "disposition": "bug"}]
    f = _write_items(tmp_path, items)
    mock_gh([
        {"match": "auth status", "stdout": "Logged in"},
        # Dedup query searches against `label:feedback is:open` (per
        # descriptor.base_labels[0]) — NOT against `label:lesson`. If the
        # CLI routed to the wrong descriptor's label, this stub won't
        # match and the dedup falls through (no existing issues seen).
        {"match": "label:feedback is:open", "stdout": "[]"},
        {"match": "label create", "stdout": "label created"},
        {"match": "issue create",
         "stdout": "https://github.com/o/r/issues/99\n"},
    ])
    result = run_tool("sulis-issues", "capture", "--descriptor", "feedback",
                      "--items-file", str(f), "--repo", "o/r")
    assert result.ok, f"capture failed: {result.error}"
    assert result.data["descriptor"] == "feedback"
    assert [c["title"] for c in result.data["created"]] == [
        "dashboard liveness wrong"]


def test_capture_feedback_dedups_against_open_feedback_issues(
    tmp_path, run_tool, mock_gh,
):
    """Feedback dedup must use the feedback prefix + the feedback base
    label, NOT the lesson prefix/label. Catches the "wrong descriptor
    routes to wrong label filter" failure mode."""
    items = [{"id": "FB-01", "title": "already filed",
              "body": "x", "disposition": "issue"}]
    f = _write_items(tmp_path, items)
    mock_gh([
        {"match": "auth status", "stdout": "Logged in"},
        # The existing open feedback issue carries the `feedback:` prefix.
        {"match": "label:feedback is:open",
         "stdout": json.dumps([{"title": "feedback: already filed"}])},
        {"match": "issue create",
         "stdout": "https://github.com/o/r/issues/100\n"},
    ])
    result = run_tool("sulis-issues", "capture", "--descriptor", "feedback",
                      "--items-file", str(f), "--repo", "o/r")
    assert result.ok
    assert result.data["created"] == []
    assert result.data["duplicates"] == ["already filed"]


def test_capture_with_unknown_descriptor_errors(tmp_path, run_tool, mock_gh):
    """Typo / unsupported descriptor — must fail fast with a helpful
    message that lists the available descriptors. No gh calls happen."""
    items = [{"id": "X", "title": "x", "body": "x", "disposition": "feedback"}]
    f = _write_items(tmp_path, items)
    mock_gh([])  # no gh calls expected before the descriptor lookup
    result = run_tool("sulis-issues", "capture", "--descriptor", "nonsense",
                      "--items-file", str(f))
    assert not result.ok
    err = (result.error or "").lower()
    # Helpful message: names the bad descriptor + lists the available ones.
    assert "nonsense" in err
    assert "lesson" in err
    assert "feedback" in err

