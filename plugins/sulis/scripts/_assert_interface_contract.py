#!/usr/bin/env python3
"""_assert_interface_contract.py — assert the interface-contract section carries
all four CF-10 founder-reviewable dimensions per operation (SC-18, FR-18).

Per FR-18 (and CONTRACT_FIRST_STANDARD CF-10), every operation in the mandatory
interface-contract section must carry the four founder-reviewable dimensions:

  1. **auth / permissions** — does it require sign-in / a permission?
  2. **audience** — who the operation is for (operator/agent vs founder/end-user)
  3. **plain-language user guide** — what it does in one sentence + when to use
  4. **error fixes** — for each error, the cause + the user-/developer-fix

A contract operation missing any one of these is *incomplete* — for a
tool-surface change the design stage does not complete (DESIGN §7.6, MUC-07).
This inspector exits 0 iff every declared operation carries all four; a missing
dimension ⇒ non-zero, naming the operation and the absent dimension.

A contract section with no operations (the explicit `n/a — <reason>` for a
change with no tool surface) passes: there is nothing to be incomplete.

Header detection is delegated to ``_doc_section_parse`` — the single source of
truth shared by all the document inspectors (WP-003 Blue).

Usage:
    _assert_interface_contract.py <doc>

Exit codes:
  0 — every contract operation carries all four CF-10 dimensions (or no ops).
  1 — at least one operation is missing a dimension (named on stderr).
  2 — bad input (file unreadable).

Pure inspector — reads the doc, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _doc_section_parse import normalise_header, parse_sections

# The four CF-10 dimensions. Each entry: (display label, anchor phrases). An
# operation's block must contain at least one anchor for each dimension.
_CF10_DIMENSIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("auth / permissions", ("auth / permissions", "auth/permissions", "permissions")),
    ("audience", ("audience",)),
    ("user guide", ("user guide", "user-guide", "plain-language")),
    ("error fixes", ("error fixes", "error-fixes")),
)

# The interface-contract section is anchored by this phrase in its name.
_SECTION_ANCHOR = "interface contract"

# An operation block opens with a heading like `#### Operation: `name``.
_OPERATION_RE = re.compile(r"operation:\s*`?([^`\n]+?)`?\s*$", re.IGNORECASE)


def _contract_section_body(text: str):
    """Return the parsed interface-contract section, or ``None`` if absent.

    ``parse_sections`` nests deeper headings inside the parent, so the section's
    ``#### Operation:`` sub-blocks are part of its body.
    """
    for section in parse_sections(text):
        if _SECTION_ANCHOR in section.key:
            return section
    return None


def _split_operations(section_body: str) -> list[tuple[str, str]]:
    """Split a contract section body into ``(operation_name, block_text)`` pairs.

    Each operation opens with an ``Operation: `name``` heading; its block runs to
    the next operation heading (or end). Returns ``[]`` when no operations are
    declared (e.g. a contract section carrying the `n/a — no tool surface`
    sentinel).
    """
    lines = section_body.splitlines()
    starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        # Operation headings may be ATX (#### Operation: `x`) — strip leading #.
        candidate = line.lstrip("#").strip()
        m = _OPERATION_RE.match(candidate)
        if m:
            starts.append((i, m.group(1).strip()))

    operations: list[tuple[str, str]] = []
    for idx, (line_i, name) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        block = "\n".join(lines[line_i:end])
        operations.append((name, block))
    return operations


def _missing_dimensions(block: str) -> list[str]:
    """Return the CF-10 dimension labels absent from an operation block."""
    haystack = normalise_header(block)
    missing: list[str] = []
    for label, anchors in _CF10_DIMENSIONS:
        if not any(anchor in haystack for anchor in anchors):
            missing.append(label)
    return missing


def incomplete_operations(text: str) -> list[tuple[str, list[str]]]:
    """Return ``(operation_name, missing_dimensions)`` for every operation that
    is missing ≥1 CF-10 dimension.

    An empty list means the contract is complete (every operation carries all
    four dimensions) OR declares no operations — both pass.
    """
    section = _contract_section_body(text)
    if section is None:
        return []
    incomplete: list[tuple[str, list[str]]] = []
    for name, block in _split_operations(section.body):
        missing = _missing_dimensions(block)
        if missing:
            incomplete.append((name, missing))
    return incomplete


def contract_complete(text: str) -> bool:
    """True iff no operation is missing a CF-10 dimension."""
    return incomplete_operations(text) == []


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_interface_contract.py",
        description=(
            "Exit 0 iff every interface-contract operation carries all four "
            "CF-10 dimensions."
        ),
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

    incomplete = incomplete_operations(text)
    if incomplete:
        for name, missing in incomplete:
            print(
                f"{args.doc}: contract operation '{name}' is incomplete — "
                f"missing CF-10 dimension(s): {', '.join(missing)}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
