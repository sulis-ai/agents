"""Scenario runner core — execute a Scenario's journey, aggregate a verdict.

Composes the runtime (WP-001 `resolve_journey`) + the dispatcher (WP-002
`execute_step`): walk the journey, run each step against a target, fold the
per-step outcomes into one per-Scenario verdict + a founder-legible summary.

Verdict precedence (worst-wins): fail > unresolved > deferred > manual-pending
> pass. So the DoD gate (WP-005) treats only `pass` as done-qualifying, and a
`deferred` surfaces its recorded need rather than faking green.

This is the unit-pure core (transports injected). The `sulis-verify-acceptance`
executable wraps it with graph-I/O (load the Scenario + its journey from the
brain), the standup recipe (WP-003), and real httpx/subprocess.

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from _scenario_dispatch import execute_step
from _scenario_runtime import resolve_journey

# worst-wins ordering for folding step statuses into a scenario verdict
_PRECEDENCE = ["fail", "unresolved", "deferred", "manual", "pass"]
# step-status → scenario-verdict label
_VERDICT_LABEL = {
    "fail": "fail",
    "unresolved": "fail",       # an unresolvable step is a real problem, not a pass
    "deferred": "deferred",
    "manual": "manual-pending",
    "pass": "pass",
}


@dataclass
class AcceptanceResult:
    scenario_id: str
    scenario_name: str
    verdict: str  # pass | fail | deferred | manual-pending
    steps: list = field(default_factory=list)  # [{name,status,detail,need}]

    @property
    def needs(self) -> list:
        return [s["need"] for s in self.steps if s.get("need")]


def run_scenario(
    scenario: dict,
    workflow: dict,
    steps_by_id: dict,
    tools_by_id: dict,
    *,
    target_base_url: str = "",
    available_artifacts=frozenset(),
    http=None,
    run=None,
) -> AcceptanceResult:
    """Resolve + execute a Scenario's journey; return the aggregated result."""
    resolved = resolve_journey(scenario, workflow, steps_by_id, tools_by_id)
    step_rows: list = []
    worst_idx = len(_PRECEDENCE)  # start more-benign than "pass"
    for rs in resolved:
        outcome = execute_step(
            rs, base_url=target_base_url,
            available_artifacts=available_artifacts, http=http, run=run,
        )
        step_rows.append({
            "name": rs.name, "status": outcome.status,
            "detail": outcome.detail, "need": outcome.need,
        })
        if outcome.status in _PRECEDENCE:
            worst_idx = min(worst_idx, _PRECEDENCE.index(outcome.status))

    worst = _PRECEDENCE[worst_idx] if worst_idx < len(_PRECEDENCE) else "pass"
    return AcceptanceResult(
        scenario_id=scenario.get("@id", ""),
        scenario_name=scenario.get("name", scenario.get("@id", "")),
        verdict=_VERDICT_LABEL.get(worst, "pass"),
        steps=step_rows,
    )


def run_bundle(
    bundle: dict,
    *,
    target_base_url: str = "",
    available_artifacts=frozenset(),
    http=None,
    run=None,
) -> AcceptanceResult:
    """Run a self-contained Scenario bundle — ``{scenario, workflow, steps[],
    tools[]}`` — the input shape the `sulis-verify-acceptance` CLI loads. (Once
    a Scenario-from-source emitter exists, the CLI will load these from the
    brain graph instead; the bundle is the v1 input.)"""
    steps_by_id = {s.get("@id"): s for s in (bundle.get("steps") or [])}
    tools_by_id = {t.get("@id"): t for t in (bundle.get("tools") or [])}
    return run_scenario(
        bundle["scenario"], bundle["workflow"], steps_by_id, tools_by_id,
        target_base_url=target_base_url, available_artifacts=available_artifacts,
        http=http, run=run,
    )


_GLYPH = {"pass": "✓", "fail": "✗", "deferred": "⏸", "manual-pending": "◻"}


def format_founder_summary(result: AcceptanceResult) -> str:
    """Plain green/red a non-technical founder reads — the scenario line + any
    non-passing step (with the deferred need named)."""
    glyph = _GLYPH.get(result.verdict, "•")
    lines = [f"{glyph} {result.scenario_name} — {result.verdict}"]
    for s in result.steps:
        if s["status"] != "pass":
            g = {"fail": "  ✗", "deferred": "  ⏸", "manual": "  ◻",
                 "unresolved": "  ⚠"}.get(s["status"], "  •")
            tail = f" (needs {s['need']})" if s.get("need") else ""
            lines.append(f"{g} {s['name']}: {s['status']}{tail}")
    return "\n".join(lines)
