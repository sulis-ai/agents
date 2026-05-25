"""Smoke tests for all 9 non-pilot resources.

Each test verifies the happy path: fake binary returns a known envelope,
SDK parses it into the correct Pydantic model, fields are accessible.

These are smoke tests — not exhaustive per-arg coverage. The transport
layer's argv construction is verified in test_pilot.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sulis_execution import SulisExecution


@pytest.fixture
def client(tmp_repo_root: Path, fake_wpx_dir: Path) -> SulisExecution:
    return SulisExecution(
        repo_root=tmp_repo_root,
        project="test-project",
        wpx_dir=fake_wpx_dir,
    )


def _ok(data: dict) -> dict:
    return {"ok": True, "data": data}


# ─── train ───────────────────────────────────────────────────────────


def test_train_queue_list(make_fake_binary, client):
    make_fake_binary(
        "wpx-train",
        stdout_payload=_ok({
            "project": "test-project",
            "eligible_count": 2,
            "ineligible_count": 1,
            "eligible": [
                {"wp": "WP-001", "branch": "feat/wp-001-x", "eligible": True,
                 "reason": "ready", "primitive": "EXPAND", "forced": False},
                {"wp": "WP-002", "branch": "feat/wp-002-y", "eligible": True,
                 "reason": "ready", "primitive": "EXPAND", "forced": False},
            ],
            "ineligible": [
                {"wp": "WP-003", "branch": "feat/wp-003-z", "eligible": False,
                 "reason": "status is in_progress", "primitive": "EXPAND"},
            ],
            "overrides": {"includes": [], "holds": []},
        }),
    )

    result = client.train.queue_list()
    assert result.eligible_count == 2
    assert len(result.eligible) == 2
    assert result.eligible[0].wp == "WP-001"
    assert result.ineligible[0].reason == "status is in_progress"


def test_train_queue_add(make_fake_binary, client):
    make_fake_binary(
        "wpx-train",
        stdout_payload=_ok({
            "wp": "WP-001",
            "action": "force_include_added",
            "overrides_path": "/tmp/overrides.yaml",
            "includes": ["WP-001"],
            "holds": [],
        }),
    )
    result = client.train.queue_add(wp="WP-001", reason="forced for hotfix")
    assert result.wp == "WP-001"
    assert result.action == "force_include_added"
    assert result.includes == ["WP-001"]


def test_train_status(make_fake_binary, client):
    make_fake_binary(
        "wpx-train",
        stdout_payload=_ok({
            "project": "test-project",
            "eligible_count": 3,
            "eligible_wps": ["WP-001", "WP-002", "WP-003"],
            "ineligible_count": 1,
            "overrides": {"includes": [], "holds": []},
            "trigger_state": "ready_size",
            "trigger_reason": "3 WPs ready",
        }),
    )
    result = client.train.status()
    assert result.trigger_state == "ready_size"
    assert result.eligible_count == 3


def test_train_run_not_triggered(make_fake_binary, client):
    """outcome=not_triggered is a normal result (NOT an exception)."""
    make_fake_binary(
        "wpx-train",
        stdout_payload=_ok({
            "result": {
                "train_id": "train-2026-05-21T120000Z",
                "outcome": "not_triggered",
                "eligible_count": 1,
                "eligible_wps": ["WP-001"],
            }
        }),
    )
    result = client.train.run(deploy_workflow="Deploy to Dev")
    assert result.outcome == "not_triggered"
    assert result.eligible_count == 1


def test_train_run_awaiting_gates(make_fake_binary, client):
    """HD-012 RED — outcome=awaiting_gates is a normal result returned
    by `train.run` when called with enable_gate_handoff=True. The
    TrainRunResult Literal must accept it and Pydantic must validate
    the `gate_handoff` envelope.
    """
    make_fake_binary(
        "wpx-train",
        stdout_payload=_ok({
            "result": {
                "train_id": "train-2026-05-23T130000Z",
                "outcome": "awaiting_gates",
                "wps_shipped": ["WP-001", "WP-002"],
                "deploy_url": "https://x.example.com/runs/123",
                "final_merge_sha": "abc1234",
                "record_path": "/tmp/train-runs/train-2026-05-23T130000Z.yaml",
                "gate_handoff": {
                    "batch_start_sha": "0000000",
                    "batch_end_sha": "abc1234",
                    "diff_range": "0000000..abc1234",
                    "wps": ["WP-001", "WP-002"],
                    "next_action": (
                        "Dispatch /sulis:code-review against diff_range; "
                        "then per-WP security review."
                    ),
                },
            }
        }),
    )
    result = client.train.run(
        deploy_workflow="Deploy to Dev",
        enable_gate_handoff=True,
    )
    assert result.outcome == "awaiting_gates"
    assert result.wps_shipped == ["WP-001", "WP-002"]
    assert result.gate_handoff is not None
    assert result.gate_handoff.diff_range == "0000000..abc1234"
    assert result.gate_handoff.wps == ["WP-001", "WP-002"]


def test_train_mark_gates_complete_success(make_fake_binary, client):
    """HD-012 RED — TrainResource.mark_gates_complete promotes a train
    paused at verifying_gates to terminal phase=success."""
    make_fake_binary(
        "wpx-train",
        stdout_payload=_ok({
            "result": {
                "train_id": "train-2026-05-23T130000Z",
                "outcome": "success",
                "phase": "success",
                "record_path": "/tmp/train-runs/train-2026-05-23T130000Z.yaml",
            }
        }),
    )
    result = client.train.mark_gates_complete(
        train_id="train-2026-05-23T130000Z",
    )
    assert result.outcome == "success"
    assert result.phase == "success"
    assert result.train_id == "train-2026-05-23T130000Z"


def test_train_mark_gates_complete_critical_found(make_fake_binary, client):
    """HD-012 RED — critical_found=True returns outcome=gate_blocker
    (phase=failed) without an exception. The Literal must accept both
    success and gate_blocker."""
    make_fake_binary(
        "wpx-train",
        stdout_payload=_ok({
            "result": {
                "train_id": "train-2026-05-23T130000Z",
                "outcome": "gate_blocker",
                "phase": "failed",
                "record_path": "/tmp/train-runs/train-2026-05-23T130000Z.yaml",
            }
        }),
    )
    result = client.train.mark_gates_complete(
        train_id="train-2026-05-23T130000Z",
        gate_findings="/tmp/findings.json",
        critical_found=True,
    )
    assert result.outcome == "gate_blocker"
    assert result.phase == "failed"


def test_train_resource_run_accepts_enable_gate_handoff():
    """HD-012 RED — Static contract check: TrainResource.run accepts
    enable_gate_handoff per HD-007. Catches accidental kwarg removal."""
    import inspect
    from sulis_execution.resources.train import (
        TrainResource, AsyncTrainResource,
    )
    sig = inspect.signature(TrainResource.run)
    assert "enable_gate_handoff" in sig.parameters, (
        "HD-012: TrainResource.run missing enable_gate_handoff kwarg"
    )
    async_sig = inspect.signature(AsyncTrainResource.run)
    assert "enable_gate_handoff" in async_sig.parameters, (
        "HD-012: AsyncTrainResource.run missing enable_gate_handoff kwarg"
    )


def test_train_resource_has_mark_gates_complete():
    """HD-012 RED — TrainResource and AsyncTrainResource expose
    mark_gates_complete corresponding to the wpx-train CLI subcommand."""
    from sulis_execution.resources.train import (
        TrainResource, AsyncTrainResource,
    )
    assert hasattr(TrainResource, "mark_gates_complete"), (
        "HD-012: TrainResource missing mark_gates_complete; "
        "SDK lags HD-007 CLI surface"
    )
    assert hasattr(AsyncTrainResource, "mark_gates_complete"), (
        "HD-012: AsyncTrainResource missing mark_gates_complete"
    )


def test_train_run_result_outcome_literal_includes_awaiting_gates():
    """HD-012 RED — TrainRunResult.outcome Literal must accept the
    awaiting_gates outcome introduced by HD-007. Pydantic validation
    must NOT fail on a synthetic awaiting_gates envelope."""
    from sulis_execution.types import TrainRunResult
    result = TrainRunResult.model_validate({
        "train_id": "train-test",
        "outcome": "awaiting_gates",
        "wps_shipped": ["WP-001"],
        "deploy_url": "https://x.example.com",
        "final_merge_sha": "abc1234",
    })
    assert result.outcome == "awaiting_gates"


# ─── index ───────────────────────────────────────────────────────────


def test_index_flip_status(make_fake_binary, client):
    make_fake_binary(
        "wpx-index",
        stdout_payload=_ok({"wp": "WP-001", "status": "done"}),
    )
    result = client.index.flip_status(wp="WP-001", to="done", expected="in_progress")
    assert result.wp == "WP-001"
    assert result.status == "done"


def test_index_list_ready(make_fake_binary, client):
    make_fake_binary(
        "wpx-index",
        stdout_payload=_ok({
            "ready": ["WP-001", "WP-002"],
            "max_parallel": 5,
            "total_pending": 3,
            "total_done": 12,
            "total_blocked": 1,
            "total_in_progress": 2,
        }),
    )
    result = client.index.list_ready()
    assert result.ready == ["WP-001", "WP-002"]
    assert result.max_parallel == 5


def test_index_mark_downstream_blocked(make_fake_binary, client):
    make_fake_binary(
        "wpx-index",
        stdout_payload=_ok({
            "blocker_wp": "WP-001",
            "flipped_to_dependency_blocked": ["WP-002", "WP-003"],
        }),
    )
    result = client.index.mark_downstream_blocked(wp="WP-001")
    assert result.blocker_wp == "WP-001"
    assert "WP-002" in result.flipped_to_dependency_blocked


# ─── journal ─────────────────────────────────────────────────────────


def test_journal_init(make_fake_binary, client):
    make_fake_binary(
        "wpx-journal",
        stdout_payload=_ok({"path": "/tmp/.executor-WP-001.md"}),
    )
    result = client.journal.init(wp="WP-001")
    assert result.path.endswith("WP-001.md")


def test_journal_complete_step(make_fake_binary, client):
    make_fake_binary(
        "wpx-journal",
        stdout_payload=_ok({
            "wp": "WP-001", "step": 2,
            "completed_at": "2026-05-21T12:30:00Z",
        }),
    )
    result = client.journal.complete_step(
        wp="WP-001", step=2, outcome="3 tests passing"
    )
    assert result.step == 2
    assert result.completed_at is not None


def test_journal_read_returns_typed_value(make_fake_binary, client):
    make_fake_binary(
        "wpx-journal",
        stdout_payload=_ok({"field": "status", "value": "in-progress"}),
    )
    result = client.journal.read(wp="WP-001", field="status")
    assert result.field == "status"
    assert result.value == "in-progress"


# ─── blocker ─────────────────────────────────────────────────────────


def test_blocker_write(make_fake_binary, client):
    make_fake_binary(
        "wpx-blocker",
        stdout_payload=_ok({
            "wp": "WP-001",
            "path": "/tmp/BLOCKER-WP-001.md",
        }),
    )
    result = client.blocker.write(
        wp="WP-001",
        title="Test failure",
        step="3 (GREEN)",
        trigger="budget-exhausted",
        observation="3 retries exhausted",
        root_cause="API response mismatch",
        scope="in-scope-budget-exhausted",
        plain_english="The API changed shape",
        suggested_next="Investigate API contract drift",
    )
    assert result.wp == "WP-001"
    assert result.path.endswith("BLOCKER-WP-001.md")


# ─── findings ────────────────────────────────────────────────────────


def test_findings_register(make_fake_binary, client):
    make_fake_binary(
        "wpx-findings",
        stdout_payload=_ok({
            "sf_id": "SF-001",
            "is_duplicate": False,
            "auto_draft_wp_id": "WP-AUTO-001",
            "source_wp": "WP-005",
            "signature": "a1b2c3d4e5f6",
            "sf_path": "/tmp/findings.md",
        }),
    )
    result = client.findings.register(
        wp="WP-005",
        severity="CONCERN",
        summary="Missing input validation",
        file="src/handler.py",
    )
    assert result.sf_id == "SF-001"
    assert result.is_duplicate is False
    assert result.auto_draft_wp_id == "WP-AUTO-001"


# ─── wp ──────────────────────────────────────────────────────────────


def test_work_package_read_metadata(make_fake_binary, client):
    make_fake_binary(
        "wpx-wp",
        stdout_payload=_ok({
            "field": "branch",
            "value": "feat/wp-001-introduce-payments",
            "present": True,
        }),
    )
    result = client.work_package.read_metadata(wp="WP-001", field="branch")
    assert result.field == "branch"
    assert result.present is True
    assert result.value == "feat/wp-001-introduce-payments"


# ─── worktree ────────────────────────────────────────────────────────


def test_worktree_create(make_fake_binary, client):
    make_fake_binary(
        "wpx-worktree",
        stdout_payload=_ok({
            "wp": "WP-001",
            "worktree_path": "/tmp/wp-001-worktree",
            "branch": "feat/wp-001-x",
            "dev_sha_at_creation": "abc123def",
            "sidecar": "/tmp/.executor-WP-001-dev-sha",
        }),
    )
    result = client.worktree.create(
        wp="WP-001",
        branch="feat/wp-001-x",
        worktree_path="/tmp/wp-001-worktree",
    )
    assert result.dev_sha_at_creation == "abc123def"
    assert result.worktree_path == "/tmp/wp-001-worktree"


# ─── lifecycle ───────────────────────────────────────────────────────


def test_lifecycle_complete(make_fake_binary, client):
    make_fake_binary(
        "wpx-step12",
        stdout_payload=_ok({
            "wp": "WP-001",
            "steps": {
                "append_evidence": {"ok": True, "path": "/tmp/WP-001.md"},
                "flip_status": {"ok": True, "wp": "WP-001", "status": "done"},
                "worktree_remove": {"ok": True, "removed": "/tmp/wt"},
            },
        }),
    )
    result = client.lifecycle.complete(
        wp="WP-001",
        branch="feat/wp-001-x",
        pipeline_result='{"merge_sha": "abc"}',
    )
    assert result.wp == "WP-001"
    assert "append_evidence" in result.steps


# ─── change (sulis-change) ───────────────────────────────────────────


def test_change_start(make_fake_binary, client):
    make_fake_binary(
        "sulis-change",
        stdout_payload=_ok({
            "branch": "change/create-introduce-payments",
            "primitive": "create",
            "slug": "introduce-payments",
            "worktree_path": "/tmp/repo-change-create-introduce-payments",
            "base_branch": "dev",
            "base_sha": "abc123de",
            "metadata_path": "/tmp/.changes/create-introduce-payments.yaml",
        }),
    )
    result = client.change.start(slug="introduce-payments", primitive="create")
    assert result.branch == "change/create-introduce-payments"
    assert result.primitive == "create"
    assert result.slug == "introduce-payments"


def test_change_list(make_fake_binary, client):
    make_fake_binary(
        "sulis-change",
        stdout_payload=_ok({
            "active_count": 2,
            "changes": [
                {"primitive": "create", "slug": "introduce-payments",
                 "branch": "change/create-introduce-payments",
                 "worktree_path": "/tmp/x", "worktree_present": True, "dirty": False},
                {"primitive": "refactor", "slug": "extract-http-client",
                 "branch": "change/refactor-extract-http-client",
                 "worktree_path": "/tmp/y", "worktree_present": True, "dirty": True},
            ],
        }),
    )
    result = client.change.list()
    assert result.active_count == 2
    assert result.changes[1].dirty is True


def test_change_finish_merge(make_fake_binary, client):
    make_fake_binary(
        "sulis-change",
        stdout_payload=_ok({
            "branch": "change/create-introduce-payments",
            "primitive": "create",
            "slug": "introduce-payments",
            "outcome": {"mode": "merge"},
            "cleanup": {
                "worktree_removed": True, "branch_deleted": True,
                "worktree_detail": "removed",
            },
        }),
    )
    result = client.change.finish(
        slug="introduce-payments", primitive="create", merge=True
    )
    assert result.outcome.mode == "merge"
    assert result.cleanup["worktree_removed"] is True
