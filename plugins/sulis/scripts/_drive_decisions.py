"""drive-decisions fixture harness (WP-012, SC-17).

A deterministic, non-interactive driver that drives the real decision-emit path
(`emit_decision_from_adr`, the same function `/sulis:draft-architecture` shells
out to via `sulis-emit-decision`) for a business decision (BDR) and a technical
decision (ADR), persisting both through the real `LocalFileEntityAdapter` (which
validates against the vendored compiled `decision.schema.json` on save).

It is the first step of SC-17 (a BDR is recorded distinct from an ADR): drive
the emit, then `_assert_bdr_adr.py` reads the two persisted instances and
verifies the discriminator + @id distinctness.

CLI
---
    python3 _drive_decisions.py --out <dir> [--base-dir <dir>]

  --out       directory the driver writes the two persisted instance paths to,
              one per line, as `kind=<adr|bdr>\\t<path>` (the asserter reads it).
  --base-dir  brain instances base dir (default: <out>/.brain/instances). Each
              invocation uses a fresh dir so the drive is hermetic.

Exit codes
----------
  0  both decisions were emitted + persisted.
  1  a stage failure (validation rejection, write error) — surfaced loudly so
     the scenario fails rather than silently producing a half-result.

Design contracts
----------------
  - Reuses the real emit path: `emit_decision_from_adr` + the validating
    adapter. This is a harness over the real path, not a fork of it.
  - The BDR and ADR carry the SAME `change_id` in their source frontmatter — a
    change that produced two decisions. The pre-WP-012 @id strategy collapsed
    both onto one @id; the harness exercises that the collision fix holds (the
    two persist as distinct files).

See:
  - plugins/sulis/scripts/_decision_emission.py (the real emit path)
  - plugins/sulis/scripts/_assert_bdr_adr.py (the SC-17 asserter)
  - .architecture/comprehensive-spec-and-journey-walk/adrs/ADR-006-*.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from _decision_emission import emit_decision_from_adr
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_repository import EntityValidationError

# Both source decisions share this change_id — a change that produced two
# decisions, the exact collision trigger the WP-012 fix addresses.
_SHARED_CHANGE_ID: Final[str] = "01KSWBWMCFTVB52NGGVAAQBA7R"

_ADR_SOURCE: Final[str] = f"""---
id: ADR-001
title: Use a discriminator field, not a new entity type
status: accepted
change_id: {_SHARED_CHANGE_ID}
date: 2026-05-30
---

# ADR-001 — Use a discriminator field

## Decision

Model ADR vs BDR as a `kind` discriminator on the existing decision entity.

## Context

A new entity type would duplicate the whole decision shape for no gain.

## Options Considered

- New `business_decision` entity — rejected; duplicates the shape.
- A `kind` discriminator — chosen; additive-optional, no migration.

## Consequences

One entity, one schema, one emit path.
"""

_BDR_SOURCE: Final[str] = f"""---
id: BDR-001
title: Ship the three phases in sequence
status: accepted
change_id: {_SHARED_CHANGE_ID}
date: 2026-05-30
---

# BDR-001 — Ship the three phases in sequence

## Decision

Ship P1, then P2, then P3 — each phase independently reversible.

## Context

A single big-bang cutover couples three unrelated risk surfaces.

## Options Considered

- Big-bang all three phases at once — rejected; couples risk.
- Phased P1 → P2 → P3 — chosen; each phase reverts independently.

## Consequences

Slower to full feature, but each phase de-risks the next.
"""


class DriveDecisionsError(Exception):
    """A stage failure the driver surfaces as a non-zero exit."""


def drive(*, out_dir: Path, base_dir: Path) -> list[tuple[str, Path]]:
    """Drive the real emit path for an ADR + a BDR; persist both.

    Returns a list of `(kind, persisted_path)` pairs. Raises
    DriveDecisionsError on any stage failure (validation rejection, write).
    """
    adapter = LocalFileEntityAdapter(
        base_dir=base_dir, domain="product-development"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, Path]] = []
    for kind, source, src_name in (
        ("adr", _ADR_SOURCE, "ADR-001.md"),
        ("bdr", _BDR_SOURCE, "BDR-001.md"),
    ):
        src_path = out_dir / src_name
        src_path.write_text(source, encoding="utf-8")
        try:
            decision = emit_decision_from_adr(src_path, adapter, kind=kind)
        except (EntityValidationError, OSError) as exc:
            raise DriveDecisionsError(
                f"emit failed for {kind} from {src_name}: {exc}"
            ) from exc
        ulid = decision["id"].rsplit(":", 1)[-1]
        persisted = (
            base_dir / "product-development" / "decision" / f"{ulid}.jsonld"
        )
        results.append((kind, persisted))
    return results


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_drive_decisions.py",
        description="Drive the real decision-emit path for an ADR + a BDR.",
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="directory to write the persisted-path manifest to",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="brain instances base dir (default: <out>/.brain/instances)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    base_dir = args.base_dir or (args.out / ".brain" / "instances")
    try:
        results = drive(out_dir=args.out, base_dir=base_dir)
    except DriveDecisionsError as exc:
        print(f"drive-decisions: stage failure: {exc}", file=sys.stderr)
        return 1

    # Write the persisted-path manifest the asserter reads.
    manifest = args.out / "decisions.manifest"
    manifest.write_text(
        "".join(f"kind={kind}\t{path}\n" for kind, path in results),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
