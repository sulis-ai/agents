# ADR-002 — Phase 1 omits the write-time decomposition gate

> Status: accepted · change_id: 01KT9HJMZC4731H0TAVW1E5QCD · Tier S

## Context

The visual-contract gate has **two** enforcement halves:

1. **Write-time** — `validate_frontend_wp_visual_contract` runs at the
   `_cells_from_frontmatter` chokepoint: a `kind: frontend` WP cannot enter
   the INDEX unless it declares (and `dependsOn`) a visual-contract WP. This
   makes the visual contract *mandatory* for every frontend WP.
2. **Runtime** — `_enforce_interaction_flow_on_done` (sibling:
   `_enforce_visual_contract_signoff_on_done`) refuses `flip-status --to done`
   until evidence is recorded.

The interaction gate could mirror *both* halves. The write-time half would
mean: every founder-facing WP must declare an interaction contract or be
refused at INDEX entry. That is exactly the spec's **Phase 2 MUST flip** —
explicitly out of scope for this change.

## Decision

**Phase 1 builds only the runtime half.** We add the runtime done-gate
(`_enforce_interaction_flow_on_done` + `interaction_flow_exercised` +
`is_interaction_contract_wp`) and recognise `contract_type: interaction`.
We do **not** add a write-time chokepoint that forces founder-facing WPs to
carry an interaction contract.

The decomposition-rule change in this phase is **documentation at SHOULD
strength** (WP-08.5 + contract-first doctrine gain a defined home for the
`interaction` contract type) — not an enforced validator.

## Rationale

- **The spec draws this line explicitly.** "Phase 1 builds and proves the
  mechanism; the decomposition-rule MUST flip … is Phase 2, so in-flight
  founder-facing WPs aren't all blocked the day this lands."
- **Regression-safety is the third acceptance criterion.** A write-time gate
  would, by construction, block existing founder-facing WPs that don't yet
  carry an interaction contract — the exact friction the phasing exists to
  avoid.
- **The runtime gate is self-sufficient for the spike.** A WP that *opts in*
  by declaring `contract_type: interaction` is fully gated at flip-to-done;
  that is everything the clinics-scheme spike needs to demonstrate
  block → exercise → release.

## Alternatives considered

- **Mirror both halves now.** Rejected: this is Phase 2; it would block
  in-flight work and contradict the spec's non-goals.
- **Add a write-time gate but in warn-only mode.** Rejected: a warn-only
  validator is neither the SHOULD-strength documentation Phase 1 wants nor
  the MUST enforcement Phase 2 wants — it would create a third, undocumented
  strength level and invite drift.

## Consequences

- `is_interaction_contract_wp` is used only by the runtime enforcer in this
  phase. The recognition predicate is the seam Phase 2 will reuse when it adds
  the write-time gate, so it lands now with no behavioural cost.
- The Phase-2 MUST flip is recorded in the change's task backlog.
