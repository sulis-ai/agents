"""UC-flow-coverage gate — does every use-case flow have a covering scenario?

The THIRD companion gate (ADR-004, FR-12/13), alongside the scenario-required
gate (`_scenario_required_gate.py`, #103) and the journey-coverage check
(`_verify_scenario_coverage.py`, #86). It does NOT replace either — all three
apply independently and report distinct verdicts (GLOSSARY "NOT the Same As"):

  - #103 asks *"is this change in scope for scenarios at all?"*
  - #86  asks *"is every scenario in the journey green / planned / out-of-scope?"*
  - this asks *"does every UC FLOW (main + alternate + exception) have a
    covering scenario at all?"* — a superset check of #86 (#86 checks hops
    *within* an existing scenario's journey; this checks a scenario *exists per
    flow*).

A `uc_flow` is `{"id": <flow-id>, "verifies": <requirement-id>}`: the Scenario
schema carries no per-flow link, so the requirement a flow proves is the join
key. A flow is **covered** iff a Scenario in the journey `verifies` that
requirement (the brain is truth — NFR-D01, via `find_scenarios_for_journey`),
OR the flow id is in the caller's `planned` set (a WP exists), OR in the
caller's `out_of_scope` set (a recorded decision). A flow that is none of those
is an uncovered GAP → the verdict is `gaps` (fail-closed — NFR-S04: absence of
coverage is never silently passed).

Verdict → exit code (CLI):
  0 — covered (every flow covered / planned / out-of-scope)
  1 — gaps    (≥1 flow neither covered, planned, nor out-of-scope)
  3 — error   (bad input / brain unreadable)

Pure decision over the brain + the caller's planned/out-of-scope sets.
Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _brain_query import find_scenarios_for_journey


@dataclass
class FlowCoverage:
    """One UC flow's coverage status within a journey."""

    flow_id: str
    verifies: str              # the requirement the flow proves (join key)
    disposition: str           # covered | planned | out-of-scope | GAP


@dataclass
class UCFlowCoverageResult:
    verdict: str  # covered | gaps | error
    journey_workflow_id: str
    coverage: list = field(default_factory=list)  # list[FlowCoverage]
    errors: list = field(default_factory=list)

    @property
    def gaps(self) -> list:
        return [c for c in self.coverage if c.disposition == "GAP"]

    @property
    def uncovered_flows(self) -> list:
        """The GAP flows as plain dicts — the founder-facing 'what's missing'."""
        return [{"id": c.flow_id, "verifies": c.verifies} for c in self.gaps]

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "journey_workflow_id": self.journey_workflow_id,
            "total": len(self.coverage),
            "uncovered_flows": self.uncovered_flows,
            "coverage": [
                {"flow_id": c.flow_id, "verifies": c.verifies,
                 "disposition": c.disposition}
                for c in self.coverage
            ],
            "errors": list(self.errors),
        }


def verify_uc_flow_coverage(
    uc_flows: list,
    journey_workflow_id: str,
    *,
    base_dir: Path,
    planned: set | list | None = None,
    out_of_scope: set | list | None = None,
    domain: str = "product-development",
) -> UCFlowCoverageResult:
    """Classify every UC flow; decide covered / gaps (fail-closed).

    Args:
        uc_flows: every flow — main + alternate + exception — each a dict
            `{"id": <flow-id>, "verifies": <dna:requirement:ulid>}`.
        journey_workflow_id: the journey's Workflow id (`dna:workflow:<ulid>`).
        planned: flow ids the change has a planned WP for.
        out_of_scope: flow ids consciously recorded out-of-scope.

    A flow is `covered` iff a Scenario in the journey verifies its requirement;
    else `planned`, else `out-of-scope`, else a `GAP`. `gaps` verdict iff any
    GAP. A flow with no covering scenario and no out-of-scope record is never
    silently passed (NFR-S04). Brain unreadable ⇒ `error`, never a silent pass.
    """
    base_dir = Path(base_dir)
    planned = set(planned or [])
    out_of_scope = set(out_of_scope or [])
    result = UCFlowCoverageResult(verdict="covered",
                                  journey_workflow_id=journey_workflow_id)

    if not base_dir.exists():
        result.verdict = "error"
        result.errors.append(f"brain base dir not found ({base_dir})")
        return result

    # Brain is truth (NFR-D01): the set of requirements a journey scenario
    # covers. Reuses #86's `find_scenarios_for_journey` (no new traversal).
    scenarios = find_scenarios_for_journey(base_dir, journey_workflow_id, domain=domain)
    covered_reqs: set = set()
    for s in scenarios:
        verifies = s.get("verifies") or []
        if isinstance(verifies, list):
            covered_reqs.update(verifies)

    for flow in uc_flows:
        flow_id = flow.get("id", "")
        req = flow.get("verifies", "")
        if req and req in covered_reqs:
            disposition = "covered"
        elif flow_id in planned:
            disposition = "planned"
        elif flow_id in out_of_scope:
            disposition = "out-of-scope"
        else:
            disposition = "GAP"
        result.coverage.append(FlowCoverage(
            flow_id=flow_id, verifies=req, disposition=disposition,
        ))

    result.verdict = "gaps" if result.gaps else "covered"
    return result


# ─── CLI (mirrors _verify_scenario_coverage's invocation shape) ────────────


_VERDICT_EXIT = {"covered": 0, "gaps": 1, "error": 3}


def _parse_set(raw: str | None) -> set:
    """Comma-separated flow-id list → set (empty string / None → empty set)."""
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UC-flow-coverage gate: every UC flow has a covering scenario?",
    )
    parser.add_argument(
        "--uc-flows", required=True,
        help="JSON array of flows: [{\"id\": ..., \"verifies\": ...}, ...] "
             "(or @path to a file containing it)")
    parser.add_argument("--journey", required=True,
                        help="the journey Workflow id (dna:workflow:<ulid>)")
    parser.add_argument("--base-dir", required=True,
                        help="the .brain/instances/ root")
    parser.add_argument("--planned", default="",
                        help="comma-separated flow ids with a planned WP")
    parser.add_argument("--out-of-scope", default="",
                        help="comma-separated flow ids recorded out-of-scope")
    parser.add_argument("--domain", default="product-development")
    args = parser.parse_args(argv)

    raw = args.uc_flows
    if raw.startswith("@"):
        raw = Path(raw[1:]).read_text()
    try:
        uc_flows = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"verdict": "error",
                          "errors": [f"--uc-flows is not valid JSON: {exc}"]}))
        return _VERDICT_EXIT["error"]

    result = verify_uc_flow_coverage(
        uc_flows, args.journey,
        base_dir=Path(args.base_dir),
        planned=_parse_set(args.planned),
        out_of_scope=_parse_set(args.out_of_scope),
        domain=args.domain,
    )
    print(json.dumps(result.as_dict(), indent=2))
    return _VERDICT_EXIT.get(result.verdict, 3)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
