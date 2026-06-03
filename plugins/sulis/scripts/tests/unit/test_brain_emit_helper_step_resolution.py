"""Tests for the name->Step-ULID resolution in `_brain_emit_helper.py` (WP-002).

Under v2 the three LifecycleRun helpers no longer pass a free `step_name`
string. They resolve a canonical Step ULID (a `prov:Plan` ref) for the run's
`step`:

  - `emit_change_started_event` -> the `change-started` Step ULID
  - `emit_change_shipped_event`  -> the `change-shipped` Step ULID
  - `emit_lifecycle_step_event(step_name=...)` -> the mapped Step ULID for a
     known name, else the `unclassified-lifecycle-step` Step; the original
     free string is carried into `run_id` for trace grouping.

The three ULIDs are the WP-001 authored values in
`plugins/sulis/instances/lifecycle-steps/steps.jsonld` (single source of
truth — no inline mint). This test pins them byte-exact against that file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _brain_emit_helper import (
    _resolve_step,
    emit_change_shipped_event,
    emit_change_started_event,
    emit_lifecycle_step_event,
)


_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SCRIPTS_DIR.parents[2]
_STEPS_JSONLD = (
    _REPO_ROOT / "plugins" / "sulis" / "instances" / "lifecycle-steps" / "steps.jsonld"
)


def _canonical_ulids() -> dict[str, str]:
    doc = json.loads(_STEPS_JSONLD.read_text())
    return {s["name"]: s["id"] for s in doc["steps"]}


class TestStepResolution:
    def test_change_started_resolves_to_canonical_step(self) -> None:
        ulids = _canonical_ulids()
        assert _resolve_step("change-started") == ulids["change-started"]

    def test_change_shipped_resolves_to_canonical_step(self) -> None:
        ulids = _canonical_ulids()
        assert _resolve_step("change-shipped") == ulids["change-shipped"]

    def test_unknown_name_resolves_to_unclassified(self) -> None:
        ulids = _canonical_ulids()
        assert _resolve_step("wpx-pipeline-success:WP-012") == ulids[
            "unclassified-lifecycle-step"
        ]

    def test_map_ulids_match_canonical(self) -> None:
        """The resolver's map values are byte-exact vs steps.jsonld."""
        ulids = _canonical_ulids()
        assert _resolve_step("change-started") == "dna:step:01KT61X5ST01CHANGESTART00A"
        assert _resolve_step("change-shipped") == "dna:step:01KT61X5ST02CHANGESH1PP00A"
        assert (
            _resolve_step("anything-unmapped")
            == "dna:step:01KT61X5ST03VNC1ASS1F1ED0A"
        )
        # And those literals are exactly what the canonical instance file holds.
        assert ulids["change-started"] == "dna:step:01KT61X5ST01CHANGESTART00A"
        assert ulids["change-shipped"] == "dna:step:01KT61X5ST02CHANGESH1PP00A"
        assert ulids["unclassified-lifecycle-step"] == "dna:step:01KT61X5ST03VNC1ASS1F1ED0A"


class TestHelpersEmitStepRefs:
    def test_change_started_emits_step_ref(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_change_started_event(
            tmp_path, change_id="01ABC", handle="CH-01ABC",
            slug="fix-login-bug", primitive="fix",
        )
        assert result is not None
        assert result["step"] == "dna:step:01KT61X5ST01CHANGESTART00A"
        assert "step_name" not in result
        # per-run specificity preserved in run_id (not lost, not in step_label)
        assert result.get("run_id") == "change-started:fix:fix-login-bug"
        assert "step_label" not in result

    def test_change_shipped_emits_step_ref(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_change_shipped_event(
            tmp_path, change_id="01ABC", handle="CH-01ABC",
            slug="fix-login-bug", primitive="fix", shipped_sha="abc1234",
        )
        assert result is not None
        assert result["step"] == "dna:step:01KT61X5ST02CHANGESH1PP00A"
        assert result.get("run_id") == "change-shipped:fix:fix-login-bug"
        assert "step_name" not in result

    def test_lifecycle_step_event_unknown_name_uses_unclassified(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_lifecycle_step_event(
            tmp_path, step_name="wpx-pipeline-success:WP-012", outcome="completed",
        )
        assert result is not None
        assert result["step"] == "dna:step:01KT61X5ST03VNC1ASS1F1ED0A"
        # the free string is carried into run_id for trace grouping
        assert result.get("run_id") == "wpx-pipeline-success:WP-012"
        assert "step_name" not in result

    def test_emitted_run_validates_v2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A helper-emitted run is persisted (i.e. it passed the adapter's
        validate against the re-vendored v2 schema — save() rejects-on-invalid,
        so a non-None return with a file on disk proves it validated)."""
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_change_started_event(
            tmp_path, change_id="01ABC", handle="CH-01ABC",
            slug="x", primitive="fix",
        )
        assert result is not None
        ulid = result["id"].split(":")[-1]
        assert (
            tmp_path / ".brain" / "instances" / "product-development"
            / "lifecyclerun" / f"{ulid}.jsonld"
        ).exists()
