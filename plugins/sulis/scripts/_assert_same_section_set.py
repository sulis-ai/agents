#!/usr/bin/env python3
"""_assert_same_section_set.py — assert two or more documents carry the
identical set of section headings (SC-02, FR-02).

Depth sizes only the interview, never which sections exist — so a document
produced at lite depth and one produced at deep depth MUST have the same
section set. This inspector compares the normalised header sets of all the
given documents and exits 0 iff they are identical; on drift it names the
headings that are present in some documents but missing from others.

Header detection is delegated to ``_doc_section_parse`` — the single source of
truth shared by all five WP-003 inspectors.

Usage:
    _assert_same_section_set.py <doc> <doc> [<doc> ...]

Exit codes:
  0 — every document has the same section set
  1 — the section sets differ (the drifting headings are named on stderr)
  2 — bad input (fewer than two docs, or a file unreadable)

Pure inspector — reads the docs, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _doc_section_parse import section_keys


def section_set_drift(doc_keys: dict[str, set[str]]) -> set[str]:
    """Given ``{doc_path: section_key_set}``, return the set of header keys
    that are NOT shared by every document (present in some, absent from
    others). Empty set ⇒ identical section sets."""
    if len(doc_keys) < 2:
        return set()
    union: set[str] = set()
    intersection: set[str] | None = None
    for keys in doc_keys.values():
        union |= keys
        intersection = keys if intersection is None else (intersection & keys)
    return union - (intersection or set())


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_same_section_set.py",
        description="Exit 0 iff every document has the identical section set.",
    )
    parser.add_argument("docs", nargs="+", help="Two or more markdown documents.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if len(args.docs) < 2:
        print("error: need at least two documents to compare", file=sys.stderr)
        return 2

    doc_keys: dict[str, set[str]] = {}
    for doc in args.docs:
        try:
            text = Path(doc).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot read {doc}: {exc}", file=sys.stderr)
            return 2
        doc_keys[doc] = section_keys(text)

    drift = section_set_drift(doc_keys)
    if drift:
        print(
            "section sets differ across documents; "
            f"not shared by all: {', '.join(sorted(drift))}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
