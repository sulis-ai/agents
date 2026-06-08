"""Journey-rigor #4 — the scenario-coverage gate (check ALL, build some).

Every Scenario in a journey must be observed-green, planned (a WP), or
consciously out-of-scope. A not-green scenario that is neither planned nor
out-of-scope is an uncovered GAP → `gaps` (blocking). The objective green-state
comes from the brain (a passing TestResult back-link), never an agent's claim.
"""

from __future__ import annotations

from pathlib import Path

from _entity_adapter_local import LocalFileEntityAdapter
from _scenario_authoring import _ulid
from _verify_scenario_coverage import verify_scenario_coverage

_WF = f"dna:workflow:{_ulid('journey-login')}"
_DES = f"dna:design:{_ulid('des')}"
_REQ = f"dna:requirement:{_ulid('req')}"
_RUN = f"dna:testrun:{_ulid('run')}"
_S_GREEN = f"dna:scenario:{_ulid('s-green')}"
_S_PLANNED = f"dna:scenario:{_ulid('s-planned')}"
_S_GAP = f"dna:scenario:{_ulid('s-gap')}"


def _seed(base: Path):
    p = LocalFileEntityAdapter(base_dir=base, domain="product-development")
    for sid in (_S_GREEN, _S_PLANNED, _S_GAP):
        p.save("scenario", {
            "id": sid, "sys_status": "active", "name": sid.split(":")[-1][:10],
            "journey": _WF, "verifies": [_REQ], "exercises": _DES, "state": "active",
        })
    # _S_GREEN has a passing TestResult back-linked → observed-green
    p.save("testresult", {
        "id": f"dna:testresult:{_ulid('tr')}", "sys_status": "active",
        "of_run": _RUN, "type": "e2e", "outcome": "pass",
        "verifies": [_REQ], "scenario": _S_GREEN,
    })


class TestScenarioCoverage:
    def test_gap_when_a_not_green_scenario_is_unplanned(self, tmp_path) -> None:
        base = tmp_path / ".brain" / "instances"
        _seed(base)
        # plan the planned one; leave _S_GAP unaccounted
        r = verify_scenario_coverage(_WF, base_dir=base, planned={_S_PLANNED})
        assert r.verdict == "gaps"
        assert {c.scenario_id for c in r.gaps} == {_S_GAP}
        # the green one needs no work; the planned one is covered
        disp = {c.scenario_id: c.disposition for c in r.coverage}
        assert disp[_S_GREEN] == "green"
        assert disp[_S_PLANNED] == "planned"
        assert disp[_S_GAP] == "GAP"

    def test_covered_when_every_not_green_is_planned_or_out_of_scope(self, tmp_path) -> None:
        base = tmp_path / ".brain" / "instances"
        _seed(base)
        r = verify_scenario_coverage(
            _WF, base_dir=base, planned={_S_PLANNED}, out_of_scope={_S_GAP})
        assert r.verdict == "covered"
        assert r.gaps == []

    def test_green_scenario_needs_no_planning(self, tmp_path) -> None:
        # Only the green scenario + nothing planned → still covered (green ≠ gap).
        base = tmp_path / ".brain" / "instances"
        p = LocalFileEntityAdapter(base_dir=base, domain="product-development")
        p.save("scenario", {
            "id": _S_GREEN, "sys_status": "active", "name": "g",
            "journey": _WF, "verifies": [_REQ], "exercises": _DES, "state": "active",
        })
        p.save("testresult", {
            "id": f"dna:testresult:{_ulid('tr2')}", "sys_status": "active",
            "of_run": _RUN, "type": "e2e", "outcome": "pass",
            "verifies": [_REQ], "scenario": _S_GREEN,
        })
        r = verify_scenario_coverage(_WF, base_dir=base)
        assert r.verdict == "covered"

    def test_missing_brain_is_error(self, tmp_path) -> None:
        r = verify_scenario_coverage(_WF, base_dir=tmp_path / "nope")
        assert r.verdict == "error"
