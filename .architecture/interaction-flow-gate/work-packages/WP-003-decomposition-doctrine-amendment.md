---
id: WP-003
change_id: 01KT9HJMZC4731H0TAVW1E5QCD
title: Document interaction contract's home in decomposition (SHOULD)
kind: backend
primitive: document
group: reinforce
status: pending
dependsOn: []
blocks: []
estimated_token_cost: { input: "~5k", output: "~2k" }
verification:
  adapter: backend
  artifact: tests/unit/test_interaction_contract_documented.py
tdd_section: "TDD §5 Decomposition-rule amendment (SHOULD strength)"
---

# WP-003 — Document interaction contract's home in decomposition

## Context

TDD §5. Documentation-only amendment at **SHOULD** strength (ADR-002). Give
`contract_type: interaction` a defined home in cross-kind decomposition,
sibling to the visual contract, in WP-08.5 and the contract-first doctrine.
No enforced validator (that's Phase 2). Independent of WP-001/002 — can start
now; touches standards files, not code.

## Contract

Amend two files:

1. `plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md` — WP-08.5
   (~L222–235, the "User-facing seams" callout). Add a paragraph: a
   founder-facing capability spanning a multi-step interaction flow **SHOULD**
   emit a `kind: contract` / `contract_type: interaction` child whose done-gate
   is the exercised-flow predicate (`exercised_at` + `exercised_by` ∈
   {agent-observed, human-attested} + `exercised_attestation`), enforced at the
   done-transition by `wpx-index` — sibling to the visual contract. State
   explicitly: Phase 1 is SHOULD; the MUST flip (mandatory for all
   founder-facing work) is Phase 2.
2. `plugins/sulis/references/standards/CONTRACT_FIRST_STANDARD.md` — near
   CF-05/CF-07, note the `interaction` contract type as a third contract
   flavour (alongside data + visual): its conformance is "the flow was
   exercised end-to-end over stubs," gated at done, SHOULD strength in Phase 1.

Wording must use the GLOSSARY-locked terms and the severity convention
(SHOULD = default, deviation justified). No MUST language for the interaction
contract in this phase.

## Definition of Done

### Red
- [ ] New `tests/unit/test_interaction_contract_documented.py` asserting:
  - [ ] `WORK_PACKAGE_STANDARD.md` contains `contract_type: interaction` and
        the strings `exercised` and `SHOULD` within the WP-08.5 region.
  - [ ] `CONTRACT_FIRST_STANDARD.md` references the `interaction` contract type.
  - [ ] Neither file states the interaction contract as `MUST` for
        founder-facing work (guard against accidentally landing Phase 2).
- [ ] Run; confirm failure (text not yet present) — Red.

### Green
- [ ] Make the two amendments per the contract.
- [ ] `pytest tests/unit/test_interaction_contract_documented.py` green.
- [ ] Run the repo's standards-shape tests (e.g. any `test_*_standard.py`
      touching these files) to confirm no structural break.

### Blue
- [ ] Read both amended sections end-to-end; confirm the interaction paragraph
      reads as a sibling of the visual paragraph (parallel structure), uses
      locked vocabulary, and the Phase-1-SHOULD / Phase-2-MUST boundary is
      unambiguous.
