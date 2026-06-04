"""Journey-rigor #84 — enumerate a journey's full scenario set + per-scenario state.

The journey-walk (design) and scenario-coverage check (plan) need to pull ALL
scenarios for a journey (to check every one even when building only some) and
to ask each one's verification state. These pin the three query helpers.
"""

from __future__ import annotations

from pathlib import Path

from _brain_query import (
    find_passing_testresults_for_scenario,
    find_scenarios_for_journey,
    find_scenarios_verifying,
)
from _entity_adapter_local import LocalFileEntityAdapter
from _scenario_authoring import _ulid  # valid 26-char Crockford ULID bodies

_WF_A = f"dna:workflow:{_ulid('wf-a')}"
_WF_B = f"dna:workflow:{_ulid('wf-b')}"
_REQ = f"dna:requirement:{_ulid('req-1')}"
_REQ2 = f"dna:requirement:{_ulid('req-2')}"
_DES = f"dna:design:{_ulid('des-1')}"
_RUN = f"dna:testrun:{_ulid('run-1')}"
_SCN_A1 = f"dna:scenario:{_ulid('scn-a1')}"
_SCN_A2 = f"dna:scenario:{_ulid('scn-a2')}"
_SCN_B1 = f"dna:scenario:{_ulid('scn-b1')}"


def _scn(sid, journey, verifies):
    return {"id": sid, "sys_status": "active", "name": sid.split(":")[-1][:8],
            "journey": journey, "verifies": verifies, "exercises": _DES,
            "state": "active"}


def _seed(base: Path):
    p = LocalFileEntityAdapter(base_dir=base, domain="product-development")
    # journey A has two scenarios; journey B has one
    p.save("scenario", _scn(_SCN_A1, _WF_A, [_REQ]))
    p.save("scenario", _scn(_SCN_A2, _WF_A, [_REQ2]))
    p.save("scenario", _scn(_SCN_B1, _WF_B, [_REQ]))


class TestScenarioSetQuery:
    def test_enumerates_full_set_for_a_journey(self, tmp_path) -> None:
        base = tmp_path / ".brain" / "instances"
        _seed(base)
        a = find_scenarios_for_journey(base, _WF_A)
        b = find_scenarios_for_journey(base, _WF_B)
        assert {s["id"] for s in a} == {_SCN_A1, _SCN_A2}
        assert len(b) == 1

    def test_scenarios_verifying_a_requirement(self, tmp_path) -> None:
        base = tmp_path / ".brain" / "instances"
        _seed(base)
        v = find_scenarios_verifying(base, _REQ)
        # the two scenarios (one per journey) that verify _REQ
        assert {s["id"] for s in v} == {_SCN_A1, _SCN_B1}

    def test_scenario_green_state_via_back_linked_passing_testresult(self, tmp_path) -> None:
        base = tmp_path / ".brain" / "instances"
        _seed(base)
        sid = _SCN_A1
        # before any run: not green
        assert find_passing_testresults_for_scenario(base, sid) == []
        # deposit a passing TestResult back-linked to the scenario
        p = LocalFileEntityAdapter(base_dir=base, domain="product-development")
        p.save("testresult", {
            "id": f"dna:testresult:{_ulid('tr-pass')}",
            "sys_status": "active", "of_run": _RUN, "type": "e2e",
            "outcome": "pass", "verifies": [_REQ], "scenario": sid,
        })
        # a FAIL on a different scenario must not count for this one
        p.save("testresult", {
            "id": f"dna:testresult:{_ulid('tr-fail')}",
            "sys_status": "active", "of_run": _RUN, "type": "e2e",
            "outcome": "fail", "verifies": [_REQ], "scenario": _SCN_B1,
        })
        green = find_passing_testresults_for_scenario(base, sid)
        assert len(green) == 1 and green[0]["outcome"] == "pass"
        # the failing/other-scenario result is correctly excluded
        assert find_passing_testresults_for_scenario(base, _SCN_B1) == []

    def test_bad_id_raises(self, tmp_path) -> None:
        import pytest
        base = tmp_path / ".brain" / "instances"
        for fn in (find_scenarios_for_journey, find_scenarios_verifying,
                   find_passing_testresults_for_scenario):
            with pytest.raises(ValueError):
                fn(base, "not-an-id")
