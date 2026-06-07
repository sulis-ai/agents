# Sizing — interaction-flow-gate

> Generated: 2026-06-04 · change_id: 01KT9HJMZC4731H0TAVW1E5QCD · Mode: brownfield (mirror existing pattern)

## Computed metrics

| Metric | Value | Derivation |
|---|---|---|
| **sFPC** | 4 | ILF 1 (interaction-evidence WP-frontmatter shape) + EIF 0 + EI 2 (`interaction_flow_exercised` predicate, `_enforce_interaction_flow_on_done` enforcer) + EO 0 + EQ 1 (`is_interaction_contract_wp` recognition) |
| **ASR count** | 4 | regression-safety (additive-only), evidence-shape integrity (who/when/source), stub-only constraint, SHOULD-strength doctrine amendment |
| **Tier** | **S** | sFPC ≤10 and ASR ≤5 |
| **File-count sanity** | OK | Touches 2 production files (`_wpxlib.py`, `wpx-index`) + 2 standards + new test files + 1 spike card. No mismatch with tier S. |

## Per-pillar addressable coverage

| Pillar | Coverage | Approach |
|---|---|---|
| **Form** | Fully covered by sibling | The visual-contract gate already establishes the seam (recognition predicate + runtime done-gate at the `flip-status` chokepoint). Reference it; add the interaction predicate as its sibling. 1-line references, no re-derivation. |
| **Armor** | N/A for this change | No external calls, no secrets, no network. The only operational surface is a local subprocess gate; the stub-only constraint is the relevant policy. |
| **Proof** | Partially covered | The visual gate has unit + integration tests. We add the symmetric interaction tests (predicate unit tests + flip-status enforcement integration tests + the spike). |

## Decision

- Tier **S** confirmed.
- TDD references the visual-contract gate rather than restating hexagonal/clean-architecture doctrine.
- No new ADRs beyond the two genuinely-new decisions (evidence-frontmatter shape; Phase-1 omits the write-time decomposition gate).

## Notes

- This change is a deliberate **mirror** of `#45 / UXD-14` (the visual-contract done-gate). The architecture's job is to keep the sibling symmetric, not to invent new structure.
- Phase 2 (MUST-flip making interaction contracts mandatory for all founder-facing work) is explicitly out of scope and captured in the change's task backlog.
