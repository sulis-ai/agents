"""Lessons-capture core (#43) — pure triage/dedup, no I/O.

A lesson is captured after the ship stage with a disposition. Actionable
dispositions become durable GitHub issues; the rest do not:

  * SEA / TASK   → actionable → a `lesson` issue (durable backlog).
  * FIX-NOW / FIXED → the commit IS the record; no issue.
  * note         → digest only; no issue.

These functions decide what becomes an issue and dedup against issues already
open, so the gh-backed CLI (`sulis-lessons`) just executes the partition they
compute. Kept separate from `_wpxlib` (and I/O-free) so the logic is trivially
testable and the gh shell-outs live only in the CLI.

A lesson dict: {id, title, body, disposition}.
"""

from __future__ import annotations

ACTIONABLE_DISPOSITIONS: frozenset[str] = frozenset({"sea", "task"})

# Issue titles get this prefix so both a human scanning the issue list and the
# dedup scan recognise a lesson-derived issue unambiguously.
_TITLE_PREFIX = "lesson:"


def is_actionable(disposition: str) -> bool:
    """True if a lesson's disposition warrants a durable GitHub issue."""
    return str(disposition or "").strip().lower() in ACTIONABLE_DISPOSITIONS


def lesson_labels(disposition: str) -> list[str]:
    """GitHub labels for a lesson issue. Always `lesson`; actionable lessons
    are also `enhancement` (SEA/TASK are forward work, not defects-in-place)."""
    labels = ["lesson"]
    if is_actionable(disposition):
        labels.append("enhancement")
    return labels


def lesson_issue_title(lesson: dict) -> str:
    """Stable, prefixed issue title for a lesson (the dedup anchor)."""
    title = str(lesson.get("title", "")).strip()
    return f"{_TITLE_PREFIX} {title}"


def lesson_issue_body(lesson: dict) -> str:
    """Issue body: root cause + disposition + provenance back-link."""
    body = str(lesson.get("body", "")).strip()
    disposition = str(lesson.get("disposition", "")).strip()
    lesson_id = str(lesson.get("id", "")).strip()
    parts = [body or "(no detail captured)", ""]
    meta = f"_Captured as a lesson (disposition: {disposition}"
    if lesson_id:
        meta += f"; {lesson_id}"
    meta += ") by /sulis:capture-lessons._"
    parts.append(meta)
    return "\n".join(parts)


def dedup_key(lesson: dict) -> str:
    """Normalised key for matching a lesson against an existing issue —
    case- and whitespace-insensitive on the title."""
    return " ".join(str(lesson.get("title", "")).strip().lower().split())


def _title_to_key(issue_title: str) -> str:
    """Reduce an existing issue title (possibly prefixed) to a dedup key."""
    t = str(issue_title or "").strip()
    if t.lower().startswith(_TITLE_PREFIX):
        t = t[len(_TITLE_PREFIX):]
    return " ".join(t.strip().lower().split())


def partition_lessons(lessons: list[dict], existing_issue_titles: list[str]) -> dict:
    """Split lessons into {to_create, duplicates, skipped}.

    * skipped     — non-actionable (FIX-NOW / FIXED / note).
    * duplicates  — actionable, but an open `lesson` issue with the same key
                    already exists (don't re-raise).
    * to_create   — actionable + new.
    """
    existing_keys = {_title_to_key(t) for t in existing_issue_titles}
    to_create: list[dict] = []
    duplicates: list[dict] = []
    skipped: list[dict] = []
    seen_this_run: set[str] = set()

    for lesson in lessons:
        if not is_actionable(lesson.get("disposition", "")):
            skipped.append(lesson)
            continue
        key = dedup_key(lesson)
        if key in existing_keys or key in seen_this_run:
            duplicates.append(lesson)
            continue
        seen_this_run.add(key)
        to_create.append(lesson)

    return {"to_create": to_create, "duplicates": duplicates, "skipped": skipped}
