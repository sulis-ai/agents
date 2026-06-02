---
id: WP-006
title: Author Tool catalogue in tools.jsonld (5 primary + 12 stub)
status: pending
kind: contract
primitive: create
group: GENERATE
sequence_id: WP-006
dependsOn: [WP-004]
blocks: [WP-002, WP-007]
estimated_token_cost:
  input: 4k
  output: 6k
tdd_section: FR-005; ADR-003
adrs: [ADR-003]
---

## Context

Authors the Tool catalogue at
`plugins/sulis/instances/release-train/tools.jsonld` per ADR-003's
two-class strategy: 5 primary Tools fully populated (inputs/outputs
schemas + implementation_detail + error_catalogue) + 12 stub Tools
with minimal fields and `state: draft`.

Depends on WP-004 because primary Tools reference FailureMode IDs in
`error_catalogue`.

## Contract

### Primary Tools (5, fully populated)

Per ADR-003: `_changeset.cumulative_tier`, `_changeset.next_version`,
`gh-pr-create`, `git-tag` + `git-push-tag` (treated as one primary
Tool pair), `gh-release-create`.

Shape (example for `_changeset.cumulative_tier`):

```jsonld
{
  "id": "dna:tool:<ulid>",
  "name": "_changeset.cumulative_tier",
  "for_domain": "dna:tenant:<marketplace>",
  "kind": "query",
  "inputs_schema_ref": "schemas/tools/changeset-cumulative-tier-input.schema.json",
  "outputs_schema_ref": "schemas/tools/changeset-cumulative-tier-output.schema.json",
  "error_catalogue": [
    "dna:failuremode:<version-drift-detected-pre-flight-ulid>"
  ],
  "implementation_kind": "python_import",
  "implementation_detail": "{\"module\":\"_changeset\",\"function\":\"cumulative_tier\"}",
  "version": "1.0.0",
  "state": "active",
  "sys_status": "active",
  "valid_from": "2026-06-01T00:00:00Z"
}
```

For each primary Tool, also author the input/output JSON schemas at
`plugins/sulis/instances/release-train/schemas/tools/<tool-name>-{input,output}.schema.json`.

### Stub Tools (12, minimal)

The remaining Tools referenced by Steps (per WP-002's tool_ref table):
`_changeset.read_changesets`, `_changeset.compare_version_files`,
`_changeset.summarise`, `gh-pr-checks-watch`, `gh-pr-mergeability`,
`gh-pr-merge`, `git-commit`, `git-compare-branch-versions`,
`update-version-file`, `prepend-changelog`, `sulis-emit-release`. Plus
one more if Step 2 needs a separate Tool from `_changeset.compare_version_files`.

Stub shape:

```jsonld
{
  "id": "dna:tool:<ulid>",
  "name": "git-commit",
  "for_domain": "dna:tenant:<marketplace>",
  "kind": "side-effect",
  "inputs_schema_ref": "none://stub-pending-path-c",
  "outputs_schema_ref": "none://stub-pending-path-c",
  "implementation_kind": "subprocess",
  "implementation_detail": "{\"command\":\"git\",\"args\":[\"commit\"],\"env_keys\":[]}",
  "version": "0.0.1",
  "state": "draft",
  "sys_status": "active",
  "valid_from": "2026-06-01T00:00:00Z"
}
```

Stubs carry just enough to be referenced by WP-002 Steps + checked by
WP-007 drift detector for existence.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_tools_instance_valid.py::test_tools_jsonld_parses`
- [ ] `tests/unit/test_tools_instance_valid.py::test_all_tools_present` — at minimum 17 Tools (5 primary + 12 stub)
- [ ] `tests/unit/test_tools_instance_valid.py::test_each_passes_brain_schema` — every Tool validates against Tool v1.0.0
- [ ] `tests/unit/test_tools_instance_valid.py::test_primary_tools_have_real_schema_refs` — 5 primary Tools' inputs_schema_ref + outputs_schema_ref both resolve to existing JSON Schema files (not `none://...`)
- [ ] `tests/unit/test_tools_instance_valid.py::test_stub_tools_state_is_draft` — 12 stub Tools have `state: draft`
- [ ] `tests/unit/test_tools_instance_valid.py::test_error_catalogue_refs_resolve` — every Tool's `error_catalogue` entries resolve to FailureMode IDs in WP-004's failuremodes.jsonld
- [ ] `tests/unit/test_tools_instance_valid.py::test_primary_tool_input_schemas_validate` — for each primary Tool, run a sample input through jsonschema validation

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/instances/release-train/tools.jsonld` authored per Contract
- [ ] 5 primary Tools fully populated with inputs/outputs schemas
- [ ] 12 stub Tools authored with minimal fields + `state: draft`
- [ ] 10 JSON Schema files authored at
      `plugins/sulis/instances/release-train/schemas/tools/<tool>-{input,output}.schema.json`
      (5 primaries × 2 schemas each)
- [ ] Tool ULIDs are stable + recorded (so WP-002's tool_ref + WP-007's
      validation can pin them)

### Blue — Refactor complete
- [ ] Schemas are minimal — describe only the load-bearing fields, not exhaustive
- [ ] Primary Tools' implementation_detail is accurate (matches the actual Python module / subprocess invocation)
- [ ] Stub Tools' implementation_detail is consistent (same JSON shape per kind)

## Sequence

- **dependsOn:** WP-004 (error_catalogue references FailureMode IDs)
- **blocks:** WP-002 (Steps reference Tool IDs via tool_ref), WP-007 (drift detector validates Tool existence per Step tool_ref)
- **Parallelisable with:** WP-001, WP-003, WP-011 (after WP-004 unblocks)

## Estimated Token Cost

- **Input:** ~4k (Tool schema + ADR-003 + primary Tools' actual signatures)
- **Output:** ~6k (17 Tool instances + 10 JSON Schema files)
- **Total:** ~10k

## Notes

- Two-class catalogue: primary Tools' contract drives the drift
  detector's input/output schema validation; stub Tools are
  existence-checked only (drift detector treats `state: draft` as
  schema-exempt per ADR-003).
- If a stub Tool's contract becomes load-bearing later (e.g.
  `update-version-file`'s shape changes), promote it to primary in a
  follow-up change — not in this WP. Discipline per ADR-003.
- The 17 Tools total assumes Step 7 uses one Tool for checks-watch
  AND a separate Tool for mergeability; recount during authoring to
  confirm.
