/**
 * TypeScript interfaces for sulis-execution SDK responses.
 *
 * Generated shapes from sulis-execution.openapi.yaml. Per SDK spec
 * v0.2.0 Part 6, field case is `snake_case` preserved from the JSON
 * wire — do NOT auto-camelCase fields in TypeScript.
 *
 * All shapes use `extra fields tolerated` via TypeScript's structural
 * typing (consumers can add fields without breaking the type check).
 */

// ─── pipeline ────────────────────────────────────────────────────────

export interface PipelineResult {
  wp: string;
  outcome: 'success' | 'blocker' | 'error' | 'pending';
  merge_sha: string | null;
  deploy_url: string | null;
  deploy_workflow_run: string | null;
  health_status: 'healthy' | 'unhealthy' | 'skipped' | null;
  health_url: string | null;
  smoke_verdict: string | null;
  blocker_reason: string | null;
  ci_poll_skipped: boolean;
  merge_already_complete: boolean;
  started_at: string;
  completed_at: string | null;
}

// ─── train ───────────────────────────────────────────────────────────

export interface EligibilityEntry {
  wp: string;
  branch?: string | null;
  eligible: boolean;
  reason: string;
  primitive?: string | null;
  forced?: boolean;
}

export interface TrainOverrides {
  includes: string[];
  holds: string[];
}

export interface TrainQueueListResult {
  project: string;
  index_md?: string | null;
  eligible_count: number;
  ineligible_count: number;
  eligible: EligibilityEntry[];
  ineligible: EligibilityEntry[];
  overrides: TrainOverrides;
}

export interface TrainOverrideResult {
  wp: string;
  action: 'force_include_added' | 'hold_added' | 'noop';
  reason?: string | null;
  overrides_path?: string | null;
  includes: string[];
  holds: string[];
}

export interface TrainStatusResult {
  project: string;
  eligible_count: number;
  eligible_wps: string[];
  ineligible_count: number;
  overrides: TrainOverrides;
  trigger_state: 'not_ready' | 'ready_size' | 'waiting';
  trigger_reason?: string | null;
  last_train_run?: string | null;
}

export interface TrainDoctorIssue {
  kind: string;
  wp?: string | null;
  detail: string;
}

export interface TrainDoctorResult {
  project: string;
  issue_count: number;
  issues: TrainDoctorIssue[];
  note_orphan_branches?: string | null;
}

// v0.17.0+ — Resumable Train state machine

export interface TrainPhaseHistoryEntry {
  phase?: string;
  started_at?: string;
  ended_at?: string | null;
  outcome?: string | null;
}

export interface TrainBundleEntryWithOutcomes {
  wp?: string;
  branch?: string;
  pre_train_sha?: string | null;
  rebased_to_sha?: string | null;
  merge_sha_on_dev?: string | null;
  phase_outcomes?: Record<string, string>;
}

export interface TrainStateSnapshot {
  train_id?: string;
  started_at?: string;
  completed_at?: string | null;
  phase?: string;
  phase_started_at?: string | null;
  phase_history?: TrainPhaseHistoryEntry[];
  pause_reason?: string | null;
  recovery_hint?: string | null;
  bundle?: TrainBundleEntryWithOutcomes[];
  args?: Record<string, unknown>;
}

export interface TrainRunListing {
  train_id?: string;
  started_at?: string | null;
  phase?: string | null;
  pause_reason?: string | null;
  in_flight?: boolean;
}

/**
 * Result of train.inspect.
 *
 * When called with train_id: behaves as TrainStateSnapshot (snapshot
 * fields populated; runs + count absent).
 *
 * Without train_id: contains runs + count listing (snapshot fields
 * absent).
 */
export interface TrainAbortResult {
  train_id?: string;
  outcome?: string;
  phase_at_abort?: string;
  post_merge?: boolean;
  restore_log?: Array<Record<string, unknown>>;
  wps_flipped?: Array<Record<string, unknown>>;
  train_blocker_path?: string | null;
  suspected_culprit?: string | null;
  revert?: Record<string, unknown>;
}

export interface TrainSkipWpResult {
  train_id?: string;
  skipped_wp?: string;
  index_flipped?: boolean;
  remaining_bundle?: string[];
  next_step?: string;
}

export interface TrainRetryWpResult {
  train_id?: string;
  retry_wp?: string;
  cleared_outcomes?: string[];
  index_restored_to?: string;
  next_step?: string;
}

export interface TrainInspectResult {
  // Snapshot fields (when train_id provided)
  train_id?: string;
  started_at?: string;
  completed_at?: string | null;
  phase?: string;
  phase_started_at?: string | null;
  phase_history?: TrainPhaseHistoryEntry[];
  pause_reason?: string | null;
  recovery_hint?: string | null;
  bundle?: TrainBundleEntryWithOutcomes[];
  args?: Record<string, unknown>;
  // Listing fields (when train_id omitted)
  runs?: TrainRunListing[];
  count?: number;
}

export interface TrainBundleEntry {
  wp?: string | null;
  branch?: string | null;
  pre_train_sha?: string | null;
  rebased_to_sha?: string | null;
  merge_sha_on_dev?: string | null;
}

export interface TrainRunResult {
  train_id: string;
  outcome: 'success' | 'not_triggered' | 'nothing_to_pack' | 'blocker' | 'error';
  wps_shipped: string[];
  eligible_count?: number | null;
  eligible_wps: string[];
  deploy_url?: string | null;
  final_merge_sha?: string | null;
  record_path?: string | null;
  bundle: TrainBundleEntry[];
  rebase_failures: Record<string, unknown>[];
  train_blocker_path?: string | null;
}

// ─── index ───────────────────────────────────────────────────────────

export interface IndexFlipStatusResult {
  wp: string;
  status: string;
}

export interface IndexListReadyResult {
  ready: string[];
  max_parallel: number;
  total_pending: number;
  total_done: number;
  total_blocked: number;
  total_in_progress: number;
}

export interface IndexReadConfigResult {
  config: Record<string, string>;
}

export interface IndexMarkDownstreamBlockedResult {
  blocker_wp: string;
  flipped_to_dependency_blocked: string[];
}

export interface IndexAddResult {
  wp: string;
  added: boolean;
}

export interface IndexRegisterPendingDraftsResult {
  synced_count: number;
  synced: string[];
}

// ─── journal ─────────────────────────────────────────────────────────

export interface JournalPathResult {
  path: string;
}

export interface JournalStepResult {
  wp: string;
  step: number;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface JournalAttemptResult {
  wp: string;
  step: number;
  attempt: number;
}

export interface JournalPreflightResult {
  wp: string;
  tool: string;
  status: string;
}

export interface JournalSecurityVerdictResult {
  wp: string;
  verdict: string;
}

export interface JournalCreatePlanResult {
  wp: string;
  approach: string;
  item_count: number;
}

export interface JournalUpdatePlanItemResult {
  wp: string;
  item: number;
  status: string;
}

export interface JournalAddPlanItemResult {
  wp: string;
  item: number;
  description: string;
  step: string;
  status: string;
}

export interface JournalReadResult {
  field: string;
  value: unknown;
}

// ─── blocker ─────────────────────────────────────────────────────────

export interface BlockerWriteResult {
  wp: string;
  path: string;
}

export interface BlockerArchiveResult {
  wp: string;
  archived_to: string;
  original: string;
}

// ─── findings ────────────────────────────────────────────────────────

export interface FindingsRegisterResult {
  sf_id: string;
  is_duplicate: boolean;
  auto_draft_wp_id?: string | null;
  source_wp: string;
  signature: string;
  sf_path?: string | null;
}

export interface FindingsDraftRemediationResult {
  auto_wp_id: string;
  path: string;
}

// ─── work_package ────────────────────────────────────────────────────

export interface WorkPackageReadMetadataResult {
  field: string;
  value?: unknown;
  frontmatter?: Record<string, unknown> | null;
  present: boolean;
}

export interface WorkPackageAppendEvidenceResult {
  wp: string;
  path: string;
}

// ─── worktree ────────────────────────────────────────────────────────

export interface WorktreeCreateResult {
  wp: string;
  worktree_path: string;
  branch: string;
  dev_sha_at_creation: string;
  sidecar: string;
}

export interface WorktreeRemoveResult {
  wp: string;
  removed: string;
}

// ─── lifecycle ───────────────────────────────────────────────────────

export interface LifecycleCompleteResult {
  wp: string;
  steps: Record<string, unknown>;
}

// ─── change (sulis-change) ───────────────────────────────────────────

export interface ChangeStartResult {
  branch: string;
  primitive: string;
  slug: string;
  worktree_path: string;
  base_branch: string;
  base_sha?: string | null;
  metadata_path?: string | null;
}

export interface ChangeAdoptResult {
  branch: string;
  primitive: string;
  slug: string;
  worktree_path: string;
  adopt_mode: string;
  moved: string[];
  uncommitted_count: number;
  local_commits_count: number;
}

export interface ChangeFinishOutcome {
  mode: 'merge' | 'pr';
  pr_url?: string | null;
}

export interface ChangeFinishResult {
  branch: string;
  primitive: string;
  slug: string;
  outcome: ChangeFinishOutcome;
  cleanup: Record<string, unknown>;
}

export interface ChangeListEntry {
  primitive: string;
  slug: string;
  branch: string;
  worktree_path?: string | null;
  worktree_present: boolean;
  dirty?: boolean;
}

export interface ChangeListResult {
  active_count: number;
  changes: ChangeListEntry[];
}

export interface ChangeStatusResult {
  branch: string;
  primitive: string;
  slug: string;
  worktree_path?: string | null;
  worktree_present: boolean;
  branch_sha?: string | null;
  base_sha?: string | null;
  ahead_of_base?: number | null;
  behind_base?: number | null;
  metadata: Record<string, unknown>;
}
