"""Tests for `_tenant_emission.py` — third worked entity emission.

Tenant is foundation-domain (cross-cutting per L13). One Tenant per project;
deterministic ID from name so cross-repo namespacing resolves correctly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from _tenant_emission import compose_tenant_from_yaml, emit_tenant_from_yaml
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_repository import EntityValidationError


_VALID = """
name: Sulis AI
kind: company
legal_name: Sulis AI Ltd
jurisdiction: GB-ENG
state: active
"""

_MINIMAL = """
name: Acme Corp
kind: company
"""


class TestComposeTenant:
    def test_emits_one_tenant_for_a_valid_yaml(self) -> None:
        result = compose_tenant_from_yaml(_VALID, source_path=".sulis/tenant.yaml")
        assert len(result) == 1
        t = result[0]
        assert t["name"] == "Sulis AI"
        assert t["kind"] == "company"
        assert t["legal_name"] == "Sulis AI Ltd"
        assert t["jurisdiction"] == "GB-ENG"
        assert t["state"] == "active"
        assert t["sys_status"] == "active"

    def test_id_matches_schema_pattern(self) -> None:
        result = compose_tenant_from_yaml(_VALID, source_path=".sulis/tenant.yaml")
        assert re.fullmatch(
            r"^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$", result[0]["id"]
        )

    def test_id_is_deterministic_from_name(self) -> None:
        a = compose_tenant_from_yaml(_VALID, source_path="path1.yaml")
        b = compose_tenant_from_yaml(_VALID, source_path="path2.yaml")
        # Same name → same id, regardless of file path. This is the
        # cross-repo-namespacing property.
        assert a[0]["id"] == b[0]["id"]

    def test_ids_differ_for_different_names(self) -> None:
        a = compose_tenant_from_yaml(_VALID, source_path="x")
        b = compose_tenant_from_yaml(_MINIMAL, source_path="x")
        assert a[0]["id"] != b[0]["id"]

    def test_minimal_yaml_emits_with_defaults(self) -> None:
        result = compose_tenant_from_yaml(_MINIMAL, source_path="x")
        assert len(result) == 1
        t = result[0]
        assert t["name"] == "Acme Corp"
        assert t["kind"] == "company"
        # Default state when not provided
        assert t["state"] == "active"
        # Optional fields absent
        assert "legal_name" not in t
        assert "jurisdiction" not in t

    def test_explicit_id_is_honoured(self) -> None:
        explicit = """
name: ManualID Co
kind: company
id: dna:tenant:01ABCDEFGHJKMNPQRSTVWXYZ12
"""
        result = compose_tenant_from_yaml(explicit, source_path="x")
        assert result[0]["id"] == "dna:tenant:01ABCDEFGHJKMNPQRSTVWXYZ12"

    def test_missing_name_returns_empty_list(self) -> None:
        # Without a name, there's nothing to derive an identity from; not a tenant.
        no_name = "kind: company\n"
        assert compose_tenant_from_yaml(no_name, source_path="x") == []

    def test_malformed_yaml_returns_empty_list(self) -> None:
        bad = "not: valid: yaml: {{{\n"
        assert compose_tenant_from_yaml(bad, source_path="x") == []


class TestEmitTenant:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="foundation",
        )

    def test_emit_persists_tenant_jsonld_to_disk(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        yaml_path = tmp_path / "tenant.yaml"
        yaml_path.write_text(_VALID)

        emitted = emit_tenant_from_yaml(yaml_path, adapter)
        assert len(emitted) == 1
        ulid = emitted[0]["id"].split(":")[-1]
        path = tmp_path / ".brain" / "instances" / "foundation" / "tenant" / f"{ulid}.jsonld"
        assert path.exists()

    def test_emit_is_idempotent(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        yaml_path = tmp_path / "tenant.yaml"
        yaml_path.write_text(_VALID)

        first = emit_tenant_from_yaml(yaml_path, adapter)
        second = emit_tenant_from_yaml(yaml_path, adapter)
        assert first[0]["id"] == second[0]["id"]

    def test_validation_propagates_for_invalid_kind(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        bad_kind = """
name: BadKind Co
kind: nonsense_kind_value
"""
        yaml_path = tmp_path / "tenant.yaml"
        yaml_path.write_text(bad_kind)

        with pytest.raises(EntityValidationError):
            emit_tenant_from_yaml(yaml_path, adapter)
