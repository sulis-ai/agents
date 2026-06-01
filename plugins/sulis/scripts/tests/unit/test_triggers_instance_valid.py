"""WP-003 — release-train Trigger entity instance validation.

Authors two Trigger instances (manual + event) at
`plugins/sulis/instances/release-train/triggers.jsonld` and verifies
them against the vendored brain Trigger JSON Schema (foundation
v0.5.0). The instances ARE the contract — these tests guard the
contract from drift.

Cross-WP coordination notes:
- `for_workflow` references `dna:workflow:01KT0RTRA1NWFW00000000000A`,
  which WP-001 (workflow.jsonld) adopts when it authors the Workflow
  entity. This test does not assert the Workflow ULID exists yet —
  WP-007 (drift detector) covers cross-entity resolution; here we
  guard the Trigger shape.
- `for_domain` references the Sulis AI marketplace tenant ULID
  `dna:tenant:01JA0AAA1BBBCCCDDDEEEFFFGS` (same as the brain's
  sync-narrative-docs exemplar).
"""

from __future__ import annotations

import json
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
    / "triggers.jsonld"
)
_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "foundation"
    / "trigger.schema.json"
)


def _load_instance() -> dict:
    return json.loads(_INSTANCE_PATH.read_text())


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


def test_triggers_jsonld_parses() -> None:
    """The triggers.jsonld file exists, is valid JSON, and exposes a
    top-level `triggers` array."""
    assert _INSTANCE_PATH.exists(), (
        f"expected triggers instance at {_INSTANCE_PATH}"
    )
    instance = _load_instance()
    assert isinstance(instance, dict)
    assert "triggers" in instance, "top-level `triggers` array missing"
    assert isinstance(instance["triggers"], list)


def test_both_triggers_present() -> None:
    """Exactly two Triggers: the manual /sulis:release-train invocation
    and the GH-Actions release-on-merge event."""
    triggers = _load_instance()["triggers"]
    assert len(triggers) == 2, (
        f"expected exactly 2 Trigger instances, got {len(triggers)}"
    )

    names = {t["name"] for t in triggers}
    assert names == {
        "manual-release-train-invocation",
        "pull-request-merged-to-main",
    }, f"trigger names mismatch: {names}"

    # Sanity: kind taxonomy matches the WP Contract — one manual, one event.
    kinds = {t["name"]: t["kind"] for t in triggers}
    assert kinds["manual-release-train-invocation"] == "manual"
    assert kinds["pull-request-merged-to-main"] == "event"


def test_each_trigger_passes_brain_schema() -> None:
    """Each Trigger validates against the vendored brain Trigger schema
    (foundation v0.5.0). This is the contract — schema-level conformance
    is non-negotiable."""
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    triggers = _load_instance()["triggers"]
    errors_by_index: dict[int, list[str]] = {}
    for i, trigger in enumerate(triggers):
        errs = sorted(validator.iter_errors(trigger), key=lambda e: e.path)
        if errs:
            errors_by_index[i] = [
                f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
                for e in errs
            ]
    if errors_by_index:
        lines = []
        for i, errs in errors_by_index.items():
            name = triggers[i].get("name", "<unnamed>")
            lines.append(f"  [{i}] {name}: {errs}")
        pytest.fail("trigger schema-validation failures:\n" + "\n".join(lines))
