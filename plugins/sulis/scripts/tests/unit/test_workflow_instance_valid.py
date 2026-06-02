"""
test_workflow_instance_valid - WP-001

Validates that `plugins/sulis/instances/release-train/workflow.jsonld`:

1. Parses as JSON-LD with the expected envelope shape.
2. Validates against the vendored foundation Workflow schema
   (v1.1.0) at
   `plugins/sulis/brain/compiled/foundation/workflow.schema.json`.
3. Carries the canonical workflow ULID
   (dna:workflow:01KT0RTRA1NWFW00000000000A) - established by prior
   waves; every Trigger + Step in the canonical entity graph already
   references this exact ULID.
4. Carries the canonical marketplace tenant ULID
   (dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM) on `for_domain` -
   cross-WP consistency with WP-002..006.
5. The `steps[]` array contains every Step name authored in
   steps.jsonld, in canonical order (10 Steps — trunk re-model, WP-001).
6. `initial_steps` is exactly ["detect-pending-changesets"] and
   `terminal_steps` includes "emit-release-entity" and
   "gate-founder-confirmation".
7. Every transition references either a Step name in `steps[]` or a
   `[terminal:<verdict>]` shorthand whose verdict is in
   {shipped, no-changesets, blocked, aborted}.
8. `state_contract` enumerates every variable declared in the WP
   Contract.
9. `for_process` == "release-train" (cross-Step consistency).
10. The transition graph is strictly linear — the JT-7 back-edge
    (`wait-for-checks-and-mergeability -> open-release-pr`) and every
    promotion/PR edge are GONE (trunk re-model, WP-001).

Tests are deterministic + offline. Schemas come from the vendored
brain/compiled directory; the instance comes from the release-train
instances directory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


_REPO_ROOT = Path(__file__).resolve().parents[5]
_INSTANCE_PATH = (
    _REPO_ROOT / "plugins" / "sulis" / "instances" / "release-train" / "workflow.jsonld"
)
_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "foundation"
    / "workflow.schema.json"
)
_STEPS_PATH = (
    _REPO_ROOT / "plugins" / "sulis" / "instances" / "release-train" / "steps.jsonld"
)

# Canonical cross-WP ULIDs - established by prior waves
# (WP-002..006). Drift in any of these breaks the canonical entity
# graph; the drift detector (WP-007) will fail. These MUST be the
# values minted here.
_CANONICAL_WORKFLOW_ULID = "dna:workflow:01KT0RTRA1NWFW00000000000A"
_CANONICAL_TENANT_ULID = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"

# The 10 kept Step names in canonical (linear) order (trunk re-model,
# WP-001). The workflow.steps[] array MUST match.
_EXPECTED_STEP_NAMES = [
    "detect-pending-changesets",  # 1
    "preflight-version-drift",  # 2
    "compute-next-version",  # 3
    "gate-founder-confirmation",  # 4
    "bump-version-files",  # 5
    "write-changelog-entry",  # 6
    "commit-bump-on-main",  # 7
    "tag-and-push",  # 8
    "publish-github-release",  # 9
    "emit-release-entity",  # 10
]

# Permitted terminal verdicts referenced in transitions
# `[terminal:<verdict>]`. Per WP Contract `final-outcome` enum.
_PERMITTED_TERMINAL_VERDICTS = {
    "shipped",
    "no-changesets",
    "blocked",
    "aborted",
}

# Variables that MUST appear in state_contract per the WP Contract.
_REQUIRED_STATE_VARIABLES = {
    "target_branch",
    "source_branch",
    "pending_changesets",
    "tier",
    "next_plugin_version",
    "next_umbrella_version",
    "pr_url",
    "merge_sha",
    "tag_pushed",
    "release_url",
    "final-outcome",
}

# Pattern matching a `[terminal:<verdict>]` reference inside a
# transitions string. Verdict is captured.
_TERMINAL_RE = re.compile(r"\[terminal:([a-z\-]+)\]")

# Pattern matching the LHS or RHS of a transition: a Step name (lowercase
# kebab) before/after the ` -> ` arrow.
_TRANSITION_RE = re.compile(
    r"^(?P<lhs>[a-z][a-z0-9\-]*)\s*->\s*(?P<rhs>.+?)(?:\s*\[.*\])?\s*$"
)


# ----- fixtures -----


@pytest.fixture(scope="module")
def envelope() -> dict:
    """The parsed workflow.jsonld envelope."""
    assert _INSTANCE_PATH.exists(), (
        f"workflow.jsonld missing at {_INSTANCE_PATH}; WP-001 must author it"
    )
    with _INSTANCE_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def workflow(envelope: dict) -> dict:
    """The single Workflow entity inside the envelope's
    `workflows[]` array (envelope-shaped, parallel to triggers.jsonld
    + steps.jsonld + tools.jsonld + failuremodes.jsonld).
    """
    workflows = envelope.get("workflows")
    assert isinstance(workflows, list), (
        f"workflow.jsonld envelope must carry a `workflows` list; "
        f"got {type(workflows).__name__}"
    )
    assert len(workflows) == 1, (
        f"expected exactly one Workflow in the envelope; got {len(workflows)}"
    )
    return workflows[0]


@pytest.fixture(scope="module")
def schema() -> dict:
    """The vendored foundation Workflow schema (v1.1.0)."""
    assert _SCHEMA_PATH.exists(), (
        f"foundation Workflow schema missing at {_SCHEMA_PATH}; "
        "expected vendored copy alongside actor/credential/tenant/"
        "failuremode/trigger/tool/step"
    )
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def step_names_from_steps_jsonld() -> list[str]:
    """The ordered list of Step names authored in WP-002."""
    assert _STEPS_PATH.exists(), (
        f"steps.jsonld missing at {_STEPS_PATH}; WP-002 must be done "
        "before WP-001 (Workflow.steps[] cross-ref)"
    )
    with _STEPS_PATH.open() as f:
        env = json.load(f)
    return [s["name"] for s in env["steps"]]


# ----- Test #1 - JSON-LD parses with expected envelope shape -----


def test_workflow_jsonld_parses_envelope(envelope: dict) -> None:
    """The file is well-formed JSON-LD with the expected envelope
    shape. Mirrors steps.jsonld / triggers.jsonld / tools.jsonld /
    failuremodes.jsonld.
    """
    assert "@context" in envelope
    assert "@id" in envelope
    assert envelope["@id"] == "dna:release-train:workflow"
    assert "@type" in envelope
    assert envelope["@type"] == "workflow-instances"
    assert envelope.get("for_tenant") == _CANONICAL_TENANT_ULID
    assert "captured_on" in envelope
    assert "workflows" in envelope
    assert isinstance(envelope["workflows"], list)


# ----- Test #2 - Workflow passes brain Workflow schema -----


def test_workflow_passes_brain_schema(workflow: dict, schema: dict) -> None:
    """The Workflow entity validates against the foundation Workflow
    schema (v1.1.0).
    """
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(workflow), key=lambda e: list(e.path))
    formatted = [f"{list(e.path)}: {e.message}" for e in errors]
    assert not errors, f"schema validation failed: {json.dumps(formatted, indent=2)}"


# ----- Test #3 - canonical workflow ULID matches -----


def test_canonical_workflow_ulid_matches(workflow: dict) -> None:
    """The Workflow.id MUST be the deterministic ULID established
    by prior waves (WP-003 Triggers + WP-002 Steps reference it
    exactly). Drift here breaks the entity graph; the drift detector
    (WP-007) will catch the mismatch.
    """
    assert workflow.get("id") == _CANONICAL_WORKFLOW_ULID, (
        f"Workflow.id mismatch: got {workflow.get('id')!r}, "
        f"expected {_CANONICAL_WORKFLOW_ULID!r}"
    )


# ----- Test #4 - canonical tenant ULID on for_domain -----


def test_canonical_tenant_ulid_for_domain(workflow: dict) -> None:
    """`for_domain` MUST be the canonical marketplace tenant ULID.
    Cross-WP consistency check; identical to the value used by every
    Step / Trigger / FailureMode / Tool.
    """
    assert workflow.get("for_domain") == _CANONICAL_TENANT_ULID, (
        f"Workflow.for_domain mismatch: got "
        f"{workflow.get('for_domain')!r}, expected "
        f"{_CANONICAL_TENANT_ULID!r}"
    )


# ----- Test #5 - steps[] matches steps.jsonld names + order -----


def test_workflow_steps_list_matches_steps_jsonld(
    workflow: dict, step_names_from_steps_jsonld: list[str]
) -> None:
    """Workflow.steps[] MUST list every Step name authored in
    steps.jsonld, in canonical order (10 Steps — trunk re-model). This
    is the cross-reference the drift detector (WP-007) enforces.
    """
    actual = workflow.get("steps", [])
    assert actual == _EXPECTED_STEP_NAMES, (
        f"Workflow.steps[] mismatch.\n"
        f"got:      {actual}\n"
        f"expected: {_EXPECTED_STEP_NAMES}"
    )
    # Also confirm the WP-002 authored names match the WP-001 contract
    # names (a Five-Whys upstream guard - if WP-002 drifted, surface
    # the mismatch here rather than silently passing).
    assert step_names_from_steps_jsonld == _EXPECTED_STEP_NAMES, (
        f"WP-002 steps.jsonld names drifted from WP-001 contract.\n"
        f"steps.jsonld: {step_names_from_steps_jsonld}\n"
        f"expected:     {_EXPECTED_STEP_NAMES}"
    )


# ----- Test #6 - initial_steps + terminal_steps canonical -----


def test_initial_and_terminal_steps_canonical(workflow: dict) -> None:
    """`initial_steps` MUST be exactly ['detect-pending-changesets']
    (single entry point per WP Contract). `terminal_steps` MUST
    include 'emit-release-entity' (happy-path terminal) and
    'gate-founder-confirmation' (founder-aborted terminal per WP
    Contract — the gate is a terminal node because confirm=no exits).
    """
    initial = workflow.get("initial_steps", [])
    assert initial == ["detect-pending-changesets"], (
        f"initial_steps mismatch: got {initial}, expected ['detect-pending-changesets']"
    )
    terminal = set(workflow.get("terminal_steps", []))
    assert "emit-release-entity" in terminal, (
        f"terminal_steps missing 'emit-release-entity'; got {sorted(terminal)}"
    )
    assert "gate-founder-confirmation" in terminal, (
        f"terminal_steps missing 'gate-founder-confirmation'; got {sorted(terminal)}"
    )


# ----- Test #7 - transitions reference only valid Step names or terminals -----


def test_transitions_reference_only_valid_step_names_and_terminals(
    workflow: dict,
) -> None:
    """Every transition's LHS resolves to a Step name in steps[];
    every transition's RHS resolves to a Step name OR a
    `[terminal:<verdict>]` whose verdict is in
    {shipped, no-changesets, blocked, aborted}.
    """
    step_set = set(workflow.get("steps", []))
    transitions = workflow.get("transitions", [])
    assert transitions, "transitions must be non-empty"

    bad: list[str] = []
    for raw in transitions:
        m = _TRANSITION_RE.match(raw)
        assert m is not None, f"transition does not parse: {raw!r}"
        lhs = m.group("lhs")
        rhs_raw = m.group("rhs").strip()
        # Strip a trailing `[if ...]` guard.
        rhs_clean = re.sub(r"\s*\[if[^\]]*\]\s*$", "", rhs_raw).strip()

        if lhs not in step_set:
            bad.append(f"unknown LHS step {lhs!r} in transition: {raw!r}")
            continue

        # RHS may be a Step name OR a [terminal:<verdict>] shorthand
        if rhs_clean.startswith("[terminal:"):
            tm = _TERMINAL_RE.match(rhs_clean)
            if tm is None:
                bad.append(f"unparseable terminal shorthand: {raw!r}")
                continue
            verdict = tm.group(1)
            if verdict not in _PERMITTED_TERMINAL_VERDICTS:
                bad.append(
                    f"terminal verdict {verdict!r} not in "
                    f"{sorted(_PERMITTED_TERMINAL_VERDICTS)}: {raw!r}"
                )
        else:
            if rhs_clean not in step_set:
                bad.append(f"unknown RHS step {rhs_clean!r} in transition: {raw!r}")

    assert not bad, "transition validation failed:\n" + "\n".join(bad)


# ----- Test #8 - state_contract enumerates required variables -----


def test_state_contract_enumerated(workflow: dict) -> None:
    """state_contract MUST declare every variable from the WP
    Contract.  Entries are `name:type` strings; we check the name
    prefix only.
    """
    raw = workflow.get("state_contract", [])
    assert raw, "state_contract must be non-empty"
    names = {entry.split(":", 1)[0] for entry in raw}
    missing = _REQUIRED_STATE_VARIABLES - names
    assert not missing, (
        f"state_contract missing required variables: {sorted(missing)}. "
        f"Got: {sorted(names)}"
    )


# ----- Test #9 - for_process is 'release-train' -----


def test_for_process_is_release_train(workflow: dict) -> None:
    """`for_process` MUST be 'release-train' - matches every Step's
    for_process for cross-WP consistency.
    """
    assert workflow.get("for_process") == "release-train", (
        f"for_process mismatch: got {workflow.get('for_process')!r}, "
        f"expected 'release-train'"
    )


# ----- Test #10 - graph is strictly linear; no back-edge / promotion edges -----


def test_no_back_edge_or_promotion_edges(workflow: dict) -> None:
    """Trunk re-model (WP-001): the JT-7 back-edge
    (`wait-for-checks-and-mergeability -> open-release-pr`) and EVERY
    promotion/PR transition are gone. No transition may reference any of
    the 5 deleted dev->main-PR Steps. The path is strictly linear over
    the 10 kept Steps (plus terminals).
    """
    deleted = {
        "preflight-cross-branch-drift",
        "draft-pr-body-and-changelog",
        "open-release-pr",
        "wait-for-checks-and-mergeability",
        "squash-merge",
    }
    transitions = workflow.get("transitions", [])
    joined = "\n".join(transitions)
    leaked = [name for name in deleted if name in joined]
    assert not leaked, (
        f"transitions still reference deleted dev->main-PR Steps {leaked} — "
        f"the JT-7 back-edge / promotion edges must be removed on the trunk.\n"
        f"transitions:\n{joined}"
    )
