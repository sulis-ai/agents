# Sizing — platform-contract-standard

> **Computed:** 2026-06-02
> **Mode:** Greenfield (spec-driven; methodology authoring in the marketplace repo)
> **Source:** `.specifications/platform-contract-standard/` (SRD, NFR, MISUSE_CASES, PRIMITIVE_TREE)

## Functional complexity

### sFPC (simplified Function Point Count)

| Element | Count | Items |
|---|---|---|
| **ILF** (internal data stores authored) | 3 | the contract-artifact schema; the GitHub Actions contract instance; the `platform-contracts/INDEX.md` |
| **EIF** (external / consumed interfaces) | 4 | faithful-generation-harness (sibling repo); decompose-validation-rubric; VERIFICATION_QUESTIONS.md; GitHub docs (manifest source) |
| **EI** (mutating ops) | 3 | harness-invocation glue (produces a contract); specify gate check; draft-architecture gate check |
| **EO** (deriving ops) | 2 | P-PLAT rubric check (derives a verdict); Verification-Plan feed (derives assertions/observables) |
| **EQ** (retrieving ops) | 1 | freshness / staleness lookup on reuse |
| **sFPC** | **13** | → tier **M** (11–30) |

### ASR (Architecturally Significant Requirements)

| Source | Count |
|---|---|
| NFRs | 8 (NFR-001..008) |
| Integrations | 3 (harness, rubric, VERIFICATION_QUESTIONS) |
| MUCs | 7 (MUC-001..007) |
| Cross-cutting policies | 3 (gate-scope write/deploy-vs-read-only; freshness; grandfather) |
| Hard data constraints | 1 (the claim-entry conformance schema) |
| **ASR** | **22** | → tier **L** (16–40) |

## Tier

sFPC → M; ASR → L. **Take the higher tier: L.**

The ASR count is unusually high for a methodology change because this change is *about*
gate integrity — its whole value is the seven misuse cases it prevents, so the MUC/NFR
density is inherent, not incidental. The tier is **L** by the rule "take the higher tier
when they disagree."

**Confirmed tier:** L (autonomous run — founder-resolved scope in the dispatch confirms
the change is non-trivial: standard + gate + first real contract + rubric phase).

## Per-pillar addressable scope

The TDD target shrinks because this change *mirrors three existing siblings* and *extends
two existing components* rather than building net-new infrastructure. Coverage is assessed
against what already exists in the marketplace (no `.context/` index exists; assessed
directly from the repo).

| Pillar | Coverage | Target |
|---|---|---|
| **Form** | Partially covered — sibling-standard shape (`CONTRACT_FIRST_STANDARD.md`, `UX_VISUAL_DESIGN_STANDARD.md`) is the template; the rubric phase pattern (P-VER, Phase 7) is the template. **Fill the gap:** the contract-artifact schema, the storage/index convention, the harness-invocation glue, the gate wiring, P-PLAT. | Full section — these are the net-new design decisions |
| **Armor** | Largely defined by the spec's NFRs + MUCs (refusal path, freshness, reviewability, probe integrity, harness-provenance). **Fill the gap:** map each MUC system-response to a mechanical control. | Full table — one row per MUC |
| **Proof** | Verification Plan is already authored in the SRD (six subsections, three integrations classified). **Reference + concretise**, don't restate: resolve the SRD's strategies into TDD-level test artifacts. | Concretion table + the n=1 dogfood as the load-bearing proof |

## Tier-L expectations vs target

- **TDD length target:** ~250–400 lines (tier L). This change sits at the **low end** of
  tier L because Form references two sibling templates rather than deriving structure from
  scratch, and Proof references the already-authored Verification Plan.
- **ADR count:** 6 (founder named all six in the dispatch). All six are genuine
  cross-component or technology-lock decisions — none is quota-filling.
- **Circuit breakers:** none expected to trigger. If the TDD exceeds ~600 lines a
  "Why is this big?" paragraph is required.

## Notes

- No `.context/{project}/INDEX.md` exists; the "respect-don't-restate" discipline is applied
  directly against the repo's existing standards and rubric.
- The faithful-generation-harness lives in a **sibling repo**
  (`/Users/iain/Documents/repos/plugins/plugins/sulis-brain/instances/faithful-generation-harness/`),
  not in this change's checkout. This cross-repo boundary is load-bearing for ADR-004.
- ASRs are documented (from the SRD), not inferred — no confidence flag needed.
