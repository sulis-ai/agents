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
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("sulis.change_state")


# ─── State-base resolver (single source of truth for ~/.sulis) ─────────────


def sulis_state_base() -> Path:
    """Resolve the Sulis local-state base dir.

    Returns ``Path(os.environ["SULIS_STATE_DIR"])`` when that env var is set
    (used by tests + by any caller that wants an isolated store), else the
    production default ``~/.sulis``.

    This is the ONE place the base is computed. Every reader/writer of the
    local store (``_change_state``, ``_change_context``, ``sulis-change``'s
    start/list/nuke, the global-index reader) routes through here — no module
    should hard-code ``Path.home() / ".sulis"``. Honouring SULIS_STATE_DIR is
    what lets subprocess-based tests point at a tmp dir and stop polluting the
    real home (and, by extension, the dashboard's global view).
    """
    override = os.environ.get("SULIS_STATE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".sulis"


def changes_base() -> Path:
    """The dir holding per-change local state: ``{state_base}/changes/``."""
    return sulis_state_base() / "changes"


def change_dir(change_id: str) -> Path:
    """The per-change local dir: ``{state_base}/changes/{change_id}/``."""
    return changes_base() / change_id


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

# Terminal stages — past the six-stage workflow. A change in a terminal stage
# is done; its audit trail (worktree, branch, change record, in-repo records
# under .architecture/ via #42) is preserved so the cockpit + future sessions
# can retrace what happened. `nuke` refuses on a terminal stage by default
# (the audit trail is the point of archiving).
TERMINAL_STAGES: tuple[str, ...] = (
    "shipped",
)


def is_valid_stage(stage: str) -> bool:
    """Return True iff ``stage`` is one of the workflow OR terminal stages.

    Case-sensitive: stages are lower-case by convention.
    """
    return stage in WORKFLOW_STAGES or stage in TERMINAL_STAGES


def _now_iso() -> str:
    """ISO-8601 UTC timestamp with a trailing Z (e.g. 2026-05-26T11:30:00Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _state_path(change_id: str) -> Path:
    """Absolute path to a change's state.json under {state_base}/changes/."""
    return change_dir(change_id) / "state.json"


def _change_record_path(change_id: str) -> Path:
    """Absolute path to a change's change.json under {state_base}/changes/."""
    return change_dir(change_id) / "change.json"


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


# ─── Global change record (the branch-independent index entry) ─────────────


# The fields the global-index record carries. The record is the cross-change
# source of truth for a change's IDENTITY (everything except the live workflow
# position). The live ``stage`` cursor stays in state.json (it carries history
# and is appended on every advance); ``list_all_changes`` overlays the live
# stage onto each record so there is ONE authoritative live stage (state.json)
# and change.json's ``stage`` is only the seed written at start. This is the
# deliberate "don't duplicate stage in two files that can drift" resolution.
_CHANGE_RECORD_FIELDS: tuple[str, ...] = (
    "change_id",
    "handle",
    "slug",
    "primitive",
    "branch",
    "worktree_path",
    "intent",
    "base_branch",
    "base_sha",
    "created_at",
    "stage",
    "shipped_at",
    "shipped_sha",
)


def write_change_record(change_id: str, record: dict) -> Path | None:
    """Write the full per-change record to ``{change_dir}/change.json``.

    ``record`` supplies the _CHANGE_RECORD_FIELDS; missing keys are written as
    "" (str) except ``stage`` which defaults to "recon". This is the branch-
    independent global-index entry the dashboard + ``sulis-change list`` read
    (git is per-branch, so a committed manifest on the change branch can't be
    enumerated from dev — this record can).

    Best-effort, mirroring write_change_stage: an unwritable path degrades to
    ``None`` + a logged warning rather than raising — ``sulis-change start``
    must never abort because the local store is unwritable.
    """
    payload = {field: record.get(field, "") for field in _CHANGE_RECORD_FIELDS}
    payload["change_id"] = change_id
    if not payload.get("stage"):
        payload["stage"] = "recon"

    record_path = _change_record_path(change_id)
    try:
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        _emit_warning(
            f"could not write change record at {record_path}: {exc} "
            f"(the global-index record is best-effort; continuing without it)"
        )
        return None
    return record_path.resolve()


def read_change_record(change_id: str) -> dict | None:
    """Read + parse ``change.json``. Returns the dict, or None if missing/corrupt.

    NOTE: this collapses two distinct states to ``None`` — "file absent"
    (benign) and "file exists but is unreadable" (load-bearing for safety
    checks). Callers that need to distinguish (e.g. ``sulis-change nuke``'s
    #38 shipped-protection guard, which must refuse to fail open) should
    use :func:`change_record_is_unreadable` instead of (or alongside) this.
    """
    record_path = _change_record_path(change_id)
    if not record_path.exists():
        return None
    try:
        return json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _emit_warning(f"could not read change record at {record_path}: {exc}")
        return None


def change_record_is_unreadable(change_id: str) -> bool:
    """Predicate: is the change record file present-but-unreadable? (#22)

    Returns True iff the ``change.json`` file exists on disk AND
    :func:`read_change_record` returns ``None`` (parse / OS failure).
    Returns False both when the file is absent (legitimate "no record" —
    common immediately after ``start`` before anything writes
    ``change.json``) and when the file reads cleanly.

    Used by safety checks (e.g. ``sulis-change nuke``'s #38 shipped-
    protection guard) that need to distinguish "no record to consult"
    from "record can't be consulted" — the former is benign; the latter
    must refuse to fail open. Without this distinction, a corrupt
    ``change.json`` causes the shipped check to silently pass and the
    nuke proceeds, destroying exactly the audit trail #38 was designed
    to preserve.
    """
    record_path = _change_record_path(change_id)
    if not record_path.exists():
        return False
    return read_change_record(change_id) is None


def session_is_live(change_id: str) -> bool:
    """Honest liveness check for a change's spawned-terminal session.

    The v0.36.0 launcher contract is two-shape: macOS sessions record
    ``pid=None, pid_kind="session", tty="/dev/ttys..."`` because the
    osascript helper pid exits within ~1s — the real liveness handle is
    the spawned tab's controlling tty. Linux + headless paths use
    ``pid=<int>, pid_kind="launcher", tty=None``. A bare ``kill -0 <pid>``
    works for the latter but raises TypeError on a None pid → every
    macOS session was incorrectly reported as "not live" (TaskCreate #32).

    This helper dispatches on ``pid_kind``:

    - ``"session"`` → check the tty's device file exists AND a ``claude``
      process is actually running on it (``ps -t <tty> -o command=``
      contains ``claude``). NOT merely "any process" — after a failed
      launch.sh or after claude exits, the shell is still attached, so
      "any process" reported a dead spawn as live (#87).
    - ``"launcher"`` → check ``os.kill(pid, 0)`` succeeds. Catches the
      ``ProcessLookupError`` for dead pids.
    - missing session.json, malformed json, no usable signal → False.

    Returns True iff the session is genuinely live (a real terminal is
    open on the founder's machine).
    """
    session_path = change_dir(change_id) / "session.json"
    if not session_path.exists():
        return False
    try:
        session = json.loads(session_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    pid_kind = str(session.get("pid_kind") or "").strip().lower()
    if pid_kind == "session":
        tty = session.get("tty")
        if not tty:
            return False
        if not Path(tty).exists():
            return False
        # A live session means the spawned `claude` is actually RUNNING on
        # the tty — not merely that the tty has *a* process (#87). After a
        # failed launch.sh (e.g. a quoting abort), or after claude exits, the
        # shell is still attached to the tty, so "any process" reported a
        # dead spawn as live. The launcher `exec`s `claude ...` (replacing
        # the shell), so a claude process on the tty is the honest signal.
        import subprocess
        try:
            proc = subprocess.run(  # noqa: S603
                ["ps", "-t", tty, "-o", "command="],
                capture_output=True, text=True, timeout=2,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        return any("claude" in line for line in proc.stdout.splitlines())
    if pid_kind == "launcher":
        pid = session.get("pid")
        if not isinstance(pid, int) or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError, OSError):
            return False
        return True
    # Unknown pid_kind / missing field → no usable signal → not live.
    return False


def mark_change_shipped(
    change_id: str,
    *,
    now: str | None = None,
    shipped_sha: str | None = None,
) -> Path | None:
    """Mark a change as shipped (#38): flip stage→'shipped', record shipped_at.

    Idempotent: a second call preserves the original ``shipped_at`` AND the
    original ``shipped_sha`` (the audit trail is the FIRST ship event;
    re-running the ship flow must not rewrite history). Returns the record
    path on success, None if the record doesn't exist.

    ``shipped_sha`` (#56 Part 2) pins the change-branch tip at ship time —
    "the state it was in when we shipped". It joins ``base_sha`` (the fork
    point) so the cockpit can show the exact shipped diff and
    ``sulis-change recreate`` can re-materialise the worktree from a stable
    ref even after the worktree is removed.

    No deletion of the *record*: the branch + change record stay so the
    cockpit + future sessions can retrace. (The ship flow removes the
    redundant *worktree* separately, gated on ``session_is_live``; recreate
    brings it back on demand.) Permanent removal is a separate explicit
    founder act (`/sulis:change nuke --force`).
    """
    record = read_change_record(change_id)
    if record is None:
        return None
    timestamp = now or _now_iso()
    # Idempotency: preserve the first ship timestamp.
    existing = str(record.get("shipped_at") or "").strip()
    if not existing:
        record["shipped_at"] = timestamp
    # Idempotency: preserve the first shipped_sha (the pinned shipped state).
    if shipped_sha and not str(record.get("shipped_sha") or "").strip():
        record["shipped_sha"] = shipped_sha
    # Persist `stage: shipped` on BOTH stores: state.json (the overlay
    # list_all_changes reads) AND change.json (what direct `read_change_record`
    # readers like cmd_nuke see). Without this update to the record itself,
    # the two stores disagree and the nuke shipped-protection misfires.
    record["stage"] = "shipped"
    write_change_stage(change_id, "shipped")
    return write_change_record(change_id, record)


def list_all_changes() -> list[dict]:
    """Enumerate every change.json under ``{state_base}/changes/*/``.

    Returns the full records, branch-independent (no git needed), sorted
    most-recent-first by ``created_at`` (records without a parseable
    ``created_at`` sort last). The live ``stage`` from each change's state.json
    is overlaid onto the record so the returned ``stage`` reflects the current
    workflow position (the single source of truth), not just the seed value.

    Dirs without a readable change.json (legacy/partial changes that predate
    this record, or a corrupt file) are skipped — the record is the index, and
    a change without one isn't in the global view until it's re-recorded.

    Best-effort: an unreadable changes base yields ``[]``.
    """
    base = changes_base()
    try:
        candidates = [d for d in base.iterdir() if d.is_dir()]
    except OSError:
        return []

    records: list[dict] = []
    for d in candidates:
        record = read_change_record(d.name)
        if record is None:
            continue
        live_stage = read_change_stage(d.name)
        if live_stage is not None:
            record["stage"] = live_stage
        records.append(record)

    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records
