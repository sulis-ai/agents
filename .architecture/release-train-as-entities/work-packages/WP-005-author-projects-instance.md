---
id: WP-005
title: Author 4 marketplace Project instances in projects.jsonld
status: pending
kind: contract
primitive: create
group: GENERATE
sequence_id: WP-005
dependsOn: [WP-001]
blocks: [WP-007]
estimated_token_cost:
  input: 2k
  output: 2k
tdd_section: FR-001; Configuration Vocabulary
adrs: [ADR-004]
---

## Context

Hand-authors the 4 Project instances at
`plugins/sulis/instances/release-train/projects.jsonld` per ADR-004 +
the SRD's Configuration Vocabulary section. Each Project entity
declares the per-plugin specifics (source.path, version_files,
branch_policy) the release-train Workflow binds at invocation time.

Depends on WP-001 to know the release-train Workflow's ULID (each
Project's `release_workflow_ref` points at it).

## Contract

4 Project instances per brain foundation v0.5.0 Project schema. Each:

```jsonld
{
  "id": "dna:project:<ulid>",
  "name": "sulis",
  "belongs_to_tenant": "dna:tenant:<sulis-plugins-marketplace>",
  "type": "plugin",
  "source": "{\"repo\":\"sulis-ai/agents\",\"path\":\"plugins/sulis\",\"primary_branch\":\"main\"}",
  "version_files": [
    "plugins/sulis/.claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json"
  ],
  "branch_policy": "gitflow-dev-main",
  "belongs_to_product_ref": "sulis-plugins-marketplace",
  "depends_on": [],
  "consumed_by": [],
  "release_workflow_ref": "dna:workflow:<release-train-ulid-from-WP-001>",
  "description": "The Sulis AI engineering team plugin (`/sulis:*` skills + the agent).",
  "state": "active",
  "sys_status": "active",
  "valid_from": "2026-06-01T00:00:00Z",
  "confidence": 1.0
}
```

The 4 Projects:

| name | repo | source.path | branch_policy |
|---|---|---|---|
| sulis | sulis-ai/agents | plugins/sulis | gitflow-dev-main |
| sulis-brain | sulis-ai/plugins | plugins/sulis-brain | gitflow-dev-main |
| plugin-builder | sulis-ai/plugins | plugins/plugin-builder | gitflow-dev-main |
| investor-coach | sulis-ai/agents | plugins/investor-coach | gitflow-dev-main |

**Open sub-question (per ADR-004):** sulis-brain + plugin-builder live
in a different repo (`sulis-ai/plugins`). Two options:
- (a) Duplicate their Project instances in the marketplace's
  `plugins/sulis/instances/release-train/projects.jsonld` (this repo).
- (b) Cross-repo reference via convention (e.g. a `repo_ref` field that
  resolves cross-repo).

For v1: duplicate (option a). Cross-repo resolution is brain's v0.7
work per DR-016. Note this in the WP's notes section.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_projects_instance_valid.py::test_projects_jsonld_parses`
- [ ] `tests/unit/test_projects_instance_valid.py::test_4_projects_present`
- [ ] `tests/unit/test_projects_instance_valid.py::test_each_passes_brain_schema`
- [ ] `tests/unit/test_projects_instance_valid.py::test_all_release_workflow_refs_resolve_to_wp001` — release_workflow_ref ULIDs all match WP-001's Workflow ID
- [ ] `tests/unit/test_projects_instance_valid.py::test_branch_policy_enum_valid`
- [ ] `tests/unit/test_projects_instance_valid.py::test_source_json_well_formed` — source field's JSON-encoded object parses + has repo/path/primary_branch keys
- [ ] `tests/unit/test_projects_instance_valid.py::test_version_files_exist_in_repos` — for in-repo Projects (sulis, investor-coach), the listed paths must exist; for cross-repo Projects (sulis-brain, plugin-builder), skip the existence check

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/instances/release-train/projects.jsonld` authored per Contract
- [ ] All 4 Project instances validate against brain Project schema
- [ ] release_workflow_ref points at the actual WP-001 Workflow ULID
- [ ] source field carries repo + path + primary_branch in JSON-encoded form
- [ ] version_files lists are accurate (verified against actual repo state)

### Blue — Refactor complete
- [ ] Descriptions are terse + accurate
- [ ] No duplicated belongs_to_tenant references (all same marketplace tenant)
- [ ] belongs_to_product_ref string consistent across all 4

## Sequence

- **dependsOn:** WP-001 (need the release-train Workflow ULID to reference)
- **blocks:** WP-007 (drift detector validates Project.name appears in marketplace.json plugins[] per MUC-008)
- **Parallelisable with:** WP-003, WP-002, WP-011 (after WP-001 unblocks)

## Estimated Token Cost

- **Input:** ~2k (Project schema + ADR-004 + repo inspection for actual paths)
- **Output:** ~2k (4 Project instances ≈ 25-35 lines each)
- **Total:** ~4k

## Notes

- The cross-repo Project authoring (sulis-brain, plugin-builder) is
  authored here as documentation. The brain repo already has its own
  Project instances at `instances/multi-repo-scenarios/scenario-1-monorepo-multi-product/projects.jsonld`. Duplication is intentional for v1
  (no cross-artifact resolution yet); the brain's v0.7+ work will close
  this gap.
- This WP is the worked example future fork-consumers reference per
  UC-004 + the Configuration Vocabulary section.
