"""Tests for `_release_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _release_emission import compose_release, emit_release


_C1 = "dna:component:01ABCDEFGHJKMNPQRSTVWXYZ12"
_C2 = "dna:component:01BCDEFGHJKMNPQRSTVWXYZ123"


class TestComposeRelease:
    def test_minimum_valid(self) -> None:
        r = compose_release(
            version="v0.34.0",
            comprises=[_C1, _C2],
            sbom="file:///tmp/sbom.spdx.json",
        )
        assert re.fullmatch(r"^dna:release:[0-9A-HJKMNP-TV-Z]{26}$", r["id"])
        assert r["version"] == "v0.34.0"
        assert r["comprises"] == [_C1, _C2]
        assert r["sbom"] == "file:///tmp/sbom.spdx.json"
        assert r["sys_status"] == "active"

    def test_optionals_emitted(self) -> None:
        r = compose_release(
            version="v0.34.0", comprises=[_C1], sbom="file://x",
            changelog="Major release",
            shipped_at="2026-05-30T20:00:00Z",
        )
        assert r["changelog"] == "Major release"
        assert r["shipped_at"] == "2026-05-30T20:00:00Z"

    def test_deterministic_id_from_version(self) -> None:
        a = compose_release(version="v0.34.0", comprises=[_C1], sbom="file://x")
        b = compose_release(version="v0.34.0", comprises=[_C1, _C2], sbom="file://y")
        # Same version → same ID; comprises can grow within a release
        assert a["id"] == b["id"]
        assert a["comprises"] != b["comprises"]

    def test_empty_version_raises(self) -> None:
        with pytest.raises(ValueError, match="version"):
            compose_release(version="", comprises=[_C1], sbom="file://x")

    def test_empty_comprises_raises(self) -> None:
        with pytest.raises(ValueError, match="comprises"):
            compose_release(version="v1", comprises=[], sbom="file://x")

    def test_bad_component_ref_raises(self) -> None:
        with pytest.raises(ValueError, match="comprises"):
            compose_release(version="v1", comprises=["not-a-ref"], sbom="file://x")

    def test_empty_sbom_raises(self) -> None:
        with pytest.raises(ValueError, match="sbom"):
            compose_release(version="v1", comprises=[_C1], sbom="")


class TestEmitRelease:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        r = emit_release(
            repo=adapter, version="v0.34.0",
            comprises=[_C1], sbom="file:///tmp/sbom.spdx.json",
        )
        ulid = r["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "release" / f"{ulid}.jsonld"
        ).exists()
