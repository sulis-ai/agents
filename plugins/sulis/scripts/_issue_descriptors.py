"""Per-type descriptors for the issue-capture engine (``_issues.py``).

Each descriptor plugs the type-agnostic engine into a specific use-case:
which dispositions are actionable, what title prefix the issues carry,
what labels GitHub gets, and how the body is formatted.

Registry lookup at ``get_descriptor("lesson") | get_descriptor("feedback")``
is what ``sulis-issues`` uses to dispatch by ``--descriptor`` flag value.

History: extracted from ``_lessons.py`` v0.43.0 when the second consumer
(feedback) landed (#20 / EP-03).
"""

from __future__ import annotations

from _issues import IssueTypeDescriptor


# ─── LESSON descriptor ──────────────────────────────────────────────────────
#
# A "lesson" is captured after the ship stage with a disposition. Actionable
# dispositions become durable GitHub issues; the rest don't:
#
#   * SEA / TASK   → actionable → a `lesson` issue (durable backlog).
#   * FIX-NOW / FIXED → the commit IS the record; no issue.
#   * note         → digest only; no issue.

def _format_lesson_body(item: dict) -> str:
    """Lesson issue body: root cause + disposition + provenance back-link."""
    body = str(item.get("body", "") or "").strip()
    disposition = str(item.get("disposition", "") or "").strip()
    item_id = str(item.get("id", "") or "").strip()
    parts = [body or "(no detail captured)", ""]
    meta = f"_Captured as a lesson (disposition: {disposition}"
    if item_id:
        meta += f"; {item_id}"
    meta += ") by /sulis:capture-lessons._"
    parts.append(meta)
    return "\n".join(parts)


LESSON = IssueTypeDescriptor(
    name="lesson",
    title_prefix="lesson:",
    actionable_dispositions=frozenset({"sea", "task"}),
    base_labels=["lesson"],
    extra_labels_for_disposition={
        # SEA/TASK lessons are forward work, not defects-in-place — tag them
        # `enhancement` so they sort sensibly in the backlog view.
        "sea": ["enhancement"],
        "task": ["enhancement"],
    },
    format_body=_format_lesson_body,
)


# ─── FEEDBACK descriptor ────────────────────────────────────────────────────
#
# Feedback comes from a Sulis founder using `/sulis:feedback`. Unlike lessons
# (the agent's own retrospective), feedback is the human's voice: a pattern
# they noticed, an issue they hit, a bug they think they spotted, or
# generic product feedback. Every disposition is actionable — the
# marketplace maintainers want all four classes on their backlog.

_FEEDBACK_DISPOSITIONS = frozenset({"pattern", "issue", "bug", "feedback"})


def _format_feedback_body(item: dict) -> str:
    """Feedback issue body: founder summary + redaction provenance.

    The body has already passed through the anonymiser (``_anonymiser.py``)
    by the time it reaches the CLI — placeholders like ``<path>``,
    ``<email>``, ``<project>`` are in the text. This formatter just
    appends the standard provenance footer so a maintainer reading the
    issue knows it came from the feedback skill with the redaction
    pipeline applied.
    """
    body = str(item.get("body", "") or "").strip()
    disposition = str(item.get("disposition", "") or "").strip()
    item_id = str(item.get("id", "") or "").strip()
    redactions = item.get("redactions_applied")  # int or None
    parts = [body or "(no detail captured)", ""]
    meta = f"_Captured via /sulis:feedback (disposition: {disposition}"
    if item_id:
        meta += f"; {item_id}"
    if isinstance(redactions, int) and redactions > 0:
        meta += f"; {redactions} redaction(s) applied"
    meta += ")._"
    parts.append(meta)
    return "\n".join(parts)


FEEDBACK = IssueTypeDescriptor(
    name="feedback",
    title_prefix="feedback:",
    actionable_dispositions=_FEEDBACK_DISPOSITIONS,
    base_labels=["feedback"],
    extra_labels_for_disposition={
        # Each disposition becomes its own sub-label so the maintainers can
        # filter the backlog by what kind of feedback came in.
        "pattern": ["pattern"],
        "issue": ["issue"],
        "bug": ["bug"],
        # Plain "feedback" disposition adds no extras — the base label is
        # already `feedback`.
    },
    format_body=_format_feedback_body,
)


# ─── Registry ───────────────────────────────────────────────────────────────


_REGISTRY: dict[str, IssueTypeDescriptor] = {
    LESSON.name: LESSON,
    FEEDBACK.name: FEEDBACK,
}


def get_descriptor(name: str) -> IssueTypeDescriptor:
    """Look up a descriptor by name. Raises ``KeyError`` with a helpful
    message listing available names if the name doesn't match."""
    key = (name or "").strip().lower()
    if key not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY))
        raise KeyError(
            f"unknown descriptor: {name!r}. Available: {available}"
        )
    return _REGISTRY[key]


def available_descriptors() -> list[str]:
    """Sorted list of descriptor names, for CLI help text."""
    return sorted(_REGISTRY)
