"""Tests for the `sulis-emit-lifecyclerun` CLI v2 step-arg migration (WP-005).

WP-002 moved the CLI's default emit path onto `--step` (a canonical Step ULID
ref). WP-005 completes the Substitute-Strangle:

  - `--step` accepts a name-or-ref: a known lifecycle name (`change-started`,
    `change-shipped`) resolves to its canonical Step ULID via WP-002's shared
    `_resolve_step`; an already-canonical `dna:step:<ulid>` ref passes through
    unchanged; an unknown name resolves to `unclassified-lifecycle-step`.
  - `--step-name <string>` is a **deprecated alias**: it emits a plain-English
    deprecation notice to stderr, resolves the legacy string through the same
    `_resolve_step`, and the original string (where trace grouping is needed) is
    carried in the canonical `run_id` field — never in a `step_label` (which does
    not exist in canonical v2.1.0).
  - Passing both `--step` and `--step-name` is an error.

These exercise the CLI end-to-end via subprocess (the same `run_tool` fixture
the other `sulis-emit-*` CLI tests use), pinning the `{ok, data}` JSON envelope
contract and the v2.1.0 schema validity of the persisted instance.
"""

from __future__ import annotations

import json
from pathlib import Path

# The three operational Steps WP-002 pins (TDD §Canonical Identifiers).
_STEP_CHANGE_STARTED = "dna:step:01KT61X5ST01CHANGESTART00A"
_STEP_UNCLASSIFIED = "dna:step:01KT61X5ST03VNC1ASS1F1ED0A"

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_VENDORED = (
    _SCRIPTS_DIR.parent
    / "brain"
    / "compiled"
    / "product-development"
    / "lifecyclerun.schema.json"
)


def _loaded_instance(result) -> dict:
    """Load the persisted JSON-LD instance the CLI reports in its envelope."""
    written = Path(result.data["entities"][0]["path"])
    assert written.exists(), f"expected persisted instance at {written}"
    return json.loads(written.read_text())


class TestStepFlagResolvesNames:
    """`--step` accepts a known lifecycle name and resolves it to a Step ULID."""

    def test_step_flag_resolves(self, tmp_path: Path, run_tool) -> None:
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
        # The free name resolved to the canonical change-started Step ULID.
        assert loaded["step"] == _STEP_CHANGE_STARTED
        # Never a legacy free string, never a non-existent step_label.
        assert "step_name" not in loaded
        assert "step_label" not in loaded

    def test_step_accepts_canonical_ulid_passthrough(
        self, tmp_path: Path, run_tool
    ) -> None:
        # An already-canonical Step ref must pass through untouched.
        result = run_tool(
            "sulis-emit-lifecyclerun",
            "--step", _STEP_CHANGE_STARTED,
            "--outcome", "completed",
            "--repo-root", str(tmp_path),
        )

        assert result.ok, (
            f"expected ok=true, got returncode={result.returncode}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        loaded = _loaded_instance(result)
        assert loaded["step"] == _STEP_CHANGE_STARTED


class TestStepNameDeprecatedAlias:
    """`--step-name` is the deprecated alias: warns, resolves, carries no label."""

    def test_step_name_alias_warns_and_resolves(
        self, tmp_path: Path, run_tool
    ) -> None:
        result = run_tool(
            "sulis-emit-lifecyclerun",
            "--step-name", "some-unmapped-event",
            "--outcome", "completed",
            "--repo-root", str(tmp_path),
        )

        assert result.ok, (
            f"expected ok=true, got returncode={result.returncode}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        # Deprecation notice goes to stderr (plain English, FE-01..FE-10) and
        # names the replacement flag so callers know what to migrate to.
        assert "deprecated" in result.stderr.lower()
        assert "--step" in result.stderr

        loaded = _loaded_instance(result)
        # Unknown name falls back to the unclassified Step.
        assert loaded["step"] == _STEP_UNCLASSIFIED
        # The original string is preserved for trace grouping in run_id…
        assert loaded.get("run_id") == "some-unmapped-event"
        # …and NEVER in a step_label (which does not exist in canonical v2.1.0).
        assert "step_label" not in loaded
        assert "step_name" not in loaded


class TestMutualExclusion:
    """Passing both `--step` and `--step-name` is an error."""

    def test_both_flags_is_error(self, tmp_path: Path, run_tool) -> None:
        result = run_tool(
            "sulis-emit-lifecyclerun",
            "--step", "change-started",
            "--step-name", "some-event",
            "--outcome", "completed",
            "--repo-root", str(tmp_path),
        )

        assert not result.ok, "expected an error when both flags are passed"
        assert result.returncode != 0


class TestOutputValidatesV2:
    """The persisted instance validates against the re-vendored v2.1.0 schema."""

    def test_output_validates_v2(self, tmp_path: Path, run_tool) -> None:
        import jsonschema

        result = run_tool(
            "sulis-emit-lifecyclerun",
            "--step", "change-started",
            "--outcome", "completed",
            "--run-id", "wpx-pipeline-success:WP-012",
            "--repo-root", str(tmp_path),
        )

        assert result.ok, (
            f"expected ok=true, got returncode={result.returncode}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        loaded = _loaded_instance(result)

        validator = jsonschema.Draft202012Validator(
            json.loads(_VENDORED.read_text())
        )
        errors = list(validator.iter_errors(loaded))
        assert errors == [], f"emitted run rejected by re-vendored v2.1.0 schema: {errors}"
