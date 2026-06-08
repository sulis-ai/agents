"""
test_scenario_schema — WP-001 (verification-substrate, kind: contract)

Round-trip validation that the compiled Scenario schema
(`plugins/sulis/brain/compiled/product-development/scenario.schema.json`)
gains the two new OPTIONAL contract fields — `isolation` and
`verdict_invariant` — additively, so:

1. A Scenario carrying `isolation: "reset"` and a well-formed
   `verdict_invariant` object validates against the schema.
2. A pre-change Scenario (no new fields) still validates.

Both run against the REAL vendored schema via `Draft202012Validator`
(no schema mock — MEA-09). The schema enforces
`unevaluatedProperties: false`, so before the schema edit the new fields
are rejected (Red) and the with-fields test fails for the right reason.

Field shapes are fixed by the contract artifact
(`contracts/verdict-invariant.contract.md`) and TDD §A:
  - isolation: enum reset|process|env
  - verdict_invariant: object {kind (req: equality|property), expected_ref,
    poll{attempts (req, >=1), interval_ms (>=0)}}; unevaluatedProperties:false

Deliberately deterministic + offline — no network, no LLM, no subprocess.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

# plugins/sulis/scripts/tests/unit/test_scenario_schema.py -> repo root is parents[5]
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "product-development"
    / "scenario.schema.json"
)


@pytest.fixture(scope="module")
def schema() -> dict:
    """The real vendored Scenario schema (product-development)."""
    assert _SCHEMA_PATH.exists(), f"scenario.schema.json missing at {_SCHEMA_PATH}"
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


def _base_scenario() -> dict:
    """A minimal Scenario instance carrying exactly the required fields.

    Mirrors the schema's `required`: id, name, verifies, exercises, journey,
    state, sys_status. ULIDs use the schema's Crockford-base32 pattern.
    """
    return {
        "id": "dna:scenario:01J0000000000000000000000A",
        "name": "checkout completes and the order is saved",
        "verifies": ["dna:requirement:01J0000000000000000000000B"],
        "exercises": "dna:design:01J0000000000000000000000C",
        "journey": "dna:workflow:01J0000000000000000000000D",
        "state": "active",
        "sys_status": "active",
    }


def test_scenario_with_new_fields_validates(schema: dict) -> None:
    """A Scenario carrying `isolation` + a well-formed `verdict_invariant`
    validates against the updated schema.

    Before the schema edit this FAILS: `unevaluatedProperties: false` rejects
    both unknown top-level properties.
    """
    instance = _base_scenario()
    instance["isolation"] = "reset"
    instance["verdict_invariant"] = {
        "kind": "property",
        "expected_ref": "dna:requirement:01J0000000000000000000000B#saved-order",
        "poll": {"attempts": 3, "interval_ms": 200},
    }

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    assert not errors, (
        "Scenario with isolation + verdict_invariant rejected by schema: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )


def test_scenario_without_new_fields_still_validates(schema: dict) -> None:
    """A pre-change Scenario (no `isolation`, no `verdict_invariant`) still
    validates — the new fields are optional, so backward-compatible.
    """
    instance = _base_scenario()

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    assert not errors, (
        "pre-change Scenario (no new fields) rejected by schema: "
        + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
    )
