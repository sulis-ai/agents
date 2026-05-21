"""Pydantic models for sulis-execution SDK responses.

Generated shapes from sulis-execution.openapi.yaml. One model per
operation result.

Per the SDK spec v0.2.0 Part 5: all models use Pydantic v2; field
case is snake_case preserved from the wire; extra=allow tolerates
forward-compatible fields from the CLI.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel


class _Base(BaseModel):
    model_config = {"extra": "allow"}


# ─── pipeline ────────────────────────────────────────────────────────


class PipelineResult(_Base):
    wp: str
    outcome: Literal["success", "blocker", "error", "pending"]
    merge_sha: Optional[str] = None
    deploy_url: Optional[str] = None
    deploy_workflow_run: Optional[str] = None
    health_status: Optional[Literal["healthy", "unhealthy", "skipped"]] = None
    health_url: Optional[str] = None
    smoke_verdict: Optional[str] = None
    blocker_reason: Optional[str] = None
    ci_poll_skipped: bool = False
    merge_already_complete: bool = False
    started_at: datetime
    completed_at: Optional[datetime] = None


# ─── train ───────────────────────────────────────────────────────────


class EligibilityEntry(_Base):
    wp: str
    branch: Optional[str] = None
    eligible: bool
    reason: str
    primitive: Optional[str] = None
    forced: bool = False


class TrainOverrides(_Base):
    includes: list[str] = []
    holds: list[str] = []


class TrainQueueListResult(_Base):
    project: str
    index_md: Optional[str] = None
    eligible_count: int
    ineligible_count: int
    eligible: list[EligibilityEntry] = []
    ineligible: list[EligibilityEntry] = []
    overrides: TrainOverrides = TrainOverrides()


class TrainOverrideResult(_Base):
    wp: str
    action: Literal["force_include_added", "hold_added", "noop"]
    reason: Optional[str] = None
    overrides_path: Optional[str] = None
    includes: list[str] = []
    holds: list[str] = []


class TrainStatusResult(_Base):
    project: str
    eligible_count: int
    eligible_wps: list[str] = []
    ineligible_count: int
    overrides: TrainOverrides = TrainOverrides()
    trigger_state: Literal["not_ready", "ready_size", "waiting"]
    trigger_reason: Optional[str] = None
    last_train_run: Optional[str] = None


class TrainDoctorIssue(_Base):
    kind: str
    wp: Optional[str] = None
    detail: str


class TrainDoctorResult(_Base):
    project: str
    issue_count: int
    issues: list[TrainDoctorIssue] = []
    note_orphan_branches: Optional[str] = None


class TrainBundleEntry(_Base):
    wp: Optional[str] = None
    branch: Optional[str] = None
    pre_train_sha: Optional[str] = None
    rebased_to_sha: Optional[str] = None
    merge_sha_on_dev: Optional[str] = None


class TrainRunResult(_Base):
    train_id: str
    outcome: Literal[
        "success", "not_triggered", "nothing_to_pack", "blocker", "error"
    ]
    wps_shipped: list[str] = []
    eligible_count: Optional[int] = None
    eligible_wps: list[str] = []
    deploy_url: Optional[str] = None
    final_merge_sha: Optional[str] = None
    record_path: Optional[str] = None
    bundle: list[TrainBundleEntry] = []
    rebase_failures: list[dict[str, Any]] = []
    train_blocker_path: Optional[str] = None


# ─── index ───────────────────────────────────────────────────────────


class IndexFlipStatusResult(_Base):
    wp: str
    status: str


class IndexListReadyResult(_Base):
    ready: list[str] = []
    max_parallel: int
    total_pending: int
    total_done: int
    total_blocked: int
    total_in_progress: int


class IndexReadConfigResult(_Base):
    config: dict[str, str]


class IndexPropagateBlockedResult(_Base):
    blocker_wp: str
    flipped_to_dependency_blocked: list[str] = []


class IndexAddWpResult(_Base):
    wp: str
    added: bool


class IndexSyncAutoDraftsResult(_Base):
    synced_count: int
    synced: list[str] = []


# ─── journal ─────────────────────────────────────────────────────────


class JournalPathResult(_Base):
    path: str


class JournalStepResult(_Base):
    wp: str
    step: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JournalAttemptResult(_Base):
    wp: str
    step: int
    attempt: int


class JournalPreflightResult(_Base):
    wp: str
    tool: str
    status: str


class JournalPostdeployResult(_Base):
    wp: str
    verdict: str


class JournalSeedPlanResult(_Base):
    wp: str
    approach: str
    item_count: int


class JournalMarkPlanItemResult(_Base):
    wp: str
    item: int
    status: str


class JournalAddPlanItemResult(_Base):
    wp: str
    item: int
    description: str
    step: str
    status: str


class JournalReadResult(_Base):
    field: str
    value: Any = None


# ─── blocker ─────────────────────────────────────────────────────────


class BlockerWriteResult(_Base):
    wp: str
    path: str


class BlockerArchiveResult(_Base):
    wp: str
    archived_to: str
    original: str


# ─── findings ────────────────────────────────────────────────────────


class FindingsRegisterResult(_Base):
    sf_id: str
    is_duplicate: bool
    auto_draft_wp_id: Optional[str] = None
    source_wp: str
    signature: str
    sf_path: Optional[str] = None


class FindingsAutoDraftWpResult(_Base):
    auto_wp_id: str
    path: str


# ─── wp ──────────────────────────────────────────────────────────────


class WpReadFrontmatterResult(_Base):
    field: str
    value: Any = None
    frontmatter: Optional[dict[str, Any]] = None
    present: bool


class WpAppendEvidenceResult(_Base):
    wp: str
    path: str


# ─── worktree ────────────────────────────────────────────────────────


class WorktreeCreateResult(_Base):
    wp: str
    worktree_path: str
    branch: str
    dev_sha_at_creation: str
    sidecar: str


class WorktreeRemoveResult(_Base):
    wp: str
    removed: str


# ─── step12 ──────────────────────────────────────────────────────────


class Step12WrapResult(_Base):
    wp: str
    steps: dict[str, Any]


# ─── change (sulis-change) ───────────────────────────────────────────


class ChangeStartResult(_Base):
    branch: str
    primitive: str
    slug: str
    worktree_path: str
    base_branch: str
    base_sha: Optional[str] = None
    metadata_path: Optional[str] = None


class ChangeAdoptResult(_Base):
    branch: str
    primitive: str
    slug: str
    worktree_path: str
    adopt_mode: str
    moved: list[str] = []
    uncommitted_count: int = 0
    local_commits_count: int = 0


class ChangeFinishOutcome(_Base):
    mode: Literal["merge", "pr"]
    pr_url: Optional[str] = None


class ChangeFinishResult(_Base):
    branch: str
    primitive: str
    slug: str
    outcome: ChangeFinishOutcome
    cleanup: dict[str, Any] = {}


class ChangeListEntry(_Base):
    primitive: str
    slug: str
    branch: str
    worktree_path: Optional[str] = None
    worktree_present: bool
    dirty: bool = False


class ChangeListResult(_Base):
    active_count: int
    changes: list[ChangeListEntry] = []


class ChangeStatusResult(_Base):
    branch: str
    primitive: str
    slug: str
    worktree_path: Optional[str] = None
    worktree_present: bool
    branch_sha: Optional[str] = None
    base_sha: Optional[str] = None
    ahead_of_base: Optional[int] = None
    behind_base: Optional[int] = None
    metadata: dict[str, Any] = {}
