# Changelog

All notable changes to the sulis-execution SDK packages.

Format per [Keep a Changelog](https://keepachangelog.com/).
Versioning per [SemVer](https://semver.org/).

## [0.2.0] — 2026-05-22

### Changed (BREAKING)

Naming sweep — every method name is now self-describing. Behaviour is
identical to v0.1.0; only public surface names changed. See
[`docs/migrations/v0.1-to-v0.2.md`](docs/migrations/v0.1-to-v0.2.md)
for the per-rename migration guide with before/after snippets.

**Resource renames:**

- `client.step12` → `client.lifecycle`
- `client.wp` → `client.work_package`

**Method renames:**

- `step12.wrap` → `lifecycle.complete`
- `index.add_wp` → `index.add`
- `index.propagate_blocked` → `index.mark_downstream_blocked`
- `index.sync_auto_drafts` → `index.register_pending_drafts`
- `findings.auto_draft_wp` → `findings.draft_remediation`
- `journal.seed_plan` → `journal.create_plan`
- `journal.mark_plan_item` → `journal.update_plan_item`
- `journal.record_postdeploy` → `journal.record_security_verdict`
- `wp.read_frontmatter` → `work_package.read_metadata`

**Result type renames** (Python class + TypeScript interface):

- `Step12WrapResult` → `LifecycleCompleteResult`
- `IndexAddWpResult` → `IndexAddResult`
- `IndexPropagateBlockedResult` → `IndexMarkDownstreamBlockedResult`
- `IndexSyncAutoDraftsResult` → `IndexRegisterPendingDraftsResult`
- `FindingsAutoDraftWpResult` → `FindingsDraftRemediationResult`
- `JournalSeedPlanResult` → `JournalCreatePlanResult`
- `JournalMarkPlanItemResult` → `JournalUpdatePlanItemResult`
- `JournalPostdeployResult` → `JournalSecurityVerdictResult`
- `WpReadFrontmatterResult` → `WorkPackageReadMetadataResult`
- `WpAppendEvidenceResult` → `WorkPackageAppendEvidenceResult`

**MCP tool name renames** (snake_case derived from new operationIds):

- `step12_wrap` → `lifecycle_complete`
- `index_add_wp` → `index_add`
- `index_propagate_blocked` → `index_mark_downstream_blocked`
- `index_sync_auto_drafts` → `index_register_pending_drafts`
- `findings_auto_draft_wp` → `findings_draft_remediation`
- `journal_seed_plan` → `journal_create_plan`
- `journal_mark_plan_item` → `journal_update_plan_item`
- `journal_record_postdeploy` → `journal_record_security_verdict`
- `wp_read_frontmatter` → `work_package_read_metadata`
- `wp_append_evidence` → `work_package_append_evidence`

### What's NOT changed

- Underlying CLI binaries + subcommands (`wpx-pipeline`, `wpx-step12`,
  `wpx-wp`, etc.) keep their names
- Wire field names (e.g. `auto_draft_wp_id` field on
  `FindingsDraftRemediationResult`) preserved per parity contract
- The `wp` parameter name (canonical WP-ID input convention)
- Error class hierarchy (no renames)

### Why

Peer-SDK test session feedback (see rubric v0.2.0). Internal-jargon
names like `step12.wrap` and `wp.read_frontmatter` required insider
context. Renames make every method self-describing without prior
knowledge of the Sulis lifecycle vocabulary.

### Migration

No automated codemod. Per-rename find-and-replace; see migration
guide for sed expressions. No compatibility aliases — pre-1.0
SemVer allows breaking minor bumps; no external consumers were
registered when this rename was applied.

### Schema source

`sulis-execution.openapi.yaml` v0.2.0 (38 operations; 9 add
`x-cli-subcommand` extension to route renamed methods to original
CLI subcommands).

## [0.1.0] — 2026-05-21

### Added

- Initial release of `sulis-execution` (Python), `@sulis-ai/execution`
  (TypeScript), and `sulis-execution-mcp` (MCP server).
- 38 operations across 10 resources (pipeline, train, index, journal,
  blocker, findings, wp, worktree, step12, change).
- Outcome-category error model (ProtocolError / ExpectedError /
  InternalError) with wpx-domain extensions (BinaryNotFoundError,
  InvalidArgumentError, UnexpectedOutputError).
- Subprocess transport for Python (sync + async via httpx-style API)
  and TypeScript (sync via spawnSync, async via spawn wrapper).
- MCP server reads OpenAPI spec at startup, registers 38 tools, maps
  wpx exit codes to MCP's two-channel error model.
- Documentation per Diátaxis quadrants.

### Schema source

`sulis-execution.openapi.yaml` v0.1.0 (38 operations).

### Spec compliance

- agent-consumable-sdk-spec.md v0.2.0
- agent-consumable-sdk-wpx-mapping.md v0.2.0
- agent-consumable-sdk-docs-spec.md v0.1.0
