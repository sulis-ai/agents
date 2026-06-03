"""Unit tests for the v1.0.0 -> v2 LifecycleRun migration (WP-006, ADR-004).

`migrate_instance(doc)` rewrites a v1 LifecycleRun (`step_name: <string>`)
into the v2 shape (`step: <dna:step:<ulid>>`):

  - maps `step_name` -> the matching canonical Step ULID via WP-002's
    `_resolve_step` (known names via the map; unknown -> the
    `unclassified-lifecycle-step` Step);
  - drops the old `step_name` string (carried into `run_id` for trace
    grouping where one isn't already present), adds `step`;
  - strips fields the v2 schema would reject (`unevaluatedProperties: false`):
    the JSON-LD envelope keys and the legacy `_`-prefixed harness fields;
  - re-validates against the re-vendored v2 schema before returning
    (reject-on-invalid — never hand back a still-invalid instance);
  - is idempotent: a doc that already carries `step` returns None (skip).

These tests author their own v1 fixtures inline — they NEVER read or mutate
the marketplace's live `.brain/instances`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

from migrate_lifecyclerun_v1_to_v2 import migrate_instance


# Canonical Step ULIDs (authored once in
# plugins/sulis/instances/lifecycle-steps/steps.jsonld; copied, never minted).
_STEP_CHANGE_STARTED = "dna:step:01KT61X5ST01CHANGESTART00A"
_STEP_UNCLASSIFIED = "dna:step:01KT61X5ST03VNC1ASS1F1ED0A"

_STEP_REF_RE = re.compile(r"^dna:step:[0-9A-HJKMNP-TV-Z]{26}$")
_RUN_ID_RE = re.compile(r"^dna:lifecyclerun:[0-9A-HJKMNP-TV-Z]{26}$")

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_VENDORED = (
    _SCRIPTS_DIR.parent
    / "brain"
    / "compiled"
    / "product-development"
    / "lifecyclerun.schema.json"
)


def _schema() -> dict:
    return json.loads(_VENDORED.read_text())


def _minimal_v1() -> dict:
    """The shape of the small on-disk v1 instance (Q0GXFX...), with a
    `step_name` that is a KNOWN canonical name (maps to change-started)."""
    return {
        "at": "2026-06-02T13:55:02Z",
        "id": "dna:lifecyclerun:Q0GXFX856ZY9M7W43YCX3KSE4K",
        "outcome": "completed",
        "step_name": "change-started",
        "sys_status": "active",
    }


def _compound_trace_v1() -> dict:
    """The realistic small on-disk v1 instance — its `step_name` is a compound
    trace string (`wpx-pipeline-success:WP-001`), which is NOT a known
    canonical name and so resolves to the unclassified Step, carrying the
    trace string into `run_id`."""
    return {
        "at": "2026-06-02T13:55:02Z",
        "id": "dna:lifecyclerun:Q0GXFX856ZY9M7W43YCX3KSE4K",
        "outcome": "completed",
        "step_name": "wpx-pipeline-success:WP-001",
        "sys_status": "active",
    }


def _rich_v1() -> dict:
    """The shape of the rich on-disk v1 instance (01KT419R...) — JSON-LD
    envelope + many legacy `_`-prefixed harness fields + extra non-schema
    top-level fields. All of these are rejected by `unevaluatedProperties:
    false`, so the migration must strip them down to the v2 field-set."""
    return {
        "@context": {
            "@vocab": "https://sulis.co/dna/",
            "dna": "https://sulis.co/dna/",
            "prov": "http://www.w3.org/ns/prov#",
        },
        "@id": "dna:lifecyclerun:01KT419R8MQBQ6BNZPXDSKZBHZ",
        "@type": "lifecyclerun",
        "id": "dna:lifecyclerun:01KT419R8MQBQ6BNZPXDSKZBHZ",
        "step_name": "faithful-generation-harness",
        "at": "2026-06-02T00:00:00Z",
        "outcome": "completed",
        "sys_status": "active",
        "valid_from": "2026-06-02T00:00:00Z",
        "confidence": 0.88,
        "_run_id": "01KT419R8MQBQ6BNZPXDSKZBHZ",
        "_workflow": "dna:workflow:01KT3GM8ZF8PC7RJSGSE5JE7QQ",
        "_final_verdict": "partial-unattributed",
        "_deterministic": False,
        "_step_runs": [{"step": "observe-manifest", "outcome": "completed"}],
    }


def _already_v2() -> dict:
    return {
        "id": "dna:lifecyclerun:01KT61V2A1READYM1GRATED00A",
        "step": _STEP_CHANGE_STARTED,
        "at": "2026-06-03T00:00:00Z",
        "outcome": "completed",
        "sys_status": "active",
    }


class TestMigrateInstance:
    def test_v1_fixture_migrates(self) -> None:
        """step_name string in -> v2 with a resolved `step`, NO `step_name`,
        NO `step_label` in the output."""
        out = migrate_instance(_minimal_v1())
        assert out is not None
        assert out["step"] == _STEP_CHANGE_STARTED
        assert "step_name" not in out
        assert "step_label" not in out
        # Identity + envelope preserved.
        assert out["id"] == "dna:lifecyclerun:Q0GXFX856ZY9M7W43YCX3KSE4K"
        assert out["outcome"] == "completed"
        assert out["sys_status"] == "active"
        assert out["at"] == "2026-06-02T13:55:02Z"

    def test_idempotent(self) -> None:
        """A doc that already carries `step` is skipped (returns None)."""
        assert migrate_instance(_already_v2()) is None

    def test_unmappable_to_unclassified(self) -> None:
        """`faithful-generation-harness` has no known mapping -> the
        `unclassified-lifecycle-step` Step ULID."""
        out = migrate_instance(_rich_v1())
        assert out is not None
        assert out["step"] == _STEP_UNCLASSIFIED
        assert "step_name" not in out
        assert "step_label" not in out

    def test_rejects_invalid(self) -> None:
        """A doc that can't be made valid (bad outcome enum that survives the
        structural swap) raises; the migration never hands back an invalid
        instance."""
        bad = {
            "id": "dna:lifecyclerun:01KT419R8MQBQ6BNZPXDSKZBHZ",
            "step_name": "change-shipped:feat:x",
            "at": "2026-06-02T00:00:00Z",
            "outcome": "exploded",  # not in the enum
            "sys_status": "active",
        }
        with pytest.raises(Exception):
            migrate_instance(bad)

    def test_revalidates_against_v2(self) -> None:
        """Both the minimal and the rich migrated outputs pass the vendored
        v2 schema (the same validator the emitter targets)."""
        validator = jsonschema.Draft202012Validator(_schema())
        for src in (_minimal_v1(), _rich_v1()):
            out = migrate_instance(src)
            assert out is not None
            assert list(validator.iter_errors(out)) == []

    def test_step_is_valid_step_ref(self) -> None:
        out = migrate_instance(_minimal_v1())
        assert out is not None
        assert _STEP_REF_RE.fullmatch(out["step"])

    def test_compound_trace_name_to_unclassified(self) -> None:
        """A compound trace `step_name` (the realistic small on-disk shape)
        is not a known canonical name -> the unclassified Step ULID."""
        out = migrate_instance(_compound_trace_v1())
        assert out is not None
        assert out["step"] == _STEP_UNCLASSIFIED

    def test_legacy_step_name_carried_into_run_id(self) -> None:
        """The old free `step_name`, where genuinely needed for trace
        grouping, is carried into `run_id` (mirrors WP-002's emitter), never
        into a non-existent `step_label`."""
        out = migrate_instance(_compound_trace_v1())
        assert out is not None
        assert out["run_id"] == "wpx-pipeline-success:WP-001"

    def test_existing_run_id_not_overwritten(self) -> None:
        """If a v1 instance already carries a `run_id`, the migration keeps
        it rather than clobbering it with the legacy `step_name`."""
        src = _minimal_v1()
        src["run_id"] = "pre-existing-trace"
        out = migrate_instance(src)
        assert out is not None
        assert out["run_id"] == "pre-existing-trace"
