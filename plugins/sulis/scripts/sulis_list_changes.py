"""sulis-list-changes — emit change-store contents as JSON for the cockpit.

The cockpit MVP's ``SulisChangeStoreReader`` adapter (WP-003) shells out to
this script. Keeping the cockpit's *consumption* of the change store far
from its *parsing* of the schema (parsing stays in Python, where the
schema is defined) is what ADR-008 alternative 2 articulates.

Three subcommands:

- ``list``           → JSON array of every change record (live ``stage``
                       overlaid from each change's ``state.json``).
- ``get <id>``       → JSON object (the raw record) or ``null``.
- ``stage <id>``     → JSON string (the live overlay stage) or ``null``.

Exit codes:

- 0 — success (stdout carries the JSON payload).
- 1 — internal exception (``{"error": "<exc class>: <message>"}`` on
      stderr, stdout empty).
- 2 — unknown command / usage error (``{"error": "..."}`` on stderr,
      stdout empty).

Honours ``SULIS_STATE_DIR`` exactly as ``_change_state.sulis_state_base()``
does — the WP-003 contract tests can seed a temp dir without polluting
``~/.sulis/changes/``.

Pure stdlib, read-only. Any field-shape change in ``_change_state.py``
propagates through this script unchanged; the TypeScript adapter does the
case-translation (Python snake_case here, TypeScript camelCase there).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

# Sibling module — the canonical reader. Path-insert mirrors the
# convention used by sulis-change (which also lives in this scripts dir).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _change_state import (  # noqa: E402
    list_all_changes,
    read_change_record,
    read_change_stage,
)


def _emit_json(payload: object) -> None:
    """Write a JSON payload to stdout with a trailing newline."""
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
    sys.stdout.write("\n")


def _emit_error(message: str) -> None:
    """Write a structured error to stderr (stdout stays empty)."""
    sys.stderr.write(json.dumps({"error": message}))
    sys.stderr.write("\n")


class _JsonErrorParser(argparse.ArgumentParser):
    """ArgumentParser that emits errors as JSON on stderr and exits 2.

    argparse's default ``error()`` writes a plain-text usage line and
    exits 2. The cockpit adapter parses stderr as JSON on non-zero exits;
    overriding ``error`` keeps that contract whether the failure originates
    from us (``_emit_error``) or from argparse (unknown subcommand, missing
    arg, etc.). All paths through this script's stderr are now JSON.
    """

    def error(self, message: str) -> None:  # type: ignore[override]
        _emit_error(message)
        raise SystemExit(2)


def _build_parser() -> argparse.ArgumentParser:
    parser = _JsonErrorParser(
        prog="sulis-list-changes",
        description=(
            "Print the Sulis change-store contents as JSON. The cockpit "
            "shells out to this helper to enumerate changes (ADR-008)."
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser(
        "list",
        help="list every change (JSON array; live stage overlaid)",
    )

    get_parser = sub.add_parser(
        "get",
        help="get one change record by id (JSON object or null)",
    )
    get_parser.add_argument("change_id", help="the change ULID")

    stage_parser = sub.add_parser(
        "stage",
        help="get the live workflow stage for a change (JSON string or null)",
    )
    stage_parser.add_argument("change_id", help="the change ULID")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch to the requested subcommand. Returns the process exit code."""
    parser = _build_parser()
    # argparse exits 2 with a usage message on unknown flags / missing
    # subcommands; we wrap so the exit code + structured error contract
    # holds even for the "no command given" case.
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse already wrote to stderr in plain text; convert to our
        # structured shape only when stdout is otherwise empty. We don't
        # try to recover argparse's own messages — they're operator-facing.
        code = exc.code if isinstance(exc.code, int) else 2
        return code or 2

    if args.command is None:
        _emit_error("no command given (expected: list | get | stage)")
        return 2

    try:
        if args.command == "list":
            _emit_json(list_all_changes())
            return 0
        if args.command == "get":
            _emit_json(read_change_record(args.change_id))
            return 0
        if args.command == "stage":
            _emit_json(read_change_stage(args.change_id))
            return 0
        # argparse's choices guard makes this unreachable, but keep an
        # explicit fallback so the contract is provable from the source.
        _emit_error(f"unknown command: {args.command!r}")
        return 2
    except Exception as exc:  # noqa: BLE001 — top-level CLI boundary
        _emit_error(f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
