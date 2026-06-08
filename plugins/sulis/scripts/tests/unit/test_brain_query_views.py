"""Tests for the WP-007 query-seam view extensions on `_brain_query.py`.

These cover the three traverse-path views built on the existing predicate
combinators (ADR-006): `find_opportunities` (the missing sibling to
`find_requirements`), the optional `state=` kwarg on `find_requirements`,
and `find_roadmap` (resolve the ADR-001 sidecar members to entities).

Seeding mirrors `test_brain_query.py`: the read seam treats each instance as
an opaque dict (it never schema-validates on read), so the fixtures write
minimal entities carrying the schema-valid `state` values the views filter
on (requirement: draft/approved/implemented/verified; opportunity:
hypothesis/validated/defined/dropped).
"""

from __future__ import annotations

import json
from pathlib import Path

from _brain_labels import roadmap_sidecar_path
from _brain_query import (
    _DONE_REQUIREMENT_STATES,
    _OPEN_OPPORTUNITY_STATES,
    _OPEN_REQUIREMENT_STATES,
    find_opportunities,
    find_requirements,
    find_roadmap,
)


# ─── Seed ids ────────────────────────────────────────────────────────────
# Requirements across the four states.
_REQ_DRAFT = "dna:requirement:01ABCDEFGHJKMNPQRSTVWXYZ12"
_REQ_APPROVED = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"
_REQ_IMPLEMENTED = "dna:requirement:01CDEFGHJKMNPQRSTVWXYZ1234"
_REQ_VERIFIED = "dna:requirement:01DEFGHJKMNPQRSTVWXYZ12345"

# Opportunities.
_OPP_HYPOTHESIS = "dna:opportunity:01EFGHJKMNPQRSTVWXYZ123456"
_OPP_VALIDATED = "dna:opportunity:01FGHJKMNPQRSTVWXYZ1234567"


def _write_entity(base: Path, entity_type: str, entity_id: str, state: str) -> None:
    """Write one opaque instance under `base/product-development/<type>/`."""
    ulid = entity_id.split(":")[-1]
    p = base / "product-development" / entity_type / f"{ulid}.jsonld"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"id": entity_id, "state": state, "sys_status": "active"}))


def _seed(tmp_path: Path) -> Path:
    """Seed a mixed graph: 4 requirements (one per state) + 2 opportunities."""
    base = tmp_path / ".brain" / "instances"
    _write_entity(base, "requirement", _REQ_DRAFT, "draft")
    _write_entity(base, "requirement", _REQ_APPROVED, "approved")
    _write_entity(base, "requirement", _REQ_IMPLEMENTED, "implemented")
    _write_entity(base, "requirement", _REQ_VERIFIED, "verified")
    _write_entity(base, "opportunity", _OPP_HYPOTHESIS, "hypothesis")
    _write_entity(base, "opportunity", _OPP_VALIDATED, "validated")
    return base


def _write_roadmap_sidecar(tmp_path: Path, members: list) -> None:
    """Write the ADR-001 roadmap sidecar under `<tmp>/.brain/labels/`."""
    brain_root = tmp_path / ".brain"
    sidecar = roadmap_sidecar_path(brain_root)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps({"label": "roadmap", "members": members}))


# ─── find_opportunities ────────────────────────────────────────────────────


def test_find_opportunities_returns_all_then_filtered(tmp_path: Path) -> None:
    base = _seed(tmp_path)

    all_opps = find_opportunities(base)
    assert {o["id"] for o in all_opps} == {_OPP_HYPOTHESIS, _OPP_VALIDATED}

    hypotheses = find_opportunities(base, state="hypothesis")
    assert {o["id"] for o in hypotheses} == {_OPP_HYPOTHESIS}


# ─── find_requirements state kwarg (backward-compat invariant) ─────────────


def test_find_requirements_state_kwarg_backward_compatible(tmp_path: Path) -> None:
    base = _seed(tmp_path)

    # Existing-style call (no state) returns every requirement — unchanged.
    all_reqs = find_requirements(base)
    assert {r["id"] for r in all_reqs} == {
        _REQ_DRAFT,
        _REQ_APPROVED,
        _REQ_IMPLEMENTED,
        _REQ_VERIFIED,
    }

    # New optional state= filter narrows to a single state.
    drafts = find_requirements(base, state="draft")
    assert {r["id"] for r in drafts} == {_REQ_DRAFT}

    # The legacy keyword-domain call signature still works alongside state.
    drafts_explicit = find_requirements(
        base, domain="product-development", state="draft"
    )
    assert {r["id"] for r in drafts_explicit} == {_REQ_DRAFT}


# ─── open / roadmap / done composite views ─────────────────────────────────


def test_open_roadmap_done_views(tmp_path: Path) -> None:
    base = _seed(tmp_path)
    _write_roadmap_sidecar(tmp_path, [_OPP_HYPOTHESIS, _REQ_IMPLEMENTED])
    brain_root = tmp_path / ".brain"

    # Open = draft requirements + hypothesis opportunities.
    open_reqs = find_requirements(base, state="draft")
    open_opps = find_opportunities(base, state="hypothesis")
    open_ids = {e["id"] for e in (*open_reqs, *open_opps)}
    assert open_ids == {_REQ_DRAFT, _OPP_HYPOTHESIS}

    # Done = implemented + verified requirements.
    done_ids = {
        r["id"]
        for state in _DONE_REQUIREMENT_STATES
        for r in find_requirements(base, state=state)
    }
    assert done_ids == {_REQ_IMPLEMENTED, _REQ_VERIFIED}

    # Roadmap = sidecar members resolved to entities.
    roadmap = find_roadmap(brain_root)
    assert {e["id"] for e in roadmap} == {_OPP_HYPOTHESIS, _REQ_IMPLEMENTED}


# ─── empty store → [] (NFR-01, Q3) ─────────────────────────────────────────


def test_empty_store_returns_empty_not_error(tmp_path: Path) -> None:
    empty_instances = tmp_path / ".brain" / "instances"  # never created
    empty_brain_root = tmp_path / ".brain"

    assert find_requirements(empty_instances) == []
    assert find_requirements(empty_instances, state="draft") == []
    assert find_opportunities(empty_instances) == []
    assert find_opportunities(empty_instances, state="hypothesis") == []
    assert find_roadmap(empty_brain_root) == []


# ─── find_roadmap tolerates a malformed sidecar (NFR-01) ───────────────────


def test_find_roadmap_tolerates_malformed_sidecar(tmp_path: Path) -> None:
    _seed(tmp_path)
    brain_root = tmp_path / ".brain"
    sidecar = roadmap_sidecar_path(brain_root)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("this is not json {{{")

    # Junk sidecar → [], never raises.
    assert find_roadmap(brain_root) == []


# ─── the open/done state sets are the single source ────────────────────────


def test_state_sets_are_single_source(tmp_path: Path) -> None:
    # The constants are the only definition of open/done; consumers import
    # them rather than re-deriving the mapping (ADR-006).
    assert _OPEN_REQUIREMENT_STATES == frozenset({"draft"})
    assert _OPEN_OPPORTUNITY_STATES == frozenset({"hypothesis"})
    assert _DONE_REQUIREMENT_STATES == frozenset({"implemented", "verified"})

    # They are immutable frozensets (single source can't be mutated in place).
    assert isinstance(_OPEN_REQUIREMENT_STATES, frozenset)
    assert isinstance(_OPEN_OPPORTUNITY_STATES, frozenset)
    assert isinstance(_DONE_REQUIREMENT_STATES, frozenset)
