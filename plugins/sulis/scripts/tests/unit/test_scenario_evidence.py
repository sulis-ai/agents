"""Tests for `_scenario_evidence.py` — the Scenario-route evidence emission.

A green Scenario run must leave a verification record the requirement-
coverage gate reads (a passing TestResult whose `verifies` contains the
requirement). These tests pin:

  - verdict → outcome mapping (pass/fail/skip);
  - the TestRun + TestResult are persisted, back-linked to the scenario,
    and carry the scenario's `verifies` set verbatim;
  - a scenario verifying nothing emits nothing (None — the gate gains
    nothing, so we don't write a verifies-less record);
  - re-running the same scenario OVERWRITES its single record (no stale
    pass left behind when a scenario regresses);
  - the end-to-end proof: a Scenario-verified FR flips the gate verdict
    from fail (no evidence) to pass (evidence emitted) — the false-red
    this change exists to kill.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _brain_query import iter_entities
from _requirement_emission import _deterministic_ulid_from
from _scenario_evidence import emit_scenario_evidence
from _verify_requirements import verify_requirements

_BASE = "_BRAIN"


def _scenario(verifies: list[str], *, sid: str = "dna:scenario:01ABCDEFGHJKMNPQRSTVWXYZ12",
              name: str = "Sign-up journey") -> dict:
    return {"id": sid, "name": name, "verifies": verifies, "sys_status": "active"}


def _persisted(base_dir: Path, entity_type: str) -> list[dict]:
    return list(iter_entities(base_dir, domain="product-development", entity_type=entity_type))


class TestEmitScenarioEvidence:
    @pytest.fixture
    def base_dir(self, tmp_path: Path) -> Path:
        return tmp_path / ".brain" / "instances"

    def test_pass_emits_passing_testresult_linked_to_scenario(self, base_dir: Path) -> None:
        req = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"
        scen = _scenario([req])
        out = emit_scenario_evidence(base_dir=base_dir, scenario=scen, verdict="pass")

        assert out is not None
        assert out["outcome"] == "pass"
        results = _persisted(base_dir, "testresult")
        runs = _persisted(base_dir, "testrun")
        assert len(results) == 1 and len(runs) == 1
        r = results[0]
        assert r["outcome"] == "pass"
        assert r["type"] == "e2e"
        assert r["verifies"] == [req]
        assert r["scenario"] == scen["id"]
        assert r["of_run"] == runs[0]["id"]
        assert runs[0]["of_scenario"] == scen["id"]

    def test_fail_verdict_maps_to_fail_outcome(self, base_dir: Path) -> None:
        out = emit_scenario_evidence(
            base_dir=base_dir,
            scenario=_scenario(["dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"]),
            verdict="fail",
        )
        assert out["outcome"] == "fail"
        assert _persisted(base_dir, "testresult")[0]["outcome"] == "fail"

    @pytest.mark.parametrize("verdict", ["deferred", "manual-pending"])
    def test_unresolved_verdicts_map_to_skip(self, base_dir: Path, verdict: str) -> None:
        out = emit_scenario_evidence(
            base_dir=base_dir,
            scenario=_scenario(["dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"]),
            verdict=verdict,
        )
        assert out["outcome"] == "skip"

    def test_no_verifies_emits_nothing(self, base_dir: Path) -> None:
        out = emit_scenario_evidence(base_dir=base_dir, scenario=_scenario([]), verdict="pass")
        assert out is None
        assert _persisted(base_dir, "testresult") == []
        assert _persisted(base_dir, "testrun") == []

    def test_rerun_overwrites_single_record_no_stale_pass(self, base_dir: Path) -> None:
        req = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"
        scen = _scenario([req])
        # First run green, then the scenario regresses → red.
        emit_scenario_evidence(base_dir=base_dir, scenario=scen, verdict="pass")
        emit_scenario_evidence(base_dir=base_dir, scenario=scen, verdict="fail")

        results = _persisted(base_dir, "testresult")
        runs = _persisted(base_dir, "testrun")
        # Exactly ONE record per scenario — the regression overwrote the pass.
        assert len(results) == 1 and len(runs) == 1
        assert results[0]["outcome"] == "fail"


class TestGateSeesScenarioRoute:
    """End-to-end: the false-red this change kills."""

    def _srd_with_fr01(self, tmp_path: Path) -> Path:
        srd = tmp_path / "SRD.md"
        srd.write_text(
            "# Requirements\n\n"
            "**FR-01: The sign-up screen accepts an email and password**\n\n"
            "**Acceptance criteria:** a new account is created.\n",
            encoding="utf-8",
        )
        return srd

    def test_scenario_verified_requirement_flips_gate_fail_to_pass(self, tmp_path: Path) -> None:
        srd = self._srd_with_fr01(tmp_path)
        base_dir = tmp_path / ".brain" / "instances"

        # The gate derives the requirement id from the RESOLVED srd path.
        resolved = srd.resolve()
        req_id = "dna:requirement:" + _deterministic_ulid_from(f"requirement:{resolved}:FR-01")

        # Before any evidence: the requirement reads as uncovered → fail.
        before = verify_requirements(srd, base_dir=base_dir)
        assert before.verdict == "fail"

        # A green Scenario run that verifies FR-01 deposits the evidence.
        emit_scenario_evidence(
            base_dir=base_dir,
            scenario=_scenario([req_id], name="Sign-up journey"),
            verdict="pass",
        )

        # Now the gate sees the Scenario route → pass.
        after = verify_requirements(srd, base_dir=base_dir)
        assert after.verdict == "pass"
        assert after.verified_count == 1

    def test_failing_scenario_does_not_cover_the_requirement(self, tmp_path: Path) -> None:
        srd = self._srd_with_fr01(tmp_path)
        base_dir = tmp_path / ".brain" / "instances"
        resolved = srd.resolve()
        req_id = "dna:requirement:" + _deterministic_ulid_from(f"requirement:{resolved}:FR-01")

        emit_scenario_evidence(
            base_dir=base_dir,
            scenario=_scenario([req_id]),
            verdict="fail",
        )
        # A red scenario is NOT coverage — the gate stays fail.
        assert verify_requirements(srd, base_dir=base_dir).verdict == "fail"
