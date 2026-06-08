"""Tests for `compose_opportunity_from_idea` — the single-idea capture path.

Sibling to `compose_opportunity_from_srd` (ADR-005): capture has no source
document, only a why-string typed in conversation, so the from-SRD parser
would have nothing to parse. This compose function feeds the same
ID-derivation and dict-shape discipline a different front end.

These tests are deliberately deterministic + offline — no store, no
subprocess. The schema test validates against the REAL vendored
`product-development/opportunity.schema.json` (no mock).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from _opportunity_emission import (
    _deterministic_ulid_from,
    compose_opportunity_from_idea,
)

# tests/unit/<this file> → parents[5] == repo root (mirrors
# test_tools_instance_valid.py's schema-path convention).
_REPO_ROOT = Path(__file__).resolve().parents[5]
_OPPORTUNITY_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "product-development"
    / "opportunity.schema.json"
)

_FOR_PRODUCT = "dna:product:" + _deterministic_ulid_from(
    "product-name:Sulis:tenant:unbound"
)
_JOB = "When I capture an idea I want it rooted in a why so it isn't orphaned."


def test_compose_is_pure_and_deterministic() -> None:
    """Two calls with identical kwargs return identical dicts incl. id;
    no file is touched (the function takes no paths and does no I/O)."""
    a = compose_opportunity_from_idea(
        job_statement=_JOB, for_product=_FOR_PRODUCT, seed="capture-idea-001"
    )
    b = compose_opportunity_from_idea(
        job_statement=_JOB, for_product=_FOR_PRODUCT, seed="capture-idea-001"
    )
    assert a == b
    assert a["id"] == b["id"]
    assert re.fullmatch(r"^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}$", a["id"])


def test_id_namespace_distinct_from_srd() -> None:
    """The same string fed as `seed` here and as an SRD path on the from-SRD
    path yields different ULIDs — the namespace prefix differs, so the two
    capture paths never collide on the same string."""
    shared = "/srd/some/path.md"
    idea = compose_opportunity_from_idea(
        job_statement=_JOB, for_product=_FOR_PRODUCT, seed=shared
    )
    idea_ulid = idea["id"].split(":")[-1]
    srd_ulid = _deterministic_ulid_from(f"opportunity-from-srd:{shared}")
    assert idea_ulid != srd_ulid
    # And the idea ULID is exactly the from-idea-namespaced derivation.
    assert idea_ulid == _deterministic_ulid_from(f"opportunity-from-idea:{shared}")


def test_output_validates_against_vendored_schema() -> None:
    """The composed dict passes jsonschema against the real vendored
    opportunity schema (unevaluatedProperties:false → no stray/null keys)."""
    schema = json.loads(_OPPORTUNITY_SCHEMA_PATH.read_text(encoding="utf-8"))
    opp = compose_opportunity_from_idea(
        job_statement=_JOB,
        for_product=_FOR_PRODUCT,
        seed="capture-idea-001",
        evidence="founder said this loses 15 mins/day",
        impact="reduces orphaned requirements to zero",
    )
    Draft202012Validator(schema).validate(opp)


def test_optional_fields_omitted_when_none() -> None:
    """evidence=None / impact=None ⇒ keys absent, not null
    (unevaluatedProperties clean). The quick-path default omits both."""
    opp = compose_opportunity_from_idea(
        job_statement=_JOB, for_product=_FOR_PRODUCT, seed="capture-idea-001"
    )
    assert "evidence" not in opp
    assert "impact" not in opp
    # Still schema-valid with the optionals absent.
    schema = json.loads(_OPPORTUNITY_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(opp)


def test_state_defaults_hypothesis() -> None:
    """Default state is hypothesis (quick path); an explicit validated is
    honoured (the full/analyst path)."""
    default = compose_opportunity_from_idea(
        job_statement=_JOB, for_product=_FOR_PRODUCT, seed="capture-idea-001"
    )
    assert default["state"] == "hypothesis"

    explicit = compose_opportunity_from_idea(
        job_statement=_JOB,
        for_product=_FOR_PRODUCT,
        seed="capture-idea-001",
        state="validated",
    )
    assert explicit["state"] == "validated"
