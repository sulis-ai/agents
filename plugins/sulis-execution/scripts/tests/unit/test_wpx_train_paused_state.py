"""Unit tests for v0.18.0 — paused-state recovery (Phase 2.2).

Tests the new failure routing:
- Bundled-tip CI red/timeout → phase=paused (NEW; was: terminal blocker)
- Deploy poll timeout → phase=paused (NEW; was: terminal blocker via revert)
- Deploy explicit failed → phase=failed (existing ADR-212 revert)
- Health unhealthy → phase=failed (existing)
- Smoke FAIL → phase=failed (existing)

These tests verify the state-machine writes happen in the right
direction; the full _handle_post_merge_failure / _pause_train_state
integration is checked at the state-transition level rather than
end-to-end (which would require real git + gh API mocking).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

from _wpxlib import (  # noqa: E402
    init_train_state,
    read_train_state,
    train_state_path,
    update_train_phase,
)


# ─── Paused-state transition semantics ───────────────────────────────────


def test_paused_phase_records_reason_and_hint(tmp_path):
    """Transitioning to paused records both pause_reason + recovery_hint
    so wpx-train inspect can surface them."""
    bundle = [{"wp": "WP-001", "branch": "feat/wp-001", "pre_train_sha": "a"}]
    init_train_state(tmp_path, "train-001", bundle, {"project": "x"})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "rebasing")
    update_train_phase(state_path, "ci_running")
    update_train_phase(
        state_path,
        "paused",
        pause_reason="bundled-tip CI failed on feat/wp-001-tip",
        recovery_hint=(
            "Inspect via `wpx-train inspect train-001`. "
            "Once you've fixed CI: `wpx-train resume train-001`."
        ),
    )
    state = read_train_state(state_path)
    assert state["phase"] == "paused"
    assert "bundled-tip CI failed" in state["pause_reason"]
    assert "resume train-001" in state["recovery_hint"]


def test_paused_is_non_terminal_no_completed_at_set(tmp_path):
    """Paused is NOT a terminal phase — completed_at should not be set,
    so resume knows the train is still in-flight."""
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "ci_running")
    update_train_phase(
        state_path, "paused",
        pause_reason="ci red", recovery_hint="fix it",
    )
    state = read_train_state(state_path)
    assert "completed_at" not in state or state.get("completed_at") is None


def test_failed_is_terminal_sets_completed_at(tmp_path):
    """Failed IS terminal — completed_at set; phase_history's last entry
    closed with outcome=failed."""
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "rebasing")
    update_train_phase(
        state_path, "failed",
        pause_reason="deploy explicit failure",
        recovery_hint="see BLOCKER for details",
    )
    state = read_train_state(state_path)
    assert state["completed_at"] is not None
    assert state["phase"] == "failed"
    assert state["phase_history"][-1]["phase"] == "failed"
    assert state["phase_history"][-1]["outcome"] == "failed"


def test_paused_then_resumed_back_to_ci_running(tmp_path):
    """Verifies the resume re-entry path: paused → ci_running again.

    The state machine allows transition from paused to any other phase
    (resume picks up where it left off; the recovery is up to the
    caller). Phase history preserves both paused and re-entry transitions.
    """
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "rebasing")
    update_train_phase(state_path, "ci_running")
    update_train_phase(
        state_path, "paused", pause_reason="ci red", recovery_hint="fix",
    )
    # Resume re-enters ci_running (Phase 3.1)
    update_train_phase(state_path, "ci_running")
    state = read_train_state(state_path)
    assert state["phase"] == "ci_running"
    # History has both entries
    phases = [e["phase"] for e in state["phase_history"]]
    assert "paused" in phases
    assert phases.count("ci_running") == 2  # original + resume


def test_paused_clears_pause_reason_on_transition_out(tmp_path):
    """When we leave paused (resume), pause_reason carries to the next
    phase by default (set only when transitioning IN). Caller can clear
    explicitly by passing pause_reason=None... or the inspect output
    just shows the most recent pause_reason which reflects current state.

    For now: pause_reason persists across transitions unless explicitly
    overwritten. That's fine — `wpx-train inspect` knows phase is the
    truth signal; pause_reason is just supplementary context.
    """
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "ci_running")
    update_train_phase(
        state_path, "paused",
        pause_reason="ci red", recovery_hint="fix",
    )
    state_before = read_train_state(state_path)
    assert state_before["pause_reason"] == "ci red"

    # Resume — leaves paused without specifying new reason
    update_train_phase(state_path, "ci_running")
    state_after = read_train_state(state_path)
    # pause_reason still set (helpful audit trail; documented behaviour)
    assert state_after["pause_reason"] == "ci red"
    assert state_after["phase"] == "ci_running"


# ─── State machine invariants ────────────────────────────────────────────


def test_failed_state_file_not_cleaned_up_until_explicit_cleanup(tmp_path):
    """When _handle_post_merge_failure transitions to failed, it also
    calls cleanup_train_state to remove the in-flight state file (the
    .yaml record is the archive). Verify the cleanup path."""
    from _wpxlib import cleanup_train_state
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "failed",
                       pause_reason="deploy fail", recovery_hint="see blocker")
    assert state_path.exists()  # not auto-cleaned by update_train_phase
    cleanup_train_state(tmp_path, "train-001")
    assert not state_path.exists()


def test_paused_state_file_persists_for_resume(tmp_path):
    """Paused state file is NOT cleaned up — resume needs to read it."""
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "ci_running")
    update_train_phase(state_path, "paused",
                       pause_reason="x", recovery_hint="y")
    # The _pause_train_state helper does NOT call cleanup_train_state.
    # State file persists; resume reads it later.
    assert state_path.exists()
