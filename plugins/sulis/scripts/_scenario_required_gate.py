"""Scenario-required gate (#103) — a user-facing change MUST author verifiable
scenarios (or carry a logged explicit exemption) before it ships.

THE GAP THIS CLOSES: every scenario gate (design journey-walk #85, plan-work
coverage #86, ship acceptance #83/4.8) fired only *IF scenarios already
existed*. Nothing forced a user-facing change to author any — so a user-facing
change with zero scenarios sailed through every gate as "advisory / nothing to
verify". This gate flips the test from *exists* to *required*: it is the one
chokepoint that asks "is this change user-facing? then scenarios are REQUIRED
(or explicitly exempted)" and BLOCKS when they're missing.

It is deliberately conservative on the user-facing signal (reuses
``paths_touch_founder_surface`` — real UI paths: ``.tsx`` / ``/components/`` /
``/pages/`` / ``.html`` …), so it does NOT over-fire on tooling / plugin-
authoring / library changes (those are covered by unit tests; scenarios don't
apply). A user-facing surface with no journey to verify is the failure mode
this exists to catch.

Pure decision over (touched paths, scenarios-present, exemption). The ship flow
(/sulis:change ship gate 4.8) calls the CLI BEFORE the acceptance run and blocks
on ``verdict == "required_missing"``. Stdlib only. Python 3.11-safe.

Verdict → exit code (CLI):
  0 — ok                 (not user-facing → N/A; OR user-facing + scenarios present; OR exempted)
  1 — required_missing   (user-facing + zero scenarios + no exemption → BLOCK)
  3 — error              (bad input)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from _specify_classifier import paths_touch_founder_surface


# Path fragments that mark a NON-FUNCTIONAL-requirements artifact — when a
# change declares/modifies NFRs (cost, storage, latency, throughput,
# resumability, data integrity, …) it MUST make them verifiable too, not just
# user-facing UI (the Capsule-Clinics lesson: production mechanisms get stubbed
# because nothing forced a scenario that drives the real condition). A unit
# test can't prove "survives a 100 MB file" or "stays under the cost budget" —
# only a driven scenario can — so NFRs need scenarios MORE than UI, not less.
_NFR_SPEC_FRAGMENTS: tuple[str, ...] = (
    "nfr.md",
    "/nfr/",
    "/nfrs/",
    "non-functional",
    "nonfunctional",
    "non_functional",
)


def paths_declare_nfrs(paths: list[str]) -> bool:
    """True if any touched path is a non-functional-requirements artifact.

    Conservative substring match (e.g. ``.specifications/{p}/NFR.md``). A
    change that declares or edits NFRs is in scope for required scenarios."""
    for path in paths:
        low = path.lower()
        if any(frag in low for frag in _NFR_SPEC_FRAGMENTS):
            return True
    return False


@dataclass(frozen=True)
class ScenarioGateVerdict:
    """The gate's decision + the founder-English reason for it."""

    verdict: str               # "ok" | "required_missing"
    user_facing: bool
    nfr_scope: bool            # the change declares non-functional requirements
    scenarios_present: bool
    exempted: bool
    reason: str                # founder-readable
    exemption_reason: str | None = None


def scenario_gate(
    *,
    touched_paths: list[str],
    scenarios_present: bool,
    exemption_reason: str | None = None,
) -> ScenarioGateVerdict:
    """Decide whether a change may ship w.r.t. verifiable-scenario coverage.

    Scenarios are REQUIRED when the change is **user-facing** (UI surface) OR
    **declares non-functional requirements** (NFRs need a driven scenario — a
    unit test can't prove the real production condition). When required:

    - scenarios present → ``ok``.
    - no scenarios + a non-empty exemption reason → ``ok`` (the conscious,
      logged escape — rare, the founder owns it).
    - no scenarios + no exemption → ``required_missing`` (BLOCK).

    Not user-facing AND no NFRs → ``ok`` (tooling/library — unit tests cover it).
    """
    paths = list(touched_paths)
    user_facing = paths_touch_founder_surface(paths)
    nfr_scope = paths_declare_nfrs(paths)
    in_scope = user_facing or nfr_scope
    exempted = bool(exemption_reason and exemption_reason.strip())

    if not in_scope:
        return ScenarioGateVerdict(
            "ok", False, False, scenarios_present, exempted,
            "Not a user-facing surface and declares no non-functional "
            "requirements — verifiable scenarios are not required (covered by "
            "unit tests).",
        )
    if scenarios_present:
        return ScenarioGateVerdict(
            "ok", user_facing, nfr_scope, True, exempted,
            "Change in scope for verifiable scenarios, and scenarios are "
            "authored.",
        )
    if exempted:
        return ScenarioGateVerdict(
            "ok", user_facing, nfr_scope, False, True,
            "In scope for scenarios with none authored — explicitly exempted.",
            exemption_reason.strip(),
        )

    if user_facing and nfr_scope:
        trigger = "a user-visible surface and non-functional requirements"
    elif nfr_scope:
        trigger = ("non-functional requirements (e.g. cost / storage / "
                   "resilience / performance / data integrity)")
    else:
        trigger = "a user-visible surface"
    return ScenarioGateVerdict(
        "required_missing", user_facing, nfr_scope, False, False,
        f"This change touches {trigger} but has no verifiable scenarios. "
        "It must be testable — author the verification scenarios at specify "
        "(do X, observe Y), or record an explicit exemption with a reason. "
        "For non-functional requirements especially, a unit test can't prove "
        "the real condition (survives a large file, stays under budget, "
        "resumes after a crash) — only a driven scenario can.",
    )


# ─── presence + exemption detection (the inputs the CLI feeds the gate) ──────

def scenarios_present_for_change(repo_root: Path, stem: str) -> bool:
    """True if the change authored ≥1 verifiable scenario.

    Primary signal: the authored ``{repo_root}/.changes/{stem}.scenarios.jsonld``
    contains at least one Scenario node. The file is what specify (deep mode)
    writes; its presence-with-content is the durable "scenarios were authored"
    marker. Malformed / empty file → treated as absent (not present)."""
    f = repo_root / ".changes" / f"{stem}.scenarios.jsonld"
    if not f.exists():
        return False
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    if isinstance(data, dict):
        # Canonical authored shape (specify deep mode): a top-level
        # ``{"scenarios": [...]}`` list — scenario nodes here carry an
        # ``SC-NN`` id, not a ``dna:scenario:`` @id, so a non-empty list IS
        # "scenarios authored". Fall back to JSON-LD ``@graph`` / bare-list
        # shapes for files that use them.
        scen = data.get("scenarios")
        if isinstance(scen, list):
            return any(isinstance(n, dict) for n in scen)
        nodes = data.get("@graph", data)
    else:
        nodes = data
    if not isinstance(nodes, list):
        return False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ident = str(node.get("@id", node.get("id", "")))
        typ = node.get("@type", node.get("type", ""))
        typ_s = " ".join(typ) if isinstance(typ, list) else str(typ)
        if "scenario" in ident.lower() or "scenario" in typ_s.lower():
            return True
    return False


def exemption_reason_for_change(repo_root: Path, stem: str) -> str | None:
    """A logged exemption: the content of ``{repo_root}/.changes/{stem}
    .scenarios-exempt`` (a deliberate, auditable, committed marker), or None."""
    f = repo_root / ".changes" / f"{stem}.scenarios-exempt"
    if not f.exists():
        return None
    try:
        txt = f.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return txt or None
