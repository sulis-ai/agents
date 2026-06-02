"""The testable-state DoD gate decision.

Folds a change's in-scope Scenario results (WP-004) into a done/blocked call.
"Done" requires every in-scope Scenario to PASS or be DEFERRED-WITH-NEED:
  - `fail` / `manual-pending` → BLOCK done (broken, or a human step unconfirmed)
  - `deferred` → acknowledged recorded gap (credential/infra absent); non-blocking
  - `pass` → done-qualifying

This is the real "done" — grounded in the gate that matters (the app is
testable), not in "merged" (the #81 Definition-of-Done discipline made
mechanical). Wires into the ship stage (step 4.8) alongside the requirements
DoD gate.

Pure decision over AcceptanceResult list. Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_BLOCKING_VERDICTS = {"fail", "manual-pending"}


@dataclass
class GateDecision:
    verdict: str  # pass | blocked
    blocking: list = field(default_factory=list)       # [{scenario, why}]
    deferred_needs: list = field(default_factory=list)  # recorded, non-blocking


def gate_decision(results) -> GateDecision:
    """Decide done/blocked over the in-scope Scenario results."""
    blocking: list = []
    deferred_needs: list = []
    for r in results:
        if r.verdict in _BLOCKING_VERDICTS:
            why = ("a step is broken" if r.verdict == "fail"
                   else "a manual check hasn't been confirmed")
            blocking.append({"scenario": r.scenario_name, "why": why,
                             "verdict": r.verdict})
        elif r.verdict == "deferred":
            deferred_needs.extend(getattr(r, "needs", []) or [])
    return GateDecision(
        verdict="blocked" if blocking else "pass",
        blocking=blocking,
        deferred_needs=sorted(set(deferred_needs)),
    )


def format_gate_message(decision: GateDecision) -> str:
    """Founder-English: why this can or can't be called done."""
    if decision.verdict == "pass":
        msg = "✓ Done — every check passed against a standing app."
        if decision.deferred_needs:
            msg += ("\n  (Recorded gaps, not blocking: "
                    + ", ".join(decision.deferred_needs) + ".)")
        return msg
    lines = ["✗ Not done yet — these need to work first:"]
    for b in decision.blocking:
        lines.append(f"  • {b['scenario']}: {b['why']}")
    if decision.deferred_needs:
        lines.append("  (Recorded gaps: " + ", ".join(decision.deferred_needs) + ".)")
    return "\n".join(lines)
