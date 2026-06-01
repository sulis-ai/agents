"""JsonLdFileReader — port 1: read canonical entity instances.

Implements the CanonicalReader port from the TDD's Form section. Reads each
of the canonical jsonld files + (optionally) validates the contents against
the vendored compiled schemas at plugins/sulis/brain/compiled/foundation/.

No global state — every call resolves paths from arguments. No network.
"""

from __future__ import annotations

import json
from pathlib import Path


_SCHEMA_FILES = {
    "workflow": "workflow.schema.json",
    "step": "step.schema.json",
    "failuremode": "failuremode.schema.json",
    "tool": "tool.schema.json",
    "trigger": "trigger.schema.json",
}


class JsonLdFileReader:
    """Read jsonld canonical entity instances + (optionally) schema-validate.

    Instance files live at <instance_dir>/<name>.jsonld with the shape:
        {"@id": "...", "@type": "...", "<plural-key>": [<item>, ...]}
    e.g. steps.jsonld has key "steps", failuremodes.jsonld has "failuremodes".
    """

    def __init__(self, schemas_dir: Path | None = None) -> None:
        """schemas_dir defaults to the marketplace's compiled foundation schemas."""
        if schemas_dir is None:
            # plugins/sulis/scripts/_canonical_drift/reader.py
            #   → plugins/sulis/brain/compiled/foundation/
            here = Path(__file__).resolve()
            schemas_dir = (
                here.parent.parent.parent / "brain" / "compiled" / "foundation"
            )
        self._schemas_dir = schemas_dir

    # ─── Public reads ────────────────────────────────────────────────────

    def read_workflow(self, instance_dir: Path, validate: bool = False) -> dict:
        """Return the first workflow in workflow.jsonld (a release-train Workflow file holds one)."""
        items = self._read_list(instance_dir, "workflow.jsonld", "workflows")
        if validate:
            self._validate_each(items, "workflow")
        if not items:
            raise ValueError(f"No workflows in {instance_dir / 'workflow.jsonld'}")
        return items[0]

    def read_steps(self, instance_dir: Path, validate: bool = False) -> list[dict]:
        items = self._read_list(instance_dir, "steps.jsonld", "steps")
        if validate:
            self._validate_each(items, "step")
        return items

    def read_failuremodes(
        self, instance_dir: Path, validate: bool = False
    ) -> list[dict]:
        items = self._read_list(instance_dir, "failuremodes.jsonld", "failuremodes")
        if validate:
            self._validate_each(items, "failuremode")
        return items

    def read_tools(self, instance_dir: Path, validate: bool = False) -> list[dict]:
        """Return tool catalogue. Tools with state=draft are schema-validation-exempt
        per ADR-003 (the stub-tier holds a minimal frontmatter only)."""
        items = self._read_list(instance_dir, "tools.jsonld", "tools")
        if validate:
            active = [t for t in items if t.get("state") == "active"]
            self._validate_each(active, "tool")
        return items

    def read_triggers(self, instance_dir: Path, validate: bool = False) -> list[dict]:
        items = self._read_list(instance_dir, "triggers.jsonld", "triggers")
        if validate:
            self._validate_each(items, "trigger")
        return items

    # ─── Internals ───────────────────────────────────────────────────────

    def _read_list(
        self, instance_dir: Path, filename: str, plural_key: str
    ) -> list[dict]:
        path = instance_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Canonical instance not found: {path}")
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON in {path}: {e}") from e
        items = doc.get(plural_key, [])
        if not isinstance(items, list):
            raise ValueError(
                f"{path}: expected '{plural_key}' to be a list, got {type(items).__name__}"
            )
        return items

    def _validate_each(self, items: list[dict], entity_type: str) -> None:
        """Validate each item against the compiled schema; raise on first failure."""
        try:
            import jsonschema
        except ImportError as e:  # pragma: no cover — jsonschema is in pyproject
            raise RuntimeError(
                "jsonschema package required for canonical validation"
            ) from e

        schema_path = self._schemas_dir / _SCHEMA_FILES[entity_type]
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")
        schema = json.loads(schema_path.read_text())

        for item in items:
            try:
                jsonschema.validate(item, schema)
            except jsonschema.ValidationError as e:
                # Field-path = json-path through the failing item.
                field_path = "/".join(str(p) for p in e.absolute_path) or "(root)"
                name = item.get("name", item.get("id", "<unknown>"))
                raise ValueError(
                    f"Schema validation failed for {entity_type} '{name}' "
                    f"at field '{field_path}': {e.message}"
                ) from e
