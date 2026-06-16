#!/usr/bin/env python3
"""set-change-product — assign a Change to a Product (set/update for_product).

The authoritative change->Product assignment is the `for_product` link on the
change's brain Change entity. This is a validated read-modify-save:

  1. `find_by_id` the existing Change entity (so TypeScript never hand-builds an
     entity — ADR-007 discipline).
  2. Set `for_product` on it, preserving every other field.
  3. `save` it — the adapter re-validates and overwrites the SAME `@id` file
     (idempotent: re-assigning never mints a second entity).

For a change with no brain entity yet (the historical changes that predate the
Change entity), there is nothing to load, so compose one from the change's
`change.json` record via the canonical `emit_change` and save it with the link.

Writes to the SAME brain the cockpit reads (`--base-dir`), so the board's
product filter reflects the assignment immediately.

Usage:
    set-change-product.py --scripts-dir <plugins/sulis/scripts>
                          --base-dir <state>/.brain/instances
                          --change-id <ulid> --for-product dna:product:<ulid>
                          [--changes-dir <state>/changes]

Envelope: {"ok": true, "data": {...}} / {"ok": false, "error": ".."} (exit 0/1).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_CHANGE_DOMAIN = "product-development"
_PRODUCT_PREFIX = "dna:product:"
_CHANGE_PREFIX = "dna:change:"


def _err(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}))
    return 1


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Assign a Change to a Product.")
    parser.add_argument("--scripts-dir", required=True, help="dir holding the brain modules")
    parser.add_argument("--base-dir", required=True, help="<state>/.brain/instances")
    parser.add_argument("--change-id", required=True, help="the change ULID")
    parser.add_argument("--for-product", required=True, help="dna:product:<ulid>")
    parser.add_argument("--changes-dir", help="<state>/changes, to compose a record-less change")
    args = parser.parse_args(argv)

    change_id = args.change_id.strip()
    for_product = args.for_product.strip()
    if not change_id or not for_product:
        return _err("--change-id and --for-product are required")
    if not for_product.startswith(_PRODUCT_PREFIX):
        return _err(f"--for-product must be a {_PRODUCT_PREFIX}<ulid> id")

    sys.path.insert(0, str(Path(args.scripts_dir).resolve()))
    try:
        from _entity_adapter_local import LocalFileEntityAdapter
        from _change_emission import emit_change
    except ImportError as exc:  # pragma: no cover - import-wiring guard
        return _err(f"cannot import brain modules from --scripts-dir: {exc}")

    adapter = LocalFileEntityAdapter(base_dir=Path(args.base_dir), domain=_CHANGE_DOMAIN)
    entity_id = f"{_CHANGE_PREFIX}{change_id}"

    existing = adapter.find_by_id("change", entity_id)
    if existing is not None:
        # Update path: set the link, preserve everything else, re-save by id.
        existing["for_product"] = for_product
        adapter.save("change", existing)
        saved = existing
    else:
        # Compose path: no entity yet — build one from the change's manifest.
        if not args.changes_dir:
            return _err(
                "change has no brain entity yet; pass --changes-dir so one can be "
                "composed from its change.json record"
            )
        record_path = Path(args.changes_dir) / change_id / "change.json"
        if not record_path.exists():
            return _err(f"no brain entity and no change.json at {record_path}")
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return _err(f"could not read change.json: {exc}")
        saved = emit_change(record, adapter, for_product=for_product)

    print(json.dumps({"ok": True, "data": {"id": saved.get("id"), "for_product": for_product}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
