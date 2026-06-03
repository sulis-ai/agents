#!/usr/bin/env python3
"""One-shot LifecycleRun v1.0.0 -> v2 migration (WP-006, ADR-004).

The data-migration half of ADR-004's "no half-migrated state". Walks every
`{base_dir}/{domain}/lifecyclerun/*.jsonld` and rewrites each v1 instance
(`step_name: <string>`) into the v2 shape (`step: <dna:step:<ulid>>`):

  1. map `step_name` -> the matching canonical Step ULID via WP-002's
     `_resolve_step` (known names via the map; unknown -> the
     `unclassified-lifecycle-step` Step — single source of truth, NO second
     map);
  2. drop the old `step_name` string (where trace grouping is genuinely
     needed it is carried into `run_id`, mirroring WP-002's emitter — NOT
     into a `step_label`, which does not exist in canonical v2), add `step`;
  3. strip fields the v2 schema rejects under `unevaluatedProperties: false`
     (the JSON-LD envelope keys, the legacy `_`-prefixed harness fields);
  4. re-validate against the re-vendored v2 schema BEFORE writing
     (reject-on-invalid — never write a still-invalid instance, the same
     `LocalFileEntityAdapter` validator the emitter targets — ONE validator);
  5. is idempotent: a doc that already carries `step` is skipped (the
     migration detects v2 by presence of `step`), so a partial run is safe
     to resume and a re-run is a no-op.

Eager-for-our-own: this runs against the marketplace's own `.brain/instances`
in this change. Downstream consumer repos migrate lazily on next emit
(graceful degradation): a consumer that never migrates keeps its old v1 files
until they touch them.

CLI:
    migrate_lifecyclerun_v1_to_v2.py [--base-dir DIR] [--domain NAME] [--dry-run]

Defaults walk `<repo_root>/.brain/instances/product-development/lifecyclerun`.
"""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Final

from _brain_emit_helper import _resolve_step
from _entity_adapter_local import LocalFileEntityAdapter

_ENTITY_TYPE: Final[str] = "lifecyclerun"
_DEFAULT_DOMAIN: Final[str] = "product-development"

# The v2 LifecycleRun field-set, per the re-vendored canonical schema
# (`unevaluatedProperties: false`). Any top-level key not here is dropped on
# migration: the JSON-LD envelope (`@context`/`@id`/`@type`), the legacy
# `_`-prefixed harness fields, and any other non-schema cruft. `step_name` is
# handled explicitly (mapped to `step`, value carried to `run_id`); it is NOT
# in this carry-over set.
_V2_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "step",
        "at",
        "outcome",
        "sys_status",
        "valid_from",
        "valid_to",
        "confidence",
        "by_actor",
        "run_id",
        "deterministic",
        "inputs_ref",
        "outputs_ref",
        "for_project",
    }
)


def migrate_instance(doc: dict) -> dict | None:
    """Migrate one v1 LifecycleRun dict to v2.

    Returns the migrated dict, or `None` if the instance is already v2
    (idempotent — detected by the presence of `step`). Re-validates the
    migrated dict against the vendored v2 schema; raises
    `EntityValidationError` on a still-invalid result (never returns an
    invalid instance).
    """
    # Idempotency: presence of `step` => already v2 => skip.
    if "step" in doc:
        return None

    out: dict = {k: v for k, v in doc.items() if k in _V2_FIELDS}

    # step_name -> step (canonical Step ULID via the single shared resolver).
    legacy_step_name = doc.get("step_name", "")
    out["step"] = _resolve_step(legacy_step_name)

    # Carry the legacy free string into run_id for trace grouping, but never
    # clobber an existing run_id.
    if legacy_step_name and "run_id" not in out:
        out["run_id"] = legacy_step_name

    # Reject-on-invalid: validate against the vendored v2 schema (the same
    # validator the emitter targets) before handing the dict back. Raises on
    # a still-invalid result; nothing is written.
    _validator().validate(_ENTITY_TYPE, out)
    return out


def migrate_store(
    base_dir: Path | str,
    domain: str = _DEFAULT_DOMAIN,
    *,
    dry_run: bool = False,
) -> dict:
    """Walk `{base_dir}/{domain}/lifecyclerun/*.jsonld` and migrate each v1
    instance in place.

    Returns a summary dict: ``{"migrated": int, "skipped": int,
    "paths": [str, ...]}``. A missing store is a no-op (graceful for a fresh
    or downstream repo). Re-validates before writing each file; an instance
    that cannot be made valid raises and aborts the run (reject-on-invalid),
    leaving already-written files in their valid migrated state (idempotent —
    a re-run resumes from where it stopped).
    """
    runs_dir = Path(base_dir) / domain / _ENTITY_TYPE
    migrated = 0
    skipped = 0
    touched: list[str] = []

    if not runs_dir.is_dir():
        return {"migrated": 0, "skipped": 0, "paths": []}

    for path in sorted(runs_dir.glob("*.jsonld")):
        doc = json.loads(path.read_text())
        out = migrate_instance(doc)
        if out is None:
            skipped += 1
            continue
        if not dry_run:
            # `sort_keys=True` + `indent=2` matches the adapter's write shape,
            # keeping git diffs stable.
            path.write_text(json.dumps(out, indent=2, sort_keys=True))
        migrated += 1
        touched.append(str(path))

    return {"migrated": migrated, "skipped": skipped, "paths": touched}


@lru_cache(maxsize=1)
def _validator() -> LocalFileEntityAdapter:
    """An adapter used purely for its schema `validate` surface (the same
    vendored v2 schema the emitter writes against). The `base_dir` is never
    written through this instance — migration writes are done by
    `migrate_store` directly so the on-disk bytes match the adapter's stable
    sort/indent shape without a second persistence path.

    Cached: the validator is loop-invariant across a `migrate_store` walk, so
    it is constructed once rather than per instance."""
    return LocalFileEntityAdapter(base_dir=Path("."), domain=_DEFAULT_DOMAIN)


def _repo_root() -> Path:
    """Resolve the marketplace repo root from this script's location:
    `plugins/sulis/scripts/migrate_lifecyclerun_v1_to_v2.py` -> repo root is
    three parents up from the scripts dir."""
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate LifecycleRun v1.0.0 instances to v2 (ADR-004)."
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="brain instances dir (default: <repo_root>/.brain/instances)",
    )
    parser.add_argument("--domain", default=_DEFAULT_DOMAIN)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing",
    )
    args = parser.parse_args(argv)

    base_dir = (
        Path(args.base_dir)
        if args.base_dir
        else _repo_root() / ".brain" / "instances"
    )
    summary = migrate_store(base_dir, args.domain, dry_run=args.dry_run)
    verb = "would migrate" if args.dry_run else "migrated"
    print(
        f"lifecyclerun migration: {verb} {summary['migrated']}, "
        f"skipped {summary['skipped']} (already v2) "
        f"under {base_dir}/{args.domain}/{_ENTITY_TYPE}"
    )
    for p in summary["paths"]:
        print(f"  {verb}: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
