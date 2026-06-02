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

import pytest

from _scenario_runtime import (
    HUMAN_DRIVER,
    UNRESOLVED_DRIVER,
    driver_for_step,
    resolve_journey,
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
