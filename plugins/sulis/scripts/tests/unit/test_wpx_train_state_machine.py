"""Unit tests for v0.17.0 — train state machine foundation (Phase 1.1).

Tests the in-flight train state primitives:
- init_train_state / read_train_state / write_train_state — round-trip
- update_train_phase — atomic phase transitions; phase history kept
- update_wp_phase_outcome — per-WP outcome updates within a phase
- TrainLock — flock-based concurrency control
- cleanup_train_state — terminal-phase cleanup

These are the foundation primitives; cmd_run integration ships in
Phase 3.1 (resume) when the per-phase factoring lands together with
the resume logic. Foundation tests pin the contract before that work.
"""
from __future__ import annotations

import multiprocessing
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

from _wpxlib import (  # noqa: E402
    PHASES,
    TERMINAL_PHASES,
    TrainLock,
    cleanup_train_state,
    init_train_state,
    read_train_state,
    train_state_path,
    update_train_phase,
    update_wp_phase_outcome,
    write_train_state,
)


# ─── init / read / write round-trip ──────────────────────────────────────


def test_init_train_state_creates_pending_state(tmp_path):
    """init_train_state writes a phase=pending state with the right shape."""
    bundle = [
        {"wp": "WP-001", "branch": "feat/wp-001", "pre_train_sha": "abc"},
        {"wp": "WP-002", "branch": "feat/wp-002", "pre_train_sha": "def"},
    ]
    args_repr = {"project": "x", "deploy_workflow": "Deploy"}
    state = init_train_state(tmp_path, "train-2026-01-01T120000Z", bundle, args_repr)
    assert state["train_id"] == "train-2026-01-01T120000Z"
    assert state["phase"] == "pending"
    assert state["pause_reason"] is None
    assert state["recovery_hint"] is None
    assert state["args"] == args_repr
    assert len(state["bundle"]) == 2
    assert state["bundle"][0]["wp"] == "WP-001"
    assert state["bundle"][0]["phase_outcomes"] == {}
    # phase_history has one entry
    assert len(state["phase_history"]) == 1
    assert state["phase_history"][0]["phase"] == "pending"
    assert state["phase_history"][0]["ended_at"] is None


def test_state_round_trips_through_json(tmp_path):
    """write_train_state + read_train_state preserve all fields."""
    state_path = train_state_path(tmp_path, "train-abc")
    original = {
        "train_id": "train-abc",
        "phase": "rebasing",
        "bundle": [{"wp": "WP-1", "phase_outcomes": {"rebasing": "rebased"}}],
        "phase_history": [
            {"phase": "pending", "started_at": "t0", "ended_at": "t1", "outcome": "advanced"},
            {"phase": "rebasing", "started_at": "t1", "ended_at": None, "outcome": None},
        ],
        "args": {"project": "x"},
    }
    write_train_state(state_path, original)
    loaded = read_train_state(state_path)
    assert loaded == original


def test_read_missing_state_raises_helpful_error(tmp_path):
    """Reading a non-existent state file raises FileNotFoundError with context."""
    state_path = train_state_path(tmp_path, "train-nope")
    with pytest.raises(FileNotFoundError) as exc_info:
        read_train_state(state_path)
    assert "train-nope" in str(exc_info.value)


def test_read_corrupt_state_raises_helpful_error(tmp_path):
    """Reading a corrupt JSON file raises RuntimeError with context."""
    state_path = train_state_path(tmp_path, "train-corrupt")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="corrupt"):
        read_train_state(state_path)


# ─── update_train_phase ─────────────────────────────────────────────────


def test_update_train_phase_advances_with_history(tmp_path):
    """Phase advance closes the previous entry + opens a new one."""
    init_train_state(tmp_path, "train-1", [], {})
    state_path = train_state_path(tmp_path, "train-1")

    update_train_phase(state_path, "rebasing")
    state = read_train_state(state_path)

    assert state["phase"] == "rebasing"
    assert len(state["phase_history"]) == 2
    # Previous phase (pending) now closed
    assert state["phase_history"][0]["phase"] == "pending"
    assert state["phase_history"][0]["ended_at"] is not None
    assert state["phase_history"][0]["outcome"] == "advanced"
    # New phase (rebasing) opened
    assert state["phase_history"][1]["phase"] == "rebasing"
    assert state["phase_history"][1]["ended_at"] is None


def test_update_train_phase_terminal_sets_completed_at(tmp_path):
    """Transition to a terminal phase (success/failed/aborted) sets completed_at."""
    init_train_state(tmp_path, "train-1", [], {})
    state_path = train_state_path(tmp_path, "train-1")
    update_train_phase(state_path, "rebasing")
    update_train_phase(state_path, "success")
    state = read_train_state(state_path)
    assert state["phase"] == "success"
    assert state.get("completed_at") is not None
    assert state["phase_history"][-1]["ended_at"] is not None
    assert state["phase_history"][-1]["outcome"] == "success"


def test_update_train_phase_paused_records_reason_and_hint(tmp_path):
    """Pausing records pause_reason + recovery_hint for inspect to surface."""
    init_train_state(tmp_path, "train-1", [], {})
    state_path = train_state_path(tmp_path, "train-1")
    update_train_phase(state_path, "rebasing")
    update_train_phase(
        state_path,
        "paused",
        pause_reason="bundled-tip-ci-red",
        recovery_hint="Fix the CI failure on feat/wp-001; run wpx-train resume train-1",
    )
    state = read_train_state(state_path)
    assert state["phase"] == "paused"
    assert state["pause_reason"] == "bundled-tip-ci-red"
    assert "wpx-train resume" in state["recovery_hint"]


def test_update_train_phase_rejects_unknown_phase(tmp_path):
    """Unknown phase name raises ValueError."""
    init_train_state(tmp_path, "train-1", [], {})
    state_path = train_state_path(tmp_path, "train-1")
    with pytest.raises(ValueError, match="Unknown phase"):
        update_train_phase(state_path, "ghosting")


def test_update_train_phase_idempotent_for_same_phase(tmp_path):
    """Calling update_train_phase with the current phase doesn't duplicate history."""
    init_train_state(tmp_path, "train-1", [], {})
    state_path = train_state_path(tmp_path, "train-1")
    update_train_phase(state_path, "rebasing")
    history_len = len(read_train_state(state_path)["phase_history"])
    update_train_phase(state_path, "rebasing")
    assert len(read_train_state(state_path)["phase_history"]) == history_len


# ─── update_wp_phase_outcome ────────────────────────────────────────────


def test_update_wp_phase_outcome_records_against_right_bundle_entry(tmp_path):
    """The right bundle entry gets the outcome; others unchanged."""
    bundle = [
        {"wp": "WP-A", "branch": "feat/a"},
        {"wp": "WP-B", "branch": "feat/b"},
    ]
    init_train_state(tmp_path, "train-1", bundle, {})
    state_path = train_state_path(tmp_path, "train-1")
    update_wp_phase_outcome(state_path, "WP-A", "rebasing", "rebased")
    state = read_train_state(state_path)
    assert state["bundle"][0]["phase_outcomes"] == {"rebasing": "rebased"}
    assert state["bundle"][1]["phase_outcomes"] == {}


def test_update_wp_phase_outcome_accumulates_across_phases(tmp_path):
    """Per-WP outcomes accumulate across phases (one dict per WP)."""
    bundle = [{"wp": "WP-A", "branch": "feat/a"}]
    init_train_state(tmp_path, "train-1", bundle, {})
    state_path = train_state_path(tmp_path, "train-1")
    update_wp_phase_outcome(state_path, "WP-A", "rebasing", "rebased")
    update_wp_phase_outcome(state_path, "WP-A", "ci_running", "green")
    update_wp_phase_outcome(state_path, "WP-A", "merging", "merged")
    state = read_train_state(state_path)
    assert state["bundle"][0]["phase_outcomes"] == {
        "rebasing": "rebased",
        "ci_running": "green",
        "merging": "merged",
    }


def test_update_wp_phase_outcome_unknown_wp_raises(tmp_path):
    """Updating an outcome for a WP not in the bundle raises ValueError."""
    bundle = [{"wp": "WP-A", "branch": "feat/a"}]
    init_train_state(tmp_path, "train-1", bundle, {})
    state_path = train_state_path(tmp_path, "train-1")
    with pytest.raises(ValueError, match="WP-X.*not in"):
        update_wp_phase_outcome(state_path, "WP-X", "rebasing", "rebased")


# ─── TrainLock concurrency ──────────────────────────────────────────────


def test_train_lock_exclusive_acquisition(tmp_path):
    """Sequential lock acquisitions work; lock file cleaned up on exit."""
    with TrainLock(tmp_path, "train-1"):
        assert (tmp_path / "train-1.lock").exists()
    assert not (tmp_path / "train-1.lock").exists()


def test_train_lock_releases_on_exception(tmp_path):
    """Lock is released even if the with block raises."""
    with pytest.raises(RuntimeError, match="boom"):
        with TrainLock(tmp_path, "train-1"):
            raise RuntimeError("boom")
    # Subsequent acquisition succeeds
    with TrainLock(tmp_path, "train-1"):
        pass


def _acquire_and_hold(lock_path_str, acquired, release) -> None:
    """Helper for the concurrency test — runs in a subprocess.

    Acquires the flock, writes its PID, *then* signals `acquired` so the
    parent knows the lock is held before it attempts its own acquisition.
    Holds until the parent signals `release` (bounded by a timeout so a
    crashed parent can never orphan this process).
    """
    import fcntl
    fh = open(lock_path_str, "w", encoding="utf-8")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    pid = multiprocessing.current_process().pid
    fh.write(f"{pid}\n")
    fh.flush()
    acquired.set()  # lock is held + PID written — parent may now proceed
    release.wait(timeout=10.0)  # hold until told to release (bounded)
    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    fh.close()


def test_train_lock_second_acquisition_raises(tmp_path):
    """Concurrent acquisition raises RuntimeError naming the existing holder's PID."""
    lock_path = tmp_path / "train-1.lock"
    acquired = multiprocessing.Event()
    release = multiprocessing.Event()
    # Hold the lock from a subprocess until we signal release.
    proc = multiprocessing.Process(
        target=_acquire_and_hold, args=(str(lock_path), acquired, release)
    )
    proc.start()
    try:
        # Deterministic sync: wait for the subprocess to actually hold the
        # lock (no timing window) before attempting our own acquisition.
        assert acquired.wait(timeout=5.0), "subprocess never acquired the lock"
        with pytest.raises(RuntimeError, match="being acted on by PID"):
            with TrainLock(tmp_path, "train-1"):
                pass
    finally:
        release.set()  # let the subprocess release + exit cleanly
        proc.join(timeout=5.0)


# ─── cleanup_train_state ────────────────────────────────────────────────


def test_cleanup_train_state_removes_file(tmp_path):
    """cleanup_train_state deletes the state file."""
    init_train_state(tmp_path, "train-1", [], {})
    state_path = train_state_path(tmp_path, "train-1")
    assert state_path.exists()
    cleanup_train_state(tmp_path, "train-1")
    assert not state_path.exists()


def test_cleanup_train_state_idempotent_when_file_missing(tmp_path):
    """cleanup is a no-op when the file is already gone."""
    cleanup_train_state(tmp_path, "train-nope")  # should not raise


# ─── PHASES + TERMINAL_PHASES constants ─────────────────────────────────


def test_phases_constants():
    """The named phases form the documented state machine."""
    assert "pending" in PHASES
    assert "rebasing" in PHASES
    assert "ci_running" in PHASES
    assert "merging" in PHASES
    assert "deploying" in PHASES
    assert "verifying" in PHASES
    assert "success" in PHASES
    assert "failed" in PHASES
    assert "paused" in PHASES
    assert "aborted" in PHASES
    assert TERMINAL_PHASES == {"success", "failed", "aborted"}
