#!/usr/bin/env python3
"""edit-product — validated re-save of a Product's editable fields (ADR-020).

Edit is NOT a new store concept (ADR-020 §Decision): it reuses the trusted
upsert-by-id path. The flow is read-modify-validate-save:

  1. `find_by_id` the existing Product (so TypeScript never hand-builds an
     entity — ADR-007 discipline).
  2. Apply the founder's field change (`name`) onto the loaded instance,
     preserving every other schema-required field (`belongs_to_tenant`,
     `state`, `sys_status`, …).
  3. `save` it. The adapter re-validates against
     `brain/compiled/product-development/product.schema.json` and overwrites
     the SAME file (same `@id` ULID). Re-save of the same id never mints a
     second entity (FR-31 idempotency parity).

Reject-on-invalid is unchanged: an edit that would produce an invalid entity
writes nothing and exits non-zero with a typed message the adapter maps to
`VALIDATION_FAILED`.

Usage:
    edit-product.py --scripts-dir <dir> --base-dir <brain/instances>
                    --id <dna:product:..> --name <new-name>

Envelope: {"ok": true, "data": {...}} / {"ok": false, "error": ".."} (exit 0/1).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _entity_edit import apply_changes, err  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Edit a Product (validated re-save).")
    parser.add_argument("--scripts-dir", required=True, help="dir holding _entity_adapter_local")
    parser.add_argument("--base-dir", required=True, help="<state>/.brain/instances")
    parser.add_argument("--id", required=True, help="dna:product:<ulid>")
    parser.add_argument("--name", required=True, help="the new product name")
    parser.add_argument("--domain", default="product-development")
    args = parser.parse_args()

    name = args.name.strip()
    if not name:
        return err("a non-empty product name is required")

    return apply_changes(
        scripts_dir=Path(args.scripts_dir),
        base_dir=Path(args.base_dir),
        domain=args.domain,
        kind="product",
        entity_id=args.id,
        changes={"name": name},
    )


if __name__ == "__main__":
    sys.exit(main())
