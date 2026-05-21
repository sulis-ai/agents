# Operations catalogue

**Applies to:** sulis-execution v0.1.0

All 38 operations, grouped by resource. Each lists the required +
optional fields and the result type.

For full request/response schemas (including JSON Schema constraints),
see [`sulis-execution.openapi.yaml`](../../sulis-execution.openapi.yaml).

For language-specific method signatures (Python + TypeScript), use
your IDE's intellisense after importing the package.

---

## pipeline (1 operation)

### `pipeline.run`

Run the per-WP Steps 8-10 pipeline.

| Required | Optional |
|---|---|
| `wp`, `branch`, `dev_sha_at_creation`, `deploy_workflow` | `staging_url`, `health_path`, `smoke_cmd`, `ci_poll_interval`, `deploy_poll_interval`, `skip_ci_poll`, `base_branch`, `worktree_path`, `repo` |

**Returns:** `PipelineResult` with `outcome: success | blocker | error | pending`.

---

## train (6 operations)

| Operation | Required | Returns |
|---|---|---|
| `train.queue_list` | (project, repo_root only) | `TrainQueueListResult` |
| `train.queue_add` | `wp` | `TrainOverrideResult` |
| `train.queue_remove` | `wp` | `TrainOverrideResult` |
| `train.status` | (project, repo_root only) | `TrainStatusResult` |
| `train.doctor` | (project, repo_root only) | `TrainDoctorResult` |
| `train.run` | `deploy_workflow` (and optional `force`, `staging_url`, `health_path`, `smoke_cmd`, `ci_poll_interval`, `deploy_poll_interval`, `max_batch_size`, `base_branch`) | `TrainRunResult` with `outcome: success | not_triggered | nothing_to_pack | blocker | error` |

---

## index (7 operations)

| Operation | Required | Returns |
|---|---|---|
| `index.flip_status` | `wp`, `to`; optional `expected` for CAS-style guard | `IndexFlipStatusResult` |
| `index.set_status` | `wp`, `to` | `IndexFlipStatusResult` |
| `index.list_ready` | — | `IndexListReadyResult` |
| `index.read_config` | — | `IndexReadConfigResult` |
| `index.propagate_blocked` | `wp` (the blocker WP) | `IndexPropagateBlockedResult` |
| `index.add_wp` | `wp`; optional metadata or `from_wp_file` | `IndexAddWpResult` |
| `index.sync_auto_drafts` | — | `IndexSyncAutoDraftsResult` |

`to` accepts: pending, in_progress, done, blocked, dependency_blocked,
auto-draft, cancelled, step-7-complete, step-7-held, step-7-blocked.

---

## journal (10 operations)

| Operation | Required | Returns |
|---|---|---|
| `journal.init` | `wp` | `JournalPathResult` |
| `journal.start_step` | `wp`, `step` | `JournalStepResult` |
| `journal.complete_step` | `wp`, `step`, `outcome` | `JournalStepResult` |
| `journal.record_attempt` | `wp`, `step`, `attempt`, `failure`, `root_cause`, `change`, `outcome` | `JournalAttemptResult` |
| `journal.record_preflight` | `wp`, `tool`, `status` | `JournalPreflightResult` |
| `journal.record_postdeploy` | `wp`, `verdict` | `JournalPostdeployResult` |
| `journal.seed_plan` | `wp`, `approach`, `plan_json` | `JournalSeedPlanResult` |
| `journal.mark_plan_item` | `wp`, `item`, `status` | `JournalMarkPlanItemResult` |
| `journal.add_plan_item` | `wp`, `description`, `step` | `JournalAddPlanItemResult` |
| `journal.read` | `wp`, `field` | `JournalReadResult` |

`status` (mark_plan_item) accepts: pending, in-progress, done, skipped.

`field` (read) accepts: status, lifecycle-step, started, step-trace,
step-N-status (N is an int), post-deploy-verification, preflight, plan.

---

## blocker (2 operations)

| Operation | Required | Returns |
|---|---|---|
| `blocker.write` | `wp`, `title`, `step`, `trigger`, `observation`, `root_cause`, `scope`, `plain_english`, `suggested_next` | `BlockerWriteResult` |
| `blocker.archive` | `wp` | `BlockerArchiveResult` |

`trigger` accepts: scope-guard, budget-exhausted, five-whys-non-convergence.
`scope` accepts: in-scope-budget-exhausted, out-of-scope, indeterminate.

---

## findings (2 operations)

| Operation | Required | Returns |
|---|---|---|
| `findings.register` | `wp`, `severity`, `summary`, `file` | `FindingsRegisterResult` |
| `findings.auto_draft_wp` | `source_finding`, `source_wp`, `auto_wp_id`, `severity` | `FindingsAutoDraftWpResult` |

`severity` (register) accepts: CRITICAL, CONCERN, ADVISORY.
`severity` (auto_draft_wp) accepts: CONCERN, ADVISORY.

---

## wp (2 operations)

| Operation | Required | Returns |
|---|---|---|
| `wp.read_frontmatter` | `wp`, `field` (or `*`) | `WpReadFrontmatterResult` |
| `wp.append_evidence` | `wp`, `evidence_json` | `WpAppendEvidenceResult` |

---

## worktree (2 operations)

| Operation | Required | Returns |
|---|---|---|
| `worktree.create` | `wp`, `branch`, `worktree_path` | `WorktreeCreateResult` |
| `worktree.remove` | `wp`, `worktree_path` | `WorktreeRemoveResult` |

---

## step12 (1 operation)

### `step12.wrap`

Atomic Step 12 — append evidence + flip INDEX + remove worktree.

| Required | Optional |
|---|---|
| `wp`, `branch`, `pipeline_result` | `pre_squash_sha`, `worktree_path`, `post_deploy_verification` |

**Returns:** `Step12WrapResult`.

---

## change (5 operations)

Note: `change` operations are project-independent. They take `repo_root`
but no `project`.

| Operation | Required | Returns |
|---|---|---|
| `change.start` | `slug` (optional `primitive`, `base`) | `ChangeStartResult` |
| `change.adopt` | `slug` (optional `primitive`, `base`, `mode`, `remote_ref`, `force`) | `ChangeAdoptResult` |
| `change.finish` | `slug` + one of `merge` or `pr` | `ChangeFinishResult` |
| `change.list` | — | `ChangeListResult` |
| `change.status` | `slug` | `ChangeStatusResult` |

## See also

- [Type catalogue](types.md)
- [Error catalogue](errors.md)
