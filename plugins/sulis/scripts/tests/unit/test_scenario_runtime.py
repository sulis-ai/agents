"""WP-001 (testable-state-done) — the Scenario runtime spine.

A `Scenario` (live brain entity) encapsulates a journey = a `Workflow` (a graph
of IDEF0 `Step`s). To AUTOMATE it, the runtime must (1) order the journey's
steps and (2) resolve each step to a concrete DRIVER via the step's
`Tool.implementation_kind` (the existing enum: http_call / subprocess /
python_import / mcp_server / claude_code_tool / skill_invocation /
workflow_dispatch), with `mechanism: human` steps surfaced as manual checklist
items rather than automated.

This WP is the pure resolution core (no execution yet — that's WP-002). It
operates on entity dicts (Scenario / Workflow / Step / Tool) so it is unit-pure.

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

from _scenario_runtime import (
    AGENT_STEP_KINDS,
    HUMAN_DRIVER,
    IMPLEMENTATION_KINDS,
    SCRIPTED_KINDS,
    UNRESOLVED_DRIVER,
    driver_for_step,
    resolve_journey,
    tier_for_kind,
)


# --- fixtures: a 3-step login journey -------------------------------------
_TOOLS = {
    "dna:tool:http": {"@id": "dna:tool:http", "implementation_kind": "http_call"},
    "dna:tool:browser": {"@id": "dna:tool:browser", "implementation_kind": "subprocess"},
}
_STEPS = {
    "dna:step:signup": {
        "@id": "dna:step:signup", "name": "POST /signup",
        "mechanism": "deterministic", "tool_ref": "dna:tool:http",
        "input_artifacts": ["a test email"],
        "postconditions": ["201 returned"],
    },
    "dna:step:submit": {
        "@id": "dna:step:submit", "name": "submit + assert session",
        "mechanism": "deterministic", "tool_ref": "dna:tool:browser",
        "postconditions": ["session cookie set"],
    },
    "dna:step:manual-check": {
        "@id": "dna:step:manual-check", "name": "eyeball the welcome email",
        "mechanism": "human",
    },
}
_WORKFLOW = {
    "@id": "dna:workflow:login-journey",
    "steps": ["dna:step:signup", "dna:step:submit", "dna:step:manual-check"],
}
_SCENARIO = {
    "@id": "dna:scenario:login",
    "name": "A new user can sign up and log in",
    "journey": "dna:workflow:login-journey",
    "verifies": ["dna:requirement:auth"],
    "exercises": "dna:design:auth-flow",
}


def test_resolve_journey_orders_steps_and_maps_drivers():
    resolved = resolve_journey(
        _SCENARIO, _WORKFLOW, _STEPS, _TOOLS,
    )
    assert [r.name for r in resolved] == [
        "POST /signup", "submit + assert session", "eyeball the welcome email",
    ]
    assert [r.driver for r in resolved] == ["http_call", "subprocess", HUMAN_DRIVER]


def test_resolved_step_carries_needs_and_asserts():
    resolved = resolve_journey(_SCENARIO, _WORKFLOW, _STEPS, _TOOLS)
    signup = resolved[0]
    assert signup.input_artifacts == ["a test email"]
    assert signup.postconditions == ["201 returned"]
    assert signup.mechanism == "deterministic"


def test_human_step_is_human_driver_regardless_of_tool():
    step = {"@id": "x", "name": "x", "mechanism": "human", "tool_ref": "dna:tool:http"}
    assert driver_for_step(step, _TOOLS) == HUMAN_DRIVER


def test_step_with_no_tool_and_not_human_is_unresolved():
    step = {"@id": "x", "name": "x", "mechanism": "deterministic"}
    assert driver_for_step(step, _TOOLS) == UNRESOLVED_DRIVER


def test_driver_reads_tool_implementation_kind():
    step = {"@id": "x", "name": "x", "mechanism": "deterministic", "tool_ref": "dna:tool:http"}
    assert driver_for_step(step, _TOOLS) == "http_call"


def test_unknown_tool_ref_is_unresolved():
    step = {"@id": "x", "name": "x", "mechanism": "deterministic", "tool_ref": "dna:tool:nope"}
    assert driver_for_step(step, _TOOLS) == UNRESOLVED_DRIVER


# --- WP-002: derived driver tier (ADR-001) --------------------------------
# The tier is a derived surfacing of implementation_kind, NOT a stored field:
#   scripted   = deterministic drivers (http_call, subprocess)
#   agent-step = probabilistic drivers (mcp_server, claude_code_tool,
#                skill_invocation) — declared here, executed in #92
#   ""         = python_import / workflow_dispatch / human / unresolved —
#                not the deterministic/probabilistic split, so no tier label.

def test_tier_for_kind_maps_every_kind():
    # Explicit expected label for every implementation_kind plus the two
    # non-tool drivers, per ADR-001's mapping.
    expected = {
        # scripted (deterministic)
        "http_call": "scripted",
        "subprocess": "scripted",
        # agent-step (probabilistic) — declared, executed in #92
        "mcp_server": "agent-step",
        "claude_code_tool": "agent-step",
        "skill_invocation": "agent-step",
        # no tier — not the deterministic/probabilistic split
        "python_import": "",
        "workflow_dispatch": "",
        HUMAN_DRIVER: "",
        UNRESOLVED_DRIVER: "",
    }
    for kind, tier in expected.items():
        assert tier_for_kind(kind) == tier, f"{kind} should map to {tier!r}"

    # Totality: every implementation_kind in the foundation enum is partitioned
    # into exactly one of the two tier frozensets, or is a deliberate "" kind.
    # A kind added to the enum later WITHOUT a tier decision is caught here.
    _NO_TIER_KINDS = {"python_import", "workflow_dispatch"}
    for kind in IMPLEMENTATION_KINDS:
        in_scripted = kind in SCRIPTED_KINDS
        in_agent = kind in AGENT_STEP_KINDS
        in_no_tier = kind in _NO_TIER_KINDS
        # exactly one bucket owns each kind
        assert (in_scripted + in_agent + in_no_tier) == 1, (
            f"{kind} must belong to exactly one tier bucket "
            f"(scripted/agent-step/no-tier); add it to the mapping"
        )
        # the bucket and tier_for_kind agree
        if in_scripted:
            assert tier_for_kind(kind) == "scripted"
        elif in_agent:
            assert tier_for_kind(kind) == "agent-step"
        else:
            assert tier_for_kind(kind) == ""

    # The two tier frozensets are disjoint.
    assert SCRIPTED_KINDS.isdisjoint(AGENT_STEP_KINDS)


def test_resolved_step_carries_tier():
    tools = {
        "dna:tool:http": {"@id": "dna:tool:http", "implementation_kind": "http_call"},
        "dna:tool:mcp": {"@id": "dna:tool:mcp", "implementation_kind": "mcp_server"},
    }
    steps = {
        "dna:step:api": {
            "@id": "dna:step:api", "name": "POST /thing",
            "mechanism": "deterministic", "tool_ref": "dna:tool:http",
        },
        "dna:step:agent": {
            "@id": "dna:step:agent", "name": "agent drives the browser",
            "mechanism": "probabilistic", "tool_ref": "dna:tool:mcp",
        },
    }
    workflow = {
        "@id": "dna:workflow:mixed",
        "steps": ["dna:step:api", "dna:step:agent"],
    }
    scenario = {"@id": "dna:scenario:mixed", "journey": "dna:workflow:mixed"}

    resolved = resolve_journey(scenario, workflow, steps, tools)
    by_name = {r.name: r for r in resolved}
    assert by_name["POST /thing"].tier == "scripted"
    assert by_name["agent drives the browser"].tier == "agent-step"
