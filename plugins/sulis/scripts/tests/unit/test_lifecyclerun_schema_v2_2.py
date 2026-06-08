"""Tests for the re-vendored LifecycleRun v2.2.0 schema's `for_project`
property (WP-016, ADR-007).

The v2.2.0 increment adds ONE optional `for_project` ref property over v2.1.0:
a plain `properties` ref string (pattern `^dna:(project):…$`), NOT a
`prov_constraints` edge, NOT in `required`. It mirrors the live
`Workflow.for_project` shape byte-for-shape. Pre-bump v2.1.0 instances (no
`for_project`) validate unchanged under v2.2.0 (zero-migration additive MINOR).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_COMPILED = _SCRIPTS_DIR.parent / "brain" / "compiled"
_VENDORED = _COMPILED / "product-development" / "lifecyclerun.schema.json"
_WORKFLOW = _COMPILED / "foundation" / "workflow.schema.json"

_STEP = "dna:step:01KT61X5ST01CHANGESTART00A"


def _schema() -> dict:
    return json.loads(_VENDORED.read_text())


def test_revendored_schema_is_at_least_2_2_0() -> None:
    schema_id = _schema()["$id"]
    # $id ends with the schema version; v2.2.0 (or a later superset) satisfies.
    version = schema_id.rstrip("/").rsplit("/", 1)[-1]
    major, minor, *_ = (int(p) for p in version.split("."))
    assert (major, minor) >= (2, 2), f"expected >= 2.2.0, got {version}"


def test_for_project_property_present_and_optional() -> None:
    schema = _schema()
    assert "for_project" in schema["properties"], "for_project must be a property"
    assert "for_project" not in schema.get("required", []), "for_project must be optional (card 0..1)"
    prop = schema["properties"]["for_project"]
    assert prop["type"] == "string"
    assert prop["pattern"] == r"^dna:(project):[0-9A-HJKMNP-TV-Z]{26}$"


def test_for_project_shape_matches_workflow() -> None:
    """for_project reuses the live Workflow.for_project shape (type + pattern) —
    one convention, EP-03 / CP-01 prior-art-in-repo."""
    wf = json.loads(_WORKFLOW.read_text())["properties"]["for_project"]
    lr = _schema()["properties"]["for_project"]
    assert lr["type"] == wf["type"]
    assert lr["pattern"] == wf["pattern"]


def test_no_prov_constraints_for_project() -> None:
    """for_project is a plain properties ref, NOT a prov_constraints edge."""
    schema = _schema()
    prov = schema.get("prov_constraints", {})
    assert "for_project" not in prov
    assert "forProject" not in json.dumps(prov)


def test_v2_1_instance_still_valid_under_2_2() -> None:
    """A run with NO for_project (a pre-bump v2.1.0 shape) validates under
    v2.2.0 — zero-migration additive MINOR."""
    v21_instance = {
        "id": "dna:lifecyclerun:01ABCDEFGHJKMNPQRSTVWXYZ12",
        "step": _STEP,
        "at": "2026-06-03T00:00:00+00:00",
        "outcome": "completed",
        "sys_status": "active",
    }
    jsonschema.validate(instance=v21_instance, schema=_schema())


def test_for_project_instance_validates() -> None:
    instance = {
        "id": "dna:lifecyclerun:01ABCDEFGHJKMNPQRSTVWXYZ12",
        "step": _STEP,
        "at": "2026-06-03T00:00:00+00:00",
        "outcome": "completed",
        "sys_status": "active",
        "for_project": "dna:project:01KT1WPR0JECT0000000000000",
    }
    jsonschema.validate(instance=instance, schema=_schema())


def test_bad_for_project_rejected_by_schema() -> None:
    instance = {
        "id": "dna:lifecyclerun:01ABCDEFGHJKMNPQRSTVWXYZ12",
        "step": _STEP,
        "at": "2026-06-03T00:00:00+00:00",
        "outcome": "completed",
        "sys_status": "active",
        "for_project": "not-a-project-ref",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=_schema())
