#!/usr/bin/env python3
"""set-entity-status — soft-delete / lifecycle status mutation (ADR-020).

Remove is a FIELD MUTATION, not a file operation (ADR-020 §Decision). This
helper loads the entity, sets `sys_status` to the requested lifecycle value
(`deleted` for remove; the schema's other values are also accepted), and
re-saves it through the validated adapter. The `.jsonld` file stays on disk
as an audit trail — **this helper NEVER deletes a file.** A soft-deleted
entity is filtered out of every read (`list-entities.py`, `readProducts`).

It reuses the same read-modify-validate-save scaffold as the edit helpers
(`_entity_edit.apply_changes`), so "remove" reduces to the trusted upsert
path with `{"sys_status": "<status>"}` as the only change. Reject-on-invalid
is unchanged: an out-of-enum status writes nothing and exits non-zero.

Usage:
    set-entity-status.py --scripts-dir <dir> --base-dir <brain/instances>
                         --domain <domain> --kind <product|project>
                         --id <dna:..> --status <active|archived|deleted|purged>

Envelope: {"ok": true, "data": {...}} / {"ok": false, "error": ".."} (exit 0/1).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _entity_edit import apply_changes, err  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set an entity's sys_status (soft-delete; never a file delete)."
    )
    parser.add_argument("--scripts-dir", required=True, help="dir holding _entity_adapter_local")
    parser.add_argument("--base-dir", required=True, help="<state>/.brain/instances")
    parser.add_argument("--domain", required=True, help="e.g. product-development | foundation")
    parser.add_argument("--kind", required=True, help="e.g. product | project")
    parser.add_argument("--id", required=True, help="dna:<kind>:<ulid>")
    parser.add_argument("--status", required=True, help="active | archived | deleted | purged")
    args = parser.parse_args()

    status = args.status.strip()
    if not status:
        return err("a non-empty status is required")

    return apply_changes(
        scripts_dir=Path(args.scripts_dir),
        base_dir=Path(args.base_dir),
        domain=args.domain,
        kind=args.kind,
        entity_id=args.id,
        changes={"sys_status": status},
    )


if __name__ == "__main__":
    sys.exit(main())
