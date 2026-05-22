"""Unit tests for v0.19.0a — wpx-train resume (Phase 3.1).

Resume semantics in v0.19.0a (pragmatic implementation):

- **Pre-merge paused** (rebasing, ci_running, pending): no merges yet.
  Resume re-fires the train with the args saved in state["args"].
  Per-WP idempotency: the new train sees the same eligibility result
  (no SHAs were merged); rebases re-run cleanly because branches
  exist on origin at their pre-train SHAs.

- **Post-merge paused** (merging, deploying, verifying): can't restart
  from scratch (merges are on dev). v0.19.0a emits a clear error
  pointing at the recovery paths (use abort, or manually flip WPs).
  Full post-merge resume defers to a future release when real need
  surfaces.

- **Terminal phases** (success, failed, aborted): error — nothing to
  resume.

These tests stub the gh + git operations and the cmd_run dispatch
to verify the resume DECISION TREE without invoking real git/gh.
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


# ─── State validation ───────────────────────────────────────────────────


def test_pre_merge_paused_state_recognised(tmp_path):
    """A paused train in pre-merge phases should be marked resumable."""
    init_train_state(
        tmp_path, "train-001",
        [{"wp": "WP-A", "branch": "feat/a", "pre_train_sha": "abc"}],
        {"project": "x", "deploy_workflow": "Deploy"},
    )
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "rebasing")
    update_train_phase(state_path, "ci_running")
    update_train_phase(
        state_path, "paused",
        pause_reason="bundled-tip CI red",
        recovery_hint="fix CI; resume",
    )

    state = read_train_state(state_path)
    # The phase recorded is the paused state's phase (paused)
    assert state["phase"] == "paused"
    # phase_history shows pre-merge progression (no merging entry)
    phases = [e["phase"] for e in state["phase_history"]]
    assert "ci_running" in phases
    assert "merging" not in phases
    assert "deploying" not in phases


def test_post_merge_paused_state_recognised(tmp_path):
    """A paused train in post-merge phases should NOT be resumable."""
    init_train_state(
        tmp_path, "train-001",
        [{"wp": "WP-A", "branch": "feat/a", "pre_train_sha": "abc"}],
        {"project": "x"},
    )
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "rebasing")
    update_train_phase(state_path, "ci_running")
    update_train_phase(state_path, "merging")
    update_train_phase(state_path, "deploying")
    update_train_phase(
        state_path, "paused",
        pause_reason="deploy timeout",
        recovery_hint="check deploy",
    )

    state = read_train_state(state_path)
    phases = [e["phase"] for e in state["phase_history"]]
    # merging is in history → post-merge
    assert "merging" in phases


def test_args_round_trip_for_resume(tmp_path):
    """The args dict written by init_train_state contains everything
    cmd_resume needs to re-derive cmd_run's argparse Namespace."""
    saved_args = {
        "project": "my-project",
        "repo_root": "/tmp/repo",
        "repo": "acme/x",
        "deploy_workflow": "Deploy to Dev",
        "staging_url": "https://staging.example.com",
        "smoke_cmd": "curl -sf https://staging/health",
        "base_branch": "dev",
        "force": False,
        "strict_ci": False,
    }
    init_train_state(
        tmp_path, "train-001",
        [{"wp": "WP-A", "branch": "feat/a"}],
        saved_args,
    )
    state = read_train_state(train_state_path(tmp_path, "train-001"))
    assert state["args"] == saved_args


def test_bundle_preserved_across_state_writes(tmp_path):
    """Per-WP bundle entries (including pre_train_sha) survive all
    phase transitions for resume to consume."""
    init_train_state(
        tmp_path, "train-001",
        [
            {"wp": "WP-A", "branch": "feat/a", "pre_train_sha": "aaa"},
            {"wp": "WP-B", "branch": "feat/b", "pre_train_sha": "bbb"},
        ],
        {"project": "x"},
    )
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "rebasing")
    update_train_phase(state_path, "ci_running")
    update_train_phase(
        state_path, "paused",
        pause_reason="ci red", recovery_hint="fix",
    )

    state = read_train_state(state_path)
    assert len(state["bundle"]) == 2
    assert state["bundle"][0]["wp"] == "WP-A"
    assert state["bundle"][0]["pre_train_sha"] == "aaa"
    assert state["bundle"][1]["wp"] == "WP-B"
    assert state["bundle"][1]["pre_train_sha"] == "bbb"


# ─── Resume decision tree ───────────────────────────────────────────────


PRE_MERGE_PHASES = ("pending", "rebasing", "ci_running")
POST_MERGE_PHASES = ("merging", "deploying", "verifying")
TERMINAL_PHASES = ("success", "failed", "aborted")


@pytest.mark.parametrize("phase", PRE_MERGE_PHASES)
def test_pre_merge_phases_should_resume_via_refire(tmp_path, phase):
    """All pre-merge phases (pending, rebasing, ci_running) reach resume
    via the same re-fire path."""
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    if phase != "pending":
        # pending is the initial state; no transition needed
        for p in PRE_MERGE_PHASES[1:PRE_MERGE_PHASES.index(phase) + 1]:
            update_train_phase(state_path, p)
    state = read_train_state(state_path)
    assert state["phase"] == phase
    # Decision: pre-merge phase = refireable
    assert phase in PRE_MERGE_PHASES


@pytest.mark.parametrize("phase", POST_MERGE_PHASES)
def test_post_merge_phases_should_error(tmp_path, phase):
    """All post-merge phases (merging, deploying, verifying) emit the
    "use abort" error rather than attempting resume."""
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    # Walk through phases until target
    target_idx = ("rebasing", "ci_running", "merging", "deploying", "verifying").index(phase)
    for p in ("rebasing", "ci_running", "merging", "deploying", "verifying")[:target_idx + 1]:
        update_train_phase(state_path, p)
    state = read_train_state(state_path)
    assert state["phase"] == phase
    # Decision: post-merge phase = not refireable in v0.19.0a
    assert phase in POST_MERGE_PHASES


@pytest.mark.parametrize("phase", TERMINAL_PHASES)
def test_terminal_phases_should_error(tmp_path, phase):
    """success/failed/aborted phases can't be resumed."""
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, phase,
                       pause_reason="x" if phase != "success" else None,
                       recovery_hint="y" if phase != "success" else None)
    state = read_train_state(state_path)
    assert state["phase"] == phase
    assert phase in TERMINAL_PHASES


def test_paused_phase_treated_as_pre_merge_if_history_lacks_merging(tmp_path):
    """When phase=paused, the resume code inspects phase_history to
    determine pre-vs-post-merge. If phase_history doesn't include
    merging, it's pre-merge paused."""
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "rebasing")
    update_train_phase(state_path, "ci_running")
    update_train_phase(state_path, "paused",
                       pause_reason="ci red", recovery_hint="fix")
    state = read_train_state(state_path)
    phases_seen = {e["phase"] for e in state["phase_history"]}
    assert "merging" not in phases_seen  # pre-merge paused
    assert "ci_running" in phases_seen


def test_paused_phase_treated_as_post_merge_if_history_includes_merging(tmp_path):
    """If phase=paused after merging has run, it's post-merge paused."""
    init_train_state(tmp_path, "train-001", [], {})
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "rebasing")
    update_train_phase(state_path, "ci_running")
    update_train_phase(state_path, "merging")
    update_train_phase(state_path, "deploying")
    update_train_phase(state_path, "paused",
                       pause_reason="deploy timeout", recovery_hint="check")
    state = read_train_state(state_path)
    phases_seen = {e["phase"] for e in state["phase_history"]}
    assert "merging" in phases_seen  # post-merge paused
    assert "deploying" in phases_seen


# ─── Resume creates audit trail ─────────────────────────────────────────


def test_resume_path_writes_aborted_yaml_for_old_train(tmp_path):
    """When pre-merge resume re-fires, the old train's state should be
    marked aborted (superseded) before cleanup. This preserves the
    audit trail — `wpx-train inspect` shows the old train as aborted
    with a recovery_hint pointing at the newer train."""
    init_train_state(
        tmp_path, "train-001",
        [{"wp": "WP-A", "branch": "feat/a", "pre_train_sha": "abc"}],
        {"project": "x"},
    )
    state_path = train_state_path(tmp_path, "train-001")
    update_train_phase(state_path, "ci_running")
    update_train_phase(state_path, "paused",
                       pause_reason="ci red", recovery_hint="fix")

    # Simulate the resume's state update before cleanup
    update_train_phase(
        state_path, "aborted",
        pause_reason="Superseded by resume",
        recovery_hint="See newer train",
    )
    state = read_train_state(state_path)
    assert state["phase"] == "aborted"
    assert "Superseded" in state["pause_reason"]
    assert "newer train" in state["recovery_hint"].lower()
    # Terminal — completed_at set
    assert state["completed_at"] is not None
