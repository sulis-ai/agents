"""Scenario↔implementation drift detector.

Flags a Scenario whose journey-step referents no longer resolve against the
implementation — the case has drifted from what it tests. Same shape as the
Path-A canonical-drift detector: a finding per unresolved referent, exit-1 when
non-empty (the runner/CI wires that). `mechanism: human` steps have no
automatable referent and are skipped.

`referent_exists(resolved_step) -> bool` is injected: the real check confirms
the step's http path is declared (ServiceSpec) / its subprocess cmd resolves.

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from dataclasses import dataclass

from _scenario_runtime import HUMAN_DRIVER, UNRESOLVED_DRIVER, ResolvedStep


@dataclass
class DriftFinding:
    step_name: str
    reason: str


def detect_scenario_drift(resolved_steps, *, referent_exists) -> list[DriftFinding]:
    """Return a finding per journey step whose referent no longer resolves.

    Two drift conditions: (1) the step's driver is UNRESOLVED (its tool was
    removed/renamed); (2) `referent_exists` reports the step's target
    (endpoint/command) is gone. Human steps are skipped — nothing automatable
    to drift.
    """
    findings: list[DriftFinding] = []
    for step in resolved_steps:
        if step.driver == HUMAN_DRIVER:
            continue
        if step.driver == UNRESOLVED_DRIVER:
            findings.append(DriftFinding(
                step_name=step.name,
                reason="step driver unresolved — its tool was removed or renamed",
            ))
            continue
        if not referent_exists(step):
            findings.append(DriftFinding(
                step_name=step.name,
                reason="step referent (endpoint/command) no longer exists in the implementation",
            ))
    return findings
