"""
test_failuremodes_instance_valid — WP-004

Validates that `plugins/sulis/instances/release-train/failuremodes.jsonld`:

1. Parses as valid JSON-LD.
2. Declares exactly 8 FailureMode instances.
3. Each instance validates against the foundation FailureMode JSON Schema
   (`plugins/sulis/brain/compiled/foundation/failuremode.schema.json`).
4. `recovery_strategy` for every instance is in the canonical
   {retry, compensate, escalate, abort, manual-review, fallback} enum.
5. The three lived defects from FR-008 (CH-01KSYZ workflow-yaml-fails-to-parse,
   CH-01KSZ1 loop-guard-matches-founder-pr, GH-token-tag bot-tag-doesnt-trigger-
   release-prod) are present by name.
6. Every `name` is kebab-case + describe-the-failure form (Blue invariant test,
   RGB-03).

These tests are deliberately deterministic + offline — no network, no LLM,
no brain CLI subprocess. The schema is read from the local
brain/compiled/foundation/ directory; the instance is read from the
release-train instances directory.
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
    / "failuremodes.jsonld"
)
_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "foundation"
    / "failuremode.schema.json"
)

_VALID_RECOVERY_STRATEGIES = {
    "retry",
    "compensate",
    "escalate",
    "abort",
    "manual-review",
    "fallback",
}

# FR-008's three lived-defect FailureModes — MUST be present by exact name.
_REQUIRED_LIVED_DEFECT_NAMES = {
    "workflow-yaml-fails-to-parse",
    "loop-guard-matches-founder-pr",
    "bot-tag-doesnt-trigger-release-prod",
}

# kebab-case: lowercase letters, digits, hyphens; must start with a letter;
# no consecutive hyphens; no trailing hyphen.
_KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)+$")


@pytest.fixture(scope="module")
def instance() -> dict:
    """The parsed failuremodes.jsonld envelope."""
    assert _INSTANCE_PATH.exists(), (
        f"failuremodes.jsonld missing at {_INSTANCE_PATH}"
    )
    with _INSTANCE_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def failuremodes(instance: dict) -> list[dict]:
    """The list of FailureMode entries inside the envelope."""
    return instance["failuremodes"]


@pytest.fixture(scope="module")
def schema() -> dict:
    """The vendored foundation FailureMode schema."""
    assert _SCHEMA_PATH.exists(), (
        f"foundation FailureMode schema missing at {_SCHEMA_PATH}; "
        "expected vendored copy alongside actor/credential/tenant schemas"
    )
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


# ----- Test #1 — JSON-LD parses -----


def test_failuremodes_jsonld_parses(instance: dict) -> None:
    """The file is well-formed JSON with the expected envelope shape."""
    assert "@context" in instance
    assert "@id" in instance
    assert "@type" in instance
    assert instance["@type"] == "failuremode-instances"
    assert "failuremodes" in instance
    assert isinstance(instance["failuremodes"], list)


# ----- Test #2 — 8 FailureModes present -----


def test_8_failuremodes_present(failuremodes: list[dict]) -> None:
    """WP-004 Contract: exactly 8 FailureMode instances."""
    assert len(failuremodes) == 8, (
        f"expected 8 FailureModes, found {len(failuremodes)}"
    )


# ----- Test #3 — each passes brain schema -----


def test_each_passes_brain_schema(
    failuremodes: list[dict], schema: dict
) -> None:
    """Every FailureMode validates against the foundation schema."""
    validator = Draft202012Validator(schema)
    errors_by_name: dict[str, list[str]] = {}
    for fm in failuremodes:
        errs = sorted(validator.iter_errors(fm), key=lambda e: e.path)
        if errs:
            errors_by_name[fm.get("name", "<unnamed>")] = [
                f"{list(e.path)}: {e.message}" for e in errs
            ]
    assert not errors_by_name, (
        f"schema validation failed for {len(errors_by_name)} FailureMode(s): "
        f"{json.dumps(errors_by_name, indent=2)}"
    )


# ----- Test #4 — recovery_strategy enum valid -----


def test_recovery_strategy_enum_valid(failuremodes: list[dict]) -> None:
    """All recovery_strategy values are in the FR-009 enum."""
    bad = [
        (fm["name"], fm.get("recovery_strategy"))
        for fm in failuremodes
        if fm.get("recovery_strategy") not in _VALID_RECOVERY_STRATEGIES
    ]
    assert not bad, (
        f"recovery_strategy out of FR-009 enum: {bad}. "
        f"Valid: {sorted(_VALID_RECOVERY_STRATEGIES)}"
    )


# ----- Test #5 — FR-008 lived defects represented -----


def test_lived_defects_represented(failuremodes: list[dict]) -> None:
    """FR-008's three lived-defect FailureModes are present by exact name."""
    names = {fm["name"] for fm in failuremodes}
    missing = _REQUIRED_LIVED_DEFECT_NAMES - names
    assert not missing, (
        f"FR-008 lived defects missing from FailureMode catalogue: {missing}. "
        f"Present names: {sorted(names)}"
    )


# ----- Test #6 — Blue invariant: kebab-case names -----


def test_names_kebab_case(failuremodes: list[dict]) -> None:
    """Every FailureMode name is kebab-case and reads as <symptom>-<context>.

    This is the Blue refactor invariant from the WP DoD: prevents naming drift
    when future FailureModes are added.
    """
    bad = [fm["name"] for fm in failuremodes if not _KEBAB_RE.match(fm["name"])]
    assert not bad, (
        f"non-kebab-case FailureMode names: {bad}. "
        "Pattern: lowercase + digits + hyphens, must include at least one "
        "hyphen, no consecutive hyphens, no trailing hyphen."
    )
