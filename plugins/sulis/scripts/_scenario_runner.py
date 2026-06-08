"""Scenario runner core — execute a Scenario's journey, aggregate a verdict.

Composes the runtime (WP-001 `resolve_journey`) + the dispatcher (WP-002
`execute_step`): walk the journey, run each step against a target, fold the
per-step outcomes into one per-Scenario verdict + a founder-legible summary.

Verdict precedence (worst-wins): fail > unresolved > deferred > manual-pending
> pass. So the DoD gate (WP-005) treats only `pass` as done-qualifying, and a
`deferred` surfaces its recorded need rather than faking green.

Beside that disposition, the runner carries two further signals (WP-004):
  * `isolation_rung` — the state-isolation rung the run used (ADR-002). The
    pure core RECORDS the requested rung (`reset` default | `process` | `env`);
    the process/env EXECUTION is adapter-level wiring in the executable, never
    pulled into this pure folder (ADR-002 Form rule).
  * `invariant_result` — an `observed | blocked | ""` verdict over the REAL
    saved record (ADR-003), produced by the pure `evaluate_invariant`. It is
    DISTINCT from the disposition: a run can be disposition-`pass` yet
    invariant-`blocked` (steps ran clean, the saved data was wrong) — exactly
    the find-one-fix-one failure this substrate exists to surface. The field
    #95's seam-DoD gate reads (contract: verdict-invariant.contract.md).

This is the unit-pure core (transports injected). The `sulis-verify-acceptance`
executable wraps it with graph-I/O (load the Scenario + its journey from the
brain), the standup recipe (WP-003), and real httpx/subprocess.

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from _scenario_dispatch import execute_step
from _scenario_runtime import _entity_id, resolve_journey

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
    verdict: str  # pass | fail | deferred | manual-pending (run disposition)
    steps: list = field(default_factory=list)  # [{name,status,detail,need}]
    # WP-004 additions — distinct from the disposition (ADR-002/ADR-003):
    isolation_rung: str = "reset"             # the rung used this run (ADR-002)
    invariant_result: str = ""                # observed | blocked | "" (ADR-003)
    tiers: dict = field(default_factory=dict)  # step-name → tier, for the report

    @property
    def needs(self) -> list:
        return [s["need"] for s in self.steps if s.get("need")]


# --- Verdict-invariant evaluator (ADR-003) ---------------------------------
# The cheapest-sufficient default + a hard ceiling so a misauthored `property`
# poll cannot spin. `attempts` default 1 means "no poll" (a single check); the
# ceiling clamps any over-large authored value.
_POLL_ATTEMPTS_DEFAULT = 1
_POLL_ATTEMPTS_MAX = 10  # hard ceiling enforced in code, not just documented

_ISOLATION_DEFAULT = "reset"


def _resolve_record(saved_record):
    """A saved record may be a plain value or a zero-arg fetcher (for polling a
    timing/ordering seam where the real record appears after a write settles).
    Resolve it to the current value. Pure given a pure fetcher; the runner
    passes the real captured record (or a fetcher that re-reads it)."""
    if callable(saved_record):
        return saved_record()
    return saved_record


def _matches(expected, record) -> bool:
    """`property` shape match: every key/value in `expected` is present and
    equal in `record` (a record matching shape X appeared). `equality` reuses
    plain `==` instead — see `evaluate_invariant`."""
    if not isinstance(record, dict) or not isinstance(expected, dict):
        return expected == record
    return all(record.get(k) == v for k, v in expected.items())


def evaluate_invariant(
    invariant: dict | None,
    saved_record,
    *,
    sleep: Callable[[float], None] | None = None,
) -> str:
    """Evaluate a Scenario's `verdict_invariant` over the REAL saved record.

    Returns `observed | blocked | ""` (never a hang, never a fake pass):
      * `None`/empty invariant → `""` (no invariant declared).
      * `kind=equality` → `observed` iff the saved record equals the expected
        shape, else `blocked`.
      * `kind=property` → `observed` if a record matching the expected shape
        appears, else a BOUNDED poll (default `attempts=1` = no poll; a hard
        max clamps an over-large value; fixed interval); poll exhausted →
        `blocked`.

    Pure: no IO. `sleep` is injected (default a no-op) so unit tests never wait;
    the executable injects `time.sleep`. The expected shape is read from the
    invariant's `expected` (the resolved value) — `expected_ref` is the
    authored ref the executable resolves before calling this evaluator.
    """
    if not invariant:
        return ""
    kind = invariant.get("kind")
    expected = invariant.get("expected")
    sleep = sleep or (lambda _secs: None)

    if kind == "equality":
        return "observed" if _resolve_record(saved_record) == expected else "blocked"

    if kind == "property":
        poll = invariant.get("poll") or {}
        attempts = int(poll.get("attempts", _POLL_ATTEMPTS_DEFAULT))
        # Clamp to [1, hard max] so a misauthored scenario cannot spin.
        attempts = max(1, min(attempts, _POLL_ATTEMPTS_MAX))
        interval_s = max(0, int(poll.get("interval_ms", 0))) / 1000.0
        for attempt in range(attempts):
            if _matches(expected, _resolve_record(saved_record)):
                return "observed"
            if attempt < attempts - 1:
                sleep(interval_s)
        return "blocked"

    # An unrecognised kind is not a pass — surface it honestly as blocked.
    return "blocked"


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
    browser=None,
) -> AcceptanceResult:
    """Resolve + execute a Scenario's journey; return the aggregated result.

    Journey-internal data-flow: an artifact a step lists in ``input_artifacts``
    that an *earlier* step in the same journey produced (its
    ``output_artifacts``) — or the ``test-target`` entry seed — is inherently
    available; it isn't an external need. Only artifacts that are neither
    caller-supplied (``available_artifacts``) nor journey-produced defer a step
    (``_scenario_dispatch``). Without this, every multi-step authored journey
    would defer on its own data-flow chain.
    """
    resolved = resolve_journey(scenario, workflow, steps_by_id, tools_by_id)
    step_rows: list = []
    tiers: dict = {}
    worst_idx = len(_PRECEDENCE)  # start more-benign than "pass"
    # The journey's own produced/seed artifacts, accumulated as we go. The
    # authoring assembler seeds the first step from ``test-target`` (the entry
    # point), so it's available to that first step.
    produced: set = {"test-target"}
    # The REAL saved record the verdict-invariant evaluates (ADR-003): the last
    # non-None record captured across the journey — the final artifact crossing
    # the seam. Never synthesised; stays None if no step produced one.
    saved_record = None
    for rs in resolved:
        outcome = execute_step(
            rs, base_url=target_base_url,
            available_artifacts=frozenset(available_artifacts) | produced,
            http=http, run=run, browser=browser,
        )
        produced.update(rs.output_artifacts)
        step_rows.append({
            "name": rs.name, "status": outcome.status,
            "detail": outcome.detail, "need": outcome.need,
        })
        # Surface the per-step tier (ADR-001) for the run report.
        if outcome.tier:
            tiers[rs.name] = outcome.tier
        if outcome.saved_record is not None:
            saved_record = outcome.saved_record
        if outcome.status in _PRECEDENCE:
            worst_idx = min(worst_idx, _PRECEDENCE.index(outcome.status))

    worst = _PRECEDENCE[worst_idx] if worst_idx < len(_PRECEDENCE) else "pass"
    # Isolation rung: the pure core records the requested rung (default
    # cheapest-sufficient `reset`); process/env EXECUTION is adapter-level
    # (ADR-002). An unknown declared value is recorded verbatim for auditability.
    isolation_rung = str(scenario.get("isolation") or _ISOLATION_DEFAULT)
    # Verdict-invariant over the REAL saved record (ADR-003), distinct from the
    # worst-wins disposition above and never substituted for it.
    invariant_result = evaluate_invariant(scenario.get("verdict_invariant"), saved_record)
    return AcceptanceResult(
        scenario_id=_entity_id(scenario),
        scenario_name=scenario.get("name", _entity_id(scenario)),
        verdict=_VERDICT_LABEL.get(worst, "pass"),
        steps=step_rows,
        isolation_rung=isolation_rung,
        invariant_result=invariant_result,
        tiers=tiers,
    )


def run_bundle(
    bundle: dict,
    *,
    target_base_url: str = "",
    available_artifacts=frozenset(),
    http=None,
    run=None,
    browser=None,
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
        http=http, run=run, browser=browser,
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
