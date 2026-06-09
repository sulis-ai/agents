"""The seam-close DoD gate decision (#95).

A **pure decision** over fixture-able inputs: given a just-``done`` WP id, the
INDEX dependency graph, and the brain store, decide whether a *seam* just
closed, resolve that seam to its covering Scenarios through the requirement
bridge (ADR-004), drive those Scenarios via the injected runner, and fold the
per-Scenario verdicts into ``observed`` / ``blocked`` / ``not-closed``.

**Observed-or-blocked discipline.** This gate reuses ``_acceptance_gate``'s
``gate_decision`` *verbatim* — there is no second copy of the observed-or-blocked
rule. A closing seam is ``observed`` only when its covering Scenarios drove the
real data across the seam (an ``equality`` or ``property`` verdict over the real
saved record, both fold to ``pass`` at the gate). A ``deferred`` Scenario (the
real outcome was never driven) is ``blocked`` by default — escapable only by a
conscious, recorded ``--allow-deferred`` (``allow_deferred=True`` here →
``require_observed=False`` at ``gate_decision``), identical discipline to the
ship gate. A ``fail`` / ``manual-pending`` Scenario is ``blocked``.

**No-coverage is blocked and DISTINCT from deferred (ADR-005).** A closing seam
with *no* covering Scenario at all short-circuits to ``blocked`` *before*
``gate_decision`` is reached — there are no results to fold. Its founder-English
reason reads "this seam has no end-to-end check — nothing drove the real data
across it", which is deliberately distinct from the deferred "couldn't run"
wording: no-coverage means there is nothing to drive; deferred means there was a
Scenario that couldn't be driven for real.

**Degrade-open on detection, never fabricate green.** If the gate cannot
*determine* whether a seam closed (malformed INDEX, missing WP row), it returns
``not-closed`` with a "couldn't evaluate the seam at <title>" reason and never
fabricates ``observed``. A seam that *is* closed but whose Scenario can't be
driven is ``blocked`` (the observed-or-blocked rule), not a silent skip.

**Open Question 2 — known degradation.** The once-fired guard uses the brain
evidence (``find_passing_testresults_for_scenario``) as the single source of the
"already driven" signal — the same source ``_verify_scenario_coverage`` uses; no
bespoke per-seam marker competes with it. Consequence: under
``--no-emit-evidence`` the once-fired signal is absent, so a settled seam may
re-drive — wasteful, never wrong; no bespoke marker is kept (the brain evidence
is the single source).

**Form (pure).** The module owns no I/O of its own. It reads through the
existing query seams (``_brain_query``, the ``_wpxlib`` INDEX parser) and invokes
the *injected* ``run_scenario`` callable; the default ``run_scenario`` (the only
place a subprocess appears) shells ``sulis-verify-acceptance`` and is overridable
so tests stub the decision/I-O seam. The dependency direction is inward/sideways
only (ADR-003 §Consequences): the hook (``wpx-step12``) calls *into* this module;
this module never imports ``wpx-step12``, ``wpx-train``, or the skills.

Stdlib + the four reused modules (``_acceptance_gate``, ``_brain_query``,
``_wpxlib``, ``_scenario_runner``) only. Python 3.11-safe. No third-party imports.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import _brain_query
from _acceptance_gate import format_gate_message, gate_decision
from _scenario_runner import AcceptanceResult
from _wpxlib import parse_index_md

# The INDEX `Kind` column lands in WPRow.extras under this header (it is a
# non-standard column the `_wpxlib` parser tolerates and stashes verbatim).
_KIND_KEY = "Kind"
# A WP that closes a seam by itself when it reaches `done` (CF-07 integration
# child). `produces: integration-check` is the same signal carried on the row.
_INTEGRATION_KINDS = {"composite"}
_DONE_STATUS = "done"
# Wall-clock bound on the default scenario runner subprocess. The gate fires at
# every seam-closing WP done-transition (build-loop machinery), so an unbounded
# runner call would hang the whole transition indefinitely on a stuck runner. On
# timeout, `subprocess.run` raises `TimeoutExpired`, which propagates to the
# wpx-step12 machinery wrapper's degrade-open catch → `not-closed` + a
# `gate_error` naming the timeout (never a fabricated green or block). Generous
# (10 min) so a legitimately slow scripted scenario is not false-timed-out.
_RUNNER_TIMEOUT_SECONDS = 600


@dataclass
class SeamCloseResult:
    verdict: str  # "observed" | "blocked" | "not-closed"
    seam_title: str
    reason: str
    blocking: list = field(default_factory=list)
    deferred_needs: list = field(default_factory=list)
    drove_scenarios: list = field(default_factory=list)


def _kind(row) -> str:
    """Read a WPRow's `kind` from the non-standard INDEX `Kind` column."""
    return (row.extras.get(_KIND_KEY, "") or "").strip().lower()


def _find_closed_seams(rows_by_id: dict, just_done_wp: str) -> list:
    """Return the contract WP ids whose seam the just-`done` WP just closed.

    A seam is rooted at a `kind: contract` WP. The just-`done` WP closes a seam
    when either (1) it is itself an integration/`kind: composite` WP that
    `dependsOn` a contract root, or (2) it is part of a contract root's fan-out
    (`dependsOn` it) and that contract WP + ALL WPs that `dependsOn` it are now
    `done`. Returns the contract roots whose seam is fully closed.
    """
    # `evaluate` guarantees the just-done WP row exists before calling here.
    just = rows_by_id[just_done_wp]

    # Contract roots this WP transitively dependsOn (one hop is the CF-05 shape:
    # producer/consumer/integration WPs dependsOn the contract WP directly).
    contract_roots = [
        dep for dep in just.depends_on
        if dep in rows_by_id and _kind(rows_by_id[dep]) == "contract"
    ]

    closed: list = []
    for root_id in contract_roots:
        # Signal (1): the just-done WP is the integration/composite child.
        if _kind(just) in _INTEGRATION_KINDS:
            if root_id not in closed:
                closed.append(root_id)
            continue
        # Signal (2): contract root + ALL its dependants are done.
        dependants = [r for r in rows_by_id.values() if root_id in r.depends_on]
        root = rows_by_id[root_id]
        if root.status == _DONE_STATUS and all(
            d.status == _DONE_STATUS for d in dependants
        ):
            if root_id not in closed:
                closed.append(root_id)
    return closed


def _seam_requirements(
    root_id: str,
    root_row,
    *,
    implements: dict | None,
    brain_base_dir: Path,
) -> list:
    """Resolve the requirement ids a closing seam implements (ADR-004 bridge).

    First source: the contract WP's `implements: [dna:requirement:…]` — passed
    explicitly via the `implements` map, or read from the WP file frontmatter.
    Fallback (Open Question 1 resolution): the contract WP's `journey:` →
    `find_scenarios_for_journey`, taking the union of those Scenarios' `verifies`
    requirements. No backfill of legacy contract WPs.
    """
    if implements and root_id in implements:
        reqs = implements[root_id]
        if reqs:
            return list(reqs)

    journey = (root_row.extras.get("Journey") or root_row.extras.get("journey") or "").strip()
    if not journey:
        return []
    reqs: list = []
    for scen in _brain_query.find_scenarios_for_journey(brain_base_dir, journey):
        for req in scen.get("verifies", []) or []:
            if req not in reqs:
                reqs.append(req)
    return reqs


def _covering_scenarios(requirements: list, brain_base_dir: Path) -> list:
    """Union of covering Scenarios over the seam's requirements (de-duplicated
    by Scenario id), via the existing `find_scenarios_verifying` query only."""
    seen: set = set()
    scenarios: list = []
    for req in requirements:
        for scen in _brain_query.find_scenarios_verifying(brain_base_dir, req):
            sid = scen.get("id")
            if sid not in seen:
                seen.add(sid)
                scenarios.append(scen)
    return scenarios


def _default_run_scenario(scenario_id: str, *, repo_root: Path, **_kwargs) -> dict:  # pragma: no cover
    """Default runner: drive a Scenario for real via `sulis-verify-acceptance`.

    The one place a subprocess appears — the decision/I-O seam. Injectable (the
    `run_scenario` arg) so the unit tests stub it and never shell out; excluded
    from coverage by design (per the WP Notes: subprocess is the default
    `run_scenario`, injectable so tests stub it)."""
    proc = subprocess.run(
        [
            "sulis-verify-acceptance",
            "--scenario", scenario_id,
            "--target", "local",
            "--repo-root", str(repo_root),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=_RUNNER_TIMEOUT_SECONDS,
    )
    return json.loads(proc.stdout)


def _result_from_envelope(scenario: dict, envelope: dict) -> AcceptanceResult:
    """Map a runner JSON envelope onto the `AcceptanceResult` `gate_decision`
    consumes. The envelope's top-level `deferred_needs` ride into the result's
    steps as `need`s so `AcceptanceResult.needs` surfaces them to the gate."""
    needs = envelope.get("deferred_needs") or []
    steps = [{"name": "drive", "status": envelope.get("verdict", ""), "need": need}
             for need in needs]
    if not steps:
        steps = list(envelope.get("steps") or [])
    return AcceptanceResult(
        scenario_id=envelope.get("scenario") or scenario.get("id", ""),
        scenario_name=scenario.get("name", scenario.get("id", "")),
        verdict=envelope.get("verdict", ""),
        steps=steps,
    )


def _no_coverage_reason(seam_title: str) -> str:
    """ADR-005: distinct from the deferred 'couldn't run' wording."""
    return (
        f"The seam \"{seam_title}\" has no end-to-end check — "
        "nothing drove the real data across it."
    )


def _couldnt_evaluate_reason(just_done_wp_title: str) -> str:
    """Degrade-open detection failure — never fabricates green."""
    return (
        f"Couldn't evaluate the seam at \"{just_done_wp_title}\" — "
        "the work-package index couldn't be read for this transition."
    )


def evaluate(
    just_done_wp,
    *,
    index_path,
    brain_base_dir,
    repo_root,
    allow_deferred: bool = False,
    run_scenario=None,
    implements: dict | None = None,
) -> SeamCloseResult:
    """Decide whether a just-`done` WP closed a seam, and the seam's verdict.

    Returns a `SeamCloseResult` with `verdict` in `observed` / `blocked` /
    `not-closed`. See the module docstring for the full discipline.
    """
    index_path = Path(index_path)
    brain_base_dir = Path(brain_base_dir)
    repo_root = Path(repo_root)
    if run_scenario is None:  # pragma: no cover - the injected-I/O seam default
        run_scenario = lambda sid, **kw: _default_run_scenario(  # noqa: E731
            sid, repo_root=repo_root, **kw
        )

    # ── Detect (degrade-open: a bad INDEX/missing row never fabricates green) ──
    try:
        rows = parse_index_md(index_path)
    except (OSError, ValueError):
        rows = []
    rows_by_id = {r.id: r for r in rows}

    just = rows_by_id.get(str(just_done_wp))
    if just is None:
        # Missing WP row: undeterminable detection → not-closed, couldn't-evaluate.
        return SeamCloseResult(
            verdict="not-closed",
            seam_title="",
            reason=_couldnt_evaluate_reason(str(just_done_wp)),
        )

    closed_roots = _find_closed_seams(rows_by_id, str(just_done_wp))
    if not closed_roots:
        # Part of no seam → silent no-op (the common single-kind case).
        return SeamCloseResult(verdict="not-closed", seam_title="", reason="")

    # One seam per closing transition in the tested decompositions; evaluate the
    # first closed root (the contract WP rooting this seam).
    root_id = closed_roots[0]
    root_row = rows_by_id[root_id]
    seam_title = root_row.title

    requirements = _seam_requirements(
        root_id, root_row, implements=implements, brain_base_dir=brain_base_dir
    )
    scenarios = _covering_scenarios(requirements, brain_base_dir)

    # ── No-coverage → blocked, distinct from deferred (ADR-005). Short-circuit
    #    BEFORE driving / gate_decision: there is nothing to drive or fold. ──
    if not scenarios:
        return SeamCloseResult(
            verdict="blocked",
            seam_title=seam_title,
            reason=_no_coverage_reason(seam_title),
        )

    # ── Once-fired guard: a Scenario already observed-green by brain evidence is
    #    not re-driven (Open Question 2). All already-green → observed, no drive. ──
    to_drive = [
        scen for scen in scenarios
        if not _brain_query.find_passing_testresults_for_scenario(
            brain_base_dir, scen.get("id")
        )
    ]
    if not to_drive:
        return SeamCloseResult(
            verdict="observed",
            seam_title=seam_title,
            reason="✓ Done — every check passed against a standing app.",
            drove_scenarios=[],
        )

    # ── Drive + fold through the REUSED gate_decision (no second copy of the
    #    observed-or-blocked rule). ──
    results: list = []
    drove: list = []
    for scen in to_drive:
        envelope = run_scenario(scen.get("id"))
        drove.append(scen.get("id"))
        results.append(_result_from_envelope(scen, envelope))

    decision = gate_decision(results, require_observed=not allow_deferred)
    verdict = "observed" if decision.verdict == "pass" else "blocked"
    reason = _founder_reason(seam_title, decision)
    return SeamCloseResult(
        verdict=verdict,
        seam_title=seam_title,
        reason=reason,
        blocking=decision.blocking,
        deferred_needs=decision.deferred_needs,
        drove_scenarios=drove,
    )


def _founder_reason(seam_title: str, decision) -> str:
    """The single founder-English builder for a driven seam (reused for every
    driven path). Names the seam by its human title and strips operator
    vocabulary — `dna:` ids and `WP-` ids never leak into the founder line.

    `format_gate_message` is reused verbatim for the per-scenario block lines;
    we prepend the seam's human title so the founder reads which seam.
    """
    body = format_gate_message(decision)
    return f"Seam \"{seam_title}\":\n{body}"
