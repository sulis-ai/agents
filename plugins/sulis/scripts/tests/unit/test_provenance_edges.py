"""Provenance edges on every PD entity (#67 / #128 slice 3a).

`produced_by_change` + `evolved_by_change` are the reverse side of Change — the
PROV `wasGeneratedBy` / `wasRevisionOf` edges that let "what did change X
produce/revise?" be a query (the transaction set for ship=commit / nuke=rollback).
They live on every product-development entity UNIFORMLY (the shared envelope),
so the reverse-query reads one field name across all types. Both are OPTIONAL +
additive — pre-existing instances stay valid without them.

Change itself is excluded: a change isn't produced_by another change; its
lineage is `parent_change`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

_REPO = Path(__file__).resolve().parents[5]
_PD = _REPO / "plugins" / "sulis" / "brain" / "compiled" / "product-development"
_SCHEMAS = sorted(p for p in _PD.glob("*.schema.json") if p.name != "change.schema.json")
_CHANGE_PAT = "^dna:change:[0-9A-HJKMNP-TV-Z]{26}$"
_ULID = "0123456789ABCDEFGHJKMNPQRS"


@pytest.mark.parametrize("schema_path", _SCHEMAS, ids=lambda p: p.name)
def test_pd_entity_defines_both_provenance_edges(schema_path):
    props = json.loads(schema_path.read_text(encoding="utf-8"))["properties"]
    pbc = props.get("produced_by_change")
    assert pbc and pbc.get("type") == "string" and pbc.get("pattern") == _CHANGE_PAT, \
        f"{schema_path.name}: produced_by_change missing/malformed"
    ebc = props.get("evolved_by_change")
    assert ebc and ebc.get("type") == "array", f"{schema_path.name}: evolved_by_change missing"
    assert ebc.get("items", {}).get("pattern") == _CHANGE_PAT, \
        f"{schema_path.name}: evolved_by_change items malformed"


def test_change_schema_has_no_self_provenance_edge():
    # A Change isn't produced_by another change — its lineage is parent_change.
    props = json.loads((_PD / "change.schema.json").read_text(encoding="utf-8"))["properties"]
    assert "produced_by_change" not in props
    assert "evolved_by_change" not in props


def _valid_scenario() -> dict:
    return {
        "id": f"dna:scenario:{_ULID}", "name": "n",
        "verifies": [f"dna:requirement:{_ULID}"], "exercises": f"dna:design:{_ULID}",
        "journey": f"dna:workflow:{_ULID}", "state": "draft", "sys_status": "active",
    }


def test_entity_validates_with_the_edges_populated():
    v = Draft202012Validator(json.loads((_PD / "scenario.schema.json").read_text()))
    s = _valid_scenario()
    s["produced_by_change"] = f"dna:change:{_ULID}"
    s["evolved_by_change"] = [f"dna:change:{_ULID}", f"dna:change:{'A' * 26}"]
    assert v.is_valid(s)


def test_entity_still_valid_without_the_edges():
    # Additive: a pre-edge instance must still validate (no migration needed).
    v = Draft202012Validator(json.loads((_PD / "scenario.schema.json").read_text()))
    assert v.is_valid(_valid_scenario())


def test_entity_rejects_a_malformed_change_ref():
    v = Draft202012Validator(json.loads((_PD / "scenario.schema.json").read_text()))
    s = _valid_scenario()
    s["produced_by_change"] = "dna:change:not-a-ulid"
    assert not v.is_valid(s)
