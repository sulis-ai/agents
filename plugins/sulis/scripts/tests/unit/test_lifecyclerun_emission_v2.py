"""Tests for the v2-migrated `compose_lifecyclerun` (WP-002).

`compose_lifecyclerun` now takes a resolved `step` ref (a
`dna:step:<ulid>`), not a free `step_name` string. The per-run specificity
that used to be smuggled into the `step_name` string is carried by the
canonical `run_id` field. The emitted run must validate against the
re-vendored v2 schema.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

from _lifecyclerun_emission import compose_lifecyclerun


_STEP = "dna:step:01KT61X5ST01CHANGESTART00A"

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


class TestComposeEmitsStepRef:
    def test_compose_emits_step_ref(self) -> None:
        r = compose_lifecyclerun(step=_STEP, outcome="completed")
        assert r["step"] == _STEP
        assert "step_name" not in r
        assert "step_label" not in r
        assert "used" not in r
        assert re.fullmatch(r"^dna:lifecyclerun:[0-9A-HJKMNP-TV-Z]{26}$", r["id"])
        assert r["outcome"] == "completed"
        assert r["sys_status"] == "active"

    def test_compose_rejects_non_step_ref(self) -> None:
        with pytest.raises(ValueError, match="step"):
            compose_lifecyclerun(step="change-started:fix:x", outcome="completed")

    def test_compose_rejects_empty_step(self) -> None:
        with pytest.raises(ValueError, match="step"):
            compose_lifecyclerun(step="", outcome="completed")

    def test_invalid_outcome_raises(self) -> None:
        with pytest.raises(ValueError, match="outcome"):
            compose_lifecyclerun(step=_STEP, outcome="exploded")

    def test_run_id_emitted_when_provided(self) -> None:
        r = compose_lifecyclerun(
            step=_STEP, outcome="completed", run_id="change-started:fix:fix-login"
        )
        assert r["run_id"] == "change-started:fix:fix-login"

    def test_run_id_absent_when_not_provided(self) -> None:
        r = compose_lifecyclerun(step=_STEP, outcome="completed")
        assert "run_id" not in r

    def test_output_validates_against_revendored_v2(self) -> None:
        r = compose_lifecyclerun(
            step=_STEP, outcome="completed", run_id="trace-123"
        )
        validator = jsonschema.Draft202012Validator(_schema())
        assert list(validator.iter_errors(r)) == []
