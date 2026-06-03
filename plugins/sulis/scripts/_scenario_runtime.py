"""Scenario runtime spine — resolve a Scenario's journey into ordered,
driver-mapped steps ready for execution.

A ``Scenario`` (brain entity) carries ``journey → Workflow``; the Workflow is a
graph of IDEF0 ``Step``s. To automate the Scenario, each Step must resolve to a
concrete DRIVER — taken from the Step's ``Tool.implementation_kind`` (the
existing enum). ``mechanism: human`` steps resolve to the human-checklist
driver rather than an automated one.

This module is the PURE resolution core (WP-001): it walks the journey and maps
drivers. Execution against a standing app (httpx / subprocess / agent) is WP-002
(the dispatcher) + WP-004 (the runner). Operating on entity dicts keeps it
unit-pure and free of graph-I/O.

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The Tool.implementation_kind enum (foundation Tool schema) — the automatable
# drivers. Kept here for reference + validation; the dispatcher (WP-002) owns
# the actual driver implementations.
IMPLEMENTATION_KINDS: frozenset[str] = frozenset(
    {
        "mcp_server",
        "subprocess",
        "python_import",
        "http_call",
        "claude_code_tool",
        "skill_invocation",
        "workflow_dispatch",
    }
)

# A ``mechanism: human`` step is surfaced as a manual checklist item, never
# automated. A step that names no resolvable tool (and isn't human) cannot yet
# be run — flagged so the runner reports it rather than silently skipping.
HUMAN_DRIVER = "human"
UNRESOLVED_DRIVER = "unresolved"


def _entity_id(entity: dict) -> str:
    """An entity's identity, tolerant of both conventions: brain-store entities
    use ``id`` (the canonical ULID ref); the v1 hand-built bundles use the
    JSON-LD ``@id``. Prefer ``id``, fall back to ``@id``, else empty."""
    return str(entity.get("id") or entity.get("@id") or "")


@dataclass
class ResolvedStep:
    """One journey step, resolved to its driver + carrying its IDEF0 fields."""

    step_id: str
    name: str
    driver: str
    mechanism: str
    tool_ref: str | None = None
    input_artifacts: list = field(default_factory=list)
    controls: list = field(default_factory=list)
    preconditions: list = field(default_factory=list)
    postconditions: list = field(default_factory=list)
    agent_instructions: str = ""
    # Driver-specific executable params (a JSON blob the dispatcher parses):
    # http_call → {"method","path","expect_status"}; subprocess → {"cmd","expect_exit"}.
    mechanism_detail: str = ""


def driver_for_step(step: dict, tools_by_id: dict) -> str:
    """Resolve the driver for one Step.

    Precedence: ``mechanism: human`` → the human-checklist driver (regardless of
    any tool_ref); else the referenced Tool's ``implementation_kind``; else
    ``UNRESOLVED_DRIVER`` (no tool, or an unknown tool_ref).
    """
    if str(step.get("mechanism", "")).strip().lower() == "human":
        return HUMAN_DRIVER
    tool_ref = step.get("tool_ref")
    if tool_ref and tool_ref in tools_by_id:
        kind = tools_by_id[tool_ref].get("implementation_kind")
        return kind if kind in IMPLEMENTATION_KINDS else UNRESOLVED_DRIVER
    return UNRESOLVED_DRIVER


def resolve_journey(
    scenario: dict,
    workflow: dict,
    steps_by_id: dict,
    tools_by_id: dict,
) -> list[ResolvedStep]:
    """Order a Scenario's journey Workflow steps and resolve each to a driver.

    v1 ordering: the Workflow's ``steps`` array order (a linear journey).
    Graph/transition traversal (cycles, guards) is a later refinement; the
    ``steps`` order is the contract for now.
    """
    ordered_ids = workflow.get("steps", []) or []
    resolved: list[ResolvedStep] = []
    for sid in ordered_ids:
        step = steps_by_id.get(sid)
        if step is None:
            # A dangling step ref is a drift/integrity problem (WP-006 catches
            # it pre-run); surface it as an unresolved placeholder rather than
            # dropping it silently.
            resolved.append(
                ResolvedStep(step_id=sid, name=sid, driver=UNRESOLVED_DRIVER,
                             mechanism="")
            )
            continue
        resolved.append(
            ResolvedStep(
                step_id=_entity_id(step) or sid,
                name=step.get("name", sid),
                driver=driver_for_step(step, tools_by_id),
                mechanism=str(step.get("mechanism", "")),
                tool_ref=step.get("tool_ref"),
                input_artifacts=list(step.get("input_artifacts", []) or []),
                controls=list(step.get("controls", []) or []),
                preconditions=list(step.get("preconditions", []) or []),
                postconditions=list(step.get("postconditions", []) or []),
                agent_instructions=str(step.get("agent_instructions", "") or ""),
                mechanism_detail=str(step.get("mechanism_detail", "") or ""),
            )
        )
    return resolved
