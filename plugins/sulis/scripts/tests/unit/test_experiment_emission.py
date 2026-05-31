"""Tests for `_experiment_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _experiment_emission import compose_experiment, emit_experiment


_METRIC = "dna:metric:01ABCDEFGHJKMNPQRSTVWXYZ12"
_REQ = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"


class TestComposeExperiment:
    def test_minimum_valid(self) -> None:
        e = compose_experiment(
            hypothesis="Reducing onboarding from 5 steps to 3 increases activation by 10%",
            success_metric=_METRIC, result="supported",
        )
        assert re.fullmatch(r"^dna:experiment:[0-9A-HJKMNP-TV-Z]{26}$", e["id"])
        assert e["hypothesis"].startswith("Reducing")
        assert e["success_metric"] == _METRIC
        assert e["result"] == "supported"
        assert e["sys_status"] == "active"

    def test_tests_pass_through(self) -> None:
        e = compose_experiment(
            hypothesis="X", success_metric=_METRIC, result="refuted",
            tests=_REQ,
        )
        assert e["tests"] == _REQ

    def test_invalid_metric_raises(self) -> None:
        with pytest.raises(ValueError, match="success_metric"):
            compose_experiment(hypothesis="X", success_metric="not-a-metric", result="supported")

    def test_invalid_result_raises(self) -> None:
        with pytest.raises(ValueError, match="result"):
            compose_experiment(hypothesis="X", success_metric=_METRIC, result="bogus")

    def test_empty_hypothesis_raises(self) -> None:
        with pytest.raises(ValueError, match="hypothesis"):
            compose_experiment(hypothesis="", success_metric=_METRIC, result="supported")

    def test_invalid_tests_raises(self) -> None:
        with pytest.raises(ValueError, match="tests"):
            compose_experiment(
                hypothesis="X", success_metric=_METRIC, result="supported",
                tests="not-a-ref",
            )


class TestEmitExperiment:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        e = emit_experiment(
            repo=adapter, hypothesis="X", success_metric=_METRIC,
            result="supported",
        )
        ulid = e["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "experiment" / f"{ulid}.jsonld"
        ).exists()
