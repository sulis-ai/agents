---
id: WP-003
title: Author 2 Trigger instances in triggers.jsonld
status: pending
kind: contract
primitive: create
group: GENERATE
sequence_id: WP-003
dependsOn: []
blocks: [WP-007]
estimated_token_cost:
  input: 1k
  output: 1k
tdd_section: Form — Component inventory (#3); FR-007
adrs: []
---

## Context

Authors the 2 Trigger instances at
`plugins/sulis/instances/release-train/triggers.jsonld`. Triggers
declare what fires the Workflow:

- `manual-release-train-invocation` — founder runs `/sulis:release-train`
- `pull-request-merged-to-main` — release-on-merge.yml fires on push to main

No dependencies. Authored alongside other entities; consumed by the
drift detector + execute-workflow agent.

## Contract

Per brain foundation v0.5.0 Trigger schema:

```jsonld
{
  "@id": "dna:release-train:triggers",
  "for_tenant": "dna:tenant:<marketplace>",
  "triggers": [
    {
      "id": "dna:trigger:<ulid>",
      "name": "manual-release-train-invocation",
      "for_domain": "dna:tenant:<marketplace>",
      "kind": "manual",
      "description": "Founder runs /sulis:release-train against a marketplace plugin Project.",
      "state": "active",
      "sys_status": "active",
      "valid_from": "2026-06-01T00:00:00Z"
    },
    {
      "id": "dna:trigger:<ulid>",
      "name": "pull-request-merged-to-main",
      "for_domain": "dna:tenant:<marketplace>",
      "kind": "event",
      "description": "GitHub release-on-merge workflow fires on push to main. Filtered by author != github-actions[bot] (CH-01KSZ1 loop-guard fix).",
      "state": "active",
      "sys_status": "active",
      "valid_from": "2026-06-01T00:00:00Z"
    }
  ]
}
```

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_triggers_instance_valid.py::test_triggers_jsonld_parses` — file exists
- [ ] `tests/unit/test_triggers_instance_valid.py::test_both_triggers_present` — exactly 2 Trigger instances
- [ ] `tests/unit/test_triggers_instance_valid.py::test_each_trigger_passes_brain_schema` — Trigger schema valid

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/instances/release-train/triggers.jsonld` authored per Contract
- [ ] Both Triggers validate against brain Trigger schema (foundation v0.5.0)
- [ ] kind ∈ {manual, event}; descriptions named the actor + condition

### Blue — Refactor complete
- [ ] No noise — Trigger descriptions terse + structural

## Sequence

- **dependsOn:** —
- **blocks:** WP-007 (drift detector reads Triggers for trigger-existence check)
- **Parallelisable with:** WP-001, WP-002, WP-004, WP-005, WP-006, WP-011

## Estimated Token Cost

- **Input:** ~1k (brain Trigger schema + WP context)
- **Output:** ~1k (~30 lines of JSON-LD)
- **Total:** ~2k

## Notes

- Triggers are informational under Path A — the imperative bash actually
  responds to GH-Actions events. They're recorded for completeness +
  drift-detector validation surface.
