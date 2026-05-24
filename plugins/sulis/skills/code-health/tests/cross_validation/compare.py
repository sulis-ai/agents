"""Cross-validation comparison — code-health vs codebase-assess.

Skeleton implementation. Wires up once per-tool wrappers exist and both
tools' outputs have comparable shape per Phase 4 iteration 2.

Run pattern (future):

    python3 plugins/sulis/skills/code-health/tests/cross_validation/compare.py \\
        --code-health-output .checkup/{project}/CHECKUP.md \\
        --codebase-assess-output .security/{project}/viability-report-LATEST.md \\
        --output divergence_report.md

Outputs a divergence report with per-primitive MATCH / DIVERGENT /
NOT_ASSESSED_BOTH counts + categorisation hints for the maintainer.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DivergenceCategory(Enum):
    MATCH = "match"
    EXPECTED_DIVERGENT = "expected_divergent"  # wrapper-pending; tracked in expected_divergence.md
    UNEXPECTED_DIVERGENT = "unexpected_divergent"  # real bug or undocumented intentional difference
    NOT_ASSESSED_BOTH = "not_assessed_both"


@dataclass
class PrimitiveComparison:
    primitive_id: str  # e.g., "SEC-07", "CQ-04"
    code_health_verdict: str | None  # PASS / ADVISORY / CONCERN / CRITICAL / HYPOTHESIS / NOT_ASSESSED / None
    codebase_assess_verdict: str | None
    category: DivergenceCategory
    notes: str = ""


def parse_code_health_output(path: Path) -> dict[str, str]:
    """Parse CHECKUP.md and extract primitive → verdict mapping.

    NOT YET IMPLEMENTED — depends on the post-wrapper CHECKUP.md format.
    Currently CHECKUP.md doesn't break out per-primitive verdicts; iteration
    2 should add a `## Primitive Coverage` section per tier.

    Returns:
        Mapping like {"SEC-01": "PASS", "SEC-07": "NOT_ASSESSED", ...}
    """
    raise NotImplementedError(
        "CHECKUP.md per-primitive parsing — implemented in Phase 2 iteration 2 when "
        "per-tool wrappers emit primitive-level verdicts."
    )


def parse_codebase_assess_output(path: Path) -> dict[str, str]:
    """Parse viability-report-{TIMESTAMP}.md and extract primitive → verdict mapping.

    NOT YET IMPLEMENTED — codebase-assess output structure documented in
    plugins/sulis-security/skills/codebase-assess/SKILL.md §"Output format".
    Look for the per-primitive table under "## Findings" section.
    """
    raise NotImplementedError(
        "viability-report.md per-primitive parsing — implemented in Phase 2 iteration 2."
    )


def categorise(
    primitive_id: str,
    code_health_verdict: str | None,
    codebase_assess_verdict: str | None,
    expected_divergence_ledger: dict[str, str],
) -> DivergenceCategory:
    """Apply the categorisation rules per README.md."""
    if code_health_verdict == codebase_assess_verdict:
        if code_health_verdict in {"NOT_ASSESSED", None}:
            return DivergenceCategory.NOT_ASSESSED_BOTH
        return DivergenceCategory.MATCH
    if primitive_id in expected_divergence_ledger:
        return DivergenceCategory.EXPECTED_DIVERGENT
    return DivergenceCategory.UNEXPECTED_DIVERGENT


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-health-output", type=Path, required=True)
    parser.add_argument("--codebase-assess-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("divergence_report.md"))
    args = parser.parse_args(argv)

    # Phase 4 iteration 1: skeleton only
    print(
        "compare.py skeleton — full implementation deferred to Phase 4 iteration 2 "
        "(post-wrapper). See README.md + expected_divergence.md for the current state.",
        file=sys.stderr,
    )
    print(
        "Current parity (pre-wrapper): 4% (1/25 primitives — CQ-04 only). Target: 95%.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
