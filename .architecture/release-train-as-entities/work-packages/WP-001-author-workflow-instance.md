---
id: WP-001
title: Author release-train Workflow instance (workflow.jsonld)
status: pending
kind: contract
primitive: create
group: GENERATE
sequence_id: WP-001
dependsOn: [WP-002]
blocks: [WP-005, WP-007, WP-010]
estimated_token_cost:
  input: 3k
  output: 2k
tdd_section: Form — Component inventory (#1)
adrs: [ADR-001, ADR-002]
---

## Context

Authors the apex canonical entity — the release-train Workflow
definition — at `plugins/sulis/instances/release-train/workflow.jsonld`.
Structural template: brain's `sync-narrative-docs/workflow.jsonld`.

This Workflow is **unscoped** at the definition level (`for_project: null`)
— bound per-invocation by the consumer. Cycle-tolerant per JT-7
(PR-conflicts back-merge → retry from open-pr). The Steps it references
(by name in `steps[]`) are authored in WP-002.

## Contract

The Workflow entity per brain foundation v0.5.0 schema. Required fields:

```jsonld
{
  "@id": "dna:release-train:workflow",
  "@type": "workflow-instance",
  "for_tenant": "dna:tenant:<sulis-plugins-marketplace-tenant>",
  "captured_on": "2026-06-01",
  "workflows": [{
    "id": "dna:workflow:<ulid>",
    "name": "release-train",
    "for_domain": "dna:tenant:<sulis-plugins-marketplace-tenant>",
    "for_process": "release-train",
    "for_project": null,   // unscoped definition
    "description": "Per-Project release pipeline: detect → preflight → compute → draft → open → wait → confirm → merge → bump → tag → publish",
    "type": "other",
    "state_contract": [
      "target_branch:string",
      "source_branch:string",
      "pending_changesets:list",
      "tier:enum[patch|minor|major|null]",
      "next_plugin_version:semver",
      "next_umbrella_version:semver",
      "pr_url:url",
      "merge_sha:sha",
      "tag_pushed:bool",
      "release_url:url",
      "final-outcome:enum[shipped|no-changesets|blocked|aborted]"
    ],
    "steps": [
      "detect-pending-changesets",
      "preflight-version-drift",
      "preflight-cross-branch-drift",
      "compute-next-version",
      "draft-pr-body-and-changelog",
      "open-release-pr",
      "wait-for-checks-and-mergeability",
      "gate-founder-confirmation",
      "squash-merge",
      "bump-version-files",
      "write-changelog-entry",
      "commit-bump-as-bot",
      "tag-and-push",
      "publish-github-release",
      "emit-release-entity"
    ],
    "initial_steps": ["detect-pending-changesets"],
    "terminal_steps": ["emit-release-entity", "gate-founder-confirmation"],
    "transitions": [
      "detect-pending-changesets -> preflight-version-drift [if pending_changesets.non_empty]",
      "detect-pending-changesets -> [terminal:no-changesets] [if pending_changesets.empty]",
      "preflight-version-drift -> preflight-cross-branch-drift",
      "preflight-cross-branch-drift -> compute-next-version",
      "compute-next-version -> draft-pr-body-and-changelog",
      "draft-pr-body-and-changelog -> open-release-pr",
      "open-release-pr -> wait-for-checks-and-mergeability",
      "wait-for-checks-and-mergeability -> gate-founder-confirmation [if checks_pass AND mergeable]",
      "wait-for-checks-and-mergeability -> open-release-pr [if pr-conflicts; back-merge then retry]",
      "wait-for-checks-and-mergeability -> [terminal:aborted] [if checks_fail]",
      "gate-founder-confirmation -> squash-merge [if confirm=yes]",
      "gate-founder-confirmation -> [terminal:aborted] [if confirm=no]",
      "squash-merge -> bump-version-files",
      "bump-version-files -> write-changelog-entry",
      "write-changelog-entry -> commit-bump-as-bot",
      "commit-bump-as-bot -> tag-and-push",
      "tag-and-push -> publish-github-release",
      "publish-github-release -> emit-release-entity",
      "emit-release-entity -> [terminal:shipped]"
    ],
    "state": "active",
    "valid_from": "2026-06-01T00:00:00Z",
    "confidence": 0.9
  }]
}
```

The back-edge `wait-for-checks-and-mergeability -> open-release-pr` is
the cycle (JT-7) for PR-conflicts recovery.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_workflow_instance_valid.py::test_workflow_jsonld_parses_as_yaml_dict` — fails because workflow.jsonld doesn't exist
- [ ] `tests/unit/test_workflow_instance_valid.py::test_workflow_passes_brain_schema` — validates against vendored compiled schema at `plugins/sulis/brain/compiled/foundation/workflow.schema.json`

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/instances/release-train/workflow.jsonld` authored per the Contract above
- [ ] File parses as JSON
- [ ] Validates against `workflow.schema.json` (foundation v0.5.0)
- [ ] All 15 step names in `steps[]` match Step names in WP-002's steps.jsonld
- [ ] All transitions reference valid step names + terminal verdicts in {shipped, no-changesets, blocked, aborted}
- [ ] state_contract enumerated per the Contract

### Blue — Refactor complete
- [ ] No duplication between transitions; one direction of edge per pair
- [ ] Comments minimal — the entity is self-describing via field names

## Sequence

- **dependsOn:** WP-002 (Steps must exist for the workflow.steps[] names to match real Step entities — WP-002 author them; here we reference by name)
- **blocks:** WP-005 (Projects reference this Workflow's ID), WP-007 (drift detector reads this), WP-010 (skill extension points at this dir)
- **Parallelisable with:** WP-003, WP-004, WP-006, WP-011

## Estimated Token Cost

- **Input:** ~3k (TDD section + brain workflow schema + sync-narrative-docs template)
- **Output:** ~2k (one ~80-line workflow.jsonld)
- **Total:** ~5k

## Notes

- Workflow ULID is assigned at authoring; record it in this WP after creation so dependent WPs (WP-005 Projects) can reference it.
- Cycle on PR-conflicts is a single back-edge with an `[if pr-conflicts; back-merge then retry]` guard — matches the brain's cycle-tolerant DAG-flattening convention.
