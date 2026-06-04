"""Human attestation — the verifier-of-last-resort drives the real flow.

Journey-rigor #6, the human-handoff half. Some journeys can't be machine-run in
v1: a browser login flow, a payment that needs a real card, anything whose only
honest check is a person looking at a screen. Since journey-rigor #1 those
journeys correctly **block** (a `manual-pending` / `deferred` verdict is not a
pass) — which is safe, but leaves no path to green. That's the gap this closes.

A human actually walks the journey, confirms each observable check (the asserts
journey-rigor #5 guarantees every scenario carries), and attests the result.
A pass deposits a **real** TestRun + TestResult — same evidence the automated
runner deposits, the same the coverage gate reads — but stamped
``harness="human-attested"`` so the green is honest about who observed it. The
blocked scenario goes genuinely green by observation, never by a rubber-stamp:
attestation requires naming what was observed, and any unobserved check fails it.

This is NOT a way to wave a scenario through. It's the opposite — it forces a
person to look at the real thing and record what they saw, then keeps that
record as durable evidence. The automated browser driver (Playwright/CDP) is the
named follow-on for the *machine* half of "drives the real flow"; until it
lands, the human is the driver and this is how their observation becomes
evidence the gate trusts.

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from _scenario_evidence import emit_scenario_evidence


@dataclass
class AttestationResult:
    verdict: str  # pass | fail
    attester: str
    observations: list = field(default_factory=list)  # [{"check","observed"}]
    evidence_summary: dict | None = None  # the deposited TestRun/TestResult, or None

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "attester": self.attester,
            "observations": list(self.observations),
            "evidence": self.evidence_summary,
        }


def fold_verdict(observations: list) -> str:
    """A scenario is human-attested *pass* iff there is at least one observation
    and every observation was observed-true; otherwise *fail*. No observations
    is not a pass — you can't attest to a journey you didn't actually check."""
    obs = [bool(o.get("observed")) for o in observations]
    return "pass" if obs and all(obs) else "fail"


def attest_scenario(
    *,
    base_dir: Path | str,
    scenario: dict,
    attester: str,
    observations: list,
    ran_at: str | None = None,
    domain: str = "product-development",
) -> AttestationResult:
    """Record a human's first-hand attestation of a scenario run.

    Args:
        scenario: the Scenario entity (carries ``verifies`` + ``id``).
        attester: who ran it (a name / handle) — recorded on the evidence so the
            observation is attributable, not anonymous.
        observations: ``[{"check": str, "observed": bool}, ...]`` — one entry per
            observable check the person confirmed (or didn't). MUST be non-empty;
            every entry MUST be observed-true for a pass.

    Deposits a real ``harness="human-attested"`` TestRun + TestResult reflecting
    the folded verdict, so the coverage gate reads the human observation exactly
    as it reads an automated run. Raises ``ValueError`` on an empty attester or
    empty observations (an attestation must name a person and name what they saw).
    """
    attester = (attester or "").strip()
    if not attester:
        raise ValueError("an attestation must name who observed the run (attester)")
    if not observations:
        raise ValueError(
            "an attestation must record at least one observed check — you can't "
            "attest to a journey you didn't actually walk"
        )

    verdict = fold_verdict(observations)
    passed = [o["check"] for o in observations if o.get("observed")]
    failed = [o["check"] for o in observations if not o.get("observed")]
    trace = f"human-attested:{attester}; observed={passed}; not-observed={failed}"

    summary = emit_scenario_evidence(
        base_dir=base_dir,
        scenario=scenario,
        verdict=verdict,
        domain=domain,
        ran_at=ran_at,
        harness="human-attested",
        evidence=trace,
    )
    return AttestationResult(
        verdict=verdict,
        attester=attester,
        observations=list(observations),
        evidence_summary=summary,
    )
