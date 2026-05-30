"""`LocalFileEntityAdapter` — file-backed implementation of
`EntityRepository`.

This is the first marketplace consumer of the Brain↔OS compile outputs
(per-entity JSON Schemas vendored at `plugins/sulis/brain/compiled/`). Writes
validated entity instances as `.jsonld` files under a git-tracked directory.

Disk layout:
    {base_dir}/{domain}/{entity_type}/{ulid}.jsonld

`{ulid}` is the suffix after `dna:{entity_type}:` in the instance's `@id`.
Schemas are read from `{schemas_dir}/{domain}/{entity_type}.schema.json` —
defaulting to `plugins/sulis/brain/compiled/` (vendored from the dna-runner
output in the `sulis-ai/plugins` repo).

When the Sulis Platform Storage Service substrate (Track 2) lands, a
`StorageServiceAdapter` implements the same `EntityRepository` port; nothing
else changes — the schemas, the validation, the call sites, all stay
identical. That's the convergence point.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import jsonschema

from _entity_repository import EntityRepository, EntityValidationError


_SCRIPTS_DIR: Final[Path] = Path(__file__).resolve().parent
_DEFAULT_SCHEMAS_DIR: Final[Path] = _SCRIPTS_DIR.parent / "brain" / "compiled"


class LocalFileEntityAdapter(EntityRepository):
    """File-backed `EntityRepository` for Brain entity instances.

    Args:
        base_dir: directory under which instance files are written. The
            adapter creates the per-entity-type subtree as needed; the caller
            is not expected to pre-create it.
        domain: the entity-schema domain (e.g. ``"product-development"``,
            ``"insurance-broking"``). Schemas are resolved under this; the
            on-disk layout scopes under this.
        schemas_dir: directory where compiled JSON Schemas live. Defaults to
            ``plugins/sulis/brain/compiled`` (the vendored copy of the
            dna-runner output).
    """

    def __init__(
        self,
        base_dir: Path,
        domain: str,
        schemas_dir: Path | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.domain = domain
        self.schemas_dir = (
            Path(schemas_dir) if schemas_dir is not None else _DEFAULT_SCHEMAS_DIR
        )

    # ─── EntityRepository surface ──────────────────────────────────────

    def save(self, entity_type: str, instance: dict) -> None:
        # Validate first; on failure the EntityValidationError propagates and
        # nothing is written. This is the reject-on-invalid discipline.
        self.validate(entity_type, instance)

        path = self._instance_path(entity_type, instance["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        # `sort_keys=True` + `indent=2` keeps git diffs stable across saves
        # of the same entity, which matters when these files are tracked.
        path.write_text(json.dumps(instance, indent=2, sort_keys=True))

    def find_by_id(self, entity_type: str, instance_id: str) -> dict | None:
        path = self._instance_path(entity_type, instance_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def validate(self, entity_type: str, instance: dict) -> None:
        schema = self._load_schema(entity_type)
        validator = jsonschema.Draft202012Validator(schema)
        errors = list(validator.iter_errors(instance))
        if not errors:
            return

        # Compose a plain-English error that names every violation with its
        # field path. Callers that want the structured details can still
        # catch and dig in; the message is the founder-readable surface.
        parts: list[str] = []
        for err in errors:
            field_path = ".".join(str(p) for p in err.absolute_path) or "(root)"
            parts.append(f"{field_path}: {err.message}")
        raise EntityValidationError(
            f"validation failed for {self.domain}/{entity_type}: "
            + "; ".join(parts)
        )

    # ─── internals ─────────────────────────────────────────────────────

    def _load_schema(self, entity_type: str) -> dict:
        path = self.schemas_dir / self.domain / f"{entity_type}.schema.json"
        if not path.exists():
            raise FileNotFoundError(
                f"no compiled schema for {self.domain}/{entity_type} "
                f"at {path}. Vendor the schema from the dna-runner output, "
                "or pass a `schemas_dir` pointing at it."
            )
        return json.loads(path.read_text())

    def _instance_path(self, entity_type: str, instance_id: str) -> Path:
        ulid = self._ulid_from_id(instance_id)
        return self.base_dir / self.domain / entity_type / f"{ulid}.jsonld"

    @staticmethod
    def _ulid_from_id(instance_id: str) -> str:
        """Extract the ULID suffix from a `dna:{entity_type}:{ulid}` id.

        Falls back to the whole string if there are no colons — defensive
        only; the schema's own pattern is what enforces the id shape.
        """
        return instance_id.rsplit(":", 1)[-1]
