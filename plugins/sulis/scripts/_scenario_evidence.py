"""Scenario-route evidence emission — close the loop the gate reads.

Background. The requirement-coverage gate (`_verify_requirements.py`) has
one rule: a Requirement is verified iff a *passing TestResult* in the brain
has it in its `verifies` array. That rule is correct and route-agnostic —
both a `@verifies`-tagged unit test and a green Scenario run are just
TestResults to the gate.

The gap this module closes: the Scenario loop (`sulis-verify-acceptance`)
*runs* a journey green but never *emitted* the evidence — so a
Scenario-verified requirement read as uncovered (a false-red). This deposits
the missing evidence: one green/red Scenario run → one TestRun + one
TestResult (`verifies` = the Scenario's `verifies`, `type=e2e`, outcome from
the verdict), so the existing gate sees the Scenario route with no rule
change. It also fills the `TestRun.of_scenario` / `TestResult.scenario`
back-links the Scenario re-point added for exactly this.

Idempotent per scenario. The TestRun id is keyed on the scenario (not the
run timestamp), so re-running a scenario OVERWRITES its single record rather
than accumulating — a regressed scenario flips its one record pass→fail, and
no stale-pass lingers for the gate to find. The record reflects the *current*
verification status, which is what "is this requirement covered?" means.
"""

from __future__ import annotations

from pathlib import Path

from _entity_adapter_local import LocalFileEntityAdapter
from _scenario_runtime import _entity_id
from _testresult_emission import emit_testresult
from _testrun_emission import emit_testrun

# Scenario verdict (pass | fail | deferred | manual-pending) → TestResult
# outcome (pass | fail | skip). Only "pass" counts as coverage at the gate;
# an unresolved verdict (deferred / awaiting a manual step) is honestly a
# skip, not a claim of coverage.
_VERDICT_TO_OUTCOME = {
    "pass": "pass",
    "fail": "fail",
    "deferred": "skip",
    "manual-pending": "skip",
}


def emit_scenario_evidence(
    *,
    base_dir: Path | str,
    scenario: dict,
    verdict: str,
    domain: str = "product-development",
    ran_at: str | None = None,
) -> dict | None:
    """Deposit the TestRun + TestResult for one Scenario run.

    Returns a small summary dict (`testrun`, `testresult`, `outcome`,
    `verifies`) on emission, or ``None`` when the scenario verifies nothing
    (no requirement refs → nothing the gate could gain, so no
    verifies-less record is written).

    Raises on a malformed scenario id / requirement ref (programmer error);
    callers that want best-effort behaviour (the CLI) wrap the call.
    """
    verifies = [v for v in (scenario.get("verifies") or []) if isinstance(v, str) and v]
    if not verifies:
        return None

    scenario_id = _entity_id(scenario)
    outcome = _VERDICT_TO_OUTCOME.get(verdict, "skip")
    adapter = LocalFileEntityAdapter(base_dir=Path(base_dir), domain=domain)

    run = emit_testrun(
        repo=adapter,
        ran_at=ran_at,
        harness="scenario-runner",
        of_scenario=scenario_id,
    )
    result = emit_testresult(
        repo=adapter,
        of_run=run["id"],
        verifies=verifies,
        type="e2e",
        outcome=outcome,
        scenario=scenario_id,
        evidence=f"scenario-run:{scenario_id}",
    )
    return {
        "testrun": run["id"],
        "testresult": result["id"],
        "outcome": outcome,
        "verifies": verifies,
    }
