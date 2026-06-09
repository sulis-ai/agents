#!/usr/bin/env python3
"""_assert_walk_subset_of_contract.py — assert the tool-surface journey-walk's
operations are a SUBSET of the interface-contract's declared operations
(WP-013, FR-19 / SC-19 / NFR-D03).

This is the **integration check of the contract-first seam** (CF-05). It ties
the two surfaces the design stage produces:

  * the *consumer* — the tool-surface ``## Journey Walk`` table (WP-009): every
    hop names a tool operation the walk classified EXISTS / planned-WP / GAP;
  * the *producer* — the §7.6 interface-contract section (WP-011): every
    ``#### Operation: `name``` block declares an operation with its schema +
    CF-10 dimensions.

Per FR-19 the walk can only classify operations the contract *declares*: a
walked operation absent from the contract is an ``OperationNotInContract``
violation — the operation must be added to the contract first (the contract is
specified first, CF-01/CF-05). The relationship enforced is therefore

    {tool-walk operations}  ⊆  {contract operations}

A document whose contract declares no operations (the explicit ``n/a — no tool
surface`` case) but whose tool walk still references operations is the
degenerate cross-kind-side-without-contract-reference case (SC-19): every
walked op is then un-declared, so it fails — the seam is unreviewable.

A document with no tool-surface walk has nothing to check and passes (there is
no consumer to be a non-subset).

Both halves delegate parsing to the existing inspectors so there is one parser
per surface and no duplicated table/section walk (WP-013 Blue, EP-03):

  * tool-walk section splitting + surface tagging → ``_assert_walk_table``
    (``_split_walk_sections`` / ``_section_surface``, WP-009);
  * contract section + operation-heading splitting → ``_assert_interface_contract``
    (``_contract_section_body`` / ``_split_operations``, WP-011).

Usage:
    _assert_walk_subset_of_contract.py <doc>

Exit codes:
  0 — every tool-walk operation is declared in the contract (walk ⊆ contract),
      or the document has no tool-surface walk (nothing to check).
  1 — ≥1 walked operation is absent from the contract (OperationNotInContract,
      FR-19); the offending operation(s) named on stderr.
  2 — bad input (file unreadable).

Pure inspector — reads the doc, no other I/O. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Reuse the existing surface parsers so the walk-table and contract parsing
# never drift from the producers (WP-009 walk table, WP-011 contract section).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _assert_interface_contract import (  # noqa: E402
    _contract_section_body,
    _split_operations,
)
from _assert_walk_table import (  # noqa: E402
    _section_surface,
    _split_walk_sections,
    hop_rows,
)

_TOOL_SURFACE = "tool"


def walked_tool_operations(text: str) -> set[str]:
    """The set of operations the *tool*-surface journey walk references.

    Only ``Surface: tool`` walk sections contribute — the UI walk's hops are
    journey steps, not contract operations, and are out of scope for FR-19.
    The walked operation is the hop-column (cell 0) of each walk-table row; the
    row grammar is owned by ``_assert_walk_table.hop_rows`` (WP-013 Blue), so
    this reader and the status reader never drift on what "a hop row" is.
    """
    ops: set[str] = set()
    for body in _split_walk_sections(text):
        if _section_surface(body) == _TOOL_SURFACE:
            ops.update(row[0] for row in hop_rows(body))
    return ops


def contract_operations(text: str) -> set[str]:
    """The set of operations the §7.6 interface contract *declares*.

    Reads the ``#### Operation: `name``` blocks via WP-011's contract parser.
    A document with no contract section ⇒ empty set (no operation declared).
    """
    section = _contract_section_body(text)
    if section is None:
        return set()
    return {name for name, _block in _split_operations(section.body)}


def operations_not_in_contract(walk_ops: set[str], contract_ops: set[str]) -> list[str]:
    """Walked operations absent from the contract, sorted for stable output.

    An empty list means the walk is a subset of the contract (the FR-19
    invariant holds). A non-empty list is the ``OperationNotInContract`` set —
    each must be added to the contract first.
    """
    return sorted(walk_ops - contract_ops)


def check(text: str) -> tuple[bool, list[str]]:
    """Return ``(ok, offenders)`` for a design document.

    ``ok`` is True iff every tool-walk operation is declared in the contract
    (walk ⊆ contract). ``offenders`` is the OperationNotInContract set when not.
    A document with no tool-surface walk passes with no offenders.
    """
    walk_ops = walked_tool_operations(text)
    if not walk_ops:
        return True, []  # no tool walk ⇒ no consumer ⇒ nothing to check
    contract_ops = contract_operations(text)
    offenders = operations_not_in_contract(walk_ops, contract_ops)
    return (offenders == []), offenders


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_walk_subset_of_contract.py",
        description=(
            "Exit 0 iff every tool-walk operation is declared in the interface "
            "contract (walk ⊆ contract, FR-19)."
        ),
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

    ok, offenders = check(text)
    if not ok:
        print(
            f"{args.doc}: tool-walk operation(s) absent from the interface "
            f"contract (OperationNotInContract, FR-19): {', '.join(offenders)} "
            "— add each to the §7.6 contract first.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
