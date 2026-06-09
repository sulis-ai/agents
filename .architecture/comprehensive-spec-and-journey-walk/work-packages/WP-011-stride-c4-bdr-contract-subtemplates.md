---
id: WP-011
title: Add STRIDE, C4, BDR, and the CF-10 interface-contract sub-templates
status: pending
sequence_id: WP-011
dependsOn: [WP-001, WP-006]
blocks: [WP-013]
estimated_token_cost:
  input: 8k
  output: 6k
tdd_section: 7.4 (requirements-templates/SKILL.md) + 4.6 (STRIDE) + 7.2 (C4) + 7.6 (contract)
adrs: [ADR-002, ADR-007]
primitive: extend
group: expand
kind: docs
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_drive_specify.py::test_doc_carries_stride_c4_and_contract
---

## Context

WP-006 landed the comprehensive base template with a contract-section skeleton.
P3 (FR-15/16/17/18) rounds it out: an always-on STRIDE threat model section, C4
architecture-at-levels (context/container/component), a BDR sub-template
alongside ADR, and the full CF-10 interface-contract section (schema + three-
category errors per CF-03 + the four founder-reviewable dimensions). ADR-007
makes the contract a mandatory doc section the tool-walk reads operations from.
This WP also ships the assertion scripts SC-15/SC-16/SC-18 invoke
(`_assert_stride.py`, `_assert_c4_levels.py`, `_assert_interface_contract.py`).

Advances DESIGN.md §6.5 hops T2/A5 (GAP → WP, Phase 3) and the §7.4
`requirements-templates/SKILL.md` "Create (1 + 3)" row.

## Contract

```text
# plugins/sulis/skills/requirements-templates/SKILL.md (this WP extends WP-006's template)
#   STRIDE sub-template: a threat table (S/T/R/I/D/E), trust boundaries, attack
#     surface (FR-15).
#   C4 sub-template: three mermaid levels — context, container, component (FR-16).
#   BDR sub-template: business-decision record shape, distinct from ADR (FR-17).
#   Interface-contract sub-template: per operation — schema (in/out types),
#     three-category errors (Protocol/Expected/Internal, CF-03), AND the four
#     CF-10 dimensions (auth, audience, user-guide, error-fixes) (FR-18).

# plugins/sulis/scripts/_assert_stride.py            ⇒ exit 0 iff a STRIDE section present (SC-15)
# plugins/sulis/scripts/_assert_c4_levels.py         ⇒ exit 0 iff context+container+component present (SC-16)
# plugins/sulis/scripts/_assert_interface_contract.py ⇒ exit 0 iff the contract carries all 4 CF-10 dimensions per operation; a missing dimension ⇒ incomplete (SC-18)
```

Invariants:
- For a tool-surface change, the contract section is mandatory; a missing
  dimension ⇒ design stage does not complete (SC-18, FR-18, MUC-07).
- STRIDE and C4 are always-on (present even when thin → `n/a — <reason>`, NFR-R01).
- The contract section's operations are the source the tool walk (WP-009) reads
  from; this WP fills the skeleton WP-006 stubbed (ADR-007).
- Lightweight CONTRACT_FIRST tier: schema + three-category errors + CF-10
  dimensions, no multi-language codegen (DESIGN.md §7.6 note).

## Definition of Done

### Red — Failing tests written
- [ ] `test_drive_specify.py::test_doc_carries_stride_c4_and_contract` — drive `sample-tool-surface`; `_assert_stride`, `_assert_c4_levels`, `_assert_interface_contract` all exit 0 (SC-15, SC-16, SC-18).
- [ ] `test_assert_interface_contract.py::test_missing_cf10_dimension_is_incomplete` — a contract op missing the user-guide dimension ⇒ non-zero (SC-18 negative).
- [ ] `test_assert_c4_levels.py::test_two_levels_only_fails` — context+container but no component ⇒ non-zero.

### Green — Implementation makes tests pass
- [ ] The four sub-templates extend WP-006's base template.
- [ ] `_assert_stride.py`, `_assert_c4_levels.py`, `_assert_interface_contract.py` exist and pass.
- [ ] A tool-surface fixture document carries the full contract section.

### Blue — Refactor complete
- [ ] The three assertion scripts reuse WP-003's markdown-section-parsing helper (no duplicated header detection).
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** WP-001 (the specify driver), WP-006 (the base template these sub-templates extend)
- **blocks:** WP-013 (the walk-⊆-contract assertion needs the full contract section to check against)
- **Parallelisable with:** WP-012 (decision schema — different file scope)

## Estimated Token Cost

- **Input:** ~8k (this WP + the STRIDE/C4/contract structures from DESIGN §4.6/§7.2/§7.6)
- **Output:** ~6k (four sub-templates + three assertion scripts + tests)
- **Total:** ~14k

## Notes

- ADR-007: the contract is a mandatory doc section the walk reads from — this WP
  is the *producer* side of the contract-first seam (CF-05); WP-009's walk is the
  consumer, WP-013 is the integration check (last).
- ADR-002: structure invariant. STRIDE/C4 are always present even when thin.
