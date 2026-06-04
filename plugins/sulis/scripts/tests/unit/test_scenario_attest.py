"""Journey-rigor #6 — human attestation drives a blocked journey to real green.

A journey a machine can't run (a browser login flow) blocks since journey-rigor
#1 (manual-pending is not a pass). This path lets a human walk the real flow,
confirm each observable check, and deposit a REAL human-attested TestResult — so
the coverage gate reads the observation exactly as it reads an automated run. The
green is honest (stamped human-attested) and earned (you must name what you saw).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _brain_query import (
    find_passing_testresults_for_scenario,
    iter_entities,
)
from _scenario_attest import attest_scenario, fold_verdict

_REQ = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"
_SID = "dna:scenario:01ABCDEFGHJKMNPQRSTVWXYZ12"


def _scenario(verifies=(_REQ,)) -> dict:
    return {"id": _SID, "name": "Login journey", "verifies": list(verifies),
            "sys_status": "active"}


def _base(tmp_path: Path) -> Path:
    return tmp_path / ".brain" / "instances"


class TestFoldVerdict:
    def test_all_observed_is_pass(self) -> None:
        assert fold_verdict([{"check": "see dashboard", "observed": True}]) == "pass"

    def test_any_unobserved_is_fail(self) -> None:
        assert fold_verdict([
            {"check": "session", "observed": True},
            {"check": "see dashboard", "observed": False},
        ]) == "fail"

    def test_no_observations_is_fail(self) -> None:
        assert fold_verdict([]) == "fail"


class TestAttestScenario:
    def test_pass_deposits_human_attested_passing_evidence(self, tmp_path: Path) -> None:
        base = _base(tmp_path)
        res = attest_scenario(
            base_dir=base, scenario=_scenario(), attester="iain",
            observations=[
                {"check": "a session is established", "observed": True},
                {"check": "the dashboard is shown", "observed": True},
            ],
        )
        assert res.verdict == "pass"
        assert res.evidence_summary["harness"] == "human-attested"
        # the coverage gate reads it as a real passing TestResult for the scenario
        passing = find_passing_testresults_for_scenario(base, _SID)
        assert len(passing) == 1
        assert passing[0]["verifies"] == [_REQ]
        # provenance is honest: the TestRun is stamped human-attested
        runs = list(iter_entities(base, domain="product-development", entity_type="testrun"))
        assert runs[0]["harness"] == "human-attested"

    def test_unobserved_check_fails_and_deposits_no_passing_evidence(self, tmp_path: Path) -> None:
        base = _base(tmp_path)
        res = attest_scenario(
            base_dir=base, scenario=_scenario(), attester="iain",
            observations=[
                {"check": "a session is established", "observed": True},
                {"check": "the dashboard is shown", "observed": False},
            ],
        )
        assert res.verdict == "fail"
        assert res.evidence_summary["outcome"] == "fail"
        # nothing green for the gate to read
        assert find_passing_testresults_for_scenario(base, _SID) == []

    def test_attester_is_required(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="attester"):
            attest_scenario(base_dir=_base(tmp_path), scenario=_scenario(),
                            attester="  ", observations=[{"check": "x", "observed": True}])

    def test_observations_are_required(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="observed check"):
            attest_scenario(base_dir=_base(tmp_path), scenario=_scenario(),
                            attester="iain", observations=[])

    def test_attestation_overwrites_prior_blocked_record(self, tmp_path: Path) -> None:
        # a prior automated run left a skip (manual-pending); human attestation
        # overwrites the single per-scenario record with a real pass
        from _scenario_evidence import emit_scenario_evidence
        base = _base(tmp_path)
        emit_scenario_evidence(base_dir=base, scenario=_scenario(), verdict="manual-pending")
        assert find_passing_testresults_for_scenario(base, _SID) == []  # skip, not pass
        attest_scenario(
            base_dir=base, scenario=_scenario(), attester="iain",
            observations=[{"check": "the dashboard is shown", "observed": True}],
        )
        passing = find_passing_testresults_for_scenario(base, _SID)
        assert len(passing) == 1  # exactly one record, now green — no stale skip lingering
