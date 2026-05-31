"""Tests for `_deployment_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _deployment_emission import compose_deployment, emit_deployment
from _entity_adapter_local import LocalFileEntityAdapter


_REL = "dna:release:01ABCDEFGHJKMNPQRSTVWXYZ12"
_ENV = "dna:environment:01BCDEFGHJKMNPQRSTVWXYZ123"
_ACTOR = "dna:actor:01CDEFGHJKMNPQRSTVWXYZ1234"


class TestComposeDeployment:
    def test_minimum_valid(self) -> None:
        d = compose_deployment(
            of_release=_REL, to_environment=_ENV, outcome="succeeded",
        )
        assert re.fullmatch(r"^dna:deployment:[0-9A-HJKMNP-TV-Z]{26}$", d["id"])
        assert d["of_release"] == _REL
        assert d["to_environment"] == _ENV
        assert d["outcome"] == "succeeded"
        assert isinstance(d["at"], str) and len(d["at"]) >= 10
        assert d["sys_status"] == "active"

    def test_with_actor(self) -> None:
        d = compose_deployment(
            of_release=_REL, to_environment=_ENV, outcome="succeeded",
            by_actor=_ACTOR,
        )
        assert d["by_actor"] == _ACTOR

    def test_invalid_release_raises(self) -> None:
        with pytest.raises(ValueError, match="of_release"):
            compose_deployment(of_release="not-a-release", to_environment=_ENV, outcome="succeeded")

    def test_invalid_environment_raises(self) -> None:
        with pytest.raises(ValueError, match="to_environment"):
            compose_deployment(of_release=_REL, to_environment="not-an-env", outcome="succeeded")

    def test_invalid_outcome_raises(self) -> None:
        with pytest.raises(ValueError, match="outcome"):
            compose_deployment(of_release=_REL, to_environment=_ENV, outcome="bogus")

    def test_invalid_actor_raises(self) -> None:
        with pytest.raises(ValueError, match="by_actor"):
            compose_deployment(
                of_release=_REL, to_environment=_ENV, outcome="succeeded",
                by_actor="not-an-actor",
            )

    def test_deterministic_id_at_same_timestamp(self) -> None:
        a = compose_deployment(of_release=_REL, to_environment=_ENV, outcome="succeeded",
                               at="2026-05-30T20:00:00Z")
        b = compose_deployment(of_release=_REL, to_environment=_ENV, outcome="failed",
                               at="2026-05-30T20:00:00Z")
        # Same release + env + timestamp → same ID (outcome doesn't bind)
        assert a["id"] == b["id"]


class TestEmitDeployment:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        d = emit_deployment(
            repo=adapter, of_release=_REL, to_environment=_ENV,
            outcome="succeeded",
        )
        ulid = d["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "deployment" / f"{ulid}.jsonld"
        ).exists()
