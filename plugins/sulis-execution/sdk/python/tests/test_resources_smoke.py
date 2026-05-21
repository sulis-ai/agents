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


def test_index_propagate_blocked(make_fake_binary, client):
    make_fake_binary(
        "wpx-index",
        stdout_payload=_ok({
            "blocker_wp": "WP-001",
            "flipped_to_dependency_blocked": ["WP-002", "WP-003"],
        }),
    )
    result = client.index.propagate_blocked(wp="WP-001")
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


def test_wp_read_frontmatter(make_fake_binary, client):
    make_fake_binary(
        "wpx-wp",
        stdout_payload=_ok({
            "field": "branch",
            "value": "feat/wp-001-introduce-payments",
            "present": True,
        }),
    )
    result = client.wp.read_frontmatter(wp="WP-001", field="branch")
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


# ─── step12 ──────────────────────────────────────────────────────────


def test_step12_wrap(make_fake_binary, client):
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
    result = client.step12.wrap(
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
