#!/usr/bin/env python3
"""_assert_doc_sections.py — assert a design document carries every required
section (SC-01, FR-01/FR-11).

The always-comprehensive document MUST contain its full Target Structure
regardless of depth. This inspector is the assertion half: given a document and
a comma-separated list of required section names, it exits 0 iff every required
section heading is present, and non-zero (naming the missing sections) otherwise.

Header detection is delegated to ``_doc_section_parse`` — the single source of
truth shared by all five WP-003 inspectors.

Usage:
    _assert_doc_sections.py --require <comma-list> <doc>

Exit codes:
  0 — every required section is present
  1 — at least one required section is missing (named on stderr)
  2 — bad input (file unreadable, no --require)

Pure inspector — reads the doc, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _doc_section_parse import normalise_header, section_keys


def missing_sections(text: str, required: list[str]) -> list[str]:
    """Return the required section names (as given) that are absent from
    ``text``. Comparison is via the shared normaliser, so case / spacing
    differences don't cause false misses."""
    present = section_keys(text)
    return [name for name in required if normalise_header(name) not in present]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_doc_sections.py",
        description="Exit 0 iff every required section heading is present.",
    )
    parser.add_argument(
        "--require",
        required=True,
        help="Comma-separated list of required section names (e.g. 'overview,nfr').",
    )
    parser.add_argument("doc", help="Path to the markdown document to inspect.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    required = [name.strip() for name in args.require.split(",") if name.strip()]
    if not required:
        print("error: --require listed no section names", file=sys.stderr)
        return 2
    try:
        text = Path(args.doc).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {args.doc}: {exc}", file=sys.stderr)
        return 2

    missing = missing_sections(text, required)
    if missing:
        print(
            f"{args.doc}: missing required section(s): {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
