---
id: WP-004
title: Author 7 FailureMode instances in failuremodes.jsonld
status: pending
kind: contract
primitive: create
group: GENERATE
sequence_id: WP-004
dependsOn: []
blocks: [WP-002, WP-006, WP-007, WP-009]
estimated_token_cost:
  input: 2k
  output: 3k
tdd_section: FR-008; Armor table (MUC→FailureMode mapping)
adrs: []
---

## Context

Authors the 7 FailureMode instances at
`plugins/sulis/instances/release-train/failuremodes.jsonld`. Each
FailureMode declares: `name`, `kind`, `recovery_strategy`, `detection`,
`severity`.

These are the **structural defenses against today's three lived
defects + the methodology gaps**. The drift detector (WP-007) verifies
each FailureMode has a corresponding recovery code path in
release-on-merge.yml (annotation-matched per WP-009).

No dependencies — FailureModes are leaf entities. Blocks Steps (WP-002)
which reference these by ULID in `handles_failures[]`.

## Contract

7 FailureMode instances per brain foundation v0.5.0 FailureMode schema.
Each:

```jsonld
{
  "id": "dna:failuremode:<ulid>",
  "name": "release-pr-conflicts-with-target-at-merge",
  "for_domain": "dna:tenant:<marketplace>",
  "kind": "operational",
  "description": "PR mergeable=CONFLICTING — source branch diverged from target since PR opened. Recovery: back-integrate target into source, push, retry from open-pr Step. This is the back-edge that makes the workflow cycle-tolerant.",
  "detection": "Step output of wait-for-checks-and-mergeability returns mergeable=CONFLICTING",
  "recovery_strategy": "escalate",
  "severity": "medium",
  "state": "active",
  "sys_status": "active",
  "valid_from": "2026-06-01T00:00:00Z"
}
```

The 7 FailureModes:

| # | name | kind | recovery_strategy | severity | Motivation |
|---|---|---|---|---|---|
| 1 | release-pr-conflicts-with-target-at-merge | operational | escalate | medium | The cycle-tolerance back-edge (lived today, back-integrated twice) |
| 2 | workflow-yaml-fails-to-parse | structural | abort | critical | CH-01KSYZ regression (PR #130's silent skip) |
| 3 | loop-guard-matches-founder-pr | structural | abort | high | CH-01KSZ1 regression (PR #132 skipped) |
| 4 | bot-tag-doesnt-trigger-release-prod | operational | fallback | high | GH-Actions GITHUB_TOKEN limitation (today's defect #3); manual `gh release create` |
| 5 | pr-checks-fail | operational | abort | medium | Standard CI gate; surface failure to founder |
| 6 | pr-open-but-mergeability-stuck | operational | escalate | low | The "founder walked away" gap your monitoring rule fixes |
| 7 | version-drift-detected-pre-flight | structural | abort | high | Plugin.json != marketplace.json entry; prior half-bump |

Plus #8 conceptually `no-changesets-pending` — but that's NOT a
FailureMode, it's a normal terminal verdict. Handled via Workflow
transitions, not as a FailureMode.

Plus #9 `probabilistic-step-token-budget-exceeded` per NFR-010 — added
as an 8th FailureMode to cover Step 5's token-budget overflow:

| 8 | probabilistic-step-token-budget-exceeded | operational | fallback | medium | NFR-010; fallback to deterministic CHANGELOG-from-template |

**Final count: 8 FailureModes** (revising the WP title to reflect this).

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_failuremodes_instance_valid.py::test_failuremodes_jsonld_parses`
- [ ] `tests/unit/test_failuremodes_instance_valid.py::test_8_failuremodes_present`
- [ ] `tests/unit/test_failuremodes_instance_valid.py::test_each_passes_brain_schema`
- [ ] `tests/unit/test_failuremodes_instance_valid.py::test_recovery_strategy_enum_valid` — all in {retry, compensate, escalate, abort, manual-review, fallback}
- [ ] `tests/unit/test_failuremodes_instance_valid.py::test_severity_enum_valid` — all in {low, medium, high, critical}

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/instances/release-train/failuremodes.jsonld` authored per Contract table (8 entries)
- [ ] All 8 validate against brain FailureMode schema
- [ ] Each carries a structural `description` naming the symptom + the recovery action
- [ ] Each motivates a real defect or NFR (no speculative FailureModes)

### Blue — Refactor complete
- [ ] FailureMode names use kebab-case + describe-the-failure form (`<symptom>-<context>`)
- [ ] recovery_strategy + severity assignments justified by description
- [ ] No noise — drop any FailureMode without a real motivation

## Sequence

- **dependsOn:** —
- **blocks:** WP-002 (Steps reference these by ULID), WP-006 (Tools cite these in error_catalogue for some), WP-007 (drift detector reads), WP-009 (annotations name each)
- **Parallelisable with:** WP-003, WP-011 (initial layer); WP-006 (after WP-004 done)

## Estimated Token Cost

- **Input:** ~2k (TDD Armor table + brain FailureMode schema + today's three defects context)
- **Output:** ~3k (8 FailureMode instances ≈ 15-20 lines each)
- **Total:** ~5k

## Notes

- The Workflow definition (WP-001) lists the `no-changesets-pending` case as a terminal transition guard, NOT a FailureMode. Don't double-record.
- FailureMode #1 (release-pr-conflicts) is what makes the Workflow cycle-tolerant — its description should explicitly name the back-edge it enables.
- Update title from "7" to "8" FailureModes on commit (8 instances total once probabilistic-step-token-budget-exceeded is included per NFR-010).

## Acceptance Evidence

- Branch: feat/wp-004-author-failuremodes-instance (deleted post-merge)
- Squash-merge SHA on dev: `c57c505`
- Health status: `skipped`
- Smoke-test verdict: skipped
- Completed: `2026-06-01T10:45:34Z` (Step 12 by calling session)
