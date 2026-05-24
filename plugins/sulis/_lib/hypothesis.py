"""Hypothesis dataclass for manual primitives.

Used by check-* skills for primitives that can't be fully automated
(DAT-01 encryption at rest, DAT-05 audit logging, CQ-05 review practices).

Per SPIRAL_TEMPLATES.md Honest Uncertainty dimension: hypotheses surface
separately from findings. A skill with 0 findings + 3 hypotheses is
"passed (with things to verify)" not "needs attention."

Founder mode rendering: hypotheses appear under "## Things to verify
with the team" section. Operator mode (--raw): `hypotheses[]` array.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Confidence(Enum):
    """Confidence level per Critical Thinking Standard CC (Confidence Calibration)."""

    VALIDATED = "VALIDATED"     # 5+ independent sources, triangulated
    SUPPORTED = "SUPPORTED"     # 3-4 sources, some triangulation
    EMERGING = "EMERGING"       # 2 sources, consistent pattern
    UNVALIDATED = "UNVALIDATED" # <2 sources
    CONTRADICTED = "CONTRADICTED"


@dataclass(frozen=True)
class Hypothesis:
    """Evidence-backed hypothesis about a primitive that can't be fully automated.

    Attributes:
        primitive_id: which primitive this hypothesis relates to (e.g., "DAT-01")
        statement: what we believe to be true/false
        evidence: list of file:line citations or measurements
        confidence: Confidence level
        verification_question: question the team can answer to confirm/refute
    """

    primitive_id: str
    statement: str
    evidence: list[str] = field(default_factory=list)
    confidence: Confidence = Confidence.UNVALIDATED
    verification_question: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise for JSON envelope (--raw mode)."""
        d = asdict(self)
        d["confidence"] = self.confidence.value
        return d

    def to_founder_markdown(self) -> str:
        """Render for founder-mode under '## Things to verify with the team'."""
        lines = [f"- **{self.primitive_id}** — {self.statement}"]
        if self.evidence:
            lines.append(f"  - Evidence: {'; '.join(self.evidence)}")
        lines.append(f"  - Confidence: {self.confidence.value}")
        if self.verification_question:
            lines.append(f"  - Verify: {self.verification_question}")
        return "\n".join(lines)
