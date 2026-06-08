"""Tests for the `sulis-emit-lifecyclerun --for-project` flag (WP-016, ADR-007).

The CLI gains an optional `--for-project dna:project:<ulid>` flag that threads
to `emit_lifecyclerun(for_project=...)`. Absent → the field is omitted (the
emit still succeeds). A bad ref is rejected with `{ok: false}`.
"""

from __future__ import annotations

import json
from pathlib import Path

_STEP_CHANGE_STARTED = "dna:step:01KT61X5ST01CHANGESTART00A"
_PROJECT = "dna:project:01KT1WPR0JECT0000000000000"

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_VENDORED = (
    _SCRIPTS_DIR.parent
    / "brain"
    / "compiled"
    / "product-development"
    / "lifecyclerun.schema.json"
)


def _loaded_instance(result) -> dict:
    written = Path(result.data["entities"][0]["path"])
    assert written.exists(), f"expected persisted instance at {written}"
    return json.loads(written.read_text())


class TestForProjectFlag:
    def test_for_project_flag_threads(self, tmp_path: Path, run_tool) -> None:
        result = run_tool(
            "sulis-emit-lifecyclerun",
            "--step", "change-started",
            "--outcome", "completed",
            "--for-project", _PROJECT,
            "--repo-root", str(tmp_path),
        )
        assert result.ok, (
            f"expected ok=true, got returncode={result.returncode}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        loaded = _loaded_instance(result)
        assert loaded["for_project"] == _PROJECT

    def test_for_project_absent_omits_field(self, tmp_path: Path, run_tool) -> None:
        result = run_tool(
            "sulis-emit-lifecyclerun",
            "--step", "change-started",
            "--outcome", "completed",
            "--repo-root", str(tmp_path),
        )
        assert result.ok, (
            f"expected ok=true, got returncode={result.returncode}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        loaded = _loaded_instance(result)
        assert "for_project" not in loaded

    def test_bad_for_project_rejected(self, tmp_path: Path, run_tool) -> None:
        result = run_tool(
            "sulis-emit-lifecyclerun",
            "--step", "change-started",
            "--outcome", "completed",
            "--for-project", "not-a-project",
            "--repo-root", str(tmp_path),
        )
        assert not result.ok
        assert "for_project" in (result.error or "")
