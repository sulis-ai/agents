---
id: WP-002
title: Author 15 Step instances in steps.jsonld
status: pending
kind: contract
primitive: create
group: GENERATE
sequence_id: WP-002
dependsOn: [WP-004, WP-006]
blocks: [WP-001, WP-007, WP-009, WP-010]
estimated_token_cost:
  input: 6k
  output: 8k
tdd_section: Form — Component inventory (#2); Steps in release-train table
adrs: [ADR-001, ADR-003]
---

## Context

Authors the 15 Step instances (per the TDD's Steps table) at
`plugins/sulis/instances/release-train/steps.jsonld`. Each Step
declares: `name`, `mechanism`, `input_artifacts`, `output_artifacts`,
`tool_ref` (where applicable), `handles_failures` (FailureMode IDs).

Steps reference Tool IDs (authored in WP-006) and FailureMode IDs
(authored in WP-004). Both must exist before authoring.

## Contract

15 Step entities per brain foundation v0.5.0 Step v1.2.0 schema.
Each Step shape:

```jsonld
{
  "@id": "dna:release-train:step:<name>",
  "@type": "step-instance",
  "for_tenant": "dna:tenant:<marketplace>",
  "steps": [
    {
      "id": "dna:step:<ulid>",
      "name": "detect-pending-changesets",
      "for_domain": "dna:tenant:<marketplace>",
      "for_process": "release-train",
      "input_artifacts": ["changeset_dir:path"],
      "output_artifacts": ["pending_changesets:list"],
      "mechanism": "deterministic",
      "tool_ref": "dna:tool:<changeset.read_changesets-ulid>",
      "preconditions": [],
      "postconditions": ["pending_changesets is non-null"],
      "agent_instructions": "Read `.changesets/*.yaml` via the changeset library; return the parsed list. Empty list signals no-release-needed (terminal:no-changesets).",
      "criticality": "critical",
      "handles_failures": [],
      "state": "active",
      "sys_status": "active",
      "valid_from": "2026-06-01T00:00:00Z"
    },
    /* ... 14 more ... */
  ]
}
```

The 15 Steps per the TDD Steps table:

| # | name | mechanism | tool_ref → Tool name | handles_failures → FailureMode names |
|---|---|---|---|---|
| 1 | detect-pending-changesets | deterministic | `_changeset.read_changesets` | — |
| 2 | preflight-version-drift | deterministic | `_changeset.compare_version_files` | `version-drift-detected-pre-flight` |
| 3 | preflight-cross-branch-drift | deterministic | `git-compare-branch-versions` | `version-drift-detected-pre-flight` |
| 4 | compute-next-version | deterministic | `_changeset.cumulative_tier` + `next_version` (composite: agent_instructions name both) | — |
| 5 | draft-pr-body-and-changelog | mixed | `_changeset.summarise` + LLM | `probabilistic-step-token-budget-exceeded` |
| 6 | open-release-pr | side-effect | `gh-pr-create` | — |
| 7 | wait-for-checks-and-mergeability | deterministic | `gh-pr-checks-watch` (+ `gh-pr-mergeability`) | `release-pr-conflicts-with-target-at-merge`, `pr-checks-fail`, `pr-open-but-mergeability-stuck` |
| 8 | gate-founder-confirmation | human | — | — |
| 9 | squash-merge | side-effect | `gh-pr-merge` | — |
| 10 | bump-version-files | side-effect | `update-version-file` (called per Project.version_files[]) | — |
| 11 | write-changelog-entry | side-effect | `prepend-changelog` | — |
| 12 | commit-bump-as-bot | side-effect | `git-commit` | — |
| 13 | tag-and-push | side-effect | `git-tag` + `git-push-tag` | — |
| 14 | publish-github-release | side-effect | `gh-release-create` | `bot-tag-doesnt-trigger-release-prod` |
| 15 | emit-release-entity | side-effect | `sulis-emit-release` | — |

Step 5 (probabilistic) carries `mechanism_detail` with the token
budget per NFR-010:
```
"mechanism_detail": "{\"token_budget\": {\"input\": 4000, \"output\": 2000}}"
```

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_steps_instance_valid.py::test_steps_jsonld_parses` — file exists + parses
- [ ] `tests/unit/test_steps_instance_valid.py::test_all_15_steps_present` — exactly 15 Step instances
- [ ] `tests/unit/test_steps_instance_valid.py::test_each_step_passes_brain_schema` — each validates against Step v1.2.0
- [ ] `tests/unit/test_steps_instance_valid.py::test_all_tool_refs_resolve_in_tools_jsonld` — every tool_ref ULID exists in WP-006's tools.jsonld
- [ ] `tests/unit/test_steps_instance_valid.py::test_all_handles_failures_resolve_in_failuremodes_jsonld` — every FailureMode ULID exists in WP-004's failuremodes.jsonld

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/instances/release-train/steps.jsonld` authored per the Contract table
- [ ] All 15 Step instances present + valid
- [ ] tool_ref / handles_failures cross-references resolve correctly
- [ ] mechanism + criticality + agent_instructions populated per Step's role
- [ ] Step 5 (probabilistic) carries the token budget per NFR-010

### Blue — Refactor complete
- [ ] Agent_instructions are descriptive but not coercive (MUC-001 honoured — no "EXECUTE THIS NOW")
- [ ] Step names use kebab-case consistently
- [ ] No duplicated input/output artifact names across Steps (per state_contract)

## Sequence

- **dependsOn:** WP-004 (FailureModes — handles_failures refs), WP-006 (Tools — tool_ref refs)
- **blocks:** WP-001 (Workflow steps[] references Step names), WP-007 (drift detector reads Steps), WP-009 (annotations name each Step), WP-010 (skill extension surfaces Step list to founder)
- **Parallelisable with:** WP-003, WP-005, WP-011 (after WP-004 + WP-006 complete)

## Estimated Token Cost

- **Input:** ~6k (TDD Steps table + brain Step schema + WP-004 + WP-006 outputs)
- **Output:** ~8k (15 Step instances ≈ 25-35 lines each + cross-references)
- **Total:** ~14k

## Notes

- Step 4 (compute-next-version) is a composite — uses two Tools (`cumulative_tier` then `next_version`). agent_instructions names the order; tool_ref points at one (the primary; `cumulative_tier`).
- Step 7's three failure modes are the load-bearing recovery surface; ensure all three are linked.
- Step 14's `bot-tag-doesnt-trigger-release-prod` is the today's-defect-3 mitigation; the failure mode has a fallback recovery_strategy (manual `gh release create`).
