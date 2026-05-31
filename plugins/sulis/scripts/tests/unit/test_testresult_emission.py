"""Tests for `_testresult_emission.py`."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _testresult_emission import compose_testresult, emit_testresult


_RUN = "dna:testrun:01ABCDEFGHJKMNPQRSTVWXYZ12"
_R1 = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"
_R2 = "dna:requirement:01CDEFGHJKMNPQRSTVWXYZ1234"


class TestComposeTestResult:
    def test_minimum_valid(self) -> None:
        r = compose_testresult(
            of_run=_RUN, verifies=[_R1], type="unit", outcome="pass",
        )
        assert re.fullmatch(r"^dna:testresult:[0-9A-HJKMNP-TV-Z]{26}$", r["id"])
        assert r["of_run"] == _RUN
        assert r["verifies"] == [_R1]
        assert r["type"] == "unit"
        assert r["outcome"] == "pass"
        assert r["sys_status"] == "active"

    def test_evidence_pass_through(self) -> None:
        r = compose_testresult(
            of_run=_RUN, verifies=[_R1, _R2], type="contract", outcome="fail",
            evidence="https://ci.example.com/runs/123/log",
        )
        assert r["evidence"] == "https://ci.example.com/runs/123/log"

    def test_deterministic_id(self) -> None:
        a = compose_testresult(of_run=_RUN, verifies=[_R1], type="unit", outcome="pass")
        b = compose_testresult(of_run=_RUN, verifies=[_R1], type="unit", outcome="fail")
        # outcome doesn't bind ID — same (run, requirements, type) is the same result-record
        assert a["id"] == b["id"]
        assert a["outcome"] != b["outcome"]

    def test_invalid_run_raises(self) -> None:
        with pytest.raises(ValueError, match="of_run"):
            compose_testresult(of_run="not-a-run", verifies=[_R1], type="unit", outcome="pass")

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="type"):
            compose_testresult(of_run=_RUN, verifies=[_R1], type="bogus", outcome="pass")

    def test_invalid_outcome_raises(self) -> None:
        with pytest.raises(ValueError, match="outcome"):
            compose_testresult(of_run=_RUN, verifies=[_R1], type="unit", outcome="bogus")

    def test_empty_verifies_raises(self) -> None:
        with pytest.raises(ValueError, match="verifies"):
            compose_testresult(of_run=_RUN, verifies=[], type="unit", outcome="pass")

    def test_bad_requirement_raises(self) -> None:
        with pytest.raises(ValueError, match="verifies"):
            compose_testresult(of_run=_RUN, verifies=["not-a-ref"], type="unit", outcome="pass")


class TestEmitTestResult:
    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_persists(self, adapter: LocalFileEntityAdapter, tmp_path: Path) -> None:
        r = emit_testresult(
            repo=adapter, of_run=_RUN, verifies=[_R1],
            type="unit", outcome="pass",
        )
        ulid = r["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development" / "testresult" / f"{ulid}.jsonld"
        ).exists()
