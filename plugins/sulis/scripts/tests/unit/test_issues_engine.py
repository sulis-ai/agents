"""Unit tests for the type-agnostic issue-capture engine (`_issues.py`).

The engine partitions items into ``{to_create, duplicates, skipped}`` per a
descriptor (which dispositions are actionable, what the title prefix is,
what labels apply). Tests run against the LESSON descriptor (the original
type) to prove byte-equivalence with the v0.43.0 ``_lessons.py`` behaviour;
the descriptor itself is exercised in ``test_issue_descriptors.py``.

History: this file replaces ``test_lessons.py``; every assertion from there
is preserved, just routed through the parameterised engine.
"""

from __future__ import annotations

import _issues as issues_engine
from _issue_descriptors import LESSON


def _lesson(disposition, title="resolve_current_change returns null", **kw):
    d = {"id": "L-01", "title": title, "body": "symptom + root cause",
         "disposition": disposition}
    d.update(kw)
    return d


# ─── is_actionable ──────────────────────────────────────────────────────────


def test_sea_and_task_dispositions_are_actionable_for_lessons():
    assert issues_engine.is_actionable(_lesson("SEA"), LESSON)
    assert issues_engine.is_actionable(_lesson("TASK"), LESSON)
    assert issues_engine.is_actionable(_lesson("task"), LESSON)  # case-insensitive


def test_fix_now_fixed_note_are_not_actionable_for_lessons():
    assert not issues_engine.is_actionable(_lesson("FIX-NOW"), LESSON)
    assert not issues_engine.is_actionable(_lesson("FIXED"), LESSON)
    assert not issues_engine.is_actionable(_lesson("note"), LESSON)
    assert not issues_engine.is_actionable(_lesson(""), LESSON)


# ─── labels + title + body ──────────────────────────────────────────────────


def test_labels_always_include_base_label():
    assert "lesson" in issues_engine.issue_labels(_lesson("SEA"), LESSON)
    assert "lesson" in issues_engine.issue_labels(_lesson("TASK"), LESSON)


def test_actionable_lesson_labels_include_enhancement():
    assert "enhancement" in issues_engine.issue_labels(_lesson("SEA"), LESSON)


def test_label_order_is_stable_and_deduplicated():
    """Base labels come first, then extras in declared order; duplicates
    (e.g. a descriptor that lists the same label in both base and extras)
    appear at most once."""
    labels = issues_engine.issue_labels(_lesson("SEA"), LESSON)
    assert labels[0] == "lesson"
    assert len(labels) == len(set(labels))


def test_issue_title_is_stable_and_prefixed():
    t = issues_engine.issue_title(
        _lesson("SEA", title="Two tools disagree on the column"), LESSON)
    assert "Two tools disagree on the column" in t
    # stable prefix so a human + the dedup scan both recognise it as a lesson
    assert t.lower().startswith("lesson:")


def test_issue_body_carries_root_cause_and_disposition():
    body = issues_engine.issue_body(
        _lesson("SEA", body="the root cause text"), LESSON)
    assert "the root cause text" in body
    assert "SEA" in body


# ─── dedup_key ──────────────────────────────────────────────────────────────


def test_dedup_key_is_normalised_title_independent_of_descriptor():
    """The dedup key normalises whitespace + case off ``item['title']``;
    the descriptor's prefix is irrelevant to the key itself (it's only
    relevant when reducing an EXISTING ISSUE title to a key — that path is
    tested via partition below)."""
    a = issues_engine.dedup_key(_lesson("SEA", title="  Two Tools Disagree  "))
    b = issues_engine.dedup_key(_lesson("TASK", title="two tools disagree"))
    assert a == b  # case + whitespace insensitive → same key


# ─── partition_items ────────────────────────────────────────────────────────


def test_partition_routes_actionable_new_to_create():
    items = [_lesson("SEA", title="alpha"), _lesson("TASK", title="beta")]
    result = issues_engine.partition_items(items, existing_issue_titles=[],
                                           descriptor=LESSON)
    assert {i["title"] for i in result["to_create"]} == {"alpha", "beta"}
    assert result["duplicates"] == []
    assert result["skipped"] == []


def test_partition_skips_non_actionable():
    items = [_lesson("FIX-NOW", title="a"), _lesson("note", title="b"),
             _lesson("FIXED", title="c")]
    result = issues_engine.partition_items(items, existing_issue_titles=[],
                                           descriptor=LESSON)
    assert result["to_create"] == []
    assert {i["title"] for i in result["skipped"]} == {"a", "b", "c"}


def test_partition_dedups_against_existing_open_issues():
    items = [_lesson("SEA", title="already raised"),
             _lesson("SEA", title="brand new")]
    # An existing issue carries the prefixed title — proving the prefix-
    # tolerant key reducer recognises it as the same lesson.
    existing = [issues_engine.issue_title(
        _lesson("SEA", title="already raised"), LESSON)]
    result = issues_engine.partition_items(items,
                                           existing_issue_titles=existing,
                                           descriptor=LESSON)
    assert {i["title"] for i in result["to_create"]} == {"brand new"}
    assert {i["title"] for i in result["duplicates"]} == {"already raised"}


def test_partition_dedup_is_case_insensitive_against_existing():
    items = [_lesson("SEA", title="Mixed Case Title")]
    existing = [issues_engine.issue_title(
        _lesson("SEA", title="mixed case title"), LESSON)]
    result = issues_engine.partition_items(items,
                                           existing_issue_titles=existing,
                                           descriptor=LESSON)
    assert result["to_create"] == []
    assert len(result["duplicates"]) == 1


def test_partition_dedups_within_a_single_run():
    """If the same item appears twice in the input list, only the first is
    routed to to_create; the second is a duplicate (against the in-run
    seen-set)."""
    items = [_lesson("SEA", title="the same thing"),
             _lesson("TASK", title="the same thing")]
    result = issues_engine.partition_items(items, existing_issue_titles=[],
                                           descriptor=LESSON)
    assert len(result["to_create"]) == 1
    assert len(result["duplicates"]) == 1


def test_partition_existing_title_without_prefix_still_matches():
    """A pre-existing issue created BEFORE the prefix convention should
    still be matched as a duplicate via the prefix-tolerant key reducer
    (the prefix-strip in ``_title_to_key`` only applies when the prefix
    IS present; bare titles compare via the same normalisation)."""
    items = [_lesson("SEA", title="legacy title without prefix")]
    existing = ["legacy title without prefix"]  # no "lesson:" prefix
    result = issues_engine.partition_items(items,
                                           existing_issue_titles=existing,
                                           descriptor=LESSON)
    assert result["to_create"] == []
    assert len(result["duplicates"]) == 1
