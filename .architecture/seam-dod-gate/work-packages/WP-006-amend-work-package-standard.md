---
# Identity (WP-01)
id: WP-006
title: Amend WORK_PACKAGE_STANDARD.md — seam-close DoD wording + contract-WP `implements:` field
status: pending
change_id: seam-dod-gate
kind: methodology
source: feat
primitive: extend
group: EXPAND

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: low

# Lifecycle (WP-07)
sequence_id: WP-006
dependsOn: [WP-005]
blocks: []

# Composite (WP-08)
child_wps: []
kinds: null

estimated_token_cost:
  input: 4k
  output: 3k
tdd_section: §Where the standards changes land — WORK_PACKAGE_STANDARD.md DoD wording + contract-WP implements:
adrs: [ADR-004]
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/unit/test_seam_close_standards_presence.py

rollback: |
  Revert the WP-05/WP-08.5 DoD-wording additions + the contract-WP
  `implements:` SHOULD clause in WORK_PACKAGE_STANDARD.md. The
  WP-standard presence test reverts to Red. No existing requirement is
  changed in meaning beyond the additive clauses.
---

# Amend the Work Package Standard for seam-close DoD + the requirement bridge

## Context

TDD §"Where the standards changes land" → `WORK_PACKAGE_STANDARD.md`. Two small,
additive amendments:

1. **Seam-close DoD wording** (WP-05 / WP-08.5): a seam-spanning (`kind:
   contract` / integration `kind: composite`) WP is not `done` until the
   seam-close gate reports `observed` (or a conscious `--allow-deferred` was
   recorded). A seam with no covering Scenario, or one needing an execution tier
   not yet live, is blocked (per CF-12).
2. **Contract WP carries `implements:`** (WP-08.5, ADR-004): a `kind: contract`
   WP **SHOULD** carry `implements: [dna:requirement:…]` — the requirement ids
   the seam satisfies — so the seam-close gate resolves the seam to its covering
   Scenarios directly. SHOULD (not MUST) because the journey-filtered fallback
   keeps older WPs working; the explicit field is the clean path
   `/sulis:plan-work` populates going forward.

`kind: methodology` — the change is methodology machinery; this WP edits a
standards file but its verification is a structural pytest presence assertion
(the `methodology` adapter shape). Additive clauses only — no existing rule is
weakened or removed. Kind and adapter agree (P-VER 9.08).

## Contract

### Files modified

```
plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md
    (MODIFY — add the seam-close DoD wording to WP-05 + WP-08.5; add the
     contract-WP `implements:` SHOULD clause to WP-08.5; version-history row)
```

### Files modified (shared test file — append only)

```
plugins/sulis/scripts/tests/unit/test_seam_close_standards_presence.py
    (MODIFY — append `test_work_package_standard_seam_close_dod`; created by WP-005)
```

> **Peer-collision note (rubric P6):** the presence test file is created by
> WP-005 (sole creator); this WP appends its one assertion. `dependsOn: WP-005`
> pins the create-before-append order.

### Amendment wording (per TDD)

**WP-05 / WP-08.5 DoD addition:**
> "A seam-spanning (`kind: contract` / integration `kind: composite`) WP is not
> `done` until the seam-close gate reports `observed` for the seam — its
> covering Scenarios drove the real data across the seam, or a conscious
> `--allow-deferred` was recorded. A seam with no covering Scenario, or one
> needing an execution tier not yet live, is blocked (per CF-12)."

**WP-08.5 `implements:` clause:**
> "A `kind: contract` WP SHOULD carry `implements: [dna:requirement:…]` — the
> requirement ids the seam satisfies — so the seam-close gate can resolve the
> seam to its covering Scenarios directly. When absent, the gate falls back to
> the change's Scenario set filtered by journey."

### Test authored here

| Test | Asserts |
|---|---|
| `test_work_package_standard_seam_close_dod` | `WORK_PACKAGE_STANDARD.md` carries the seam-close DoD wording **and** the `implements:` contract-WP SHOULD clause |

## Definition of Done

### Red — Failing tests written
- [ ] `test_work_package_standard_seam_close_dod` appended to `test_seam_close_standards_presence.py`, **failing** before the WP-standard edits.

### Green — Implementation makes tests pass
- [ ] WP-05 + WP-08.5 gain the seam-close DoD wording.
- [ ] WP-08.5 gains the `implements:` SHOULD clause (with the fallback note).
- [ ] A version-history row added noting both amendments + provenance (CH-01KTP7).
- [ ] `test_work_package_standard_seam_close_dod` passes; WP-005's `test_contract_first_standard_has_cf12` still passes (this WP doesn't touch CF).

### Blue — Refactor complete
- [ ] The `implements:` clause names ADR-004 and notes the SHOULD-not-MUST rationale (fallback keeps legacy WPs working) inline, so a future reader understands why it isn't mandatory.
- [ ] The DoD wording cross-references CF-12 by ID (the timing rule it enforces).
- [ ] Additive only — no existing WP-NN requirement's meaning is changed; the worked-example frontmatter block (WP standard §"Required WP file shape") MAY gain an `implements:` example line for contract WPs, but no required field is removed.

## Sequence
- **dependsOn:** WP-005 (creates the shared presence-test file this WP appends to)
- **blocks:** —
- **Parallelisable with:** WP-001/002/003 (different files) — ordered after WP-005 only for the shared-file create-before-append rule

## Estimated Token Cost
- **Input:** ~4k (WORK_PACKAGE_STANDARD.md WP-05/WP-08.5 sections + the worked-example block + TDD wording + ADR-004)
- **Output:** ~3k (≈ the two clauses + version row + one presence test)
- **Total:** ~7k

## Notes
- **Open Question 1 resolution recorded in the standard:** the `implements:` field is SHOULD with a journey-filtered fallback — the chosen path (no backfill of legacy contract WPs; `/sulis:plan-work` populates it going forward). This WP is where that decision becomes methodology.
- **Why depends on WP-005 not parallel:** purely the shared test-file create-before-append ordering (rubric P6). The two standards files are otherwise independent; if the executor preferred, WP-005 could create an empty test scaffold and both run parallel — but the explicit dependency is the boring, collision-safe choice.

## Verification Plan
- **Adapter:** `methodology` (standards-doc presence assertion + PR-time review).
- **Concrete artifact:** `plugins/sulis/scripts/tests/unit/test_seam_close_standards_presence.py::test_work_package_standard_seam_close_dod`.
- **What this WP's verification proves:** the Work Package Standard now carries the seam-close DoD wording (a seam-spanning WP isn't done until `observed`) and the contract-WP `implements:` SHOULD field with its fallback — closing the requirement-bridge loop ADR-004 designed.
