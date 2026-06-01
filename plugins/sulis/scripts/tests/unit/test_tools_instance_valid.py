"""
test_tools_instance_valid — WP-006

Validates that `plugins/sulis/instances/release-train/tools.jsonld`:

1. Parses as valid JSON-LD with the expected envelope shape.
2. Declares the full release-train Tool catalogue (17 = 5 primary + 12 stub
   per ADR-003).
3. Each Tool validates against the foundation Tool JSON Schema
   (`plugins/sulis/brain/compiled/foundation/tool.schema.json`, v1.1.0).
4. The 5 primary Tools' `inputs_schema_ref` and `outputs_schema_ref` resolve
   to real JSON Schema files (NOT `none://...` stub URIs) under
   `plugins/sulis/instances/release-train/schemas/tools/`.
5. The 12 stub Tools all carry `state: draft`.
6. Every Tool's `error_catalogue` entries resolve to FailureMode IDs in
   WP-004's `failuremodes.jsonld`.
7. Each primary Tool's input schema accepts a representative sample payload
   (CF-04: stubs include the happy-path example).

These tests are deliberately deterministic + offline — no network, no LLM,
no subprocess. Schemas come from the vendored brain/compiled directory; the
instance comes from the release-train instances directory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


_REPO_ROOT = Path(__file__).resolve().parents[5]
_INSTANCE_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "instances"
    / "release-train"
    / "tools.jsonld"
)
_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "foundation"
    / "tool.schema.json"
)
_TOOL_SCHEMAS_DIR = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "instances"
    / "release-train"
    / "schemas"
    / "tools"
)
_FAILUREMODES_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "instances"
    / "release-train"
    / "failuremodes.jsonld"
)

# Primary Tool names (ADR-003 — fully populated with real input/output schemas).
# git-tag + git-push-tag treated as one primary slot per WP-006 Contract;
# git-tag is the primary entity, git-push-tag drops to stub.
_PRIMARY_TOOL_NAMES = {
    "_changeset.cumulative_tier",
    "_changeset.next_version",
    "gh-pr-create",
    "git-tag",
    "gh-release-create",
}

# Stub Tool names — minimal frontmatter, state=draft per ADR-003.
_STUB_TOOL_NAMES = {
    "_changeset.read_changesets",
    "_changeset.compare_version_files",
    "_changeset.summarise",
    "gh-pr-checks-watch",
    "gh-pr-mergeability",
    "gh-pr-merge",
    "git-commit",
    "git-compare-branch-versions",
    "update-version-file",
    "prepend-changelog",
    "sulis-emit-release",
    "git-push-tag",
}

_EXPECTED_TOOL_COUNT = len(_PRIMARY_TOOL_NAMES) + len(_STUB_TOOL_NAMES)  # 17

# A representative sample input payload per primary Tool, for the CF-04
# stub-validation test. Keep these minimal — the schemas describe only the
# load-bearing fields per ADR-003 (Blue refactor invariant).
_PRIMARY_SAMPLE_INPUTS: dict[str, dict] = {
    "_changeset.cumulative_tier": {
        "changesets": [
            {"tier": "patch", "primitive": "fix"},
            {"tier": "minor", "primitive": "feat"},
        ]
    },
    "_changeset.next_version": {
        "current": "0.85.0",
        "tier": "minor",
    },
    "gh-pr-create": {
        "title": "release: sulis v0.86.0 (minor)",
        "body": "Release PR body.",
        "base": "main",
        "head": "release/auto",
    },
    "git-tag": {
        "tag": "v1.131.0",
        "message": "release v1.131.0",
    },
    "gh-release-create": {
        "tag": "v1.131.0",
        "title": "sulis v0.86.0",
        "notes": "auto-generated release notes",
    },
}


@pytest.fixture(scope="module")
def instance() -> dict:
    """The parsed tools.jsonld envelope."""
    assert _INSTANCE_PATH.exists(), (
        f"tools.jsonld missing at {_INSTANCE_PATH}"
    )
    with _INSTANCE_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def tools(instance: dict) -> list[dict]:
    """The list of Tool entries inside the envelope."""
    return instance["tools"]


@pytest.fixture(scope="module")
def schema() -> dict:
    """The vendored foundation Tool schema (v1.1.0)."""
    assert _SCHEMA_PATH.exists(), (
        f"foundation Tool schema missing at {_SCHEMA_PATH}; "
        "expected vendored copy alongside actor/credential/tenant/failuremode/trigger"
    )
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def failuremode_ids() -> set[str]:
    """The set of FailureMode dna:failuremode:<ulid> IDs authored in WP-004."""
    assert _FAILUREMODES_PATH.exists(), (
        f"failuremodes.jsonld missing at {_FAILUREMODES_PATH}; "
        "WP-004 must be done before WP-006 (error_catalogue cross-ref)"
    )
    with _FAILUREMODES_PATH.open() as f:
        fm_envelope = json.load(f)
    return {fm["id"] for fm in fm_envelope["failuremodes"]}


# ----- Test #1 — JSON-LD parses with expected envelope shape -----


def test_tools_jsonld_parses(instance: dict) -> None:
    """The file is well-formed JSON-LD with the expected envelope shape."""
    assert "@context" in instance
    assert "@id" in instance
    assert "@type" in instance
    assert instance["@type"] == "tool-instances"
    assert "tools" in instance
    assert isinstance(instance["tools"], list)


# ----- Test #2 — 17 Tools present (5 primary + 12 stub) -----


def test_all_tools_present(tools: list[dict]) -> None:
    """WP-006 + ADR-003 Contract: 17 Tool instances by exact-name match."""
    assert len(tools) == _EXPECTED_TOOL_COUNT, (
        f"expected {_EXPECTED_TOOL_COUNT} Tools, found {len(tools)}"
    )
    names = {t["name"] for t in tools}
    expected_names = _PRIMARY_TOOL_NAMES | _STUB_TOOL_NAMES
    missing = expected_names - names
    extra = names - expected_names
    assert not missing, f"missing Tool names: {sorted(missing)}"
    assert not extra, f"unexpected Tool names: {sorted(extra)}"


# ----- Test #3 — Each Tool passes brain Tool schema -----


def test_each_passes_brain_schema(tools: list[dict], schema: dict) -> None:
    """Every Tool validates against the foundation Tool schema (v1.1.0)."""
    validator = Draft202012Validator(schema)
    errors_by_name: dict[str, list[str]] = {}
    for t in tools:
        errs = sorted(validator.iter_errors(t), key=lambda e: e.path)
        if errs:
            errors_by_name[t.get("name", "<unnamed>")] = [
                f"{list(e.path)}: {e.message}" for e in errs
            ]
    assert not errors_by_name, (
        f"schema validation failed for {len(errors_by_name)} Tool(s): "
        f"{json.dumps(errors_by_name, indent=2)}"
    )


# ----- Test #4 — Primary Tools have real schema refs (NOT none://) -----


def test_primary_tools_have_real_schema_refs(tools: list[dict]) -> None:
    """5 primary Tools' inputs/outputs_schema_ref resolve to real .schema.json
    files under plugins/sulis/instances/release-train/schemas/tools/.
    """
    by_name = {t["name"]: t for t in tools}
    primaries = [by_name[n] for n in _PRIMARY_TOOL_NAMES]
    unresolved: list[str] = []
    for t in primaries:
        for ref_field in ("inputs_schema_ref", "outputs_schema_ref"):
            ref = t[ref_field]
            assert not ref.startswith("none://"), (
                f"primary Tool {t['name']} has stub {ref_field}={ref}; "
                "primaries MUST point at a real schema per ADR-003"
            )
            # Refs are relative to the tools.jsonld file's directory.
            ref_path = _INSTANCE_PATH.parent / ref
            if not ref_path.exists():
                unresolved.append(f"{t['name']}.{ref_field}={ref}")
    assert not unresolved, (
        f"unresolved schema refs for primary Tools: {unresolved}"
    )


# ----- Test #5 — Stub Tools state == draft -----


def test_stub_tools_state_is_draft(tools: list[dict]) -> None:
    """12 stub Tools per ADR-003 carry state=draft (drift-detector exempts
    these from input/output schema validation).
    """
    by_name = {t["name"]: t for t in tools}
    bad = []
    for stub_name in _STUB_TOOL_NAMES:
        t = by_name[stub_name]
        if t.get("state") != "draft":
            bad.append((stub_name, t.get("state")))
    assert not bad, (
        f"stub Tools not in state=draft: {bad}. "
        f"Per ADR-003, all {len(_STUB_TOOL_NAMES)} stubs must be state=draft."
    )


# ----- Test #6 — error_catalogue refs resolve to WP-004 FailureModes -----


def test_error_catalogue_refs_resolve(
    tools: list[dict], failuremode_ids: set[str]
) -> None:
    """Every error_catalogue entry resolves to a FailureMode ID authored in
    WP-004's failuremodes.jsonld.
    """
    dangling: list[str] = []
    for t in tools:
        for fm_ref in t.get("error_catalogue", []):
            if fm_ref not in failuremode_ids:
                dangling.append(f"{t['name']}: {fm_ref}")
    assert not dangling, (
        f"error_catalogue refs not found in WP-004 FailureModes: {dangling}. "
        f"Available FailureMode IDs: {sorted(failuremode_ids)}"
    )


# ----- Test #7 — Primary Tool input schemas validate sample payload (CF-04) -----


def test_primary_tool_input_schemas_validate(tools: list[dict]) -> None:
    """For each primary Tool, the input schema accepts a representative
    happy-path payload (CF-04 — stubs include the happy-path example).
    """
    by_name = {t["name"]: t for t in tools}
    failures: list[str] = []
    for primary_name in _PRIMARY_TOOL_NAMES:
        t = by_name[primary_name]
        schema_ref = t["inputs_schema_ref"]
        schema_path = _INSTANCE_PATH.parent / schema_ref
        assert schema_path.exists(), (
            f"input schema for {primary_name} missing at {schema_path}"
        )
        with schema_path.open() as f:
            input_schema = json.load(f)
        sample = _PRIMARY_SAMPLE_INPUTS[primary_name]
        validator = Draft202012Validator(input_schema)
        errs = sorted(validator.iter_errors(sample), key=lambda e: e.path)
        if errs:
            failures.append(
                f"{primary_name} sample input failed schema: "
                + "; ".join(f"{list(e.path)}: {e.message}" for e in errs)
            )
    assert not failures, "primary Tool input schemas rejected sample payloads:\n" + "\n".join(failures)


# ----- Blue invariant: kebab-case-ish tool names -----

# Tool names accept _changeset.* dot-notation OR kebab. Pattern:
# either dot-prefixed (_changeset.foo_bar) OR pure kebab (gh-pr-create).
_DOT_NS_RE = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
_KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)+$")


def test_names_use_convention(tools: list[dict]) -> None:
    """Tool names use kebab-case OR the _changeset.<snake> namespaced form.
    Blue invariant — prevents naming drift as Tools accrete.
    """
    bad = []
    for t in tools:
        name = t["name"]
        if not (_KEBAB_RE.match(name) or _DOT_NS_RE.match(name)):
            bad.append(name)
    assert not bad, (
        f"Tool names violate convention (kebab-case OR _changeset.snake): {bad}"
    )
