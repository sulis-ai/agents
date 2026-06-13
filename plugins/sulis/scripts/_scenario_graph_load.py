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

Read split (ADR-001 / WP-002): the foundation library and the captures come
from DIFFERENT roots. `product-development/*` (the Scenario, step 1) is read
from the **captures root** (`base_dir`, owned by `brain_base_dir`). The
`foundation/workflow|step|tool` library (steps 2-3 + tools) is read from the
read-only, plugin-relative **library root** (`LIBRARY_ROOT`) — derived the same
way the compiled schemas already ship plugin-relative. The two are unioned with
the **captures root winning** on collision, so a fresh install with an empty
captures root still loads the shipped library by construction. Pass
`library_root=None` to collapse back to a single-root read.

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from _entity_adapter_local import LocalFileEntityAdapter

_SCRIPTS_DIR: Final[Path] = Path(__file__).resolve().parent

# The read-only, plugin-relative LIBRARY ROOT (ADR-001 / WP-002).
#
# The shipped `foundation/workflow|step|tool` library is read from where it
# ships with the plugin, derived the SAME way `_entity_adapter_local`'s
# `_DEFAULT_SCHEMAS_DIR` derives the compiled-schemas dir — anchored at
# `Path(__file__).parent`, not at the captures location. This mirrors the
# existing, proven schema/instance separation: definitions ship plugin-relative
# and are read independent of the captures `base_dir`. We extend that exact
# pattern to library *instances*.
#
# A fresh install therefore loads the shipped library by construction (any
# install that has the plugin has the library) with no install-time seeding,
# while `brain_base_dir` remains the single source of truth for the *captures*
# location — the library root is a separate, fixed, read-only constant, not a
# competing "location". Defined ONCE here; no hard-coded `.brain` path strings
# elsewhere in the read path.
LIBRARY_ROOT: Final[Path] = _SCRIPTS_DIR.parent.parent.parent / ".brain" / "instances"


class JourneyNotFound(Exception):
    """The Scenario, or its journey Workflow, isn't in the brain store."""


@dataclass
class LoadedJourney:
    scenario: dict
    workflow: dict
    steps_by_name: dict = field(default_factory=dict)   # Step.name → Step entity
    tools_by_id: dict = field(default_factory=dict)      # Tool.id → Tool entity
    missing_steps: list = field(default_factory=list)    # workflow.steps names absent from the store


def _index_steps_in_one_root(base_dir: Path, foundation_domain: str) -> dict:
    """Index every Step under a SINGLE root by `name`. Names are globally unique
    (the assembler namespaces them), so this is an unambiguous name → entity
    map. A missing root yields an empty index."""
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


def _index_steps_by_name(
    base_dir: Path,
    foundation_domain: str,
    *,
    library_root: Path | None = None,
) -> dict:
    """Index Steps by `name`, unioning the captures root with the library root.

    Per ADR-001 the read is the union of the captures root (`base_dir`, the live
    record) and the read-only library root (where the shipped foundation library
    lives, plugin-relative). On a name collision the **captures root wins** — it
    is the live record; the library is the immutable shipped baseline that must
    never shadow a capture. In practice the two are disjoint (the library ships
    the foundation steps; captures hold `product-development/*`), so the
    collision case is defensive, not expected.
    """
    index = _index_steps_in_one_root(library_root, foundation_domain) if library_root else {}
    # Captures-win: overlay the captures index on top of the library baseline.
    index.update(_index_steps_in_one_root(base_dir, foundation_domain))
    return index


def _find_foundation_entity(
    captures: LocalFileEntityAdapter,
    library: LocalFileEntityAdapter | None,
    entity_type: str,
    entity_id: str,
) -> dict | None:
    """Resolve a foundation entity, captures-root first then library root.

    ADR-001 precedence: the captures root wins on id collision (it is the live
    record); the library root is the read-only shipped baseline, consulted only
    when the captures root does not carry the id. Either lookup returning None
    falls through to the next root; both missing → None.

    Takes pre-built adapters so a single `load_scenario_journey` call constructs
    each root's foundation adapter ONCE and reuses it across the workflow lookup
    and every tool lookup, rather than re-constructing per resolution.
    """
    found = captures.find_by_id(entity_type, entity_id)
    if found is not None:
        return found
    if library is not None:
        return library.find_by_id(entity_type, entity_id)
    return None


def load_scenario_journey(
    base_dir: Path,
    scenario_id: str,
    *,
    library_root: Path | None = LIBRARY_ROOT,
    pd_domain: str = "product-development",
    foundation_domain: str = "foundation",
) -> LoadedJourney:
    """Load a Scenario + its journey Workflow + Steps + referenced Tools.

    The read is split across two roots (ADR-001 / WP-002):

    - **Captures root** (`base_dir`): the live record — `product-development/*`
      (the Scenario) and any captured foundation records. Owned by
      `brain_base_dir`; this function does not resolve the captures location, it
      reads from the `base_dir` the caller hands it.
    - **Library root** (`library_root`, default `LIBRARY_ROOT`): the read-only,
      plugin-relative shipped `foundation/workflow|step|tool` library. The
      Scenario's journey Workflow, its Steps, and their Tools resolve from here
      when the captures root does not carry them — so a fresh install (empty
      captures) still loads the shipped library by construction.

    Union is by entity id / Step name with the **captures root winning** on
    collision (the live record never shadowed by the immutable baseline). Pass
    `library_root=None` to read from a single root (the historical behaviour).

    Raises `JourneyNotFound` if the Scenario, or its journey Workflow, is in
    neither root. Returns the pieces `run_scenario` consumes (steps keyed by
    name, tools keyed by id), plus any `missing_steps` (drift)."""
    product = LocalFileEntityAdapter(base_dir=Path(base_dir), domain=pd_domain)

    scenario = product.find_by_id("scenario", scenario_id)
    if scenario is None:
        raise JourneyNotFound(f"no Scenario {scenario_id} in the brain store at {base_dir}")

    # Build each root's foundation adapter ONCE; reused for the workflow lookup
    # and every tool lookup below (captures-win precedence in
    # `_find_foundation_entity`).
    captures_foundation = LocalFileEntityAdapter(
        base_dir=Path(base_dir), domain=foundation_domain
    )
    library_foundation = (
        LocalFileEntityAdapter(base_dir=Path(library_root), domain=foundation_domain)
        if library_root is not None
        else None
    )

    journey_ref = scenario.get("journey")
    workflow = (
        _find_foundation_entity(
            captures_foundation, library_foundation, "workflow", journey_ref
        )
        if journey_ref
        else None
    )
    if workflow is None:
        raise JourneyNotFound(
            f"Scenario {scenario_id} references journey {journey_ref!r}, "
            "which isn't in the brain store"
        )

    name_index = _index_steps_by_name(
        Path(base_dir), foundation_domain, library_root=library_root
    )
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
            tool = _find_foundation_entity(
                captures_foundation, library_foundation, "tool", ref
            )
            if tool is not None:
                tools_by_id[ref] = tool

    return LoadedJourney(
        scenario=scenario,
        workflow=workflow,
        steps_by_name=steps_by_name,
        tools_by_id=tools_by_id,
        missing_steps=missing,
    )
