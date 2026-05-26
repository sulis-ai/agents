"""Unit tests for the ``sulis-list-changes`` Python helper (WP-002).

The cockpit MVP's ``SulisChangeStoreReader`` adapter (WP-003) shells out to
this script to enumerate the change store. The script is the one shimming
surface between TypeScript and the canonical Python change store; ADR-008
alternative 2.

Contract surface (three subcommands):

- ``sulis-list-changes list``           → JSON array of change records.
- ``sulis-list-changes get <id>``       → JSON object or ``null``.
- ``sulis-list-changes stage <id>``     → JSON string or ``null``.

The helper wraps ``_change_state.list_all_changes()`` /
``read_change_record(id)`` / ``read_change_stage(id)`` verbatim and emits
their output as JSON. Field-shape changes in ``_change_state.py`` propagate
through unchanged — the TypeScript adapter handles the case-translation.

Read-only by contract: the helper never writes to the change store. The
final test snapshots the dir contents before/after every invocation as a
mechanical assertion of that property.

Tests invoke the wrapper as a subprocess (the wrapper IS the contract
surface). ``SULIS_STATE_DIR`` is set per-test by the repo-wide conftest
fixture; we extend it with a seeded change store.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# Documentation block — the inventory grep referenced in the WP's Blue DoD.
# These two greps return no matches against sulis_list_changes.py; the
# script is read-only by contract. The mechanical assertion lives in
# ``test_no_writes_to_state_dir``.
#
#   grep -n 'open(.*"w"'  sulis_list_changes.py
#   grep -n 'write'       sulis_list_changes.py


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
_WRAPPER = _SCRIPTS_DIR / "sulis-list-changes"

_ULID_A = "01HYQC71000000000000000001"
_ULID_B = "01HYQC71000000000000000002"


# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def seeded_state_dir(tmp_path, monkeypatch):
    """Seed two change records under SULIS_STATE_DIR.

    SULIS_STATE_DIR is already set to a per-test tmp dir by the repo-wide
    conftest fixture. We extend it with two change subdirs, each with a
    minimal change.json. Returns the state_dir Path.
    """
    state_dir = Path(os.environ["SULIS_STATE_DIR"])
    changes = state_dir / "changes"
    changes.mkdir(parents=True, exist_ok=True)

    record_a = {
        "change_id": _ULID_A,
        "handle": "CH-AAA",
        "slug": "alpha",
        "primitive": "create",
        "branch": "change/create-alpha",
        "worktree_path": "/tmp/alpha",
        "intent": "first change",
        "base_branch": "dev",
        "created_at": "2026-05-26T10:00:00Z",
        "stage": "specify",
    }
    record_b = {
        "change_id": _ULID_B,
        "handle": "CH-BBB",
        "slug": "beta",
        "primitive": "fix",
        "branch": "change/fix-beta",
        "worktree_path": "/tmp/beta",
        "intent": "second change",
        "base_branch": "dev",
        "created_at": "2026-05-26T11:00:00Z",
        "stage": "recon",
    }
    for rec in (record_a, record_b):
        d = changes / rec["change_id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "change.json").write_text(
            json.dumps(rec, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    # Overlay a state.json for record_a so the "live stage" overlay can be
    # observed (per _change_state.list_all_changes contract).
    (changes / _ULID_A / "state.json").write_text(
        json.dumps(
            {
                "change_id": _ULID_A,
                "stage": "design",
                "updated_at": "2026-05-26T12:00:00Z",
                "stage_history": [
                    {"stage": "specify", "at": "2026-05-26T10:00:00Z"},
                    {"stage": "design", "at": "2026-05-26T12:00:00Z"},
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return state_dir


def _run(*args, check=False):
    """Invoke the wrapper as a subprocess, capturing stdout/stderr/returncode.

    Uses ``python3`` to invoke the wrapper directly so we don't depend on the
    +x bit being preserved across git operations during early local runs;
    the wrapper still ships +x for shell users (asserted separately).
    """
    proc = subprocess.run(
        [sys.executable, str(_WRAPPER), *args],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    if check and proc.returncode != 0:
        raise AssertionError(
            f"wrapper failed: rc={proc.returncode}\n"
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
        )
    return proc


def _snapshot(state_dir: Path) -> dict[str, bytes]:
    """Return {relpath: file-bytes} for every regular file under state_dir."""
    snap: dict[str, bytes] = {}
    for path in sorted(state_dir.rglob("*")):
        if path.is_file():
            snap[str(path.relative_to(state_dir))] = path.read_bytes()
    return snap


# ─── list ────────────────────────────────────────────────────────────────


def test_list_emits_array_for_seeded_state_dir(seeded_state_dir):
    proc = _run("list")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert isinstance(payload, list)
    assert len(payload) == 2
    ids = {row["change_id"] for row in payload}
    assert ids == {_ULID_A, _ULID_B}


def test_empty_state_dir_emits_empty_array(tmp_path):
    # conftest already isolated SULIS_STATE_DIR; no change subdirs seeded.
    proc = _run("list")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == []


# ─── get ────────────────────────────────────────────────────────────────


def test_get_returns_record_for_known_id(seeded_state_dir):
    proc = _run("get", _ULID_A)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload is not None
    assert payload["change_id"] == _ULID_A
    assert payload["slug"] == "alpha"
    # The raw record (read_change_record) returns the seed stage, not the
    # state.json overlay — only list_all_changes overlays. This is the
    # contract.
    assert payload["stage"] == "specify"


def test_get_returns_null_for_unknown_id(seeded_state_dir):
    proc = _run("get", "01BOGUS000000000000000000")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) is None


# ─── stage ──────────────────────────────────────────────────────────────


def test_stage_returns_overlay_from_state_json(seeded_state_dir):
    # Record_A has a state.json overlaying stage: "design" — that is the
    # live stage that read_change_stage returns (separate from change.json's
    # seed stage of "specify").
    proc = _run("stage", _ULID_A)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == "design"


# ─── Error handling ─────────────────────────────────────────────────────


def test_unknown_command_exits_2_with_stderr_error(seeded_state_dir):
    proc = _run("invent-a-command")
    assert proc.returncode == 2
    # stderr must carry a JSON error object, stdout must NOT carry one
    # (contract per WP Shape table: errors go to stderr, exit 2).
    assert proc.stdout.strip() == ""
    err = json.loads(proc.stderr)
    assert "error" in err
    assert err["error"]


# ─── Read-only invariant ────────────────────────────────────────────────


def test_no_writes_to_state_dir(seeded_state_dir):
    before = _snapshot(seeded_state_dir)
    # Run every read subcommand the helper exposes.
    _run("list", check=True)
    _run("get", _ULID_A, check=True)
    _run("get", "01BOGUS000000000000000000", check=True)
    _run("stage", _ULID_A, check=True)
    after = _snapshot(seeded_state_dir)
    assert before == after, "helper must not write to the change store"
