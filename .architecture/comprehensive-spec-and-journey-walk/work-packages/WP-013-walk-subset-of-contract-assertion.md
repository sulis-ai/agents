---
id: WP-013
title: Build the walk-operations-subset-of-contract assertion (contract-first integration)
status: pending
sequence_id: WP-013
dependsOn: [WP-009, WP-011]
blocks: []
estimated_token_cost:
  input: 6k
  output: 4k
tdd_section: 7.4 (_assert_walk_subset_of_contract.py) + 7.6 (contract completeness check)
adrs: [ADR-007]
primitive: create
group: expand
kind: backend
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_assert_walk_subset_of_contract.py::test_walked_op_absent_from_contract_is_flagged
---

## Context

FR-19 requires every walked tool operation to appear in the interface-contract
section (the tool walk is a subset of the contract). `_assert_walk_subset_of_contract.py`
checks this mechanically over the produced document (NFR-D03, ADR-007's §7.6
completeness check). This is the **integration WP of the contract-first seam**
(CF-05): it `dependsOn` both the contract *producer* (WP-011's full contract
section) and the walk *consumer* (WP-009's tool walk), and closes the graph by
verifying the consumer's operations ⊆ the producer's contract. Ships the SC-19
assertion.

Advances DESIGN.md §6.5 hop T10 (GAP → WP, Phase 3), the §7.4
`_assert_walk_subset_of_contract.py` "Create" row, and the §7.6 contract-
completeness check (the mechanical enforcement).

## Contract

```python
# plugins/sulis/scripts/_assert_walk_subset_of_contract.py (this WP creates)
# CLI: python3 _assert_walk_subset_of_contract.py <design-doc>
#   exit 0 iff every operation in the tool ## Journey Walk table appears as an
#   operation in the §7.6 interface-contract section.
#   exit 1 if a walked operation is absent from the contract (OperationNotInContract,
#   FR-19) — or, for a cross-kind side, if it has no contract reference (flagged).
```

Invariants:
- Walk ⊆ contract: a walked operation absent from the contract ⇒ non-zero
  (FR-19, NFR-D03) — `OperationNotInContract`, the operation must be added to the
  contract first.
- A cross-kind side with no contract reference ⇒ flagged (SC-19).
- Pure document inspector — no production-code dependency beyond reading the
  produced design doc.

## Definition of Done

### Red — Failing tests written
- [ ] `test_assert_walk_subset_of_contract.py::test_walked_op_absent_from_contract_is_flagged` — a doc whose tool walk references an op not in §7.6 ⇒ non-zero (SC-19).
- [ ] `test_assert_walk_subset_of_contract.py::test_walk_subset_of_contract_passes` — every walked op present in the contract ⇒ exit 0.
- [ ] `test_assert_walk_subset_of_contract.py::test_crosskind_side_without_contract_ref_flagged` — a cross-kind operation with no contract reference ⇒ flagged.

### Green — Implementation makes tests pass
- [ ] `_assert_walk_subset_of_contract.py` exists and passes.
- [ ] Runs against a real tool-surface design doc (produced via WP-002's walk driver + WP-011's contract section).

### Blue — Refactor complete
- [ ] Operation-extraction shares WP-003's section-parsing + WP-009's table-parsing helpers (no duplicated table walk).
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** WP-009 (the tool-walk operations being checked), WP-011 (the full contract section checked against)
- **blocks:** none (integration WP — closes the contract-first seam, last in P3)
- **Parallelisable with:** WP-012 (different file scope)

## Estimated Token Cost

- **Input:** ~6k
- **Output:** ~4k (assertion script + test file)
- **Total:** ~10k

## Notes

- CF-05 contract-first integration: this is the LAST WP of the contract seam —
  producer (WP-011 contract section) and consumer (WP-009 tool walk) both land
  first; this WP verifies consumer ⊆ producer. It depends on both, never the
  reverse.
- ADR-007 §7.6: the mechanical enforcement of the contract-completeness check.
