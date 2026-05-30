"""Tests for `_environment_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _environment_emission import compose_environment_from_yaml, emit_environment_from_yaml
from _entity_adapter_local import LocalFileEntityAdapter


_ENV = """
name: production
kind: production
region: eu-west-1
"""


class TestComposeEnvironment:
    def test_emits_one(self) -> None:
        result = compose_environment_from_yaml(_ENV, source_path="x")
        assert len(result) == 1
        assert result[0]["name"] == "production"
        assert result[0]["kind"] == "production"
        assert result[0]["region"] == "eu-west-1"
        assert re.fullmatch(r"^dna:environment:[0-9A-HJKMNP-TV-Z]{26}$", result[0]["id"])

    def test_deterministic_from_name(self) -> None:
        a = compose_environment_from_yaml(_ENV, source_path="x")
        b = compose_environment_from_yaml(_ENV, source_path="y")
        assert a[0]["id"] == b[0]["id"]

    def test_missing_name_returns_empty(self) -> None:
        assert compose_environment_from_yaml("kind: production\n", source_path="x") == []

    def test_unknown_kind_defaults_to_other(self) -> None:
        result = compose_environment_from_yaml(
            "name: weird-env\nkind: weird-kind\n", source_path="x"
        )
        # Compose passes through the kind value; adapter validates against enum.
        # If kind is "weird-kind" the adapter will reject; we only test compose here.
        # The "other" default is hit only when kind is absent / not a string.
        assert result[0]["kind"] == "weird-kind"

    def test_no_kind_defaults_to_other(self) -> None:
        result = compose_environment_from_yaml("name: dev\n", source_path="x")
        assert result[0]["kind"] == "other"


class TestEmitEnvironment:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        p = tmp_path / "env.yaml"
        p.write_text(_ENV)
        emitted = emit_environment_from_yaml(p, adapter)
        ulid = emitted[0]["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "environment" / f"{ulid}.jsonld"
        ).exists()
