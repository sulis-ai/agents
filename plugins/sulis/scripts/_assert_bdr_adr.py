#!/usr/bin/env python3
"""_assert_bdr_adr.py — assert a BDR is recorded distinct from an ADR (SC-17).

Reads the persisted-path manifest written by `_drive_decisions.py` (one
`kind=<adr|bdr>\\t<path>` line per emitted decision) and verifies the SC-17
contract (FR-17, ADR-006):

  1. The decision driven as a BDR carries `kind: bdr`.
  2. The decision driven as an ADR carries `kind: adr`.
  3. The two decisions have distinct `@id`s — the bundled multi-decision @id
     collision fix (both sources shared a `change_id`, the pre-fix trigger).

Usage:
    _assert_bdr_adr.py --manifest <path>

Exit codes:
  0 — the BDR is kind:bdr, the ADR is kind:adr, and their @ids differ (SC-17).
  1 — at least one assertion failed (the failing check is printed to stderr).
  2 — bad input (manifest unreadable/malformed, or a persisted file missing).

Pure inspector — reads the manifest + the persisted instances, no other I/O.
Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_manifest(manifest_path: Path) -> dict[str, Path]:
    """Parse the `kind=<k>\\t<path>` manifest into a {kind: path} mapping.

    Raises ValueError on a malformed line or a missing kind.
    """
    by_kind: dict[str, Path] = {}
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if "\t" not in line or not line.startswith("kind="):
            raise ValueError(f"malformed manifest line: {raw!r}")
        kind_token, path_str = line.split("\t", 1)
        kind = kind_token[len("kind=") :]
        by_kind[kind] = Path(path_str)
    for required in ("adr", "bdr"):
        if required not in by_kind:
            raise ValueError(f"manifest missing a {required!r} decision")
    return by_kind


def _load_decision(path: Path) -> dict:
    """Load a persisted decision instance. Raises on missing/malformed file."""
    if not path.is_file():
        raise FileNotFoundError(f"persisted decision not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def check(by_kind: dict[str, Path]) -> list[str]:
    """Return a list of failure messages (empty ⇒ SC-17 holds)."""
    adr = _load_decision(by_kind["adr"])
    bdr = _load_decision(by_kind["bdr"])

    failures: list[str] = []
    if bdr.get("kind") != "bdr":
        failures.append(
            f"BDR carries kind={bdr.get('kind')!r}, expected 'bdr'"
        )
    if adr.get("kind") != "adr":
        failures.append(
            f"ADR carries kind={adr.get('kind')!r}, expected 'adr'"
        )
    if adr.get("id") == bdr.get("id"):
        failures.append(
            f"ADR and BDR collided on the same @id: {adr.get('id')!r}"
        )
    return failures


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_bdr_adr.py",
        description="Exit 0 iff the BDR is kind:bdr and distinct from the ADR.",
    )
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="path to the decisions.manifest written by _drive_decisions.py",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        by_kind = _load_manifest(args.manifest)
    except (OSError, ValueError) as exc:
        print(f"assert-bdr-adr: bad manifest: {exc}", file=sys.stderr)
        return 2

    try:
        failures = check(by_kind)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"assert-bdr-adr: bad input: {exc}", file=sys.stderr)
        return 2

    if failures:
        for f in failures:
            print(f"assert-bdr-adr: {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
