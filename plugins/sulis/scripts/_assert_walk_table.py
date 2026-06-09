#!/usr/bin/env python3
"""_assert_walk_table.py — assert a design document's journey-walk table(s)
classify every hop, with the FR-09 binding bar (WP-009, SC-06 / SC-08 / SC-09).

The design stage emits one ``## Journey Walk`` section per surface (the WP-002
``_drive_journey_walk.py`` driver writes a ``Surface: <ui|tool>`` line and a
``| hop | evidence | status |`` table per scenario). This inspector is the
assertion half: given a document and a ``--surface``, it verifies the named
surface's walk table classifies every hop, and — under the optional flags —
that no bare GAP remains and that BOTH surface tables are present (NFR-D02).

It does NOT re-implement classification policy: the driver already owns that
(``_drive_journey_walk.classify_hop`` — the single source of the EXISTS/GAP rule,
including the tool binding bar). This script only reads the produced table and
checks its shape + verdict, so there is one classifier, consumed two ways.

Usage:
    _assert_walk_table.py --surface <ui|tool> [--no-bare-gap] \\
        [--require-two-tables] <doc>

Exit codes:
  0 — the named surface's table classifies every hop (and, with the flags, no
      bare GAP remains / both surface tables are present)
  1 — the surface's table is missing/empty, a bare GAP remains under
      --no-bare-gap, or a surface table is absent under --require-two-tables
  2 — bad input (file unreadable)

Pure inspector — reads the doc, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Reuse the driver's status vocabulary so the gate and the producer never drift.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _drive_journey_walk import EXISTS, GAP, PLANNED  # noqa: E402

_SURFACES = ("ui", "tool")
_VALID_STATUSES = {EXISTS, PLANNED, GAP}


def _split_walk_sections(text: str) -> list[list[str]]:
    """Return each ``## Journey Walk`` section as a list of its body lines.

    A section runs from its ``## Journey Walk`` heading to the next ``## ``
    heading (or end of document). The heading line itself is not included.
    """
    lines = text.splitlines()
    sections: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if line.strip() == "## Journey Walk":
            current = []
            sections.append(current)
            continue
        if line.startswith("## ") and current is not None:
            # A new top-level section closes the current walk section.
            current = None
        if current is not None:
            current.append(line)
    return sections


def _section_surface(body: list[str]) -> str | None:
    """Read the ``Surface: <surface>`` line from a walk section body."""
    for line in body:
        stripped = line.strip()
        if stripped.lower().startswith("surface:"):
            return stripped.split(":", 1)[1].strip().lower()
    return None


def _table_hop_statuses(body: list[str]) -> list[str]:
    """Return the status cell of every hop row in the section's tables.

    A hop row is a Markdown table row ``| hop | evidence | status |`` that is
    neither the header (``| hop |``) nor the divider (``| --- |``).
    """
    statuses: list[str] = []
    for line in body:
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) != 3:
            continue
        if cells[0].lower() == "hop":  # header row
            continue
        if set(cells[2]) <= {"-"}:  # divider row
            continue
        statuses.append(cells[2])
    return statuses


def surfaces_present(text: str) -> set[str]:
    """The set of surfaces that have a Journey Walk section in the document."""
    found: set[str] = set()
    for body in _split_walk_sections(text):
        surface = _section_surface(body)
        if surface:
            found.add(surface)
    return found


def check(
    text: str, surface: str, *, no_bare_gap: bool, require_two_tables: bool
) -> tuple[bool, str]:
    """Return ``(ok, reason)`` for the document against the requested checks."""
    present = surfaces_present(text)

    if require_two_tables:
        missing = [s for s in _SURFACES if s not in present]
        if missing:
            return False, (
                "both surface walk tables must be present (NFR-D02); "
                f"missing: {', '.join(missing)}"
            )

    # Find the section(s) for the requested surface and collect hop statuses.
    statuses: list[str] = []
    saw_surface = False
    for body in _split_walk_sections(text):
        if _section_surface(body) == surface:
            saw_surface = True
            statuses.extend(_table_hop_statuses(body))

    if not saw_surface:
        return False, f"no `{surface}`-surface Journey Walk section in the document"

    # Every hop must carry a recognised classification (no blank status cell).
    unknown = [s for s in statuses if s not in _VALID_STATUSES]
    if unknown:
        return False, (
            f"`{surface}` walk has hop(s) with an unrecognised status: "
            f"{', '.join(sorted(set(unknown)))}"
        )

    if no_bare_gap and GAP in statuses:
        return False, (
            f"`{surface}` walk has a bare GAP — a hop neither built nor planned "
            "blocks design completion (NFR-S04)"
        )

    return True, ""


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_walk_table.py",
        description="Assert a journey-walk table classifies every hop.",
    )
    parser.add_argument(
        "--surface", required=True, choices=list(_SURFACES), help="which surface to check"
    )
    parser.add_argument(
        "--no-bare-gap",
        action="store_true",
        help="fail if the surface's walk has a bare GAP (a hop neither built nor planned)",
    )
    parser.add_argument(
        "--require-two-tables",
        action="store_true",
        help="fail unless BOTH the ui and tool walk tables are present (NFR-D02)",
    )
    parser.add_argument("doc", help="path to the design document to inspect")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        text = Path(args.doc).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {args.doc}: {exc}", file=sys.stderr)
        return 2

    ok, reason = check(
        text,
        args.surface,
        no_bare_gap=args.no_bare_gap,
        require_two_tables=args.require_two_tables,
    )
    if not ok:
        print(f"{args.doc}: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
