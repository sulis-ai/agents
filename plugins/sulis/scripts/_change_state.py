"""Per-change workflow-stage persistence for the change dashboard.

A change moves through the six-stage Sulis workflow:

    recon -> specify -> design -> implement -> review -> ship

The current stage is persisted as lightweight per-change LOCAL state at
``~/.sulis/changes/{change_id}/state.json`` — alongside the existing
``CONTEXT.md`` / ``session.json`` / ``launch.sh`` that sulis-change writes.

This is deliberately NOT the committed ``.changes/{primitive}-{slug}.yaml``
manifest: stage is a local workflow *position*, not shared/committed state.
Two operators on two machines can be at different stages of the same change;
the manifest is the shared identity, state.json is the per-checkout cursor.

state.json shape::

    {
      "change_id": "01HYQC...",
      "stage": "implement",
      "updated_at": "2026-05-26T11:30:00Z",
      "stage_history": [
        {"stage": "recon",     "at": "2026-05-26T11:00:00Z"},
        {"stage": "specify",   "at": "2026-05-26T11:10:00Z"},
        {"stage": "implement", "at": "2026-05-26T11:30:00Z"}
      ]
    }

``stage_history`` is appended on every write — cheap, and useful for the
dashboard's timeline view (slice B).

Best-effort, mirroring ``_change_context.write_change_context``: a write to
an unwritable path (permission denied, read-only FS, disk full) degrades to
``None`` + a logged warning rather than raising. ``sulis-change start``
stamps the initial stage and must never abort if local state is unwritable.

Kept separate from _wpxlib.py (logically distinct concern; see the same note
in _change_context.py). Stdlib only.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("sulis.change_state")


# Canonical ordered workflow stages. Order is meaningful (recon is first,
# ship is last) and used by the dashboard to render progress.
WORKFLOW_STAGES: tuple[str, ...] = (
    "recon",
    "specify",
    "design",
    "implement",
    "review",
    "ship",
)


def is_valid_stage(stage: str) -> bool:
    """Return True iff ``stage`` is one of the six canonical stages.

    Case-sensitive: stages are lower-case by convention.
    """
    return stage in WORKFLOW_STAGES


def _now_iso() -> str:
    """ISO-8601 UTC timestamp with a trailing Z (e.g. 2026-05-26T11:30:00Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _state_path(change_id: str) -> Path:
    """Absolute path to a change's state.json under ~/.sulis/changes/."""
    return Path.home() / ".sulis" / "changes" / change_id / "state.json"


def _emit_warning(message: str) -> None:
    """Log a best-effort warning. Extracted so tests can assert it fired."""
    logger.warning(message)


def write_change_stage(change_id: str, stage: str) -> Path | None:
    """Write/update ``~/.sulis/changes/{change_id}/state.json`` with ``stage``.

    Creates the change dir if needed. Appends a ``{stage, at}`` row to the
    ``stage_history`` list, preserving any prior history.

    Rejects an unknown ``stage`` (not one of WORKFLOW_STAGES): logs a warning
    and returns ``None`` without writing — a bad stage is a caller bug, but
    crashing the caller (e.g. a stage skill) is worse than degrading.

    Best-effort: an ``OSError`` while creating the dir or writing the file
    degrades to ``None`` + a logged warning rather than raising. Returns the
    absolute path to the written file on success, else ``None``.
    """
    if not is_valid_stage(stage):
        _emit_warning(
            f"refusing to write unknown stage {stage!r} for change {change_id} "
            f"(valid: {', '.join(WORKFLOW_STAGES)})"
        )
        return None

    state_path = _state_path(change_id)
    now = _now_iso()

    # Preserve prior history if a readable state.json already exists.
    history: list[dict] = []
    existing = _read_state(change_id)
    if existing is not None:
        prior = existing.get("stage_history")
        if isinstance(prior, list):
            history = [row for row in prior if isinstance(row, dict)]
    history.append({"stage": stage, "at": now})

    payload = {
        "change_id": change_id,
        "stage": stage,
        "updated_at": now,
        "stage_history": history,
    }

    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        _emit_warning(
            f"could not write stage state at {state_path}: {exc} "
            f"(stage persistence is best-effort; continuing without it)"
        )
        return None
    return state_path.resolve()


def _read_state(change_id: str) -> dict | None:
    """Read + parse state.json. Returns the dict, or None if missing/corrupt."""
    state_path = _state_path(change_id)
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _emit_warning(f"could not read stage state at {state_path}: {exc}")
        return None


def read_change_stage(change_id: str) -> str | None:
    """Return the current stage for a change, or ``None``.

    ``None`` when there is no state.json, the file is unreadable, the JSON is
    malformed, or the ``stage`` key is absent. Degrades quietly — callers
    treat ``None`` as "stage unknown".
    """
    state = _read_state(change_id)
    if state is None:
        return None
    stage = state.get("stage")
    return stage if isinstance(stage, str) else None
