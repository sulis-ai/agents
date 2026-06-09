#!/usr/bin/env python3
"""list-entities — the validated read-back the Settings tree needs (ADR-020).

The adapter surface has `save` / `find_by_id` / `validate` but NO `list`
(verified in `_entity_adapter_local.py`). This helper adds the small read-back
the Settings tree needs: it walks `{base}/{domain}/{kind}/*.jsonld` — the same
directory walk `readProducts` does in TypeScript, exposed once (ADR-020 §Read-
back) — and returns the ACTIVE entities as JSON.

"Active" means `sys_status == "active"`: soft-deleted / archived / purged
entities (set by `set-entity-status.py`) are omitted, so a removed entity
disappears from the cockpit. This is a read helper — it never writes a byte.

Usage:
    list-entities.py --scripts-dir <dir> --base-dir <brain/instances>
                     --domain <domain> --kind <product|project>

Envelope: {"ok": true, "data": {"entities": [...]}} /
          {"ok": false, "error": ".."} (exit 0/1).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _entity_edit import err, ok  # noqa: E402

_ACTIVE = "active"


def main() -> int:
    parser = argparse.ArgumentParser(description="List active entities of a kind.")
    parser.add_argument("--scripts-dir", required=True, help="dir holding _entity_adapter_local")
    parser.add_argument("--base-dir", required=True, help="<state>/.brain/instances")
    parser.add_argument("--domain", required=True, help="e.g. product-development | foundation")
    parser.add_argument("--kind", required=True, help="e.g. product | project")
    args = parser.parse_args()

    kind_dir = Path(args.base_dir).resolve() / args.domain / args.kind
    if not kind_dir.is_dir():
        # No entities of this kind yet is a normal outcome, not a failure.
        return ok({"entities": []})

    entities: list[dict] = []
    for path in sorted(kind_dir.glob("*.jsonld")):
        try:
            entity = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            return err(f"could not read {path.name}: {exc}")
        if entity.get("sys_status") == _ACTIVE:
            entities.append(entity)

    return ok({"entities": entities})


if __name__ == "__main__":
    sys.exit(main())
