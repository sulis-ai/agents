"""Tests for `_design_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _design_emission import compose_design_from_tdd, emit_design_from_tdd
from _entity_adapter_local import LocalFileEntityAdapter


_TDD_BODY = """
# Technical Design Document

This TDD satisfies FR-001 and FR-002, plus NFR-001 for latency.

The architecture choices are documented in ADR-001 and ADR-002.

FR-001 is implemented by the X service; FR-002 by the Y worker.
"""


def _layout(tmp_path: Path) -> Path:
    project = tmp_path / ".architecture" / "demo"
    project.mkdir(parents=True)
    tdd = project / "TDD.md"
    tdd.write_text(_TDD_BODY)
    # SRD sibling
    srd_dir = tmp_path / ".specifications" / "demo"
    srd_dir.mkdir(parents=True)
    (srd_dir / "SRD.md").write_text("# SRD\n")
    # ADRs
    adrs = project / "adrs"
    adrs.mkdir()
    (adrs / "ADR-001-x.md").write_text("# ADR-001\n")
    (adrs / "ADR-002-y.md").write_text("# ADR-002\n")
    return tdd


class TestComposeDesign:
    def test_emits_one_design_with_requirements_and_decisions(self, tmp_path: Path) -> None:
        tdd = _layout(tmp_path)
        result = compose_design_from_tdd(tdd.read_text(), tdd_path=tdd)
        assert len(result) == 1
        d = result[0]
        assert re.fullmatch(r"^dna:design:[0-9A-HJKMNP-TV-Z]{26}$", d["id"])
        assert d["state"] == "draft"
        assert d["sys_status"] == "active"
        # 3 unique FR/NFR markers → 3 requirement refs
        assert len(d["satisfies"]) == 3
        for ref in d["satisfies"]:
            assert re.fullmatch(r"^dna:requirement:[0-9A-HJKMNP-TV-Z]{26}$", ref)
        # 2 ADRs → 2 decision refs
        assert "decisions" in d
        assert len(d["decisions"]) == 2

    def test_deterministic_id(self, tmp_path: Path) -> None:
        tdd = _layout(tmp_path)
        a = compose_design_from_tdd(tdd.read_text(), tdd_path=tdd)
        b = compose_design_from_tdd(tdd.read_text(), tdd_path=tdd)
        assert a[0]["id"] == b[0]["id"]

    def test_empty_when_no_srd_and_no_explicit_path(self, tmp_path: Path) -> None:
        tdd = tmp_path / "standalone.md"
        tdd.write_text(_TDD_BODY)
        assert compose_design_from_tdd(tdd.read_text(), tdd_path=tdd) == []

    def test_views_pass_through(self, tmp_path: Path) -> None:
        tdd = _layout(tmp_path)
        result = compose_design_from_tdd(
            tdd.read_text(), tdd_path=tdd, views=["context", "container"]
        )
        assert result[0]["views"] == ["context", "container"]

    def test_invalid_state_raises(self, tmp_path: Path) -> None:
        tdd = _layout(tmp_path)
        with pytest.raises(ValueError, match="state"):
            compose_design_from_tdd(tdd.read_text(), tdd_path=tdd, state="bogus")

    def test_invalid_view_raises(self, tmp_path: Path) -> None:
        tdd = _layout(tmp_path)
        with pytest.raises(ValueError, match="views"):
            compose_design_from_tdd(tdd.read_text(), tdd_path=tdd, views=["bogus"])


class TestEmitDesign:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        tdd = _layout(tmp_path)
        designs = emit_design_from_tdd(tdd, adapter)
        ulid = designs[0]["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "design" / f"{ulid}.jsonld"
        ).exists()
