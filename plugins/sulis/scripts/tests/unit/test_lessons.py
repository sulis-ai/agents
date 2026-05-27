"""Unit tests for the lessons-capture triage/dedup core (#43).

A "lesson" is captured after the ship stage with a disposition. Actionable
dispositions (SEA / TASK) become durable GitHub issues; the rest (FIX-NOW /
FIXED — the commit is the record; note — digest only) do not. These pure
functions decide what becomes an issue and dedup against issues already open,
so the gh-backed CLI just executes the partition they compute.
"""

from __future__ import annotations

from _lessons import (
    dedup_key,
    is_actionable,
    lesson_issue_body,
    lesson_issue_title,
    lesson_labels,
    partition_lessons,
)


def _lesson(disposition, title="resolve_current_change returns null", **kw):
    d = {"id": "L-01", "title": title, "body": "symptom + root cause",
         "disposition": disposition}
    d.update(kw)
    return d


# ─── is_actionable ──────────────────────────────────────────────────────────


def test_sea_and_task_are_actionable():
    assert is_actionable("SEA")
    assert is_actionable("TASK")
    assert is_actionable("task")  # case-insensitive


def test_fix_now_fixed_note_are_not_actionable():
    assert not is_actionable("FIX-NOW")
    assert not is_actionable("FIXED")
    assert not is_actionable("note")
    assert not is_actionable("")


# ─── labels + title + body ──────────────────────────────────────────────────


def test_labels_always_include_lesson():
    assert "lesson" in lesson_labels("SEA")
    assert "lesson" in lesson_labels("TASK")


def test_actionable_labels_include_enhancement():
    assert "enhancement" in lesson_labels("SEA")


def test_issue_title_is_stable_and_prefixed():
    t = lesson_issue_title(_lesson("SEA", title="Two tools disagree on the column"))
    assert "Two tools disagree on the column" in t
    # stable prefix so a human + the dedup scan both recognise it as a lesson
    assert t.lower().startswith("lesson:")


def test_issue_body_carries_root_cause_and_disposition():
    body = lesson_issue_body(_lesson("SEA", body="the root cause text"))
    assert "the root cause text" in body
    assert "SEA" in body


# ─── dedup_key ──────────────────────────────────────────────────────────────


def test_dedup_key_is_normalised_title():
    a = dedup_key(_lesson("SEA", title="  Two Tools Disagree  "))
    b = dedup_key(_lesson("TASK", title="two tools disagree"))
    assert a == b  # case + whitespace insensitive → same key


# ─── partition_lessons ──────────────────────────────────────────────────────


def test_partition_routes_actionable_new_to_create():
    lessons = [_lesson("SEA", title="alpha"), _lesson("TASK", title="beta")]
    result = partition_lessons(lessons, existing_issue_titles=[])
    assert {l["title"] for l in result["to_create"]} == {"alpha", "beta"}
    assert result["duplicates"] == []
    assert result["skipped"] == []


def test_partition_skips_non_actionable():
    lessons = [_lesson("FIX-NOW", title="a"), _lesson("note", title="b"),
               _lesson("FIXED", title="c")]
    result = partition_lessons(lessons, existing_issue_titles=[])
    assert result["to_create"] == []
    assert {l["title"] for l in result["skipped"]} == {"a", "b", "c"}


def test_partition_dedups_against_existing_open_issues():
    lessons = [_lesson("SEA", title="already raised"),
               _lesson("SEA", title="brand new")]
    # an existing issue carries the prefixed title
    existing = [lesson_issue_title(_lesson("SEA", title="already raised"))]
    result = partition_lessons(lessons, existing_issue_titles=existing)
    assert {l["title"] for l in result["to_create"]} == {"brand new"}
    assert {l["title"] for l in result["duplicates"]} == {"already raised"}


def test_partition_dedup_is_case_insensitive():
    lessons = [_lesson("SEA", title="Mixed Case Title")]
    existing = [lesson_issue_title(_lesson("SEA", title="mixed case title"))]
    result = partition_lessons(lessons, existing_issue_titles=existing)
    assert result["to_create"] == []
    assert len(result["duplicates"]) == 1
