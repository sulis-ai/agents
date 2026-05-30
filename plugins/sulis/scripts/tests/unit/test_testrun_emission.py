"""Tests for `_testrun_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _testrun_emission import compose_testrun, emit_testrun


_COMP = "dna:component:01ABCDEFGHJKMNPQRSTVWXYZ12"


class TestComposeTestRun:
    def test_minimum_valid(self) -> None:
        r = compose_testrun()
        assert re.fullmatch(r"^dna:testrun:[0-9A-HJKMNP-TV-Z]{26}$", r["id"])
        assert isinstance(r["ran_at"], str) and len(r["ran_at"]) >= 10
        assert r["sys_status"] == "active"

    def test_with_component_and_harness(self) -> None:
        r = compose_testrun(in_run=_COMP, harness="pytest")
        assert r["in_run"] == _COMP
        assert r["harness"] == "pytest"

    def test_invalid_component_raises(self) -> None:
        with pytest.raises(ValueError, match="in_run"):
            compose_testrun(in_run="not-a-component")

    def test_deterministic_id(self) -> None:
        a = compose_testrun(ran_at="2026-05-30T20:00:00Z", harness="pytest")
        b = compose_testrun(ran_at="2026-05-30T20:00:00Z", harness="pytest")
        assert a["id"] == b["id"]


class TestEmitTestRun:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        r = emit_testrun(repo=adapter, harness="pytest")
        ulid = r["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "testrun" / f"{ulid}.jsonld"
        ).exists()
