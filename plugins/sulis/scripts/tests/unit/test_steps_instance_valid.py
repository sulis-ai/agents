"""
test_steps_instance_valid - WP-002, re-pinned to the trunk shape by
WP-001 (CH-01KT4K, simplify-release-robot).

Validates that `plugins/sulis/instances/release-train/steps.jsonld`:

1. Parses as valid JSON-LD with the expected envelope shape.
2. Declares exactly 10 Step instances (trunk re-model — the 5
   dev->main-PR Steps deleted).
3. Each Step validates against the vendored foundation Step JSON
   Schema (v1.2.0) at
   `plugins/sulis/brain/compiled/foundation/step.schema.json`.
4. Every Step's `tool_ref` resolves to a Tool ID in WP-006's
   `tools.jsonld`.
5. Every Step's `handles_failures` entry resolves to a FailureMode
   ID in WP-004's `failuremodes.jsonld`.
6. Step names use kebab-case (Blue invariant - prevents naming
   drift as Steps accrete).
7. Every Step's `for_domain` is the canonical tenant ULID
   (cross-WP consistency with WP-003 + WP-004 + WP-006).
8. Every Step's `for_workflow` is the canonical workflow ULID
   (cross-WP consistency with WP-003).
9. `gate-founder-confirmation` has `mechanism: human` (the
   load-bearing founder gate; MUC-007).
10. The envelope carries `excluded_from_yaml` naming the 2 Steps
    that by design have no annotation in `release-on-merge.yml`
    (gate-founder-confirmation + publish-github-release).

Trunk re-model (WP-001): the probabilistic draft-pr-body-and-changelog
Step (the old Step 5 / NFR-010 token-budget surface) was deleted — there
is no probabilistic Step on the trunk; changelog drafting consolidates
into write-changelog-entry.

These tests are deliberately deterministic + offline - no network,
no LLM, no subprocess. Schemas come from the vendored
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
    _REPO_ROOT / "plugins" / "sulis" / "instances" / "release-train" / "steps.jsonld"
)
_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "foundation"
    / "step.schema.json"
)
_TOOLS_PATH = (
    _REPO_ROOT / "plugins" / "sulis" / "instances" / "release-train" / "tools.jsonld"
)
_FAILUREMODES_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "instances"
    / "release-train"
    / "failuremodes.jsonld"
)

# Canonical cross-WP ULIDs - established by prior waves (WP-003 + WP-004
# + WP-006). Drift in any of these breaks the canonical entity graph.
_CANONICAL_TENANT_ULID = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"
_CANONICAL_WORKFLOW_ULID = "dna:workflow:01KT0RTRA1NWFW00000000000A"

# The 10 kept Step names in canonical (linear) order (trunk re-model,
# WP-001). The 5 dev->main-PR Steps (preflight-cross-branch-drift,
# draft-pr-body-and-changelog, open-release-pr,
# wait-for-checks-and-mergeability, squash-merge) were deleted;
# commit-bump-as-bot became commit-bump-on-main (commits directly to main).
_EXPECTED_STEP_NAMES = [
    "detect-pending-changesets",  # 1
    "preflight-version-drift",  # 2
    "compute-next-version",  # 3
    "gate-founder-confirmation",  # 4 - mechanism=human (MUC-007)
    "bump-version-files",  # 5
    "write-changelog-entry",  # 6
    "commit-bump-on-main",  # 7 - commits directly to main (no promotion PR)
    "tag-and-push",  # 8
    "publish-github-release",  # 9
    "emit-release-entity",  # 10
]
_EXPECTED_STEP_COUNT = len(_EXPECTED_STEP_NAMES)  # 10

# The 2 by-design absences from release-on-merge.yml after the trunk
# re-model. Both are real Steps that are deliberately unannotated in the
# imperative: gate-founder-confirmation is the founder's manual merge
# (MUC-007); publish-github-release fires from the downstream
# release-prod.yml on the v* tag, not from this workflow. Encoded at
# envelope level because the per-Step brain schema sets
# unevaluatedProperties:false and rejects arbitrary new fields on Step
# objects; the envelope carries no such constraint.
_EXPECTED_EXCLUDED_FROM_YAML = {
    "gate-founder-confirmation",  # mechanism=human (MUC-007 founder gate)
    "publish-github-release",  # release-prod.yml fires on the v* tag, not here
}

# Kebab-case pattern: lowercase, hyphen-separated, no leading digit.
_KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)+$")


# ----- fixtures -----


@pytest.fixture(scope="module")
def instance() -> dict:
    """The parsed steps.jsonld envelope."""
    assert _INSTANCE_PATH.exists(), f"steps.jsonld missing at {_INSTANCE_PATH}"
    with _INSTANCE_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def steps(instance: dict) -> list[dict]:
    """The list of Step entries inside the envelope."""
    return instance["steps"]


@pytest.fixture(scope="module")
def schema() -> dict:
    """The vendored foundation Step schema (v1.2.0)."""
    assert _SCHEMA_PATH.exists(), (
        f"foundation Step schema missing at {_SCHEMA_PATH}; "
        "expected vendored copy alongside actor/credential/tenant/"
        "failuremode/trigger/tool"
    )
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def tool_ids() -> set[str]:
    """The set of Tool dna:tool:<ulid> IDs authored in WP-006."""
    assert _TOOLS_PATH.exists(), (
        f"tools.jsonld missing at {_TOOLS_PATH}; WP-006 must be done "
        "before WP-002 (tool_ref cross-ref)"
    )
    with _TOOLS_PATH.open() as f:
        envelope = json.load(f)
    return {t["id"] for t in envelope["tools"]}


@pytest.fixture(scope="module")
def failuremode_ids() -> set[str]:
    """The set of FailureMode dna:failuremode:<ulid> IDs authored in
    WP-004.
    """
    assert _FAILUREMODES_PATH.exists(), (
        f"failuremodes.jsonld missing at {_FAILUREMODES_PATH}; "
        "WP-004 must be done before WP-002 (handles_failures cross-ref)"
    )
    with _FAILUREMODES_PATH.open() as f:
        envelope = json.load(f)
    return {fm["id"] for fm in envelope["failuremodes"]}


# ----- Test #1 - JSON-LD parses with expected envelope shape -----


def test_steps_jsonld_parses(instance: dict) -> None:
    """The file is well-formed JSON-LD with the expected envelope
    shape.
    """
    assert "@context" in instance
    assert "@id" in instance
    assert "@type" in instance
    assert instance["@type"] == "step-instances"
    assert "steps" in instance
    assert isinstance(instance["steps"], list)


# ----- Test #2 - exactly 10 Step instances by exact-name match -----


def test_all_steps_present(steps: list[dict]) -> None:
    """Trunk re-model (WP-001): 10 Step instances by exact-name match."""
    assert len(steps) == _EXPECTED_STEP_COUNT, (
        f"expected {_EXPECTED_STEP_COUNT} Steps, found {len(steps)}"
    )
    names = {s["name"] for s in steps}
    expected_names = set(_EXPECTED_STEP_NAMES)
    missing = expected_names - names
    extra = names - expected_names
    assert not missing, f"missing Step names: {sorted(missing)}"
    assert not extra, f"unexpected Step names: {sorted(extra)}"


# ----- Test #3 - Each Step passes brain Step schema -----


def test_each_step_passes_brain_schema(steps: list[dict], schema: dict) -> None:
    """Every Step validates against the foundation Step schema
    (v1.2.0).
    """
    validator = Draft202012Validator(schema)
    errors_by_name: dict[str, list[str]] = {}
    for s in steps:
        errs = sorted(validator.iter_errors(s), key=lambda e: e.path)
        if errs:
            errors_by_name[s.get("name", "<unnamed>")] = [
                f"{list(e.path)}: {e.message}" for e in errs
            ]
    assert not errors_by_name, (
        f"schema validation failed for {len(errors_by_name)} Step(s): "
        f"{json.dumps(errors_by_name, indent=2)}"
    )


# ----- Test #4 - tool_ref cross-refs resolve to WP-006 Tools -----


def test_all_tool_refs_resolve_in_tools_jsonld(
    steps: list[dict], tool_ids: set[str]
) -> None:
    """Every Step's tool_ref (when present) resolves to a Tool ID
    authored in WP-006's tools.jsonld.
    """
    dangling: list[str] = []
    for s in steps:
        tool_ref = s.get("tool_ref")
        if tool_ref is None:
            continue
        if tool_ref not in tool_ids:
            dangling.append(f"{s['name']}: {tool_ref}")
    assert not dangling, (
        f"tool_ref values not found in WP-006 Tools: {dangling}. "
        f"Available Tool IDs: {sorted(tool_ids)}"
    )


# ----- Test #5 - handles_failures resolve to WP-004 FailureModes -----


def test_all_handles_failures_resolve_in_failuremodes_jsonld(
    steps: list[dict], failuremode_ids: set[str]
) -> None:
    """Every handles_failures entry resolves to a FailureMode ID
    authored in WP-004's failuremodes.jsonld.
    """
    dangling: list[str] = []
    for s in steps:
        for fm_ref in s.get("handles_failures", []):
            if fm_ref not in failuremode_ids:
                dangling.append(f"{s['name']}: {fm_ref}")
    assert not dangling, (
        f"handles_failures refs not found in WP-004 FailureModes: "
        f"{dangling}. "
        f"Available FailureMode IDs: {sorted(failuremode_ids)}"
    )


# ----- Test #6 - Step names use kebab-case (Blue invariant) -----


def test_step_names_use_kebab_case(steps: list[dict]) -> None:
    """Step names are pure kebab-case. Blue invariant - prevents
    naming drift as Steps accrete.
    """
    bad = [s["name"] for s in steps if not _KEBAB_RE.match(s["name"])]
    assert not bad, f"Step names violate kebab-case convention: {bad}"


# ----- Test #7 - canonical tenant + workflow ULIDs -----


def test_tenant_and_workflow_ulids_canonical(instance: dict, steps: list[dict]) -> None:
    """Every Step's for_domain is the canonical marketplace tenant
    ULID (per-Step, per brain Step v1.2.0 schema); the envelope's
    for_workflow is the canonical release-train workflow ULID (the
    step->workflow relation is modelled at envelope level per the
    schema, parallel to how triggers.jsonld declares for_workflow
    on each Trigger because the Trigger schema permits it).
    Cross-WP consistency check - drift here breaks the entity graph.
    """
    bad_domain = [
        (s["name"], s.get("for_domain"))
        for s in steps
        if s.get("for_domain") != _CANONICAL_TENANT_ULID
    ]
    assert not bad_domain, (
        f"Steps with non-canonical for_domain: {bad_domain}. "
        f"Expected: {_CANONICAL_TENANT_ULID}"
    )
    assert instance.get("for_workflow") == _CANONICAL_WORKFLOW_ULID, (
        f"Envelope for_workflow mismatch: got "
        f"{instance.get('for_workflow')!r}, expected "
        f"{_CANONICAL_WORKFLOW_ULID!r}"
    )


# ----- Test #8 - no probabilistic Step survives on the trunk -----


def test_no_probabilistic_step_on_trunk(steps: list[dict]) -> None:
    """The only probabilistic Step (draft-pr-body-and-changelog,
    the NFR-010 token-budget surface) was deleted in the trunk re-model
    (WP-001). No surviving Step is probabilistic; changelog drafting
    consolidates into the deterministic write-changelog-entry Step.
    """
    by_name = {s["name"]: s for s in steps}
    assert "draft-pr-body-and-changelog" not in by_name, (
        "the probabilistic draft-pr-body-and-changelog Step must be deleted "
        "on the trunk"
    )
    probabilistic = [
        s["name"] for s in steps if s.get("mechanism") in ("probabilistic", "mixed")
    ]
    assert not probabilistic, (
        f"no probabilistic Step should remain on the trunk; found {probabilistic}"
    )


# ----- Test #9 - gate-founder-confirmation mechanism=human (founder gate) -----


def test_founder_gate_is_human_mechanism(steps: list[dict]) -> None:
    """gate-founder-confirmation MUST have mechanism=human. This is the
    load-bearing founder-confirmation gate from MUC-007 - the LLM dry-run
    path respects this and refuses to auto-execute the ship-phase Steps
    without the founder's go-ahead.
    """
    by_name = {s["name"]: s for s in steps}
    gate = by_name["gate-founder-confirmation"]
    assert gate.get("mechanism") == "human", (
        f"gate-founder-confirmation mechanism must be 'human'; "
        f"got {gate.get('mechanism')}"
    )
    # mechanism=human Steps SHOULD NOT carry a tool_ref (per brain
    # semantics: human steps are not Tool invocations).
    assert "tool_ref" not in gate or gate["tool_ref"] is None, (
        "gate-founder-confirmation (human) should not carry a tool_ref"
    )


# ----- Test #10 - input/output artifacts have unique names (state contract) -----


def test_io_artifact_names_consistent(steps: list[dict]) -> None:
    """Output artifact names across all Steps are unique by name
    (state_contract Blue invariant - no two Steps produce an artifact
    of the same name with different meaning).
    """
    seen_outputs: dict[str, str] = {}  # artifact_name -> first-step-that-emitted-it
    collisions: list[tuple[str, str, str]] = []
    for s in steps:
        for artifact in s.get("output_artifacts", []):
            if artifact in seen_outputs:
                collisions.append((artifact, seen_outputs[artifact], s["name"]))
            else:
                seen_outputs[artifact] = s["name"]
    assert not collisions, (
        f"Output artifact name collisions (artifact, first-step, second-step): "
        f"{collisions}"
    )


# ----- Test #11 - envelope.excluded_from_yaml names the 2 by-design absences -----


def test_envelope_excluded_from_yaml_names_by_design_absences(
    instance: dict, steps: list[dict]
) -> None:
    """The steps.jsonld envelope carries `excluded_from_yaml`, a list of
    Step names that the drift detector must NOT flag as missing_in_yaml.

    On the trunk these are the 2 real-but-unannotated Steps:
    gate-founder-confirmation (the founder's manual merge, MUC-007) and
    publish-github-release (fires from the downstream release-prod.yml on
    the v* tag, not from this workflow). The list is the load-bearing
    signal that lets the drift detector run in blocking mode without
    false positives.

    Each name in the list MUST resolve to a real Step in the steps array
    (no dangling names; the list cannot drift out of sync with the Steps
    it labels).
    """
    excluded = instance.get("excluded_from_yaml")
    assert excluded is not None, (
        "steps.jsonld envelope must declare 'excluded_from_yaml' — "
        "the by-design-absence list the drift detector consumes"
    )
    assert isinstance(excluded, list), (
        f"excluded_from_yaml must be a list; got {type(excluded).__name__}"
    )
    assert set(excluded) == _EXPECTED_EXCLUDED_FROM_YAML, (
        f"excluded_from_yaml mismatch — got {sorted(excluded)}, "
        f"expected {sorted(_EXPECTED_EXCLUDED_FROM_YAML)}"
    )
    # Every name resolves to an actual Step (no dangling pointers).
    step_names = {s["name"] for s in steps}
    dangling = [name for name in excluded if name not in step_names]
    assert not dangling, (
        f"excluded_from_yaml contains names not present in steps[]: {dangling}"
    )
