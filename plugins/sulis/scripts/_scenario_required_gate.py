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


@dataclass(frozen=True)
class ScenarioGateVerdict:
    """The gate's decision + the founder-English reason for it."""

    verdict: str               # "ok" | "required_missing"
    user_facing: bool
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

    - Not user-facing → ``ok`` (scenarios don't apply; unit tests cover it).
    - User-facing + scenarios present → ``ok``.
    - User-facing + no scenarios + a non-empty exemption reason → ``ok`` (the
      conscious, logged escape — rare, the founder owns it).
    - User-facing + no scenarios + no exemption → ``required_missing`` (BLOCK).
    """
    user_facing = paths_touch_founder_surface(list(touched_paths))
    exempted = bool(exemption_reason and exemption_reason.strip())

    if not user_facing:
        return ScenarioGateVerdict(
            "ok", False, scenarios_present, exempted,
            "Not a user-facing surface — verifiable scenarios are not required "
            "(covered by unit tests).",
        )
    if scenarios_present:
        return ScenarioGateVerdict(
            "ok", True, True, exempted,
            "User-facing change with verifiable scenarios authored.",
        )
    if exempted:
        return ScenarioGateVerdict(
            "ok", True, False, True,
            "User-facing change with no scenarios — explicitly exempted.",
            exemption_reason.strip(),
        )
    return ScenarioGateVerdict(
        "required_missing", True, False, False,
        "This change touches a user-visible surface but has no verifiable "
        "scenarios. A user-facing journey must be testable — author the "
        "verification scenarios at specify (do X, observe Y), or record an "
        "explicit exemption with a reason.",
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
    nodes = data.get("@graph", data) if isinstance(data, dict) else data
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
