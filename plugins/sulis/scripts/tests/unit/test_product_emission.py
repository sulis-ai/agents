"""Tests for `_product_emission.py` — n=4 entity emission with cross-file
Tenant resolution.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _product_emission import compose_product_from_yaml, emit_product_from_yaml
from _entity_adapter_local import LocalFileEntityAdapter


_TENANT_YAML = """
name: Sulis AI
kind: company
"""

_PRODUCT_YAML = """
name: Team Todo App
description: A shared todo list for teams
category: saas
state: active
"""


def _layout(tmp_path: Path, product_slug: str = "team-todo-app") -> Path:
    """Create the conventional `.sulis/{tenant.yaml, products/{slug}.yaml}` layout."""
    sulis = tmp_path / ".sulis"
    products = sulis / "products"
    products.mkdir(parents=True, exist_ok=True)
    (sulis / "tenant.yaml").write_text(_TENANT_YAML)
    product_path = products / f"{product_slug}.yaml"
    product_path.write_text(_PRODUCT_YAML)
    return product_path


class TestComposeProduct:
    def test_resolves_belongs_to_tenant_from_sibling_tenant_yaml(self, tmp_path: Path) -> None:
        product_path = _layout(tmp_path)
        result = compose_product_from_yaml(
            product_path.read_text(), source_path=str(product_path)
        )
        assert len(result) == 1
        assert re.fullmatch(
            r"^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$", result[0]["belongs_to_tenant"]
        )

    def test_id_matches_schema_pattern(self, tmp_path: Path) -> None:
        product_path = _layout(tmp_path)
        result = compose_product_from_yaml(
            product_path.read_text(), source_path=str(product_path)
        )
        assert re.fullmatch(
            r"^dna:product:[0-9A-HJKMNP-TV-Z]{26}$", result[0]["id"]
        )

    def test_id_is_deterministic_from_name_and_tenant(self, tmp_path: Path) -> None:
        a_path = _layout(tmp_path / "a")
        b_path = _layout(tmp_path / "b")
        a = compose_product_from_yaml(a_path.read_text(), source_path=str(a_path))
        b = compose_product_from_yaml(b_path.read_text(), source_path=str(b_path))
        # Same product name + same tenant name → same id
        assert a[0]["id"] == b[0]["id"]

    def test_emits_optional_fields_when_present(self, tmp_path: Path) -> None:
        product_path = _layout(tmp_path)
        result = compose_product_from_yaml(
            product_path.read_text(), source_path=str(product_path)
        )
        p = result[0]
        assert p["description"] == "A shared todo list for teams"
        assert p["category"] == "saas"
        assert p["state"] == "active"
        assert p["sys_status"] == "active"

    def test_explicit_belongs_to_tenant_takes_precedence(self, tmp_path: Path) -> None:
        explicit_yaml = """
name: Explicit Product
belongs_to_tenant: dna:tenant:01ABCDEFGHJKMNPQRSTVWXYZ12
"""
        result = compose_product_from_yaml(explicit_yaml, source_path="x")
        assert result[0]["belongs_to_tenant"] == "dna:tenant:01ABCDEFGHJKMNPQRSTVWXYZ12"

    def test_missing_name_returns_empty_list(self) -> None:
        assert compose_product_from_yaml("description: only\n", source_path="x") == []


class TestEmitProduct:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists_product_jsonld(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        product_path = _layout(tmp_path)
        emitted = emit_product_from_yaml(product_path, adapter)
        assert len(emitted) == 1
        ulid = emitted[0]["id"].split(":")[-1]
        assert (tmp_path / ".brain" / "instances" / "product-development" / "product" / f"{ulid}.jsonld").exists()

    def test_emission_degrades_gracefully_when_no_tenant_can_be_resolved(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        # Place product yaml without a sibling tenant.yaml — belongs_to_tenant
        # cannot resolve, so the body fails reject-on-invalid at the port.
        product_path = tmp_path / "product-only.yaml"
        product_path.write_text(_PRODUCT_YAML)

        # WP-012: emission is now best-effort. It delegates to evolve_entity and
        # swallows persistence/validation faults so the host operation never
        # fails on an emit failure — the graceful-degradation discipline the WP
        # Contract preserves. It returns the composed list and writes NO
        # envelope for the invalid body (reject-on-invalid still blocks the
        # write; only the raise into the host is swallowed).
        emitted = emit_product_from_yaml(product_path, adapter)
        assert len(emitted) == 1, "compose still returns the attempted body"
        ulid = emitted[0]["id"].split(":")[-1]
        envelope_path = (
            tmp_path
            / ".brain"
            / "instances"
            / "product-development"
            / "product"
            / f"{ulid}.jsonld"
        )
        assert not envelope_path.exists(), (
            "an invalid body must not be persisted (reject-on-invalid still "
            "blocks the write; only the raise is swallowed)"
        )
