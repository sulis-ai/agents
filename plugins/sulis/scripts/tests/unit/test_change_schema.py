"""test_change_schema — the Change entity (#128 mint, DR-031).

Round-trip validation of the compiled Change schema
(`plugins/sulis/brain/compiled/product-development/change.schema.json`) — the
work-unit prov:Activity, sibling to LifecycleRun. Pins, against the REAL
vendored schema via Draft202012Validator (no schema mock):

1. A minimal in-flight Change (the earliest lifecycle state) validates — every
   required field holds at state=in-flight (FIELD-SPEC §1 attack B).
2. A shipped Change carrying the optional lineage + git + shipped_at fields validates.
3. Bad id / missing intent / bad primitive / bad state / bad for_product reject
   (the schema is `unevaluatedProperties:false`, so a stray field rejects too).
4. parent_change + relationship (the #123/#124 carry) validate when present.

Deterministic + offline — no network, no LLM, no subprocess.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

# .../scripts/tests/unit/test_change_schema.py -> repo root is parents[5]
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SCHEMA_PATH = (
    _REPO_ROOT / "plugins" / "sulis" / "brain" / "compiled"
    / "product-development" / "change.schema.json"
)

_ULID = "0123456789ABCDEFGHJKMNPQRS"  # 26 Crockford chars
_CHANGE_ID = f"dna:change:{_ULID}"
_PRODUCT_ID = f"dna:product:{_ULID}"


@pytest.fixture(scope="module")
def schema() -> dict:
    assert _SCHEMA_PATH.exists(), f"change.schema.json missing at {_SCHEMA_PATH}"
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


def _base_change() -> dict:
    """Minimal in-flight Change — exactly the required set."""
    return {
        "id": _CHANGE_ID,
        "handle": "CH-01HQ8X",
        "slug": "fix-login-bug",
        "intent": "fix the login bug",
        "primitive": "fix",
        "state": "in-flight",
        "for_product": _PRODUCT_ID,
        "started_at": "2026-06-12T09:00:00Z",
        "sys_status": "active",
    }


def _validator(schema) -> Draft202012Validator:
    return Draft202012Validator(schema)


def test_minimal_in_flight_change_validates(schema):
    assert _validator(schema).is_valid(_base_change())


def test_shipped_change_with_optionals_validates(schema):
    c = _base_change()
    c.update({
        "state": "shipped",
        "shipped_at": "2026-06-12T10:00:00Z",
        "base_sha": "7a6d267cb05960aba6246ef508ba343ee9f50442",
        "branch": "change/fix-login-bug",
        "by_actor": f"dna:actor:{_ULID}",
        "confidence": 1.0,
    })
    assert _validator(schema).is_valid(c)


def test_parent_change_and_relationship_validate(schema):
    c = _base_change()
    c.update({"parent_change": f"dna:change:{_ULID}", "relationship": "builds_on"})
    assert _validator(schema).is_valid(c)


def test_nuked_state_validates(schema):
    c = _base_change()
    c["state"] = "nuked"
    assert _validator(schema).is_valid(c)


@pytest.mark.parametrize("mutate", [
    lambda c: c.update({"id": "dna:change:not-a-ulid"}),
    lambda c: c.pop("intent"),
    lambda c: c.pop("for_product"),
    lambda c: c.update({"primitive": "frobnicate"}),     # not in the 22-value enum
    lambda c: c.update({"state": "merged"}),             # not in-flight|shipped|nuked
    lambda c: c.update({"for_product": "dna:product:bad"}),
    lambda c: c.update({"relationship": "sibling_of"}),  # not builds_on|depends_on
    lambda c: c.update({"worktree_path": "/tmp/wt"}),    # excluded machine-local field
])
def test_invalid_changes_reject(schema, mutate):
    c = _base_change()
    mutate(c)
    assert not _validator(schema).is_valid(c)


def test_all_22_primitives_accepted(schema):
    v = _validator(schema)
    for p in ["create", "feat", "fix", "refactor", "harden", "decompose", "delete",
              "replace", "extend", "test", "docs", "chore", "perf", "build", "ci",
              "revert", "style", "merge", "spike", "migrate", "deprecate", "release"]:
        c = _base_change()
        c["primitive"] = p
        assert v.is_valid(c), f"primitive {p!r} should validate"
