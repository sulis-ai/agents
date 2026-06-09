#!/usr/bin/env python3
"""_assert_stride.py — assert a design document carries a STRIDE threat model
section (SC-15, FR-15).

The always-comprehensive document MUST carry an always-on STRIDE threat model:
the methodology's "attackers" are the bypasses that ship incomplete work
(DESIGN §4.6). This inspector is the assertion half — given a document, it exits
0 iff a real STRIDE section is present: a Threat-Model / STRIDE heading whose
body covers all six STRIDE categories (Spoofing, Tampering, Repudiation,
Information disclosure, Denial of service, Elevation of privilege).

A bare heading with no categories does NOT pass — "present" means a populated
STRIDE analysis, so a thin change still states the categories (marking each
`n/a — <reason>` where it does not apply, NFR-R01), never an empty stub.

Header detection is delegated to ``_doc_section_parse`` — the single source of
truth shared by all the document inspectors (WP-003 Blue), so the STRIDE
asserter agrees with its siblings on what "a section" is.

Usage:
    _assert_stride.py <doc>

Exit codes:
  0 — a populated STRIDE section is present (all six categories named).
  1 — no STRIDE section, or one missing categories (named on stderr).
  2 — bad input (file unreadable).

Pure inspector — reads the doc, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _doc_section_parse import normalise_header, parse_sections

# The six STRIDE categories. Each maps to the canonical phrase a populated
# analysis names; matching is done over the normalised (lower-cased) body.
_STRIDE_CATEGORIES: tuple[str, ...] = (
    "spoofing",
    "tampering",
    "repudiation",
    "information disclosure",
    "denial of service",
    "elevation of privilege",
)

# A section is a "threat model / STRIDE" section if its normalised name contains
# either anchor word.
_SECTION_ANCHORS: tuple[str, ...] = ("threat model", "stride")


def _is_stride_section_name(key: str) -> bool:
    return any(anchor in key for anchor in _SECTION_ANCHORS)


def missing_categories(text: str) -> list[str] | None:
    """Return the STRIDE categories absent from the threat-model section, or
    ``None`` when there is no threat-model section at all.

    A return of ``[]`` means the section is present and covers all six
    categories (the pass condition). A non-empty list names the categories the
    present section fails to cover. ``None`` distinguishes "no section" from
    "section present but thin".
    """
    stride_bodies: list[str] = []
    for section in parse_sections(text):
        if _is_stride_section_name(section.key):
            # Include the heading text itself plus the body — a one-line
            # skeleton may name categories inline.
            stride_bodies.append(f"{section.name}\n{section.body}")
    if not stride_bodies:
        return None

    haystack = normalise_header(" ".join(stride_bodies))
    return [cat for cat in _STRIDE_CATEGORIES if cat not in haystack]


def stride_present(text: str) -> bool:
    """True iff a populated STRIDE section (all six categories) is present."""
    missing = missing_categories(text)
    return missing == []


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_stride.py",
        description="Exit 0 iff a populated STRIDE threat-model section is present.",
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

    missing = missing_categories(text)
    if missing is None:
        print(
            f"{args.doc}: no STRIDE threat-model section found "
            f"(expected a heading containing 'Threat Model' or 'STRIDE')",
            file=sys.stderr,
        )
        return 1
    if missing:
        print(
            f"{args.doc}: STRIDE section present but missing categories: "
            f"{', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
