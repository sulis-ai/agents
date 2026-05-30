"""Tests for `_metric_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _metric_emission import compose_metric, emit_metric


_REL = "dna:release:01ABCDEFGHJKMNPQRSTVWXYZ12"
_OPP = "dna:opportunity:01BCDEFGHJKMNPQRSTVWXYZ123"


class TestComposeMetric:
    def test_minimum_valid_release(self) -> None:
        m = compose_metric(kind="DORA", measures=_REL, value=2.5)
        assert re.fullmatch(r"^dna:metric:[0-9A-HJKMNP-TV-Z]{26}$", m["id"])
        assert m["kind"] == "DORA"
        assert m["measures"] == _REL
        assert m["value"] == 2.5
        assert m["sys_status"] == "active"

    def test_with_opportunity(self) -> None:
        m = compose_metric(kind="product", measures=_OPP, value=42.0)
        assert m["measures"] == _OPP

    def test_window_pass_through(self) -> None:
        m = compose_metric(kind="DORA", measures=_REL, value=1.0, window="P7D")
        assert m["window"] == "P7D"

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="kind"):
            compose_metric(kind="bogus", measures=_REL, value=1.0)

    def test_invalid_measures_raises(self) -> None:
        with pytest.raises(ValueError, match="measures"):
            compose_metric(kind="DORA", measures="not-a-ref", value=1.0)

    def test_invalid_window_raises(self) -> None:
        with pytest.raises(ValueError, match="window"):
            compose_metric(kind="DORA", measures=_REL, value=1.0, window="7 days")


class TestEmitMetric:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        m = emit_metric(repo=adapter, kind="DORA", measures=_REL, value=2.5)
        ulid = m["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "metric" / f"{ulid}.jsonld"
        ).exists()
