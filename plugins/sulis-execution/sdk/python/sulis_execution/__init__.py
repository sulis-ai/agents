"""sulis-execution — typed Python SDK for the sulis-execution plugin's CLI tools.

Per the agent-consumable SDK spec at
plugins/sulis-execution/docs/research/agent-consumable-sdk-spec.md (v0.2.0).

Transport: subprocess (v0.2.0 Part 4.3) — the SDK spawns the underlying
CLI binaries (wpx-pipeline, wpx-train, sulis-change, etc.) and reads
structured JSON from stdout, mapping exit codes 0/1/2 to outcome
categories (Protocol / Expected / Internal) per v0.2.0 Part 3.

For LLM-direct invocation, see the sibling sulis-execution-mcp package.

38 operations across 10 resources: pipeline (1), train (6), index (7),
journal (10), blocker (2), findings (2), work_package (2),
worktree (2), lifecycle (1), change (5).
"""
from __future__ import annotations

from sulis_execution._client import SulisExecution, AsyncSulisExecution
from sulis_execution.errors import (
    SulisExecutionError,
    ProtocolError,
    ExpectedError,
    InternalError,
    BinaryNotFoundError,
    InvalidArgumentError,
    UnexpectedOutputError,
)
from sulis_execution.types import (
    # pipeline
    PipelineResult,
    # train
    TrainQueueListResult,
    TrainOverrideResult,
    TrainStatusResult,
    TrainDoctorResult,
    TrainAbortResult,
    TrainSkipWpResult,
    TrainRetryWpResult,
    TrainInspectResult,
    TrainStateSnapshot,
    TrainRunListing,
    TrainPhaseHistoryEntry,
    TrainBundleEntryWithOutcomes,
    TrainRunResult,
    EligibilityEntry,
    TrainBundleEntry,
    TrainOverrides,
    TrainDoctorIssue,
    # index
    IndexFlipStatusResult,
    IndexListReadyResult,
    IndexReadConfigResult,
    IndexMarkDownstreamBlockedResult,
    IndexAddResult,
    IndexRegisterPendingDraftsResult,
    # journal
    JournalPathResult,
    JournalStepResult,
    JournalAttemptResult,
    JournalPreflightResult,
    JournalSecurityVerdictResult,
    JournalCreatePlanResult,
    JournalUpdatePlanItemResult,
    JournalAddPlanItemResult,
    JournalReadResult,
    # blocker
    BlockerWriteResult,
    BlockerArchiveResult,
    # findings
    FindingsRegisterResult,
    FindingsDraftRemediationResult,
    # wp
    WorkPackageReadMetadataResult,
    WorkPackageAppendEvidenceResult,
    # worktree
    WorktreeCreateResult,
    WorktreeRemoveResult,
    # step12
    LifecycleCompleteResult,
    # change
    ChangeStartResult,
    ChangeAdoptResult,
    ChangeFinishResult,
    ChangeFinishOutcome,
    ChangeListResult,
    ChangeListEntry,
    ChangeStatusResult,
)

__version__ = "0.2.4"

__all__ = [
    # Clients
    "SulisExecution",
    "AsyncSulisExecution",
    # Errors
    "SulisExecutionError",
    "ProtocolError",
    "ExpectedError",
    "InternalError",
    "BinaryNotFoundError",
    "InvalidArgumentError",
    "UnexpectedOutputError",
    # Result types
    "PipelineResult",
    "TrainQueueListResult",
    "TrainOverrideResult",
    "TrainStatusResult",
    "TrainDoctorResult",
    "TrainAbortResult",
    "TrainSkipWpResult",
    "TrainRetryWpResult",
    "TrainInspectResult",
    "TrainStateSnapshot",
    "TrainRunListing",
    "TrainPhaseHistoryEntry",
    "TrainBundleEntryWithOutcomes",
    "TrainRunResult",
    "EligibilityEntry",
    "TrainBundleEntry",
    "TrainOverrides",
    "TrainDoctorIssue",
    "IndexFlipStatusResult",
    "IndexListReadyResult",
    "IndexReadConfigResult",
    "IndexMarkDownstreamBlockedResult",
    "IndexAddResult",
    "IndexRegisterPendingDraftsResult",
    "JournalPathResult",
    "JournalStepResult",
    "JournalAttemptResult",
    "JournalPreflightResult",
    "JournalSecurityVerdictResult",
    "JournalCreatePlanResult",
    "JournalUpdatePlanItemResult",
    "JournalAddPlanItemResult",
    "JournalReadResult",
    "BlockerWriteResult",
    "BlockerArchiveResult",
    "FindingsRegisterResult",
    "FindingsDraftRemediationResult",
    "WorkPackageReadMetadataResult",
    "WorkPackageAppendEvidenceResult",
    "WorktreeCreateResult",
    "WorktreeRemoveResult",
    "LifecycleCompleteResult",
    "ChangeStartResult",
    "ChangeAdoptResult",
    "ChangeFinishResult",
    "ChangeFinishOutcome",
    "ChangeListResult",
    "ChangeListEntry",
    "ChangeStatusResult",
    "__version__",
]
