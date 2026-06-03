"""Tests for `compose_requirement_from_idea` in `_requirement_emission.py`.

The single-idea compose path (ADR-005) — sibling to the from-SRD path. It
takes a what-string + a *real* Opportunity ref typed in conversation (no
document to parse) and produces one Requirement entity dict of the same shape
the from-SRD path emits (one per FR block there; exactly one here).

The load-bearing invariant (ADR-005, ADR-003): the Requirement's `source` is a
**real** Opportunity id the orchestrator just emitted — never a synthetic
placeholder. The compose function passes `source` through verbatim and refuses
to compose a Requirement whose `source` is not a well-formed
`dna:opportunity:<ulid>` ref. This is the code-level enforcement of "no orphan
requirements": a Requirement physically cannot be composed without a real
Opportunity ref.

Decisions pinned by these tests:
  - **Pure** — same inputs → identical dict (incl. id); no I/O.
  - **Deterministic id** — `dna:requirement:` +
    `_deterministic_ulid_from("requirement-from-idea:" + seed)`; a distinct
    namespace from the from-SRD path so the two never collide on the same seed.
  - **Verbatim source pass-through + validation** — a malformed `source`
    raises `ValueError`.
  - **Schema-clean** — the dict validates against the real vendored
    `product-development/requirement.schema.json` under
    `unevaluatedProperties: false`.
  - **Defaults** — `state="draft"`, `priority="must"`,
    `verification_method="test"`, `sys_status="active"`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

from _requirement_emission import (
    compose_requirement_from_idea,
    compose_requirements_from_srd,
)


# ─── fixtures ─────────────────────────────────────────────────────────────


# A well-formed (real) Opportunity ref — 26 Crockford-base32 chars.
_REAL_OPPORTUNITY = "dna:opportunity:01ARZ3NDEKTSV4RRFFQ69G5FAV"

# The vendored schemas live at plugins/sulis/brain/compiled — i.e. a sibling
# of the scripts dir, not under it. Reuse the adapter's own resolution so the
# test reads exactly the schema the persistence path validates against.
from _entity_adapter_local import _DEFAULT_SCHEMAS_DIR  # noqa: E402

_REQUIREMENT_SCHEMA_PATH = (
    _DEFAULT_SCHEMAS_DIR / "product-development" / "requirement.schema.json"
)


@pytest.fixture(scope="module")
def requirement_schema() -> dict:
    """The real vendored Requirement JSON Schema (unevaluatedProperties:false)."""
    return json.loads(_REQUIREMENT_SCHEMA_PATH.read_text(encoding="utf-8"))


def _compose(**overrides) -> dict:
    """Compose a Requirement with sensible defaults, overridable per test."""
    kwargs = {
        "statement": "Capture the founder's idea as a draft requirement",
        "source": _REAL_OPPORTUNITY,
        "seed": "capture-the-founders-idea",
    }
    kwargs.update(overrides)
    return compose_requirement_from_idea(**kwargs)


# ─── pure-transformation tests ────────────────────────────────────────────


def test_compose_is_pure_and_deterministic(tmp_path: Path) -> None:
    """Two identical calls → identical dict incl. id; no file touched."""
    before = set(p for p in tmp_path.rglob("*"))

    a = _compose()
    b = _compose()

    assert a == b, "same inputs must produce an identical dict"
    assert a["id"] == b["id"], "id must be deterministic across calls"

    after = set(p for p in tmp_path.rglob("*"))
    assert before == after, "compose must perform no I/O"


def test_source_is_real_opportunity_ref() -> None:
    """Given a real opportunity id, the dict's `source` equals it verbatim."""
    r = _compose(source=_REAL_OPPORTUNITY)
    assert r["source"] == _REAL_OPPORTUNITY


def test_rejects_malformed_source() -> None:
    """A non-`dna:opportunity:` source raises ValueError (no dangling ref)."""
    malformed = [
        "",
        "opportunity:01ARZ3NDEKTSV4RRFFQ69G5FAV",  # missing dna: prefix
        "dna:requirement:01ARZ3NDEKTSV4RRFFQ69G5FAV",  # wrong entity type
        "dna:opportunity:not-a-ulid",  # bad ULID body
        "dna:opportunity:01ARZ3NDEKTSV4RRFFQ69G5FA",  # 25 chars (too short)
        "dna:opportunity:01ARZ3NDEKTSV4RRFFQ69G5FAVX",  # 27 chars (too long)
        "dna:opportunity:01ARZ3NDEKTSV4RRFFQ69G5FAI",  # 'I' not in Crockford alphabet
    ]
    for bad in malformed:
        with pytest.raises(ValueError):
            _compose(source=bad)


def test_output_validates_against_vendored_schema(requirement_schema: dict) -> None:
    """The composed dict validates against the real vendored schema, clean."""
    r = _compose()
    # Raises jsonschema.ValidationError on any violation, including
    # unevaluatedProperties:false (an extra key would fail here).
    jsonschema.Draft202012Validator(requirement_schema).validate(r)


def test_state_defaults_draft() -> None:
    """Default state is `draft` (captured-and-set-aside lives as draft)."""
    r = _compose()
    assert r["state"] == "draft"


# ─── shape / default tests ────────────────────────────────────────────────


def test_id_matches_schema_pattern() -> None:
    r = _compose()
    assert re.match(r"^dna:requirement:[0-9A-HJKMNP-TV-Z]{26}$", r["id"]), r["id"]


def test_id_namespace_is_distinct_from_from_srd_path() -> None:
    """from-idea and from-srd must not collide on the same seed string.

    The from-SRD path derives its requirement id from
    `requirement:{srd_path}:{fr_id}`; the from-idea path from
    `requirement-from-idea:{seed}`. Even if a caller passed a seed equal to a
    from-SRD `{srd_path}:{fr_id}`, the distinct namespace prefix keeps the ids
    apart.
    """
    seed = "x/SRD.md:FR-01"
    from_idea = compose_requirement_from_idea(
        statement="s", source=_REAL_OPPORTUNITY, seed=seed
    )
    from_srd = compose_requirements_from_srd(
        "**FR-01: Title**\n\nbody\n", srd_path="x/SRD.md"
    )
    assert from_idea["id"] != from_srd[0]["id"]


def test_priority_and_verification_method_defaults() -> None:
    r = _compose()
    assert r["priority"] == "must"
    assert r["verification_method"] == "test"
    assert r["sys_status"] == "active"


def test_priority_override_is_respected() -> None:
    r = _compose(priority="should")
    assert r["priority"] == "should"


def test_acceptance_criteria_passed_through() -> None:
    criteria = ["The draft requirement is persisted", "It traces to the opportunity"]
    r = _compose(acceptance_criteria=criteria)
    assert r["acceptance_criteria"] == criteria


def test_default_acceptance_criteria_keeps_schema_clean(
    requirement_schema: dict,
) -> None:
    """acceptance_criteria=None ⇒ a single honest placeholder (minItems:1)."""
    r = _compose(acceptance_criteria=None)
    jsonschema.Draft202012Validator(requirement_schema).validate(r)
    ac = r["acceptance_criteria"]
    assert isinstance(ac, list) and len(ac) >= 1


def test_does_not_touch_from_srd_path() -> None:
    """Regression guard: the from-SRD composer still works unchanged."""
    rs = compose_requirements_from_srd(
        "**FR-01: Authenticate**\n\nThe system MUST authenticate.\n",
        srd_path="x/SRD.md",
    )
    assert len(rs) == 1
    assert rs[0]["state"] == "draft"
    assert rs[0]["source"].startswith("dna:opportunity:")
