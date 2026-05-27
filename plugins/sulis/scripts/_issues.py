"""Issue-capture engine — pure triage/dedup, type-agnostic (#20).

A founder-facing skill (`/sulis:capture-lessons`, `/sulis:feedback`, ...) hands
this module a list of items + the existing open issue titles + a *descriptor*
(see `_issue_descriptors.py`) that tells the engine which dispositions are
actionable, what title prefix to expect, and how to format an issue.

The engine then partitions the items into ``{to_create, duplicates, skipped}``;
the gh-backed CLI (``sulis-issues``) just executes the partition.

Kept I/O-free so the logic is trivially testable and the gh shell-outs live
only in the CLI. Replaces the type-coupled ``_lessons.py`` from v0.43.0; per
EP-03, the extraction lands in the same change as the second consumer
(feedback), so the engine has two real users from day one and the
parameterisation is justified by use, not by speculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class IssueTypeDescriptor:
    """Per-type configuration plugged into the engine.

    Fields:
      * ``name`` — short stable name (``"lesson"``, ``"feedback"``). The CLI
        flag value.
      * ``title_prefix`` — the stable prefix every issue carries, both for
        human scanability and for the dedup scan to recognise its own. Must
        end with ``":"`` and a space-separated suffix (e.g. ``"lesson:"``).
      * ``actionable_dispositions`` — dispositions that warrant a real issue.
        Other dispositions are *skipped* (digest-only / commit-is-record).
        Stored lowercased.
      * ``base_labels`` — labels always applied (e.g. ``["lesson"]`` or
        ``["feedback"]``).
      * ``extra_labels_for_disposition`` — disposition → list[str] of extra
        labels. Keys lowercased. Use this for sub-classification
        (``"bug"`` → ``["bug"]``, ``"sea"`` → ``["enhancement"]`` etc.).
      * ``format_body`` — ``item -> str`` formatter that produces the issue
        body, including provenance / disposition / captured-by attribution.
        Title is composed mechanically (prefix + ``item["title"]``); body is
        per-descriptor.
    """

    name: str
    title_prefix: str
    actionable_dispositions: frozenset[str]
    base_labels: list[str]
    extra_labels_for_disposition: dict[str, list[str]] = field(default_factory=dict)
    format_body: Callable[[dict], str] = lambda item: str(item.get("body", "") or "").strip()


# ─── Public API ──────────────────────────────────────────────────────────────


def is_actionable(item: dict, descriptor: IssueTypeDescriptor) -> bool:
    """True if an item's disposition warrants a durable GitHub issue."""
    disposition = str(item.get("disposition", "") or "").strip().lower()
    return disposition in descriptor.actionable_dispositions


def issue_title(item: dict, descriptor: IssueTypeDescriptor) -> str:
    """Stable, prefixed issue title (the dedup anchor).

    Composition: ``"{title_prefix} {item['title']}"``. The single space after
    the colon is preserved so an existing issue created without the prefix
    matches via the prefix-tolerant ``_title_to_key`` normaliser below.
    """
    title = str(item.get("title", "") or "").strip()
    return f"{descriptor.title_prefix} {title}"


def issue_body(item: dict, descriptor: IssueTypeDescriptor) -> str:
    """Issue body produced by the descriptor's formatter."""
    return descriptor.format_body(item)


def issue_labels(item: dict, descriptor: IssueTypeDescriptor) -> list[str]:
    """Labels for the GitHub issue: base labels + disposition-derived extras.

    Returned in stable order: base first, then extras in the order the
    descriptor declared them. De-duplicated while preserving order.
    """
    disposition = str(item.get("disposition", "") or "").strip().lower()
    extras = descriptor.extra_labels_for_disposition.get(disposition, [])
    seen: set[str] = set()
    out: list[str] = []
    for label in (*descriptor.base_labels, *extras):
        if label and label not in seen:
            seen.add(label)
            out.append(label)
    return out


def dedup_key(item: dict) -> str:
    """Normalised key for matching an item against an existing issue —
    case- and whitespace-insensitive on the title. Independent of descriptor:
    the prefix is stripped *off the existing issue title* in
    ``_title_to_key`` before comparing keys."""
    return " ".join(str(item.get("title", "") or "").strip().lower().split())


def _title_to_key(issue_title: str, descriptor: IssueTypeDescriptor) -> str:
    """Reduce an existing issue title (with or without the descriptor's
    prefix) to a dedup key. Prefix is matched case-insensitively."""
    t = str(issue_title or "").strip()
    prefix = descriptor.title_prefix
    if t.lower().startswith(prefix.lower()):
        t = t[len(prefix):]
    return " ".join(t.strip().lower().split())


def partition_items(items: list[dict], existing_issue_titles: list[str],
                    descriptor: IssueTypeDescriptor) -> dict:
    """Split items into ``{to_create, duplicates, skipped}`` per the descriptor.

    * ``skipped``    — disposition is not in ``descriptor.actionable_dispositions``.
    * ``duplicates`` — actionable, but an open issue with the same key already
      exists (either in ``existing_issue_titles`` or seen earlier in this run).
    * ``to_create``  — actionable + new (this run + against the open backlog).
    """
    existing_keys = {_title_to_key(t, descriptor) for t in existing_issue_titles}
    to_create: list[dict] = []
    duplicates: list[dict] = []
    skipped: list[dict] = []
    seen_this_run: set[str] = set()

    for item in items:
        if not is_actionable(item, descriptor):
            skipped.append(item)
            continue
        key = dedup_key(item)
        if key in existing_keys or key in seen_this_run:
            duplicates.append(item)
            continue
        seen_this_run.add(key)
        to_create.append(item)

    return {"to_create": to_create, "duplicates": duplicates, "skipped": skipped}
