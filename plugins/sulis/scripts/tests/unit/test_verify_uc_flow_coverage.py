"""WP-008 — the UC-flow-coverage gate (FR-12/13, ADR-004).

The THIRD companion gate (not a rewrite of #103/#86): for every UC flow
(main + alternate + exception), is there a covering scenario in the brain, a
planned WP, or a recorded out-of-scope decision? Absence ⇒ ``gaps``
(fail-closed, NFR-S04). The covering-scenario truth comes from the brain
(``find_scenarios_for_journey`` — NFR-D01), never an agent claim.

A ``uc_flow`` is ``{"id": <flow-id>, "verifies": <requirement-id>}``: the
flow is covered iff a Scenario in the journey ``verifies`` that requirement
(the scenario schema has no per-flow link, so the requirement the flow proves
is the join key). ``planned`` / ``out_of_scope`` are sets of flow ids.
"""

from __future__ import annotations

from pathlib import Path

from _entity_adapter_local import LocalFileEntityAdapter
from _scenario_authoring import _ulid
from _verify_uc_flow_coverage import verify_uc_flow_coverage

_WF = f"dna:workflow:{_ulid('uc-flow-journey')}"
_DES = f"dna:design:{_ulid('des')}"
_REQ_MAIN = f"dna:requirement:{_ulid('req-main')}"
_REQ_ALT = f"dna:requirement:{_ulid('req-alt')}"
_REQ_EXC = f"dna:requirement:{_ulid('req-exc')}"

# Three UC flows: main, alternate, exception. Each names the requirement it proves.
_FLOW_MAIN = {"id": "UC-06-main", "verifies": _REQ_MAIN}
_FLOW_ALT = {"id": "UC-06-2a", "verifies": _REQ_ALT}
_FLOW_EXC = {"id": "UC-06-3a", "verifies": _REQ_EXC}


def _seed_scenarios(base: Path, *covered_reqs: str) -> None:
    """Author one journey Scenario per requirement in ``covered_reqs``."""
    p = LocalFileEntityAdapter(base_dir=base, domain="product-development")
    for req in covered_reqs:
        p.save("scenario", {
            "id": f"dna:scenario:{_ulid('s-' + req)}", "sys_status": "active",
            "name": "covers " + req.split(":")[-1][:8], "journey": _WF,
            "verifies": [req], "exercises": _DES, "state": "active",
        })


class TestUCFlowCoverage:
    def test_uncovered_flow_yields_gaps(self, tmp_path) -> None:
        # SC-13/SC-14: main + alternate covered, the EXCEPTION flow has no scenario.
        base = tmp_path / ".brain" / "instances"
        _seed_scenarios(base, _REQ_MAIN, _REQ_ALT)
        r = verify_uc_flow_coverage(
            [_FLOW_MAIN, _FLOW_ALT, _FLOW_EXC], _WF, base_dir=base)
        assert r.verdict == "gaps"
        assert {f["id"] for f in r.uncovered_flows} == {"UC-06-3a"}

    def test_all_flows_covered_passes(self, tmp_path) -> None:
        # SC-12: every flow (main + alternate + exception) has a covering scenario.
        base = tmp_path / ".brain" / "instances"
        _seed_scenarios(base, _REQ_MAIN, _REQ_ALT, _REQ_EXC)
        r = verify_uc_flow_coverage(
            [_FLOW_MAIN, _FLOW_ALT, _FLOW_EXC], _WF, base_dir=base)
        assert r.verdict == "covered"
        assert r.uncovered_flows == []

    def test_out_of_scope_flow_not_a_gap(self, tmp_path) -> None:
        # An uncovered flow with a recorded out-of-scope decision ⇒ covered.
        base = tmp_path / ".brain" / "instances"
        _seed_scenarios(base, _REQ_MAIN, _REQ_ALT)
        r = verify_uc_flow_coverage(
            [_FLOW_MAIN, _FLOW_ALT, _FLOW_EXC], _WF,
            base_dir=base, out_of_scope={"UC-06-3a"})
        assert r.verdict == "covered"
        assert r.uncovered_flows == []

    def test_planned_flow_not_a_gap(self, tmp_path) -> None:
        # An uncovered flow with a planned WP ⇒ covered (parity with #86 `planned`).
        base = tmp_path / ".brain" / "instances"
        _seed_scenarios(base, _REQ_MAIN, _REQ_ALT)
        r = verify_uc_flow_coverage(
            [_FLOW_MAIN, _FLOW_ALT, _FLOW_EXC], _WF,
            base_dir=base, planned={"UC-06-3a"})
        assert r.verdict == "covered"

    def test_brain_unreadable_yields_error(self, tmp_path) -> None:
        # Brain unreadable ⇒ error, NEVER a silent pass (NFR-S04 fail-closed).
        r = verify_uc_flow_coverage(
            [_FLOW_MAIN], _WF, base_dir=tmp_path / "nope")
        assert r.verdict == "error"
