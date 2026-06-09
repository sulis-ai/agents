#!/usr/bin/env python3
"""_assert_measurable_nfr.py — assert each named NFR category carries a
measurable (numeric / threshold) target, not an adjective (SC-05, FR-06).

"Always-on NFR with measurable targets" means a category like Performance must
state a number — ``< 5 ms``, ``1000 calls < 5 s``, ``≤ 1.6×``, ``99.9%`` — not
just an adjective like "fast" or "responsive". This inspector checks that the
body of each named category section contains at least one measurable token.

A *measurable token* is any of:
  - a comparator followed by a number  (``< 5``, ``<= 5``, ``≤ 5``, ``>= 99``)
  - a number with a unit               (``5 ms``, ``5s``, ``200KB``, ``1.6x``)
  - a percentage                       (``99.9%``)
  - a bare number adjacent to a word   (``1000 calls``)

Header detection + body extraction is delegated to ``_doc_section_parse`` —
the single source of truth shared by all five WP-003 inspectors.

Usage:
    _assert_measurable_nfr.py --categories <comma-list> <doc>

Exit codes:
  0 — every named category has a measurable target
  1 — at least one category is adjective-only (named on stderr)
  2 — bad input (file unreadable, no --categories, a category section missing)

Pure inspector — reads the doc, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _doc_section_parse import find_section

# A measurable token: an optional comparator, a number (int/float), and an
# optional unit/percent/multiplier. Also matches a plain number followed by a
# unit word. The comparators include the unicode ≤ / ≥ used in the design docs.
_MEASURABLE_RE = re.compile(
    r"""
    (?:[<>]=?|≤|≥)\s*\d                       # comparator + number:  < 5, ≤ 5
  | \d+(?:\.\d+)?\s*                           # a number ...
      (?:%|x|×|ms|s\b|m\b|h\b|kb|mb|gb|tb|     # ... with a unit / percent / ×
         req|rps|qps|calls?|requests?|bytes?|seconds?|minutes?)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def unmeasured_categories(text: str, categories: list[str]) -> tuple[list[str], list[str]]:
    """Return ``(missing, adjective_only)``:
    - ``missing``: category section names that are absent from the document.
    - ``adjective_only``: present category sections whose body has no
      measurable token.
    A category in neither list is present and measurable."""
    missing: list[str] = []
    adjective_only: list[str] = []
    for name in categories:
        section = find_section(text, name)
        if section is None:
            missing.append(name)
            continue
        if not _MEASURABLE_RE.search(section.body):
            adjective_only.append(name)
    return missing, adjective_only


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_measurable_nfr.py",
        description="Exit 0 iff each named NFR category has a measurable target.",
    )
    parser.add_argument(
        "--categories",
        required=True,
        help="Comma-separated NFR category section names (e.g. 'performance,reliability').",
    )
    parser.add_argument("doc", help="Path to the markdown document to inspect.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    categories = [name.strip() for name in args.categories.split(",") if name.strip()]
    if not categories:
        print("error: --categories listed no category names", file=sys.stderr)
        return 2
    try:
        text = Path(args.doc).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {args.doc}: {exc}", file=sys.stderr)
        return 2

    missing, adjective_only = unmeasured_categories(text, categories)
    if missing:
        print(
            f"{args.doc}: NFR category section(s) missing: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 2
    if adjective_only:
        print(
            f"{args.doc}: NFR category(ies) have no measurable target "
            f"(adjective-only): {', '.join(adjective_only)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
