#!/usr/bin/env python3
"""_assert_c4_levels.py — assert a design document carries architecture-at-levels
(C4: context + container + component) (SC-16, FR-16).

Per FR-16 the comprehensive document carries architecture at three distinct C4
levels: System Context, Container, and Component (DESIGN §7.2). This inspector
is the assertion half — given a document, it exits 0 iff an architecture-at-
levels section is present AND all three levels are documented. A section with
only two levels (e.g. context + container, no component) is incomplete and
fails, naming the missing level(s).

Header detection is delegated to ``_doc_section_parse`` — the single source of
truth shared by all the document inspectors (WP-003 Blue).

Usage:
    _assert_c4_levels.py <doc>

Exit codes:
  0 — all three C4 levels (context, container, component) are present.
  1 — the C4 section is absent, or a level is missing (named on stderr).
  2 — bad input (file unreadable).

Pure inspector — reads the doc, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _doc_section_parse import normalise_header, parse_sections

# The three C4 levels in order. Each is detected by its anchor word appearing in
# a level heading or the architecture section body.
_C4_LEVELS: tuple[str, ...] = ("context", "container", "component")

# The architecture-at-levels section is anchored by either phrase in its name.
_SECTION_ANCHORS: tuple[str, ...] = ("architecture-at-levels", "c4")


def _architecture_haystack(text: str) -> str | None:
    """Return the normalised text of the architecture-at-levels section (its
    heading + body, including nested level sub-headings), or ``None`` if there
    is no such section.

    ``parse_sections`` nests deeper headings inside a parent's body, so the C4
    section's ``### Level N`` sub-headings are part of its body — exactly the
    span we search for the three level anchors.
    """
    for section in parse_sections(text):
        if any(anchor in section.key for anchor in _SECTION_ANCHORS):
            return normalise_header(f"{section.name}\n{section.body}")
    return None


def missing_levels(text: str) -> list[str] | None:
    """Return the C4 levels absent from the architecture section, or ``None``
    when there is no architecture-at-levels section at all.

    ``[]`` means all three levels are present (the pass condition); a non-empty
    list names the missing ones; ``None`` distinguishes "no section".
    """
    haystack = _architecture_haystack(text)
    if haystack is None:
        return None
    return [level for level in _C4_LEVELS if level not in haystack]


def c4_complete(text: str) -> bool:
    """True iff all three C4 levels are present."""
    return missing_levels(text) == []


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_c4_levels.py",
        description="Exit 0 iff C4 context+container+component levels are present.",
    )
    parser.add_argument("doc", help="Path to the markdown document to inspect.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        text = Path(args.doc).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {args.doc}: {exc}", file=sys.stderr)
        return 2

    missing = missing_levels(text)
    if missing is None:
        print(
            f"{args.doc}: no architecture-at-levels (C4) section found "
            f"(expected a heading containing 'Architecture-at-Levels' or 'C4')",
            file=sys.stderr,
        )
        return 1
    if missing:
        print(
            f"{args.doc}: C4 section present but missing level(s): "
            f"{', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
