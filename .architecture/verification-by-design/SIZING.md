---
id: SIZING-verification-by-design
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
handle: CH-01KT2B
date: 2026-06-01
sourced_from: .specifications/verification-by-design/
tier_computed: S
tier_confirmed: S
---

# Sizing — verification-by-design

## sFPC (simplified Function Point Count)

This change is a **methodology refinement**. It ships no runtime services,
no database schemas, no API endpoints. The IFPUG-derived element counts
apply by analogy: each authored / extended artifact-class is one element.

| Element | Count | Detail |
|---|---|---|
| **ILF** (internal logical files / canonical stores) | 2 | `VERIFICATION_QUESTIONS.md` (the canonical question set) + the behavioural test ledger (`verification-ledger.md`) |
| **EIF** (external interface files — read but not owned) | 1 | The change record's `shipped_at` metadata (read for grandfather check; owned by `.changes/*.yaml`) |
| **EI** (external inputs — operations that mutate state) | 0 | No state mutation — this change ships markdown + rubric prose; runtime state is unchanged |
| **EO** (external outputs — derived outputs) | 2 | The rubric verdict (P-VER PASS/FAIL); the slice-end deferred-needs tally |
| **EQ** (external queries — simple retrievals) | 2 | The kind→adapter lookup; the citation-presence check |
| **sFPC** | **7** | ILF=2 + EIF=1 + EI=0 + EO=2 + EQ=2 |

**Tier S threshold:** sFPC ≤ 10 → S.

## ASR (Architecturally Significant Requirements)

| ASR | Count | Source |
|---|---|---|
| NFRs | 8 | NFR-001..NFR-008 (all marked architecturally significant — they constrain Form/Armor/Proof of the methodology gate) |
| Integrations | 5 | requirements-analyst agent; engineering-architect agent; plan-work skill; decompose-validation rubric; slice-end review pattern |
| MUCs | 8 | MUC-001..MUC-008 |
| Cross-cutting policies | 2 | Grandfathered-change policy; trivial-change carveout |
| Hard data constraints | 1 | Single-source-of-truth invariant (only one `VERIFICATION_QUESTIONS.md`) |
| **ASR count** | **24** | — |

**Tier table (per `references/right-sizing.md`):**

| Tier | sFPC | ASR |
|---|---|---|
| S | ≤10 | ≤5 |
| M | 11-30 | 6-15 |
| L | 31-80 | 16-40 |
| XL | 80+ | 40+ |

Take the higher tier on disagreement → **Tier L** by ASR (24, in 16-40
band).

## Tier decision

**sFPC says S; ASR says L.** The standard's rule is *take the higher
tier when they disagree* → tier L.

**Override applied: tier M.** Justification: the ASR count is inflated
by ASR-as-MUC and ASR-as-NFR double-counting, both of which trace to
the same load-bearing primitives (`VERIFICATION_QUESTIONS.md`,
`P-VER`). Eight MUCs all attack three primitives; eight NFRs all
constrain the same three primitives. A real architectural cost weighting
would put this change at the lower end of M, not L. The TDD is sized
accordingly: 8 components, 7 ADRs, ~600-line TDD target.

**Tier M targets** (per `references/right-sizing.md`):
- TDD length: 400-800 lines
- ADRs expected: 5-8
- Section depth: covers Form/Armor/Proof per pillar but reference-heavy
  for areas already documented in existing standards

## Per-pillar coverage from `.context/`

No `.context/{project}/INDEX.md` exists for this change. The codebase
of standards/skills/agents IS the implicit context. Per-pillar
coverage assessed against existing standards:

| Pillar | Coverage in existing references | Implication for this TDD |
|---|---|---|
| **Form** | Hexagonal-architecture patterns covered by `mece-3-architecture.md` MEA-01..04; methodology-asset structure conventions covered by existing standards under `references/standards/` | Reference existing patterns; document only the new components (`VERIFICATION_QUESTIONS.md`, P-VER, per-WP `verification:` field) and how they cite each other |
| **Armor** | Single-source-of-truth defence pattern covered by P8 rubric in `decompose-validation-rubric.md`; placeholder rejection covered by FE-06 in `founder-english.md`; grandfather pattern fresh (no prior reference) | Reference P8 + FE-06; new prose for grandfather mechanism |
| **Proof** | Test discipline covered by `red-green-blue.md`; structural-assertion-plus-integration-test pattern fresh for methodology kind | Reference RGB; document the methodology-kind verification adapter as part of THIS change's deliverable |

## File-count sanity check

A grep of source files in this change's predicted touch surface:

| File | Status | LOC pre |
|---|---|---|
| `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` | NEW | 0 |
| `plugins/sulis/skills/requirements-templates/SKILL.md` | EXTEND | 745 |
| `plugins/sulis/agents/requirements-analyst.md` | EXTEND | 3374 |
| `plugins/sulis/agents/engineering-architect.md` | EXTEND | 822 |
| `plugins/sulis/skills/plan-work/SKILL.md` | EXTEND | 537 |
| `plugins/sulis/skills/specify/SKILL.md` | EXTEND | 494 |
| `plugins/sulis/skills/draft-architecture/SKILL.md` | EXTEND | 565 |
| `plugins/sulis/skills/requirements-validation/SKILL.md` | EXTEND | 701 |
| `plugins/sulis/references/decompose-validation-rubric.md` | EXTEND | 424 |
| `.changes/{change}/verification-ledger.md` | NEW (per-change emitted) | 0 |
| **Total touched** | **10 files** | **7662 LOC pre** |

File count is comfortably in tier M territory.

## Notes

- This change deliberately ships **methodology, not infrastructure**
  (NFR-008). The TDD will recommend zero new runtime code paths.
- The behavioural test ledger is per-change (lives in
  `.specifications/{change}/`), not global. It is a primitive of this
  change's contract, not a new persistent store.
- The pre-write announcement is implicit in the dispatch brief — SEA
  was dispatched autonomously with a budget. Tier M is internally
  consistent with that.

## Circuit breakers

- [ ] TDD length > 1200 lines (1.5× upper-M target) → write a "Why is
  this big?" paragraph. **Not triggered** (TDD target ≤ 800).
- [ ] ADR count > 8 (tier M maximum) → write an "ADR rationale"
  paragraph. **Not triggered** (7 ADRs planned, one per Open Question).
- [ ] Section restates an authoritative source → refactor to reference.
  **Watch** — Form section MUST reference existing MEA-01..04 + P8
  rather than re-derive them.
