"""Tests for `_brain_query.py`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _brain_query import (
    find_entities,
    find_passing_testresults_verifying,
    find_requirements,
    find_testresults_verifying,
    iter_entities,
    where_field_equals,
    where_field_in,
    where_id_in,
    where_list_field_contains,
)


_REQ_A = "dna:requirement:01ABCDEFGHJKMNPQRSTVWXYZ12"
_REQ_B = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"
_REQ_C = "dna:requirement:01CDEFGHJKMNPQRSTVWXYZ1234"


def _seed(tmp_path: Path) -> Path:
    """Build a small entity graph: 3 requirements + 3 testresults.

    TestResults verifying:
      - tr1 (pass, unit) → REQ_A
      - tr2 (fail, unit) → REQ_A + REQ_B
      - tr3 (pass, integration) → REQ_B
      - REQ_C is intentionally unverified.
    """
    base = tmp_path / ".brain" / "instances"

    # Requirements (we don't need full schema-valid instances for query
    # tests — query layer treats the JSON as opaque dicts).
    for req_id in (_REQ_A, _REQ_B, _REQ_C):
        ulid = req_id.split(":")[-1]
        p = base / "product-development" / "requirement" / f"{ulid}.jsonld"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "id": req_id, "title": f"Req {ulid[-2:]}",
            "priority": "must", "sys_status": "active",
        }))

    # TestResults
    test_results = [
        {
            "id": "dna:testresult:01TR0000000000000000000001",
            "of_run": "dna:testrun:01RUN000000000000000000001",
            "verifies": [_REQ_A], "type": "unit", "outcome": "pass",
            "sys_status": "active",
        },
        {
            "id": "dna:testresult:01TR0000000000000000000002",
            "of_run": "dna:testrun:01RUN000000000000000000001",
            "verifies": [_REQ_A, _REQ_B], "type": "unit", "outcome": "fail",
            "sys_status": "active",
        },
        {
            "id": "dna:testresult:01TR0000000000000000000003",
            "of_run": "dna:testrun:01RUN000000000000000000001",
            "verifies": [_REQ_B], "type": "integration", "outcome": "pass",
            "sys_status": "active",
        },
    ]
    for tr in test_results:
        ulid = tr["id"].split(":")[-1]
        p = base / "product-development" / "testresult" / f"{ulid}.jsonld"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(tr))

    return base


class TestIterEntities:
    def test_walks_everything(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        all_e = list(iter_entities(base))
        assert len(all_e) == 6  # 3 reqs + 3 testresults

    def test_filter_by_entity_type(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        reqs = list(iter_entities(base, entity_type="requirement"))
        assert len(reqs) == 3
        assert all(r["id"].startswith("dna:requirement:") for r in reqs)

    def test_filter_by_domain(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        pd = list(iter_entities(base, domain="product-development"))
        assert len(pd) == 6
        # No foundation entities seeded
        assert list(iter_entities(base, domain="foundation")) == []

    def test_missing_base_is_empty(self, tmp_path: Path) -> None:
        assert list(iter_entities(tmp_path / "does-not-exist")) == []

    def test_malformed_files_skipped_silently(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        bad = base / "product-development" / "requirement" / "MALFORMED.jsonld"
        bad.write_text("this is not json")
        # Bad file ignored; the 3 good ones still surface.
        reqs = list(iter_entities(base, entity_type="requirement"))
        assert len(reqs) == 3


class TestPredicates:
    def test_where_field_equals(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        passes = find_entities(
            base, entity_type="testresult",
            predicate=where_field_equals("outcome", "pass"),
        )
        assert len(passes) == 2
        assert all(p["outcome"] == "pass" for p in passes)

    def test_where_field_in(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        finals = find_entities(
            base, entity_type="testresult",
            predicate=where_field_in("outcome", ["pass", "fail"]),
        )
        assert len(finals) == 3

    def test_where_list_field_contains(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        verifying_a = find_entities(
            base, entity_type="testresult",
            predicate=where_list_field_contains("verifies", _REQ_A),
        )
        assert len(verifying_a) == 2  # tr1, tr2

    def test_where_id_in(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        targets = find_entities(
            base, entity_type="requirement",
            predicate=where_id_in([_REQ_A, _REQ_C]),
        )
        assert len(targets) == 2


class TestHighLevelQueries:
    def test_find_testresults_verifying(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        # REQ_A is verified by tr1 (pass) and tr2 (fail)
        results = find_testresults_verifying(base, _REQ_A)
        assert len(results) == 2

    def test_find_testresults_verifying_unverified_returns_empty(
        self, tmp_path: Path
    ) -> None:
        base = _seed(tmp_path)
        # REQ_C is intentionally unverified
        assert find_testresults_verifying(base, _REQ_C) == []

    def test_find_passing_testresults_verifying(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        # REQ_A has tr1 (pass) and tr2 (fail) — only tr1 is a passing verifier
        passing = find_passing_testresults_verifying(base, _REQ_A)
        assert len(passing) == 1
        assert passing[0]["outcome"] == "pass"

    def test_find_passing_testresults_verifying_none_when_only_failures(
        self, tmp_path: Path
    ) -> None:
        base = _seed(tmp_path)
        # Simulate a Requirement verified only by a failing test
        only_fail = "dna:requirement:01DEFGHJKMNPQRSTVWXYZ23456"
        tr = {
            "id": "dna:testresult:01TR0000000000000000000099",
            "of_run": "dna:testrun:01RUN000000000000000000001",
            "verifies": [only_fail], "type": "unit", "outcome": "fail",
            "sys_status": "active",
        }
        p = base / "product-development" / "testresult" / "01TR0000000000000000000099.jsonld"
        p.write_text(json.dumps(tr))
        assert find_passing_testresults_verifying(base, only_fail) == []

    def test_find_requirements(self, tmp_path: Path) -> None:
        base = _seed(tmp_path)
        reqs = find_requirements(base)
        assert len(reqs) == 3
        assert {r["id"] for r in reqs} == {_REQ_A, _REQ_B, _REQ_C}

    def test_find_testresults_verifying_rejects_bad_id(
        self, tmp_path: Path
    ) -> None:
        base = _seed(tmp_path)
        with pytest.raises(ValueError, match="requirement_id"):
            find_testresults_verifying(base, "not-a-valid-ref")
