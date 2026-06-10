#!/usr/bin/env python3
"""_assert_section_na.py — assert a section is either populated or carries a
justified ``n/a`` (SC-03, NFR-R01).

The reliability invariant "degrade detail, not existence" means a section that
doesn't apply to a given change is marked ``n/a — <reason>``, never silently
dropped. This inspector distinguishes the three states of the named section:

  - missing heading                 ⇒ FAIL (a dropped section is not an n/a one)
  - present, body is bare ``n/a``    ⇒ FAIL (no justification)
  - present, body is ``n/a — <reason>`` (a reason follows)  ⇒ PASS
  - present, body has real content   ⇒ PASS (populated)

The em-dash (``—``), en-dash (``–``), or an ASCII ``--``/``-`` separator after
``n/a`` all count, as long as a non-empty reason follows.

Header detection + body extraction is delegated to ``_doc_section_parse`` —
the single source of truth shared by all five WP-003 inspectors.

Usage:
    _assert_section_na.py --section <name> <doc>

Exit codes:
  0 — the section is present AND (populated OR a justified n/a)
  1 — the section is missing, or a bare/unjustified n/a (reason on stderr)
  2 — bad input (file unreadable, no --section)

Pure inspector — reads the doc, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _doc_section_parse import find_section

# Matches a body that starts with "n/a" optionally followed by a separator and a
# reason. Group 'reason' captures whatever follows the separator (may be empty).
_NA_RE = re.compile(
    r"^n/?a\b\s*(?:[—–]+|-{1,2}|:)?\s*(?P<reason>.*)$",
    re.IGNORECASE | re.DOTALL,
)


def section_na_verdict(text: str, section: str) -> tuple[bool, str]:
    """Return ``(ok, reason)``. ``ok`` is True iff the section is present and
    either populated or a justified n/a. ``reason`` is a human-readable
    explanation when not ok (empty when ok)."""
    found = find_section(text, section)
    if found is None:
        return False, f"section '{section}' is missing (a dropped section is not a justified n/a)"

    body = found.body.strip()
    if not body:
        return False, f"section '{section}' is empty (mark it 'n/a — <reason>' or populate it)"

    match = _NA_RE.match(body)
    if match is None:
        # Body has real content that isn't an n/a marker ⇒ populated ⇒ ok.
        return True, ""

    reason = match.group("reason").strip()
    if not reason:
        return False, f"section '{section}' is a bare 'n/a' with no justification"
    return True, ""


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_section_na.py",
        description="Exit 0 iff the section is present and populated or a justified n/a.",
    )
    parser.add_argument("--section", required=True, help="Section name to inspect.")
    parser.add_argument("doc", help="Path to the markdown document to inspect.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        text = Path(args.doc).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {args.doc}: {exc}", file=sys.stderr)
        return 2

    ok, reason = section_na_verdict(text, args.section)
    if not ok:
        print(f"{args.doc}: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
