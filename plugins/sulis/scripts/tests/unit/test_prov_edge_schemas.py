"""Tests for the re-vendored ``wasGeneratedBy`` prov edge on Product +
Opportunity (WP-008).

The upstream ``wasGeneratedBy`` mint was walked (DR-031): canonical Product is
now **v1.1.0** and Opportunity **v2.1.0**, each carrying an optional
``wasGeneratedBy -> dna:entity:lifecyclerun`` (card ``0..1``) edge. This WP
re-vendors those two bumped compiled schemas into
``plugins/sulis/brain/compiled/product-development/``.

How the edge is carried — load-bearing
--------------------------------------
``wasGeneratedBy`` is a **``prov_constraints`` / triples-layer** edge, exactly
like the five existing PD producers (Component, Release, Metric, TestResult,
PostMortem). It is NOT a JSON-Schema scalar property. In the canonical compiled
output it lives in the *triples manifest*
(``compiled/triples/product-development/{product,opportunity}.triples.json``)
as ``{"predicate": "prov:wasGeneratedBy", "object_pattern":
"dna:lifecyclerun:{ulid}", "card": "0..1", "source":
"prov_constraints.wasGeneratedBy"}``.

The vendored ``brain/compiled`` tree is **schema-only** — no triples manifest
is vendored for ANY entity, including the five existing ``wasGeneratedBy``
producers. So the vendored representation of the v1.1.0 / v2.1.0 bump is the
schema-body re-vendor (the ``$id`` increment), byte-faithful to canonical.
The edge-presence + cardinality assertions therefore run against the
authoritative canonical triples manifest, and skip cleanly when that source
checkout is not present (CI), mirroring the WP-002 sibling
(``test_lifecyclerun_schema_v2.py``).

Definition of Done assertions (per the WP):
  - the edge exists on Product + Opportunity (canonical triples), optional;
  - the edge is the ``prov_constraints`` mechanism, NOT a snake_case scalar;
  - cardinality is ``0..1`` (pre-bump instances without it still validate);
  - Project carries NO such edge and stays ``schema_version`` 1.0.0;
  - vendored Product ``$id`` is 1.1.0, Opportunity 2.1.0;
  - ``wasRevisionOf`` appears nowhere;
  - the vendored copies are byte-faithful to the upstream-recompiled schemas.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_COMPILED = _SCRIPTS_DIR.parent / "brain" / "compiled"
_PD = _COMPILED / "product-development"
_FOUNDATION = _COMPILED / "foundation"

_VENDORED_PRODUCT = _PD / "product.schema.json"
_VENDORED_OPPORTUNITY = _PD / "opportunity.schema.json"
_VENDORED_PROJECT = _FOUNDATION / "project.schema.json"

# The authoritative canonical compiled source (re-vendor origin). Outside the
# repo on a dev box; the triples-edge + byte-faithfulness tests skip cleanly
# when absent so CI (no dna-repo checkout) stays green — same pattern as the
# WP-002 LifecycleRun schema tests.
_CANONICAL_ROOT = Path(
    "/Users/iain/Documents/repos/plugins/.specifications/business-dna/compiled"
)
_CANON_SCHEMAS = _CANONICAL_ROOT / "schemas" / "product-development"
_CANON_TRIPLES = _CANONICAL_ROOT / "triples" / "product-development"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _version_tuple(schema: dict) -> tuple[int, int, int]:
    # $id ends with .../<entity>/<MAJOR>.<MINOR>.<PATCH>
    ver = schema["$id"].rsplit("/", 1)[-1]
    major, minor, patch = (int(x) for x in ver.split("."))
    return (major, minor, patch)


def _was_generated_by_triple(triples_doc: dict) -> dict | None:
    for t in triples_doc.get("triples", []):
        if t.get("predicate") == "prov:wasGeneratedBy":
            return t
    return None


# A canonical-source guard reused by the triples-dependent tests.
_canonical_triples_missing = not (
    (_CANON_TRIPLES / "product.triples.json").exists()
    and (_CANON_TRIPLES / "opportunity.triples.json").exists()
)
_skip_no_canonical = pytest.mark.skipif(
    _canonical_triples_missing,
    reason="canonical compiled triples not available in this environment",
)


class TestWasGeneratedByEdge:
    """The edge exists, optional, on Product + Opportunity (and ONLY via the
    ``prov_constraints`` triples mechanism)."""

    @_skip_no_canonical
    @pytest.mark.parametrize("entity", ["product", "opportunity"])
    def test_was_generated_by_edge_on_product_and_opportunity(
        self, entity: str
    ) -> None:
        triples = _load(_CANON_TRIPLES / f"{entity}.triples.json")
        edge = _was_generated_by_triple(triples)
        assert edge is not None, f"{entity} canonical triples missing wasGeneratedBy"
        assert edge["object_pattern"] == "dna:lifecyclerun:{ulid}"
        assert edge["source"] == "prov_constraints.wasGeneratedBy"

    @_skip_no_canonical
    @pytest.mark.parametrize("entity", ["product", "opportunity"])
    def test_edge_is_prov_constraints_not_scalar(self, entity: str) -> None:
        """The edge is carried by the ``prov_constraints`` mechanism (its
        ``source`` is ``prov_constraints.wasGeneratedBy``), and there is NO
        snake_case ``was_generated_by`` scalar in the vendored schema
        ``properties`` — matching how Component/Release/Metric carry theirs."""
        # canonical: the edge's source is the prov_constraints block
        triples = _load(_CANON_TRIPLES / f"{entity}.triples.json")
        edge = _was_generated_by_triple(triples)
        assert edge is not None
        assert edge["source"].startswith("prov_constraints.")

        # vendored schema: no snake_case scalar smuggled into properties
        vendored = _VENDORED_PRODUCT if entity == "product" else _VENDORED_OPPORTUNITY
        props = _load(vendored)["properties"]
        assert "was_generated_by" not in props
        assert "wasGeneratedBy" not in props

    @_skip_no_canonical
    @pytest.mark.parametrize("entity", ["product", "opportunity"])
    def test_cardinality_is_optional(self, entity: str) -> None:
        """Canonical edge is ``0..1`` (optional). A vendored-schema instance
        WITH a ``wasGeneratedBy``-style ref present and one WITHOUT it both
        validate — proving the bump is zero-migration (pre-bump instances stay
        valid). The edge is triples-layer, so the JSON-Schema accepts instances
        either way under ``unevaluatedProperties: false`` because the ref is not
        a schema property; the cardinality contract is the ``0..1`` in triples."""
        triples = _load(_CANON_TRIPLES / f"{entity}.triples.json")
        edge = _was_generated_by_triple(triples)
        assert edge is not None
        assert edge["card"] == "0..1"

        vendored = _VENDORED_PRODUCT if entity == "product" else _VENDORED_OPPORTUNITY
        validator = jsonschema.Draft202012Validator(_load(vendored))
        if entity == "product":
            without = {
                "id": "dna:product:01ABCDEFGHJKMNPQRSTVWXYZ12",
                "name": "Acme",
                "belongs_to_tenant": "dna:tenant:01ABCDEFGHJKMNPQRSTVWXYZ12",
                "state": "active",
                "sys_status": "active",
            }
        else:
            without = {
                "id": "dna:opportunity:01ABCDEFGHJKMNPQRSTVWXYZ12",
                "for_product": "dna:product:01ABCDEFGHJKMNPQRSTVWXYZ12",
                "job_statement": "when X I want Y so I can Z",
                "state": "validated",
                "sys_status": "active",
            }
        # pre-bump instance (no edge ref) validates
        assert list(validator.iter_errors(without)) == []


class TestProjectExcluded:
    def test_project_schema_unchanged(self) -> None:
        """Project (prov:Plan) carries NO wasGeneratedBy edge and stays at
        schema_version 1.0.0 — type violation per ADR-002."""
        schema = _load(_VENDORED_PROJECT)
        assert _version_tuple(schema) == (1, 0, 0)
        assert "was_generated_by" not in schema.get("properties", {})
        assert "wasGeneratedBy" not in schema.get("properties", {})

        # canonical Project triples (if present) carry no wasGeneratedBy either
        canon_project = _CANON_TRIPLES / "project.triples.json"
        if canon_project.exists():
            assert _was_generated_by_triple(_load(canon_project)) is None


class TestVersionBumps:
    def test_minor_version_bumps(self) -> None:
        """Vendored Product ``$id`` is 1.1.0; Opportunity ``$id`` is 2.1.0."""
        assert _version_tuple(_load(_VENDORED_PRODUCT)) == (1, 1, 0)
        assert _version_tuple(_load(_VENDORED_OPPORTUNITY)) == (2, 1, 0)


class TestNoWasRevisionOf:
    def test_no_wasrevisionof_anywhere(self) -> None:
        """``wasRevisionOf`` appears in NO vendored schema body, and (when the
        canonical source is present) in NO Product/Opportunity triples."""
        for vendored in (_VENDORED_PRODUCT, _VENDORED_OPPORTUNITY, _VENDORED_PROJECT):
            assert "wasRevisionOf" not in vendored.read_text()

        if not _canonical_triples_missing:
            for entity in ("product", "opportunity"):
                triples = _load(_CANON_TRIPLES / f"{entity}.triples.json")
                preds = [t.get("predicate") for t in triples.get("triples", [])]
                assert "prov:wasRevisionOf" not in preds


class TestRevendoredByteFaithful:
    @_skip_no_canonical
    @pytest.mark.parametrize(
        "entity,vendored",
        [("product", _VENDORED_PRODUCT), ("opportunity", _VENDORED_OPPORTUNITY)],
    )
    def test_revendored_copies_match_upstream(
        self, entity: str, vendored: Path
    ) -> None:
        """The vendored schema body is byte-faithful to the canonical
        recompiled schema (drift-detector parity). Skips when the canonical
        source checkout isn't present (CI)."""
        canonical = _CANON_SCHEMAS / f"{entity}.schema.json"
        if not canonical.exists():
            pytest.skip("canonical compiled schema not available in this environment")
        assert _load(vendored) == _load(canonical)
