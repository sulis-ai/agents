"""_entity_edit — shared read-modify-validate-save scaffold for the spine
edit/status helpers (WP-004, ADR-020).

The `edit-product.py` / `edit-project.py` / `set-entity-status.py` helpers all
do the same three things against the brain instance store: load an entity by
id, apply a small field change, and re-save it through the validated adapter
(reject-on-invalid; overwrite the same file). That read-modify-validate-save is
factored here once (the 2-consumer threshold is met by the two edit helpers —
EP-03 / Non-Negotiable 2), so each CLI is a thin argv parser over this core.

No new store primitive is introduced (ADR-020): every path reduces to the
adapter's existing `find_by_id` + `save` (an upsert keyed on the `@id` ULID).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def ok(data: dict) -> int:
    """Emit the success envelope and return exit code 0."""
    print(json.dumps({"ok": True, "data": data}, indent=2))
    return 0


def err(message: str) -> int:
    """Emit the failure envelope and return exit code 1 (nothing written)."""
    print(json.dumps({"ok": False, "error": message}, indent=2))
    return 1


def _load_adapter(scripts_dir: Path):
    """Import the validated adapter from the spine scripts dir.

    Returns `(LocalFileEntityAdapter, EntityValidationError)` or raises
    `ImportError` with a surfaced message if the scripts dir is wrong.
    """
    scripts_dir = scripts_dir.resolve()
    if not (scripts_dir / "_entity_adapter_local.py").exists():
        raise ImportError(f"adapter scripts not found under: {scripts_dir}")
    sys.path.insert(0, str(scripts_dir))
    from _entity_adapter_local import LocalFileEntityAdapter
    from _entity_repository import EntityValidationError

    return LocalFileEntityAdapter, EntityValidationError


def apply_changes(
    scripts_dir: Path,
    base_dir: Path,
    domain: str,
    kind: str,
    entity_id: str,
    changes: dict,
) -> int:
    """Load `entity_id`, apply `changes`, re-validate, and re-save in place.

    Preserves every field not named in `changes` (no required field dropped).
    On a schema failure NOTHING is written and a non-zero exit is returned with
    a typed message the adapter maps to `VALIDATION_FAILED`. The same id is
    overwritten — never a second entity (FR-31).
    """
    try:
        adapter_cls, validation_error = _load_adapter(scripts_dir)
    except ImportError as exc:
        return err(str(exc))

    adapter = adapter_cls(base_dir=base_dir.resolve(), domain=domain)

    existing = adapter.find_by_id(kind, entity_id)
    if existing is None:
        return err(f"no {kind} found with id {entity_id}")

    updated = {**existing, **changes}

    try:
        adapter.save(kind, updated)  # validates first; nothing written on invalid
    except validation_error as exc:
        return err(f"{kind} failed schema validation: {exc}")
    except Exception as exc:  # noqa: BLE001 — surface the write problem verbatim
        return err(f"{kind} write failed: {exc}")

    return ok({"id": entity_id, "changed": sorted(changes.keys())})
