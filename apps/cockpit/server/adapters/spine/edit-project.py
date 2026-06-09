#!/usr/bin/env python3
"""edit-project — validated re-save of a Project's editable fields (ADR-020).

Mirrors `edit-product.py`: read-modify-validate-save against the trusted
upsert-by-id path (ADR-020 — no new store primitive). `find_by_id` the
Project, apply the founder's field change(s), then `save` through the
validated adapter against
`brain/compiled/foundation/project.schema.json` — overwriting the same file.

Editable fields here are `name`, and optionally `branch_policy` (an enum the
schema constrains) and `source` (the JSON-encoded `{repo, path, primary_branch}`
string). Every other schema-required field is preserved — critically
`belongs_to_product_ref`, which the Settings tree depends on. Reject-on-invalid
is unchanged: an edit that would break the schema writes nothing and exits
non-zero.

`--source-json` exists so the SpineSettingsAdapter's attach/unlink (WP-005)
mutate `Project.source` through the SAME validated upsert path — never by
hand-building an entity in TypeScript (ADR-007 discipline; gate fix for the
WP-002/004/007 batch composition CONCERN). When only the source is being edited
`--name` is OPTIONAL: at least one of `--name` / `--source-json` /
`--branch-policy` must be supplied, and any field not named is preserved by
`_entity_edit`'s `{**existing, **changes}` merge.

Usage:
    edit-project.py --scripts-dir <dir> --base-dir <brain/instances>
                    --id <dna:project:..>
                    [--name <new-name>]
                    [--branch-policy <trunk|gitflow-dev-main|...>]
                    [--source-json '{"repo":..,"path":..,"primary_branch":..}']

Envelope: {"ok": true, "data": {...}} / {"ok": false, "error": ".."} (exit 0/1).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _entity_edit import apply_changes, err  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Edit a Project (validated re-save).")
    parser.add_argument("--scripts-dir", required=True, help="dir holding _entity_adapter_local")
    parser.add_argument("--base-dir", required=True, help="<state>/.brain/instances")
    parser.add_argument("--id", required=True, help="dna:project:<ulid>")
    parser.add_argument("--name", help="the new project name")
    parser.add_argument("--branch-policy", help="optional branch_policy enum value")
    parser.add_argument(
        "--source-json",
        help='JSON-encoded {repo, path, primary_branch} for Project.source',
    )
    parser.add_argument("--domain", default="foundation")
    args = parser.parse_args()

    changes: dict = {}
    if args.name is not None:
        name = args.name.strip()
        if not name:
            return err("a non-empty project name is required")
        changes["name"] = name
    if args.branch_policy is not None:
        changes["branch_policy"] = args.branch_policy
    if args.source_json is not None:
        changes["source"] = args.source_json

    if not changes:
        return err(
            "nothing to edit: pass at least one of --name / --branch-policy / "
            "--source-json"
        )

    return apply_changes(
        scripts_dir=Path(args.scripts_dir),
        base_dir=Path(args.base_dir),
        domain=args.domain,
        kind="project",
        entity_id=args.id,
        changes=changes,
    )


if __name__ == "__main__":
    sys.exit(main())
