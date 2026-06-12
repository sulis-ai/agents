"""Property-based tests for compose_change (#119, #128 slice 2.5).

The Change composer is deterministic logic with a real combinatorial input
space (22 primitives × 3 states × optional fields present/absent × product /
parent on-or-off) and hand-coded invariants. Example tests pin specific points;
these `hypothesis` properties hammer the whole space and assert the invariants
hold EVERYWHERE — the regression guard for the exact defect class proving caught
by hand (the in-flight+shipped_at contradiction; a malformed entity slipping
past the schema).

The load-bearing property: for ANY well-formed input, `compose_change` produces
a SCHEMA-VALID entity AND every invariant holds. Validates against the REAL
vendored schema (no mock).
"""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st
from jsonschema import Draft202012Validator

_SCRIPTS = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_emission import compose_change  # noqa: E402

# .../scripts/tests/unit/ -> repo root is parents[5]
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SCHEMA = json.loads((
    _REPO_ROOT / "plugins" / "sulis" / "brain" / "compiled"
    / "product-development" / "change.schema.json").read_text())
_VALIDATOR = Draft202012Validator(_SCHEMA)

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ULID = st.text(alphabet=_CROCKFORD, min_size=26, max_size=26)
_PRIMITIVES = ["create", "feat", "fix", "refactor", "harden", "decompose", "delete",
               "replace", "extend", "test", "docs", "chore", "perf", "build", "ci",
               "revert", "style", "merge", "spike", "migrate", "deprecate", "release"]
_STATES = ["in-flight", "shipped", "nuked"]
_TS = st.sampled_from(["2026-06-12T09:00:00Z", "2026-01-01T00:00:00Z", "2025-12-31T23:59:59Z"])
_OPT_PRODUCT = st.one_of(st.none(), _ULID.map(lambda u: f"dna:product:{u}"))
_OPT_PARENT = st.one_of(st.none(), _ULID.map(lambda u: f"dna:change:{u}"))
_OPT_REL = st.one_of(st.none(), st.sampled_from(["builds_on", "depends_on"]))
_OPT_TS = st.one_of(st.none(), _TS)


@given(
    change_id=_ULID,
    handle=st.text(min_size=1, max_size=20),
    slug=st.text(min_size=1, max_size=20),
    intent=st.text(max_size=60),
    primitive=st.sampled_from(_PRIMITIVES),
    state=st.sampled_from(_STATES),
    started_at=_TS,
    for_product=_OPT_PRODUCT,
    parent_change=_OPT_PARENT,
    relationship=_OPT_REL,
    shipped_at=_OPT_TS,
)
def test_compose_is_always_schema_valid_and_holds_invariants(
    change_id, handle, slug, intent, primitive, state, started_at,
    for_product, parent_change, relationship, shipped_at,
):
    c = compose_change(
        change_id=change_id, handle=handle, slug=slug, intent=intent,
        primitive=primitive, started_at=started_at, state=state,
        for_product=for_product, parent_change=parent_change,
        relationship=relationship, shipped_at=shipped_at,
    )

    # 1. Always schema-valid (raises on any violation — the property that would
    #    have caught a malformed entity slipping past the example tests).
    _VALIDATOR.validate(c)

    # 2. id reuses the manifest ULID, always.
    assert c["id"] == f"dna:change:{change_id}"

    # 3. Invariant: an in-flight change never carries shipped_at.
    if c["state"] == "in-flight":
        assert "shipped_at" not in c

    # 4. Invariant: a parent link always carries a (non-empty) relationship —
    #    never the empty link that was the #123 bug shape.
    if "parent_change" in c:
        assert c.get("relationship") in ("builds_on", "depends_on")

    # 5. for_product is omitted, never null, when absent (optional link).
    if for_product is None:
        assert "for_product" not in c
