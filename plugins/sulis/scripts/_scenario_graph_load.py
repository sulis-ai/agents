"""Load a Scenario's journey from the flat brain store (bundle-from-graph).

Closes the testable-state loop: instead of a hand-built `{scenario, workflow,
steps[], tools[]}` bundle, `sulis-verify-acceptance` loads the journey from the
emitted brain entities — the Scenario authored at `/sulis:specify` and emitted
by `sulis-author-scenario`.

Reconstruction, mirroring how the canonical instances co-locate a Workflow with
its Steps:

  1. find the Scenario by id            (product-development/scenario/{ulid})
  2. follow `scenario.journey`           → the Workflow (foundation/workflow/{ulid})
  3. resolve `workflow.steps` (NAMES)    → Step entities

Step (3) is the subtle part: `workflow.steps` holds Step *names* (slugs), but
the store keys files by ULID, so there is no `find_by_id` for a name. We index
the foundation `step` directory by name and pick the workflow's steps. This is
sound only because step names are GLOBALLY UNIQUE (the authoring assembler
namespaces them by journey seed) — otherwise a name could match a different
scenario's step. A `workflow.steps` name with no entity in the store is
surfaced in `missing_steps` (drift), never silently dropped.

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from _entity_adapter_local import LocalFileEntityAdapter


class JourneyNotFound(Exception):
    """The Scenario, or its journey Workflow, isn't in the brain store."""


@dataclass
class LoadedJourney:
    scenario: dict
    workflow: dict
    steps_by_name: dict = field(default_factory=dict)   # Step.name → Step entity
    tools_by_id: dict = field(default_factory=dict)      # Tool.id → Tool entity
    missing_steps: list = field(default_factory=list)    # workflow.steps names absent from the store


def _index_steps_by_name(base_dir: Path, foundation_domain: str) -> dict:
    """Index every emitted Step by `name`. Names are globally unique (the
    assembler namespaces them), so this is an unambiguous name → entity map."""
    step_dir = Path(base_dir) / foundation_domain / "step"
    index: dict = {}
    if not step_dir.is_dir():
        return index
    for path in sorted(step_dir.glob("*.jsonld")):
        try:
            step = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError, OSError):
            continue
        name = step.get("name")
        if name:
            index[name] = step
    return index


def load_scenario_journey(
    base_dir: Path,
    scenario_id: str,
    *,
    pd_domain: str = "product-development",
    foundation_domain: str = "foundation",
) -> LoadedJourney:
    """Load a Scenario + its journey Workflow + Steps + referenced Tools from the
    brain store. Raises `JourneyNotFound` if the Scenario or its Workflow is
    absent. Returns the pieces `run_scenario` consumes (steps keyed by name,
    tools keyed by id), plus any `missing_steps` (drift)."""
    product = LocalFileEntityAdapter(base_dir=Path(base_dir), domain=pd_domain)
    foundation = LocalFileEntityAdapter(base_dir=Path(base_dir), domain=foundation_domain)

    scenario = product.find_by_id("scenario", scenario_id)
    if scenario is None:
        raise JourneyNotFound(f"no Scenario {scenario_id} in the brain store at {base_dir}")

    journey_ref = scenario.get("journey")
    workflow = foundation.find_by_id("workflow", journey_ref) if journey_ref else None
    if workflow is None:
        raise JourneyNotFound(
            f"Scenario {scenario_id} references journey {journey_ref!r}, "
            "which isn't in the brain store"
        )

    name_index = _index_steps_by_name(Path(base_dir), foundation_domain)
    wanted = workflow.get("steps", []) or []
    steps_by_name: dict = {}
    missing: list = []
    for nm in wanted:
        step = name_index.get(nm)
        if step is None:
            missing.append(nm)
        else:
            steps_by_name[nm] = step

    tools_by_id: dict = {}
    for step in steps_by_name.values():
        ref = step.get("tool_ref")
        if ref and ref not in tools_by_id:
            tool = foundation.find_by_id("tool", ref)
            if tool is not None:
                tools_by_id[ref] = tool

    return LoadedJourney(
        scenario=scenario,
        workflow=workflow,
        steps_by_name=steps_by_name,
        tools_by_id=tools_by_id,
        missing_steps=missing,
    )
