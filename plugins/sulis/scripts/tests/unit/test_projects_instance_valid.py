"""
test_projects_instance_valid — WP-005

Validates that `plugins/sulis/instances/release-train/projects.jsonld`:

1. Parses as valid JSON-LD with the expected envelope shape.
2. Declares exactly 4 Project instances (sulis, sulis-brain,
   plugin-builder, investor-coach — the 4 marketplace plugins per
   ADR-004).
3. Each instance validates against the vendored foundation Project
   schema at `plugins/sulis/brain/compiled/foundation/project.schema.json`.
4. All `release_workflow_ref` fields resolve to the WP-001 canonical
   release-train Workflow ULID (dna:workflow:01KT0RTRA1NWFW00000000000A).
5. Every `branch_policy` is in the foundation enum
   {trunk, gitflow-dev-main, gitlab-pre-prod, custom}.
6. Each `source` field is a JSON-encoded object string with `repo`,
   `path`, and `primary_branch` keys (per foundation v0.6.0 contract:
   source is type=string with x-sensitive=true, the JSON-encoded
   future-tagged-union).
7. `version_files` paths exist for in-repo Projects (sulis,
   investor-coach); cross-repo Projects (sulis-brain, plugin-builder)
   are skipped per WP DoD.
8. All 4 Projects carry the canonical marketplace tenant ULID
   (dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM).
9. Names are unique and match the 4 marketplace plugins exactly.

Tests are deterministic + offline: no network, no LLM, no subprocess.
Schema is read from the local vendored copy; instance is read from
the release-train instances directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


_REPO_ROOT = Path(__file__).resolve().parents[5]
_INSTANCE_PATH = (
    _REPO_ROOT / "plugins" / "sulis" / "instances" / "release-train" / "projects.jsonld"
)
_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "foundation"
    / "project.schema.json"
)

# Canonical cross-references (MUST match upstream wave 1-4 instances).
_CANONICAL_TENANT_ULID = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"
_CANONICAL_RELEASE_TRAIN_WORKFLOW_ULID = "dna:workflow:01KT0RTRA1NWFW00000000000A"

# Foundation v0.6.0 branch_policy enum.
_VALID_BRANCH_POLICIES = {
    "trunk",
    "gitflow-dev-main",
    "gitlab-pre-prod",
    "custom",
}

# The 4 marketplace plugins per ADR-004 + WP-005 Contract table.
_EXPECTED_PROJECT_NAMES = {
    "sulis",
    "sulis-brain",
    "plugin-builder",
    "investor-coach",
}

# Projects whose source.path lives in THIS repo (sulis-ai/agents) — we
# can verify version_files existence locally. The other two live in
# sulis-ai/plugins and are skipped per WP DoD.
_IN_REPO_PROJECT_NAMES = {"sulis", "investor-coach"}


@pytest.fixture(scope="module")
def instance() -> dict:
    """The parsed projects.jsonld envelope."""
    assert _INSTANCE_PATH.exists(), f"projects.jsonld missing at {_INSTANCE_PATH}"
    with _INSTANCE_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def projects(instance: dict) -> list[dict]:
    """The list of Project entries inside the envelope."""
    return instance["projects"]


@pytest.fixture(scope="module")
def schema() -> dict:
    """The vendored foundation Project schema."""
    assert _SCHEMA_PATH.exists(), (
        f"foundation Project schema missing at {_SCHEMA_PATH}; "
        "expected vendored copy alongside workflow/tool/trigger/"
        "failuremode/step/actor/credential/tenant schemas"
    )
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


# ----- Test #1 — JSON-LD parses -----


def test_projects_jsonld_parses(instance: dict) -> None:
    """The file is well-formed JSON with the expected envelope shape."""
    assert "@context" in instance
    assert "@id" in instance
    assert "@type" in instance
    assert instance["@type"] == "project-instances"
    assert "projects" in instance
    assert isinstance(instance["projects"], list)


# ----- Test #2 — 4 Projects present -----


def test_4_projects_present(projects: list[dict]) -> None:
    """WP-005 Contract: exactly 4 Project instances."""
    assert len(projects) == 4, f"expected 4 Projects, found {len(projects)}"


# ----- Test #3 — each passes brain schema -----


def test_each_passes_brain_schema(projects: list[dict], schema: dict) -> None:
    """Every Project validates against the foundation schema."""
    validator = Draft202012Validator(schema)
    errors_by_name: dict[str, list[str]] = {}
    for p in projects:
        errs = sorted(validator.iter_errors(p), key=lambda e: str(e.path))
        if errs:
            errors_by_name[p.get("name", "<unnamed>")] = [
                f"{list(e.path)}: {e.message}" for e in errs
            ]
    assert not errors_by_name, (
        f"schema validation failed for {len(errors_by_name)} Project(s): "
        f"{json.dumps(errors_by_name, indent=2)}"
    )


# ----- Test #4 — release_workflow_ref resolves to WP-001 ULID -----


def test_all_release_workflow_refs_resolve_to_wp001(
    projects: list[dict],
) -> None:
    """All 4 Projects bind to the canonical WP-001 release-train Workflow."""
    bad = [
        (p["name"], p.get("release_workflow_ref"))
        for p in projects
        if p.get("release_workflow_ref") != _CANONICAL_RELEASE_TRAIN_WORKFLOW_ULID
    ]
    assert not bad, (
        f"release_workflow_ref drift from canonical "
        f"{_CANONICAL_RELEASE_TRAIN_WORKFLOW_ULID}: {bad}"
    )


# ----- Test #5 — branch_policy enum valid -----


def test_branch_policy_enum_valid(projects: list[dict]) -> None:
    """All branch_policy values are in the foundation v0.6.0 enum."""
    bad = [
        (p["name"], p.get("branch_policy"))
        for p in projects
        if p.get("branch_policy") not in _VALID_BRANCH_POLICIES
    ]
    assert not bad, (
        f"branch_policy out of foundation enum: {bad}. "
        f"Valid: {sorted(_VALID_BRANCH_POLICIES)}"
    )


# ----- Test #6 — source field is JSON-encoded with required keys -----


def test_source_json_well_formed(projects: list[dict]) -> None:
    """Each source field is a JSON-encoded string with repo/path/primary_branch."""
    for p in projects:
        name = p["name"]
        raw = p.get("source")
        assert isinstance(raw, str), (
            f"Project {name}: source must be a string (JSON-encoded), "
            f"got {type(raw).__name__}"
        )
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as e:
            pytest.fail(f"Project {name}: source is not valid JSON: {e}")
        assert isinstance(decoded, dict), (
            f"Project {name}: source must decode to an object, "
            f"got {type(decoded).__name__}"
        )
        for key in ("repo", "path", "primary_branch"):
            assert key in decoded, (
                f"Project {name}: source missing key '{key}'. "
                f"Got keys: {sorted(decoded.keys())}"
            )


# ----- Test #7 — version_files exist for in-repo Projects -----


def test_version_files_exist_in_repos(projects: list[dict]) -> None:
    """For sulis + investor-coach (in this repo), version_files paths
    must exist. For sulis-brain + plugin-builder (cross-repo), skip
    per WP DoD — those Projects live in sulis-ai/plugins."""
    missing: list[tuple[str, str]] = []
    for p in projects:
        name = p["name"]
        if name not in _IN_REPO_PROJECT_NAMES:
            continue
        for vf in p.get("version_files", []):
            full = _REPO_ROOT / vf
            if not full.exists():
                missing.append((name, vf))
    assert not missing, (
        f"version_files not found in repo: {missing}. "
        "In-repo Projects (sulis, investor-coach) must reference "
        "files that exist on this branch."
    )


# ----- Test #8 — canonical tenant on every Project -----


def test_canonical_tenant_consistent(projects: list[dict]) -> None:
    """All 4 Projects belong to the canonical marketplace tenant."""
    bad = [
        (p["name"], p.get("belongs_to_tenant"))
        for p in projects
        if p.get("belongs_to_tenant") != _CANONICAL_TENANT_ULID
    ]
    assert not bad, (
        f"belongs_to_tenant drift from canonical {_CANONICAL_TENANT_ULID}: {bad}"
    )


# ----- Test #9 — names unique + match the 4 marketplace plugins -----


def test_names_unique_and_match_marketplace(
    projects: list[dict],
) -> None:
    """Names are unique and exactly match the 4 marketplace plugins."""
    names = [p["name"] for p in projects]
    assert len(names) == len(set(names)), f"duplicate Project names: {names}"
    assert set(names) == _EXPECTED_PROJECT_NAMES, (
        f"Project names do not match marketplace. "
        f"Expected: {sorted(_EXPECTED_PROJECT_NAMES)}; "
        f"Found: {sorted(names)}"
    )
