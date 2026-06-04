"""Scenario-coverage gate — is every scenario in a journey accounted for?

The plan-stage sibling of `_verify_requirements` (the requirement-coverage
gate). Where that gate asks *"does every Requirement have a passing
TestResult?"*, this asks *"is every Scenario in the journey either
observed-green, or planned-for, or consciously out-of-scope?"* — so a change
that builds **some** of a journey still **checks all** of it, and nothing
falls through silently (the founder's "check ALL even if we build some").

The objective core comes from the brain (not an agent's claim): for every
Scenario in the journey (`find_scenarios_for_journey`, #84), is it
observed-green (a passing TestResult back-links it —
`find_passing_testresults_for_scenario`)? The gate splits the journey set into:

  - **green**       — already observed-green; no work needed
  - **not_green**   — NOT proven; needs a planned WP or a recorded out-of-scope
                      decision before the change is "covered"

The caller (plan-work) supplies which not-green scenarios it has **planned**
(a WP exists) and which are **out_of_scope** (recorded). A not-green scenario
that is neither planned nor out-of-scope is an **uncovered GAP** → the verdict
is `gaps` (blocking). When every not-green scenario is planned-or-out-of-scope,
the verdict is `covered`.

Verdict → exit code (CLI):
  0 — covered (every journey scenario green / planned / out-of-scope)
  1 — gaps    (≥1 not-green scenario neither planned nor out-of-scope)
  3 — error   (bad input / brain unreadable)

Pure decision over the brain + the caller's planned/out-of-scope sets.
Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from _brain_query import (
    find_passing_testresults_for_scenario,
    find_scenarios_for_journey,
)


@dataclass
class ScenarioCoverage:
    """One scenario's coverage status within a journey."""

    scenario_id: str
    name: str
    green: bool                # observed-green (a passing TestResult)
    disposition: str           # green | planned | out-of-scope | GAP


@dataclass
class ScenarioCoverageResult:
    verdict: str  # covered | gaps | error
    journey_workflow_id: str
    coverage: list = field(default_factory=list)  # list[ScenarioCoverage]
    errors: list = field(default_factory=list)

    @property
    def gaps(self) -> list:
        return [c for c in self.coverage if c.disposition == "GAP"]

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "journey_workflow_id": self.journey_workflow_id,
            "total": len(self.coverage),
            "green": [c.scenario_id for c in self.coverage if c.green],
            "gaps": [
                {"scenario_id": c.scenario_id, "name": c.name}
                for c in self.gaps
            ],
            "coverage": [
                {"scenario_id": c.scenario_id, "name": c.name,
                 "green": c.green, "disposition": c.disposition}
                for c in self.coverage
            ],
            "errors": list(self.errors),
        }


def verify_scenario_coverage(
    journey_workflow_id: str,
    *,
    base_dir: Path,
    planned: set | list | None = None,
    out_of_scope: set | list | None = None,
    domain: str = "product-development",
) -> ScenarioCoverageResult:
    """Classify every Scenario in a journey; decide covered / gaps.

    Args:
        journey_workflow_id: the journey's Workflow id (`dna:workflow:<ulid>`).
        planned: scenario ids the change has a planned WP for.
        out_of_scope: scenario ids consciously recorded out-of-scope.

    A scenario is `green` if observed-green; otherwise it is `planned`,
    `out-of-scope`, or — if neither — a `GAP`. `gaps` verdict iff any GAP.
    """
    base_dir = Path(base_dir)
    planned = set(planned or [])
    out_of_scope = set(out_of_scope or [])
    result = ScenarioCoverageResult(verdict="covered",
                                    journey_workflow_id=journey_workflow_id)

    if not base_dir.exists():
        result.verdict = "error"
        result.errors.append(f"brain base dir not found ({base_dir})")
        return result

    scenarios = find_scenarios_for_journey(base_dir, journey_workflow_id, domain=domain)
    if not scenarios:
        # No scenarios for this journey — nothing to cover. Surface, don't fail.
        result.errors.append(
            f"no scenarios found for journey {journey_workflow_id}"
        )
        return result

    for s in scenarios:
        sid = s.get("id", "")
        name = s.get("name", sid)
        green = bool(find_passing_testresults_for_scenario(base_dir, sid, domain=domain))
        if green:
            disposition = "green"
        elif sid in planned:
            disposition = "planned"
        elif sid in out_of_scope:
            disposition = "out-of-scope"
        else:
            disposition = "GAP"
        result.coverage.append(ScenarioCoverage(
            scenario_id=sid, name=name, green=green, disposition=disposition,
        ))

    result.verdict = "gaps" if result.gaps else "covered"
    return result
