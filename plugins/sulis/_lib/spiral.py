"""OODA-spiral helper for multi-cycle scans.

Used by check-* skills (esp. check-security HEAVY tier) to structure
scans into the OODA cycles documented in CRITICAL_THINKING_STANDARD.md +
SPIRAL_TEMPLATES.md:

1. Observe — reconnaissance (detect language / frameworks / deployment)
2. Orient — triage + depth (run broad tools first; prioritise CRITICAL)
3. Decide — cross-primitive chaining (look for findings that combine)
4. Act — fix-as-you-go OR record + move to next iteration
5. (Optional) Hypothesis — for manual primitives, write evidence-backed
   hypotheses

Termination: all applicable primitives have a status; no productive
lines of inquiry remain. Max iterations: 3 (per SPIRAL_TEMPLATES tier).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SpiralContext:
    """Shared state across a spiral run."""

    repo_root: str
    scope: str = "codebase"
    iteration: int = 0
    max_iterations: int = 3
    findings: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[Any] = field(default_factory=list)  # list[Hypothesis] — type hint elided to avoid cycle
    primitive_status: dict[str, str] = field(default_factory=dict)  # primitive_id → PASS/ADVISORY/CONCERN/CRITICAL/HYPOTHESIS/NOT_ASSESSED
    metadata: dict[str, Any] = field(default_factory=dict)
    terminate_reason: str = ""


@dataclass
class SpiralResult:
    """Final result of a spiral run."""

    iterations_used: int
    termination_reason: str  # "sufficient" | "max_iterations" | "irreducible_blocker"
    findings: list[dict[str, Any]]
    hypotheses: list[Any]
    primitive_status: dict[str, str]
    metadata: dict[str, Any]


def run_spiral(
    *,
    repo_root: str,
    scope: str = "codebase",
    observe: Callable[[SpiralContext], None] | None = None,
    orient: Callable[[SpiralContext], None] | None = None,
    decide: Callable[[SpiralContext], None] | None = None,
    act: Callable[[SpiralContext], bool] | None = None,
    hypothesise: Callable[[SpiralContext], None] | None = None,
    max_iterations: int = 3,
) -> SpiralResult:
    """Run an OODA spiral with the given phase callables.

    Each phase callable receives the shared SpiralContext and mutates it.
    The `act` callable returns True if termination should be considered
    (i.e., no more productive work in this iteration).

    Args:
        repo_root: target repo path
        scope: scope arg passed through to consumers (codebase / pr / auto)
        observe: reconnaissance phase
        orient: triage + depth phase
        decide: cross-primitive chaining phase
        act: fix-as-you-go OR record-and-advance phase; returns True if no more work
        hypothesise: optional hypothesis-formation phase (for manual primitives)
        max_iterations: termination cap

    Returns:
        SpiralResult capturing the accumulated state.
    """
    ctx = SpiralContext(repo_root=repo_root, scope=scope, max_iterations=max_iterations)

    for iteration in range(1, max_iterations + 1):
        ctx.iteration = iteration

        if observe is not None:
            observe(ctx)
        if orient is not None:
            orient(ctx)
        if decide is not None:
            decide(ctx)
        if act is not None:
            done = act(ctx)
            if done:
                ctx.terminate_reason = "sufficient"
                break
        else:
            # No act phase = single-pass spiral
            ctx.terminate_reason = "sufficient"
            break
    else:
        ctx.terminate_reason = "max_iterations"

    if hypothesise is not None:
        hypothesise(ctx)

    return SpiralResult(
        iterations_used=ctx.iteration,
        termination_reason=ctx.terminate_reason,
        findings=ctx.findings,
        hypotheses=ctx.hypotheses,
        primitive_status=ctx.primitive_status,
        metadata=ctx.metadata,
    )
