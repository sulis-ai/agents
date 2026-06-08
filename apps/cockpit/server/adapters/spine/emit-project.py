#!/usr/bin/env python3
"""emit-project — schema-validated Project mint into the active brain.

WP-010 (fix-forward). The Tenant and Product spine emitters ship as
first-class CLIs (`sulis-emit-tenant` / `sulis-emit-product`); a Project
emitter does not, so the cockpit's deterministic server-side mint drives the
SAME validated adapter the other emitters use (`_entity_adapter_local`) to
write the Project entity through the vendored schema. This is NOT a freehand
entity write (ADR-007): the entity is validated against
`brain/compiled/foundation/project.schema.json` before any byte is written —
the same reject-on-invalid discipline as every other emitter.

It derives the Project ULID deterministically from the Product id + the
project name (the same scheme the product/tenant emitters use), so a re-mint
of the same names overwrites in place and never duplicates (FR-31). The
Project carries `belongs_to_product_ref`, `belongs_to_tenant`, and
`source` = JSON {repo, path, primary_branch} (FR-36).

Usage:
    emit-project.py --scripts-dir <dir> --base-dir <brain/instances>
                    --tenant-id <dna:tenant:..> --product-id <dna:product:..>
                    --name <project-name> --source-json <json>

Envelope: {"ok": true, "data": {...}} / {"ok": false, "error": ".."} (exit 0/1).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ok(data: dict) -> int:
    print(json.dumps({"ok": True, "data": data}, indent=2))
    return 0


def _err(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}, indent=2))
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a Project entity (validated).")
    parser.add_argument("--scripts-dir", required=True, help="the spine-emitter scripts dir (has _entity_adapter_local)")
    parser.add_argument("--base-dir", required=True, help="<state>/.brain/instances")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--source-json", required=True, help="JSON {repo, path, primary_branch}")
    parser.add_argument("--domain", default="foundation")
    args = parser.parse_args()

    scripts_dir = Path(args.scripts_dir).resolve()
    if not (scripts_dir / "_entity_adapter_local.py").exists():
        return _err(f"emitter scripts not found under: {scripts_dir}")
    sys.path.insert(0, str(scripts_dir))

    try:
        from _entity_adapter_local import LocalFileEntityAdapter  # noqa: E402
        from _entity_repository import EntityValidationError  # noqa: E402
        from _tenant_emission import _deterministic_ulid_from  # noqa: E402
    except Exception as exc:  # noqa: BLE001 — surface the import problem verbatim
        return _err(f"could not import the validated adapter: {exc}")

    name = args.name.strip()
    if not name:
        return _err("a non-empty project name is required")

    # Deterministic ULID from product + name ⇒ idempotent re-mint (FR-31).
    ulid = _deterministic_ulid_from(f"project-name:{name}:product:{args.product_id}")
    entity = {
        "id": f"dna:project:{ulid}",
        "name": name,
        "belongs_to_tenant": args.tenant_id,
        "belongs_to_product_ref": args.product_id,
        "type": "application",
        "source": args.source_json,
        "version_files": ["package.json"],
        "branch_policy": "trunk",
        "state": "active",
        "sys_status": "active",
    }

    adapter = LocalFileEntityAdapter(
        base_dir=Path(args.base_dir).resolve(), domain=args.domain
    )
    try:
        adapter.save("project", entity)  # validates first; nothing written on invalid
    except EntityValidationError as exc:
        return _err(f"project failed schema validation: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _err(f"project write failed: {exc}")

    return _ok({"id": entity["id"], "name": name})


if __name__ == "__main__":
    sys.exit(main())
