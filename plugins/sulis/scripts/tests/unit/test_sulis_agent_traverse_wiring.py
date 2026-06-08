"""Wiring tests for the Sulis agent's FR-08 traverse + ADR-004 analyst routing.

WP-012 (REORGANISE-Refactor, the only internal-code edit in this change). The
agent body `plugins/sulis/agents/sulis.md` gains two additive routing
capabilities, proved here against the REAL agent file (MEA-09 / TDD §10.2 —
characterise against reality, not a fixture):

  1. Conversational traverse (FR-08, NFR-02): the founder asks "what's open /
     deferred / on the roadmap / state of the requirements" and the agent
     answers inline off the brain graph by calling the `sulis-brain-query`
     seam (WP-008's `--open|--roadmap|--done` modes) — explicitly distinct from
     the change-store views (`/sulis:dashboard`, `/sulis:inbox`).
  2. Analyst recommendation (ADR-004): the `dispatch_via` block recommends
     `claude --agent opportunity-analyst`, byte-for-pattern identical to the
     existing `requirements-analyst` row.

The third test re-asserts the WP-012 characterisation snapshot post-edit (the
existing routes survived) — the EP-07 "confirm still passes" half. It defers to
the single characterisation authority in `test_route_inventory.py` so there is
one snapshot definition, not two that can drift.
"""

from __future__ import annotations

from pathlib import Path

from _route_frontmatter import parse_frontmatter

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SULIS_AGENT = _REPO_ROOT / "plugins" / "sulis" / "agents" / "sulis.md"


def _read_agent() -> str:
    """The raw text of the live orchestrator agent body."""
    return _SULIS_AGENT.read_text(encoding="utf-8")


# --- FR-08: conversational traverse answers "what's open" off the brain ------


def test_agent_answers_whats_open_off_brain():
    """The body carries a routing capability mapping "what's open"-class founder
    intent to the brain query seam (`sulis-brain-query`), NOT the change-store.

    FR-08 / NFR-02: the founder need not remember a command; "what's open / on
    the roadmap / state of the requirements" is answered inline off the brain
    graph. The seam is WP-008's `sulis-brain-query` with the `--open` /
    `--roadmap` / `--done` modes; the answer is rendered in founder English and
    is explicitly distinct from `/sulis:dashboard` + `/sulis:inbox` (which read
    the change-store, a different surface).
    """
    body = _read_agent()

    # The seam the capability calls (WP-008) — named so the routing is concrete.
    assert "sulis-brain-query" in body, (
        "FR-08 traverse capability must call the sulis-brain-query seam"
    )
    # The founder-facing query verbs (the FR-07 vocabulary the modes expose).
    for flag in ("--open", "--roadmap", "--done"):
        assert flag in body, f"traverse capability must reference the {flag} mode"

    # At least one of the founder-intent trigger phrases the capability matches.
    lowered = body.lower()
    assert any(
        phrase in lowered
        for phrase in ("what's open", "whats open", "on the roadmap", "what's deferred")
    ), "traverse capability must name the founder-intent trigger phrases"

    # Explicitly distinct from the change-store surfaces (the WP Contract's
    # disambiguation requirement: the brain backlog is NOT the change dashboard).
    assert "/sulis:dashboard" in body and "/sulis:inbox" in body, (
        "the traverse capability must distinguish the brain graph from the "
        "change-store dashboard/inbox"
    )


# --- ADR-004: recommend the opportunity-analyst, mirroring requirements ------


def test_agent_recommends_opportunity_analyst():
    """The `dispatch_via` block contains the opportunity-analyst recommendation
    row, byte-for-pattern identical in shape to the requirements-analyst row.

    ADR-004: the opportunity-analyst is a full facilitation agent (FR-11,
    "mirroring the requirements-analyst"); it is recommended via an agent
    invocation, never an in-process call. The row therefore reuses the existing
    `requirements-analyst` recommend-shape verbatim (the reuse mandate, EP-03 /
    CP-01).
    """
    body = _read_agent()

    # The new dispatch_via row, the exact recommend-shape of the sibling row.
    assert (
        'opportunity-analyst: ["recommend `claude --agent opportunity-analyst`"]'
        in body
    ), "dispatch_via must recommend `claude --agent opportunity-analyst` (ADR-004)"

    # It mirrors the requirements-analyst row byte-for-pattern (same recommend
    # verb, same `claude --agent <name>` shape) — proving the reuse, not a new
    # mechanism.
    assert (
        'requirements-analyst: ["recommend `claude --agent requirements-analyst`"]'
        in body
    ), "the requirements-analyst row (the mirrored convention) must be intact"

    # The analyst is enumerated as a known specialist (routes_to slug) so the
    # founder-intent trigger resolves through the same routing surface.
    mapping, _ = parse_frontmatter(body)
    routes_to = mapping.get("routes_to")
    assert isinstance(routes_to, list)
    slugs = {item.get("slug") for item in routes_to if isinstance(item, dict)}
    assert "opportunity-analyst" in slugs, (
        "opportunity-analyst must be a known specialist in routes_to"
    )


# --- EP-07 second half: the existing routes survived the additive edit -------


def test_existing_routes_still_present_after_edit():
    """Re-assert the WP-012 characterisation snapshot AFTER the edit.

    EP-07 discipline: characterise -> confirm passes -> edit -> confirm STILL
    passes. The snapshot authority lives once in
    `test_route_inventory.test_existing_dispatch_routes_preserved`; this test
    invokes it so there is a single snapshot definition (no drift) and the
    "survived the edit" assertion is co-located with the FR-08 wiring tests it
    protects.
    """
    from unit.test_route_inventory import test_existing_dispatch_routes_preserved

    # Runs the same characterisation assertions against the (now-edited) agent.
    test_existing_dispatch_routes_preserved()
