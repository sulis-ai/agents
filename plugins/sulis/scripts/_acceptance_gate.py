"""The testable-state DoD gate decision.

Folds a change's in-scope Scenario results (WP-004) into a done/blocked call.
**Observed-or-blocked** is the default (`require_observed=True`): "done"
requires every in-scope Scenario to actually PASS — to have been *observed*
green.
  - `fail` / `manual-pending` → BLOCK done (broken, or a human step unconfirmed)
  - `deferred` → the real outcome was NOT driven (a credential / infra /
    third-party hop absent). By default this **BLOCKS** — its need is surfaced
    + the escape named. It does NOT count as done.
  - `pass` → done-qualifying (observed).

Why default-block on `deferred`: across four attempts at "founder can log in,"
the journey reached "done" on a *deferred* (never-driven) sign-in — merged /
green / believed-done while no human ever signed in. "I couldn't verify it"
must read as BLOCKED, never DONE. This is the #81 Definition-of-Done discipline
made mechanical (the Outcome Test with teeth).

The escape: pass `require_observed=False` (CLI `--allow-deferred`) ONLY for a
consciously non-user-facing Scenario where a recorded, non-blocking gap is the
honest call (e.g. an infra leg genuinely unavailable in a local run). That
restores the legacy "deferred is a recorded gap" behaviour — by deliberate
choice, not by default.

Wires into the ship stage (step 4.8) alongside the requirements DoD gate.

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


def gate_decision(results, *, require_observed: bool = True) -> GateDecision:
    """Decide done/blocked over the in-scope Scenario results.

    `require_observed` (default True): the outcome must be OBSERVED. A
    `deferred` Scenario (the real thing wasn't driven) BLOCKS "done", its need
    surfaced + the escape named. Pass `require_observed=False` (CLI
    `--allow-deferred`) only for a consciously non-user-facing Scenario where a
    recorded, non-blocking gap is acceptable — then `deferred` records the need
    without blocking (the legacy behaviour, by deliberate choice).
    """
    blocking: list = []
    deferred_needs: list = []
    for r in results:
        if r.verdict in _BLOCKING_VERDICTS:
            why = ("a step is broken" if r.verdict == "fail"
                   else "a manual check hasn't been confirmed")
            blocking.append({"scenario": r.scenario_name, "why": why,
                             "verdict": r.verdict})
        elif r.verdict == "deferred":
            needs = getattr(r, "needs", []) or []
            deferred_needs.extend(needs)
            if require_observed:
                why = "the real outcome wasn't driven"
                if needs:
                    why += f" (needs: {', '.join(needs)})"
                why += " — drive it, or pass --allow-deferred if this isn't a user-facing outcome"
                blocking.append({"scenario": r.scenario_name, "why": why,
                                 "verdict": "deferred"})
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
