"""Tests for the re-vendored LifecycleRun v2 schema (WP-002).

The vendored schema at
`plugins/sulis/brain/compiled/product-development/lifecyclerun.schema.json`
is a surgical re-vendor of the canonical compiled LifecycleRun (ADR-004).

Since the WP was written the upstream `for_project` mint was walked, so the
current canonical is **v2.2.0** — a clean superset of v2.1.0 (same breaking
`step_name`->`step` ref change, PLUS the DR-013 optional fields
`run_id`/`deterministic`/`inputs_ref`/`outputs_ref` and the new optional
`for_project`). Any DoD check expecting `2.1.0` is satisfied by `2.2.0`
(the superset): we assert `>= 2.1.0`.

Load-bearing assertions (per the WP Definition of Done):
  - the vendored schema requires `step` (a ref), NOT `step_name`;
  - there is NO `step_label` property and NO `used` property;
  - the four DR-013 optional fields are present and optional.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_VENDORED = (
    _SCRIPTS_DIR.parent
    / "brain"
    / "compiled"
    / "product-development"
    / "lifecyclerun.schema.json"
)

# The authoritative canonical compiled source (re-vendor origin). Outside the
# repo on a dev box; the byte-faithfulness test skips cleanly when absent so
# CI (which has no access to the dna repo checkout) stays green.
_CANONICAL_SOURCE = Path(
    "/Users/iain/Documents/repos/plugins/.specifications/business-dna"
    "/compiled/schemas/product-development/lifecyclerun.schema.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _version_tuple(schema: dict) -> tuple[int, int, int]:
    # $id ends with .../lifecyclerun/<MAJOR>.<MINOR>.<PATCH>
    ver = schema["$id"].rsplit("/", 1)[-1]
    major, minor, patch = (int(x) for x in ver.split("."))
    return (major, minor, patch)


class TestRevendoredSchema:
    def test_revendored_schema_matches_canonical(self) -> None:
        """Vendored file is structurally equal to the canonical compiled
        schema (modulo the byte-identical drop-in re-vendor). Skips when the
        canonical source checkout isn't present (CI)."""
        if not _CANONICAL_SOURCE.exists():
            pytest.skip("canonical compiled source not available in this environment")
        assert _load(_VENDORED) == _load(_CANONICAL_SOURCE)

    def test_schema_id_is_at_least_2_1_0(self) -> None:
        """`$id` is the canonical LifecycleRun at >= 2.1.0 (2.2.0 superset OK)."""
        schema = _load(_VENDORED)
        assert schema["$id"].startswith("https://sulis.co/dna/schema/lifecyclerun/")
        assert _version_tuple(schema) >= (2, 1, 0)

    def test_v2_requires_step_ref(self) -> None:
        """A doc with a `step` ref validates; one with `step_name` and no
        `step` is rejected (the breaking required-field swap)."""
        schema = _load(_VENDORED)
        validator = jsonschema.Draft202012Validator(schema)

        good = {
            "id": "dna:lifecyclerun:01ABCDEFGHJKMNPQRSTVWXYZ12",
            "step": "dna:step:01KT61X5ST01CHANGESTART00A",
            "at": "2026-06-03T00:00:00Z",
            "outcome": "completed",
            "sys_status": "active",
        }
        assert list(validator.iter_errors(good)) == []

        bad = {
            "id": "dna:lifecyclerun:01ABCDEFGHJKMNPQRSTVWXYZ12",
            "step_name": "change-started:fix:x",
            "at": "2026-06-03T00:00:00Z",
            "outcome": "completed",
            "sys_status": "active",
        }
        assert list(validator.iter_errors(bad)) != []

    def test_step_property_is_a_step_ref_pattern(self) -> None:
        schema = _load(_VENDORED)
        step = schema["properties"]["step"]
        assert step["type"] == "string"
        assert "step" in step["pattern"]

    def test_no_step_name_property(self) -> None:
        schema = _load(_VENDORED)
        assert "step_name" not in schema["properties"]
        assert "step_name" not in schema.get("required", [])

    def test_no_step_label_field(self) -> None:
        schema = _load(_VENDORED)
        assert "step_label" not in schema["properties"]

    def test_no_used_field(self) -> None:
        schema = _load(_VENDORED)
        assert "used" not in schema["properties"]

    def test_dr013_optional_fields_present(self) -> None:
        schema = _load(_VENDORED)
        required = set(schema.get("required", []))
        for field in ("run_id", "deterministic", "inputs_ref", "outputs_ref"):
            assert field in schema["properties"], f"{field} missing"
            assert field not in required, f"{field} must be optional"
