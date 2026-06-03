"""Integration: schema + emitter agree in lockstep (WP-002).

The whole point of the atomic re-vendor (ADR-004) is that there is no window
where a helper emits a run the vendored schema rejects. This test proves it
end-to-end: a real helper call composes a run, the real adapter validates it
against the **re-vendored** vendored schema, and persists it — in one pass,
no monkeypatched schema, no hand-built instance.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from _brain_emit_helper import (
    emit_change_shipped_event,
    emit_change_started_event,
    emit_lifecycle_step_event,
)


_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_VENDORED = (
    _SCRIPTS_DIR.parent
    / "brain"
    / "compiled"
    / "product-development"
    / "lifecyclerun.schema.json"
)


def _validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(json.loads(_VENDORED.read_text()))


@pytest.mark.parametrize(
    "emit",
    [
        lambda root: emit_change_started_event(
            root, change_id="c", handle="h", slug="s", primitive="fix"
        ),
        lambda root: emit_change_shipped_event(
            root, change_id="c", handle="h", slug="s", primitive="fix",
            shipped_sha="abc1234",
        ),
        lambda root: emit_lifecycle_step_event(
            root, step_name="wpx-pipeline-success:WP-012", outcome="completed"
        ),
    ],
)
def test_schema_and_emitter_agree(
    emit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
    run = emit(tmp_path)
    # Non-None means the adapter's reject-on-invalid validate() passed against
    # the re-vendored schema (graceful degradation returns None on any failure).
    assert run is not None, "helper emit returned None — schema/emitter disagree"

    # Belt-and-braces: re-validate the returned payload against the vendored
    # schema directly, proving no reject-on-invalid window.
    errors = list(_validator().iter_errors(run))
    assert errors == [], f"emitted run rejected by re-vendored schema: {errors}"

    # And the run carries a `step` ref, never a legacy `step_name`.
    assert run["step"].startswith("dna:step:")
    assert "step_name" not in run
