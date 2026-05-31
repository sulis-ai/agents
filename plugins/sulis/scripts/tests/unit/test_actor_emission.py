"""Tests for `_actor_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _actor_emission import compose_actor_from_yaml, emit_actor_from_yaml
from _entity_adapter_local import LocalFileEntityAdapter
from _entity_repository import EntityValidationError


_TENANT = "name: Sulis AI\nkind: company\n"
_ACTOR = "name: CI bot\nkind: automation\n"


def _layout(tmp_path: Path) -> Path:
    sulis = tmp_path / ".sulis"
    (sulis / "actors").mkdir(parents=True)
    (sulis / "tenant.yaml").write_text(_TENANT)
    p = sulis / "actors" / "ci-bot.yaml"
    p.write_text(_ACTOR)
    return p


class TestComposeActor:
    def test_emits_one_actor(self, tmp_path: Path) -> None:
        p = _layout(tmp_path)
        result = compose_actor_from_yaml(p.read_text(), source_path=str(p))
        assert len(result) == 1
        assert result[0]["kind"] == "automation"
        assert result[0]["name"] == "CI bot"
        assert re.fullmatch(r"^dna:actor:[0-9A-HJKMNP-TV-Z]{26}$", result[0]["id"])

    def test_resolves_tenant_from_sibling(self, tmp_path: Path) -> None:
        p = _layout(tmp_path)
        result = compose_actor_from_yaml(p.read_text(), source_path=str(p))
        assert re.fullmatch(
            r"^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$",
            result[0]["belongs_to_tenant"],
        )

    def test_deterministic_id(self, tmp_path: Path) -> None:
        p = _layout(tmp_path / "x")
        a = compose_actor_from_yaml(p.read_text(), source_path=str(p))
        b = compose_actor_from_yaml(p.read_text(), source_path=str(p))
        assert a[0]["id"] == b[0]["id"]

    def test_missing_kind_returns_empty(self) -> None:
        assert compose_actor_from_yaml("name: noname\n", source_path="x") == []


class TestEmitActor:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="foundation",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        p = _layout(tmp_path)
        emitted = emit_actor_from_yaml(p, adapter)
        ulid = emitted[0]["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "foundation" / "actor" / f"{ulid}.jsonld"
        ).exists()

    def test_validation_fails_without_tenant_resolution(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        # No sibling tenant.yaml → belongs_to_tenant unresolved → rejected.
        p = tmp_path / "actor.yaml"
        p.write_text(_ACTOR)
        with pytest.raises(EntityValidationError):
            emit_actor_from_yaml(p, adapter)
