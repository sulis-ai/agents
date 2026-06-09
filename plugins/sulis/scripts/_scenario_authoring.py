"""Scenario-authoring assembler — the `/sulis:specify` intake mechanism.

A founder authors a verification journey in PLAIN ENGLISH (numbered steps,
drafted from the SRD's acceptance criteria). This module turns that into the
IDEF0 graph underneath — a `Scenario` + a `Workflow` + its `Step`s — that the
founder never has to see. The plain-English instruction lands in
`Step.agent_instructions`; the founder's "see X" checks become
`Step.postconditions`. Founder-authored journeys default to `mechanism: human`
(run by hand); a real `tool_ref` is wired later when the journey is automated.

Output is the bundle shape the ingest emitters consume:
`{"scenarios": [...], "workflows": [...], "steps": [...]}` — feed each list to
`sulis-emit-{scenario,workflow,step}` (or the in-process emitters).

The schema constraints this honours (all verified against the compiled schemas):
  - Workflow references its steps by `Step.name` (slug), NOT by ULID.
  - `Step.input_artifacts` / `output_artifacts` are `minItems:1`.
  - `Workflow.transitions` is `minItems:1` (a 1-step journey gets a terminal
    sentinel edge `"<step> -> end"`).
  - `unevaluatedProperties:false` everywhere — emit ONLY schema-defined keys.
  - Verification discriminator: `Workflow.type = "review"` +
    `for_process = "verification"` (no new enum member — see the #65 checkpoint).
"""

from __future__ import annotations

import hashlib
import re
from typing import Final

_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # no I/L/O/U

# The consumer surfaces a scenario can exercise (ADR-005, FR-10). A closed
# enum: a typo'd surface is a bug, not a third surface, so reject it at
# authoring rather than persist a tag the brain schema would later refuse.
_SURFACES: Final[frozenset[str]] = frozenset({"ui", "tool"})


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def _slugify(text: str, *, index: int) -> str:
    """A readable, unique step slug used as `Step.name` (and referenced by the
    Workflow). Lowercase, alphanumeric-and-hyphen, truncated, index-suffixed so
    two similarly-worded steps don't collide."""
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40].strip("-")
    return f"{base or 'step'}-{index + 1}"


def assemble_scenario_graph(
    *,
    name: str,
    verifies: list[str],
    exercises: str,
    tenant: str,
    seed: str,
    steps: list[dict],
    surface: str = "ui",
    require_verifiable: bool = True,
) -> dict:
    """Assemble a plain-English journey into a Scenario + Workflow + Steps.

    Args:
        name: the scenario's human name (e.g. "A user can pay with a saved card").
        verifies: ≥1 `dna:requirement:<ulid>` refs the scenario proves.
        exercises: the `dna:design:<ulid>` ref it runs against.
        tenant: the owning `dna:tenant:<ulid>` (Step/Workflow `for_domain`).
        seed: a stable string for deterministic ULIDs (idempotent re-author).
        surface: the consumer surface this scenario exercises — ``"ui"`` (the
            default) or ``"tool"`` (ADR-005, FR-10). Persisted first-class on
            the Scenario node so the verification set can be partitioned by
            surface. Additive-optional: it does NOT feed any ULID seed, so the
            same ``seed`` yields the same scenario id with or without a surface
            (NFR-05). A surface outside the closed ``{ui, tool}`` enum is a
            typo, not a third surface, and raises ``ValueError`` at authoring.
        steps: ordered journey beats, each a dict:
            {"instruction": str,                 # plain-English; → agent_instructions
             "asserts": list[str] = [],          # "see X" checks → postconditions
             "mechanism": str = "human",         # deterministic|probabilistic|human|mixed
             "tool_ref": str | None = None,      # dna:tool:<ulid> when automated
             "mechanism_detail": str | None = None,  # JSON driver params:
                                                  #   subprocess → {"cmd","expect_exit"}
                                                  #   http_call  → {"method","path","expect_status"}
             "input_artifacts": list[str] = []}  # EXTRA external needs (credentials/
                                                  #   fixtures) beyond the data-flow chain
        require_verifiable: when True (the default), the journey MUST be
            verifiable — at least one beat carries an observable check
            (``asserts``) AND the final (outcome) beat carries one. A journey
            with no checks, or whose outcome isn't observable, can report green
            while the feature is broken (the green-but-broken-login class
            journey-rigor #5 closes). Pass False only for structural tests of
            properties orthogonal to verifiability.

    Returns the emitter-ready bundle: {"scenarios", "workflows", "steps"}.

    Data-flow vs needs: the first beat's ``input_artifacts`` seeds from
    ``test-target`` and each subsequent beat consumes the previous beat's
    ``output_artifacts`` — the IDEF0 data-flow chain (also what satisfies the
    Step schema's ``input_artifacts`` minItems:1). The runner recognises an
    artifact produced by an earlier step in the same journey as available
    (``_scenario_runner``), so the chain doesn't defer a runnable journey. A
    beat that needs a genuinely-external artifact (a credential) declares it via
    ``input_artifacts``; that one isn't journey-produced, so the runner surfaces
    it as a deferred need rather than faking green.
    """
    if not steps:
        raise ValueError("a scenario journey needs at least one step")

    if surface not in _SURFACES:
        raise ValueError(
            f"surface must be one of {sorted(_SURFACES)} (ADR-005); got "
            f"{surface!r}. The surface tag is a closed enum — a value outside "
            "it is a typo, not a third consumer surface."
        )

    # Verifiability gate (journey-rigor #5). A *verification* journey that
    # carries no observable check is just a description of clicks — it can pass
    # while the feature is broken. The outcome (final beat) MUST be provable, or
    # the whole journey proves nothing. This is the "verifiable at specify"
    # mechanical tooth: a journey can't be authored unverifiable.
    if require_verifiable:
        total_asserts = sum(len(beat.get("asserts") or []) for beat in steps)
        if total_asserts == 0:
            raise ValueError(
                "a verification journey needs at least one observable check — "
                "every journey must carry an 'asserts' entry (what the user "
                "should see / what proves it worked). A journey with no checks "
                "can report green while the feature is broken."
            )
        if not (steps[-1].get("asserts") or []):
            raise ValueError(
                "the outcome of a verification journey must be observable — the "
                "final step needs an 'asserts' entry (what proves the journey "
                "succeeded). Without it the journey can pass while the feature "
                "is broken."
            )

    # Step names are the linkage the Workflow uses (workflow.steps holds
    # Step.name slugs, not ULIDs) — and the flat brain store keys files by
    # ULID, so reconstructing a journey from the store resolves those names
    # back to Step entities. Names MUST therefore be globally unique, or a
    # name lookup could match a different scenario's step. Namespace every
    # name with a journey-stable prefix derived from the seed.
    namespace = _ulid(f"{seed}:journey-namespace")[:8].lower()

    step_entities: list[dict] = []
    prev_output = ["test-target"]
    for i, beat in enumerate(steps):
        instruction = beat["instruction"]
        slug = f"{namespace}-{_slugify(instruction, index=i)}"
        output = [f"{slug}-result"]
        # input_artifacts = the data-flow chain (previous beat's output, or the
        # test-target seed for the first beat) PLUS any beat-declared external
        # needs. The data-flow part is journey-produced (the runner treats it as
        # available); a declared external need is not, so it surfaces if absent.
        needs = list(prev_output) + list(beat.get("input_artifacts") or [])
        step: dict = {
            "id": f"dna:step:{_ulid(f'{seed}:step:{i}')}",
            "name": slug,
            "for_domain": tenant,
            "input_artifacts": needs,
            "output_artifacts": output,
            "mechanism": beat.get("mechanism", "human"),
            "agent_instructions": instruction,
            "for_process": "verification",
            "state": "draft",
            "sys_status": "active",
        }
        asserts = beat.get("asserts") or []
        if asserts:
            step["postconditions"] = list(asserts)
        tool_ref = beat.get("tool_ref")
        if tool_ref:
            step["tool_ref"] = tool_ref
        # The driver params (subprocess cmd / http_call path) — carried through
        # so the runner can actually execute the step. The runtime reads this
        # off the stored Step (_scenario_runtime), the dispatcher parses it as
        # the driver's JSON params (_scenario_dispatch).
        mechanism_detail = beat.get("mechanism_detail")
        if mechanism_detail:
            step["mechanism_detail"] = mechanism_detail
        step_entities.append(step)
        prev_output = output

    names = [s["name"] for s in step_entities]
    transitions = [f"{names[i]} -> {names[i + 1]}" for i in range(len(names) - 1)]
    if not transitions:  # single-step journey — satisfy transitions minItems:1
        transitions = [f"{names[0]} -> end"]

    workflow_id = f"dna:workflow:{_ulid(f'{seed}:workflow')}"
    workflow: dict = {
        "id": workflow_id,
        "name": name,
        "for_domain": tenant,
        "type": "review",                 # verification journeys reuse the review bucket
        "for_process": "verification",    # the real discriminator (#65 checkpoint)
        "steps": names,
        "initial_steps": [names[0]],
        "terminal_steps": [names[-1]],
        "transitions": transitions,
        "state": "draft",
        "sys_status": "active",
    }

    scenario: dict = {
        "id": f"dna:scenario:{_ulid(f'{seed}:scenario')}",
        "name": name,
        "verifies": list(verifies),
        "exercises": exercises,
        "journey": workflow_id,
        "surface": surface,
        "state": "draft",
        "sys_status": "active",
    }

    return {"scenarios": [scenario], "workflows": [workflow], "steps": step_entities}


def repoint_scenarios_exercises(bundle: dict, design_id: str) -> dict:
    """Resolve the specify-time synthetic Design placeholder once the real
    Design exists.

    At `/sulis:specify` a scenario's ``exercises`` is a synthetic
    ``dna:design:<ulid>`` placeholder (no Design entity exists yet). When the
    design stage emits the change's real Design, this re-points every scenario
    in the bundle at it — a change produces one Design that all its scenarios
    exercise, so the mapping is unambiguous. Uses the REAL emitted id (not a
    recomputation of the path-derived id), so it can't drift on a path-string
    mismatch. Returns a new bundle; inputs are not mutated.
    """
    if not design_id:
        raise ValueError("design_id is required to re-point scenarios")
    scenarios = [{**s, "exercises": design_id} for s in (bundle.get("scenarios") or [])]
    return {**bundle, "scenarios": scenarios}
