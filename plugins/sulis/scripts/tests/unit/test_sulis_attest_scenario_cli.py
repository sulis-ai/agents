"""End-to-end CLI tests for `sulis-attest-scenario` (journey-rigor #6).

Seed a real journey into the brain via `sulis-author-scenario --emit`, then
attest it by hand and prove a human-attested pass lands as evidence the
coverage gate reads — and that an unobserved check records a fail instead.
"""

from __future__ import annotations

import json
from pathlib import Path

from _scenario_authoring import _ulid

_TENANT = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"


def _spec() -> dict:
    return {
        "name": "A user can sign in",
        "verifies": [f"dna:requirement:{_ulid('req-login')}"],
        "exercises": f"dna:design:{_ulid('des-login')}",
        "tenant": _TENANT,
        "seed": "sign-in",
        "steps": [
            {"instruction": "Open the sign-in page and enter valid credentials",
             "asserts": ["a session is established"]},
            {"instruction": "Land on the dashboard",
             "asserts": ["the dashboard is shown"]},
        ],
    }


def _seed(tmp_path: Path, run_tool) -> tuple[str, Path]:
    jpath = tmp_path / "journey.json"
    jpath.write_text(json.dumps(_spec()))
    base = tmp_path / ".brain" / "instances"
    res = run_tool(
        "sulis-author-scenario", "--journey", str(jpath),
        "--out", str(tmp_path / "x.scenarios.jsonld"),
        "--emit", "--base-dir", str(base), "--repo-root", str(tmp_path),
    )
    assert res.ok, f"seed failed: {res.stderr!r}"
    return res.data["scenario_id"], base


def _passing(base: Path, scenario_id: str) -> list:
    import sys
    sys.path.insert(0, str(base.parents[2] / "plugins" / "sulis" / "scripts"))
    from _brain_query import find_passing_testresults_for_scenario
    return find_passing_testresults_for_scenario(base, scenario_id)


class TestAttestScenarioCli:
    def test_list_prints_checklist_and_deposits_nothing(self, tmp_path: Path, run_tool) -> None:
        sid, base = _seed(tmp_path, run_tool)
        res = run_tool("sulis-attest-scenario", "--scenario", sid,
                       "--base-dir", str(base), "--list", "--json")
        assert res.returncode == 0
        checklist = res.json["checklist"]
        assert len(checklist) == 2
        assert "the dashboard is shown" in [c for it in checklist for c in it["look_for"]]

    def test_all_observed_records_human_attested_pass(self, tmp_path: Path, run_tool) -> None:
        sid, base = _seed(tmp_path, run_tool)
        res = run_tool("sulis-attest-scenario", "--scenario", sid, "--base-dir", str(base),
                       "--attester", "iain", "--all-observed", "--json")
        assert res.ok, f"stderr: {res.stderr!r}"
        assert res.data["verdict"] == "pass"
        assert res.data["evidence"]["harness"] == "human-attested"
        assert len(_passing(base, sid)) == 1

    def test_not_observed_records_fail_no_passing_evidence(self, tmp_path: Path, run_tool) -> None:
        sid, base = _seed(tmp_path, run_tool)
        res = run_tool("sulis-attest-scenario", "--scenario", sid, "--base-dir", str(base),
                       "--attester", "iain",
                       "--observed", "a session is established",
                       "--not-observed", "the dashboard is shown", "--json")
        assert res.returncode == 1
        assert res.data["verdict"] == "fail"
        assert _passing(base, sid) == []

    def test_no_observations_is_invocation_error(self, tmp_path: Path, run_tool) -> None:
        sid, base = _seed(tmp_path, run_tool)
        res = run_tool("sulis-attest-scenario", "--scenario", sid, "--base-dir", str(base),
                       "--attester", "iain", "--json")
        assert res.returncode == 2
