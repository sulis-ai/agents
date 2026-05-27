"""Unit tests for per-type descriptors in ``_issue_descriptors.py``.

The engine in ``_issues.py`` is exercised by test_issues_engine.py via the
LESSON descriptor; these tests pin the descriptor *fields themselves* — the
prefix, the dispositions, the label sets, the body formatter — so a change
to one descriptor can't silently affect the other.

Adding a new descriptor (e.g. FEEDBACK in Stage 2) means adding a section
here, not touching the engine tests.
"""

from __future__ import annotations

import pytest

from _issue_descriptors import (
    FEEDBACK,
    LESSON,
    available_descriptors,
    get_descriptor,
)
from _issues import is_actionable, issue_body, issue_labels, issue_title


# ─── Registry ───────────────────────────────────────────────────────────────


def test_lesson_descriptor_is_registered():
    assert "lesson" in available_descriptors()
    assert get_descriptor("lesson") is LESSON


def test_get_descriptor_is_case_insensitive():
    assert get_descriptor("LESSON") is LESSON
    assert get_descriptor("Lesson") is LESSON


def test_get_descriptor_raises_keyerror_on_unknown():
    with pytest.raises(KeyError) as exc:
        get_descriptor("nonsense")
    # Helpful message lists the available names.
    msg = str(exc.value)
    assert "nonsense" in msg
    assert "lesson" in msg


# ─── LESSON descriptor ──────────────────────────────────────────────────────


def test_lesson_prefix_is_lesson_colon():
    assert LESSON.title_prefix == "lesson:"


def test_lesson_dispositions_are_sea_and_task():
    assert LESSON.actionable_dispositions == frozenset({"sea", "task"})


def test_lesson_base_label_is_lesson():
    assert LESSON.base_labels == ["lesson"]


def test_lesson_sea_and_task_get_enhancement_label():
    """SEA/TASK lessons are forward work — should be tagged `enhancement`."""
    sea_labels = issue_labels(
        {"title": "x", "disposition": "SEA"}, LESSON)
    task_labels = issue_labels(
        {"title": "x", "disposition": "TASK"}, LESSON)
    assert "enhancement" in sea_labels
    assert "enhancement" in task_labels


def test_lesson_non_actionable_dispositions_get_no_enhancement_label():
    """A FIX-NOW item should NOT carry the `enhancement` label — even if
    the engine somehow let it through, the descriptor's extras-map
    shouldn't apply to dispositions outside its actionable set."""
    labels = issue_labels(
        {"title": "x", "disposition": "FIX-NOW"}, LESSON)
    assert "enhancement" not in labels


def test_lesson_body_format_includes_root_cause_and_provenance_attribution():
    body = issue_body(
        {"id": "L-15", "title": "x",
         "body": "the root cause text",
         "disposition": "SEA"},
        LESSON,
    )
    assert "the root cause text" in body
    # Disposition tag + captured-by attribution is the provenance back-link
    # that lets a maintainer trace an issue back to its lesson source.
    assert "SEA" in body
    assert "L-15" in body
    assert "/sulis:capture-lessons" in body


def test_lesson_body_handles_empty_input_gracefully():
    body = issue_body({"title": "x", "body": "", "disposition": "SEA"}, LESSON)
    # Sentinel for empty bodies — prevents the gh issue body being blank
    # without losing the disposition attribution.
    assert "no detail" in body.lower()
    assert "SEA" in body


def test_lesson_issue_title_prefixes_the_supplied_title():
    t = issue_title({"title": "the actual lesson title"}, LESSON)
    assert t == "lesson: the actual lesson title"


# ─── FEEDBACK descriptor ────────────────────────────────────────────────────


def test_feedback_descriptor_is_registered():
    assert "feedback" in available_descriptors()
    assert get_descriptor("feedback") is FEEDBACK


def test_feedback_prefix_is_feedback_colon():
    assert FEEDBACK.title_prefix == "feedback:"


def test_feedback_dispositions_cover_pattern_issue_bug_feedback():
    """All four founder-chosen disposition values are actionable — unlike
    lessons where FIX-NOW/note are skipped, every feedback disposition
    should land as a maintainer-triageable issue."""
    assert FEEDBACK.actionable_dispositions == frozenset(
        {"pattern", "issue", "bug", "feedback"}
    )
    for disp in ("pattern", "issue", "bug", "feedback"):
        assert is_actionable(
            {"title": "x", "disposition": disp}, FEEDBACK
        ), f"feedback disposition {disp!r} should be actionable"


def test_feedback_base_label_is_feedback():
    assert FEEDBACK.base_labels == ["feedback"]


def test_feedback_disposition_sub_labels():
    """Each disposition becomes its own sub-label so the maintainers can
    filter the backlog by feedback class (pattern vs bug vs issue vs
    just-feedback)."""
    pattern_labels = issue_labels(
        {"title": "x", "disposition": "pattern"}, FEEDBACK)
    bug_labels = issue_labels(
        {"title": "x", "disposition": "bug"}, FEEDBACK)
    issue_labels_ = issue_labels(
        {"title": "x", "disposition": "issue"}, FEEDBACK)
    feedback_only = issue_labels(
        {"title": "x", "disposition": "feedback"}, FEEDBACK)

    assert "feedback" in pattern_labels and "pattern" in pattern_labels
    assert "feedback" in bug_labels and "bug" in bug_labels
    assert "feedback" in issue_labels_ and "issue" in issue_labels_
    # Plain "feedback" disposition: just the base label, no duplication.
    assert feedback_only == ["feedback"]


def test_feedback_body_carries_summary_and_provenance():
    body = issue_body(
        {"id": "FB-01", "title": "x",
         "body": "founder's redacted summary text",
         "disposition": "bug"},
        FEEDBACK,
    )
    assert "founder's redacted summary text" in body
    assert "bug" in body
    assert "FB-01" in body
    assert "/sulis:feedback" in body


def test_feedback_body_includes_redaction_count_when_provided():
    body = issue_body(
        {"title": "x", "body": "the body",
         "disposition": "feedback",
         "redactions_applied": 7},
        FEEDBACK,
    )
    # The anonymiser provenance footer should surface "7 redaction(s)" so a
    # maintainer reading the issue knows how aggressively the founder's
    # text was scrubbed.
    assert "7 redaction" in body


def test_feedback_body_omits_redaction_count_when_zero_or_missing():
    body_no_field = issue_body(
        {"title": "x", "body": "y", "disposition": "feedback"}, FEEDBACK)
    body_zero = issue_body(
        {"title": "x", "body": "y", "disposition": "feedback",
         "redactions_applied": 0}, FEEDBACK)
    assert "redaction" not in body_no_field.lower()
    assert "redaction" not in body_zero.lower()


def test_feedback_issue_title_prefixes_the_supplied_title():
    t = issue_title({"title": "the dashboard liveness check is wrong"},
                    FEEDBACK)
    assert t == "feedback: the dashboard liveness check is wrong"


def test_feedback_does_not_inherit_lesson_extras():
    """The `enhancement` label is lesson-specific. A feedback item with a
    SEA/TASK-like disposition (which isn't valid for feedback anyway)
    must NOT pick up the lesson's extras — the descriptors are disjoint."""
    labels = issue_labels(
        {"title": "x", "disposition": "bug"}, FEEDBACK)
    assert "enhancement" not in labels
