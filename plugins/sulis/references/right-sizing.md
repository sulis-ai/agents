# Right-Sizing the Architecture Effort

> **Status:** Active — v0.5.0

The architecture output should fit the project, not the template. A small
feature does not deserve a 600-line TDD with eleven ADRs. A complex
multi-bounded-context system cannot be served by a 200-line skeleton. The
"Full" TDD template is a *maximum*, not a target.

This standard codifies how SEA decides how much to write. It does so by
measuring **functional complexity**, not code volume — because file count,
LOC, and similar volume proxies routinely mislead in both directions.

---

## Provenance and Industry Context

This standard adapts two established frameworks:

**Function Point Analysis** (Albrecht, 1979; IFPUG, ongoing). FPA counts
what a system *does* — Internal Logical Files, External Interface Files,
External Inputs, Outputs, and Inquiries — weighted by complexity, then
adjusted for system characteristics. The result is language-agnostic and
measures functionality rather than implementation volume.

**Architecturally Significant Requirements** (Bass, Clements, Kazman —
*Software Architecture in Practice*). ASRs are requirements that strongly
influence the architecture, are difficult to satisfy, and force trade-offs.
Identifying them is a workshop activity in formal SEI practice.

This standard borrows the **structure** of both — counting functional
elements (FPA) and architecturally significant requirements (ASR) — without
adopting either in IFPUG-compliant or SEI-workshop form. The output is a
fast, reproducible complexity proxy computable from the SRD artifacts
SEA already reads.

**Why not formal FPA?** IFPUG requires per-element Low/Average/High
complexity assessments using detailed lookup tables, plus 14 General System
Characteristics ratings applied as a Value Adjustment Factor. Too heavy for
a slash-command session. We treat every element as "Average" and skip the
VAF. The result is `sFPC` — *simplified* Function Point Count — and we are
explicit that this deviates from IFPUG.

**Why not formal ASR identification?** SEI's ASR workshop process involves
stakeholder interviews and prioritisation. SEA assumes every NFR, every
integration, and every misuse case is architecturally significant for
sizing purposes — an over-inclusive heuristic that biases toward bigger
tier in ambiguous cases.

**Other related conventions we are *not* using:**

- **COCOMO II** — sizes by SLOC + 17 cost drivers. SLOC-based, which we are explicitly avoiding.
- **Cyclomatic / Cognitive Complexity** — per-function metrics; don't aggregate to system sizing.
- **C4 Model** (Brown) — documentation effort scales by level (Context → Container → Component → Code). Excellent vocabulary but no quantitative tier prescription.
- **DDD Bounded Contexts** (Evans) — used as a *promotion criterion* to XL tier, not as a counter.

We acknowledge: **all sizing heuristics proxy complexity imperfectly.** The
manual tier override exists because the metrics will sometimes be wrong.

---

## Two-Axis Sizing Model

SEA's output size is governed by two axes.

### Axis 1 — Functional Complexity (sFPC + ASR)

How much does the system do, and how many architecturally significant
constraints shape it?

#### sFPC — simplified Function Point Count

Five element types, each counted by parsing SRD artifacts:

| Element | Definition | Where SEA finds it |
|---|---|---|
| **ILF** — Internal Logical Files | Data the system maintains | `PRIMITIVE_TREE.jsonld` nodes where `type ∈ {domain-entity, data-store}` |
| **EIF** — External Interface Files | Data the system reads from external sources | `PRIMITIVE_TREE.jsonld` nodes where `type = integration` (inbound or bidirectional) |
| **EI** — External Inputs | Operations that change state | Use cases in `SRD.md` whose flow includes a write/mutate step |
| **EO** — External Outputs | Operations producing derived data | Use cases whose flow includes computation, formatting, or aggregation |
| **EQ** — External Inquiries | Operations that retrieve data with no derivation | Use cases that read but don't mutate or derive |

```
sFPC = count(ILF) + count(EIF) + count(EI) + count(EO) + count(EQ)
```

Treat every element as "Average" complexity. Skip the VAF. Document the
simplification in the SIZING.md output.

#### ASR — Architecturally Significant Requirements

Five sources, each counted by parsing SRD artifacts:

| Source | Where SEA finds it |
|---|---|
| **NFRs** | `NFR.md` — every NFR-NNN entry |
| **Integrations as ASRs** | `PRIMITIVE_TREE.jsonld` integration nodes (each carries protocol/auth/error/resilience decisions) |
| **MUCs** | `MISUSE_CASES.md` — every MUC-NNN entry (each forces an Armor decision via its System Response) |
| **Cross-cutting policies** | `PRIMITIVE_TREE.jsonld` nodes where `type = policy` |
| **Hard data constraints** | NFR or business rule entries that mandate a specific retention period, integrity guarantee, residency requirement, or consistency model |

```
ASR_count = NFRs + integrations + MUCs + cross_cutting_policies + hard_data_constraints
```

Some double-counting is unavoidable (a security NFR may also map to a MUC,
which also maps to an integration's ASR surface). Tolerate it — we're using
the count as a tier signal, not a billing metric.

#### Tier from sFPC × ASR

| Tier | sFPC | ASR | Description |
|---|---|---|---|
| **S** (Small) | ≤ 10 | ≤ 5 | Small feature, few integrations, few NFRs |
| **M** (Medium) | 11-30 | 6-15 | A capability with several primitives + meaningful hardening surface |
| **L** (Large) | 31-80 | 16-40 | Full subsystem with rich integration + extensive NFR/MUC coverage |
| **XL** (Extra Large) | 80+ | 40+ | Multi-context system; promote to XL also if multiple bounded contexts are evident |

**Either axis can promote tier.** Take the higher of the two. A system with
sFPC=8 (small data model) but ASR=20 (extensive cross-cutting concerns)
is tier L — the architectural work is in the hardening surface, not the
entities.

**Either axis can keep tier low.** sFPC=60 in a CRUD app with two NFRs
and one integration is tier M for architecture purposes — many entities,
few decisions.

**DDD promotion to XL.** Independent of the counts, if the work spans
two or more bounded contexts (multiple business domains, multiple deployable
services), promote to XL and split into per-context TDDs.

### Axis 2 — Addressable Scope (per-pillar coverage)

How much of the work is *not already covered* by authoritative sources in
`.context/{project}/INDEX.md`?

The principle: SEA's output addresses the gap between what the project
*needs* and what the project *already documents*. If the context index
marks `ARCHITECTURE.md` as authoritative and it covers the Form pillar
fully, SEA's Form section is a one-line reference, not a re-derivation.

Coverage is judged per MECE-3 pillar:

| Pillar | Fully covered when the index has authoritative... |
|---|---|
| **Form** | Architecture docs, domain models, or component-inventory docs covering all primitives the new work touches |
| **Armor** | Standards docs for resilience, secrets, observability — covering the integration types and MUCs the new work introduces |
| **Proof** | Test conventions covering contract tests, integration test patterns, and chaos test patterns at the same depth the new work demands |

When a pillar is **fully covered**, that section of the TDD is a one-line
reference. When **partially covered**, the section addresses only the gap.
When **uncovered**, the section is full-tier-sized.

---

## Combined Sizing Decision

Compute tier from Axis 1. Then *shrink* the target by Axis 2 coverage:

| Tier | Fully covered pillar | Partially covered pillar | Uncovered pillar |
|---|---|---|---|
| S | 1 line + reference | ~50 lines for the gap | Full S section |
| M | 1 line + reference | ~100 lines for the gap | Full M section |
| L | 1 line + reference | ~200 lines for the gap | Full L section |
| XL | 1 line + reference per context | Per-context summary + gap detail | Full XL split per context |

### Per-tier output expectations

| Tier | Total TDD (uncovered baseline) | Total TDD (rich coverage) | Expected ADRs | Form components |
|---|---|---|---|---|
| S | 100-300 lines | 50-150 lines | 0-3 | 1-4 |
| M | 300-600 lines | 150-300 lines | 2-6 | 4-12 |
| L | 600-1000 lines | 200-500 lines | 5-12 | 10-25 |
| XL | per-context: M or L sized | per-context, reduced by coverage | per-context counts | per-context |

### Proof section sizing

| Tier | Contract tests | Integration tests | Chaos tests |
|---|---|---|---|
| S | One per port; in-memory only if mocks would otherwise be used | 1 (golden path) | Only if NFR explicitly requires |
| M | Per port; in-memory + one real adapter via testcontainers | 2-4 | 2-4 (one per critical resilience primitive) |
| L | Per port; in-memory + every real adapter | 5-10 | 5-12 (per resilience primitive on hot path) |
| XL | Per port per context | Per context | Per context |

**Chaos tests need a named NFR or MUC.** Each must defend a specific
requirement. A chaos test for "what if the cache is down" without a
corresponding NFR/MUC is testing imagination, not requirements — drop it.

---

## Brownfield Equivalence

When SEA runs on a brownfield codebase **without an SRD** (audit-only mode),
sFPC and ASR are derived from the code itself rather than from SRD
artifacts:

| Element | Where to find it in code |
|---|---|
| **ILF** | Database schemas, ORM models, persistent collection definitions |
| **EIF** | Outbound HTTP/RPC/queue clients to external systems |
| **EI** | Endpoints that mutate state — POST/PUT/PATCH/DELETE handlers, message consumers that update state |
| **EO** | Endpoints that compute or aggregate — derived reports, calculated responses |
| **EQ** | Endpoints that read without derivation — simple GETs |
| **NFRs as ASRs** | Inferred from observed thresholds (rate limits, timeouts, retention policies) — but flag as "inferred, not documented" if no NFR.md exists |
| **Integrations as ASRs** | Same as EIF |
| **MUCs as ASRs** | Inferred from auth/audit/replay-protection code paths — flag as "inferred" |
| **Cross-cutting policies** | Middleware, interceptors, decorators with authz/audit/rate-limit purpose |

**Inferred counts are flagged in SIZING.md.** When the auditor is guessing
("system likely has X NFR based on observed behaviour"), the count is recorded
with a confidence note. The Sizing Report makes this visible so the user
can correct.

**File count is a sanity check, not a tier driver.** If sFPC + ASR suggest
tier S but the codebase has 2000+ files, surface the mismatch:
*"Computed tier is S but codebase has 2247 source files. Either the codebase
has substantial volume not represented in the functional metrics
(generated code? boilerplate?), or the audit scope should be narrowed to
specific modules. Want to override tier or scope?"*

---

## SIZING.md — The Sizing Artifact

The first SEA skill in a session computes sFPC + ASR + per-pillar coverage
once and writes the result to `.architecture/{project}/SIZING.md`.
Subsequent skills read this file rather than recomputing.

### When SIZING.md is generated

- First time a SEA skill runs on a project after `.context/{project}/INDEX.md`
  is produced
- When any source artifact's mtime is newer than SIZING.md's `Generated`
  timestamp (regenerated to match)
- Manually via `/sea:size` (planned for v0.6.0 — for now, inline in each skill)

### Schema

```markdown
# Sizing Report

> **Project:** {project-slug}
> **Generated:** {ISO timestamp}
> **Generated by:** /sea:{skill-name}
> **Source artifacts:** SRD.md@{mtime}, PRIMITIVE_TREE.jsonld@{mtime}, NFR.md@{mtime}, MISUSE_CASES.md@{mtime}, CONTEXT_INDEX.md@{mtime}

## Summary

- Tier (computed): {S | M | L | XL}
- Tier (confirmed by user): {same | overridden to ...}
- Target TDD length: {range}
- Expected ADRs: {range}

## sFPC = {N}

| Element | Count | Source |
|---|---|---|
| ILF — entities + data stores | 8 | PRIMITIVE_TREE: 6 domain-entity + 2 data-store |
| EIF — integrations | 4 | PRIMITIVE_TREE: 4 integration |
| EI — mutating operations | 9 | SRD use cases UC-01, UC-03, UC-05, ... |
| EO — deriving operations | 4 | SRD use cases UC-02, UC-07, ... |
| EQ — retrieving operations | 2 | SRD use cases UC-04, UC-06 |

> sFPC is simplified Function Point Count — informed by IFPUG FPA but treats
> every element as Average complexity and omits the Value Adjustment Factor.
> Not IFPUG-compliant.

## ASR Count = {N}

| Source | Count | Items |
|---|---|---|
| NFRs | 6 | NFR-01...NFR-06 |
| Integrations (also counted as EIF) | 4 | (see EIF row above) |
| MUCs | 3 | MUC-01, MUC-02, MUC-03 |
| Cross-cutting policies | 4 | PRIMITIVE_TREE: 4 policy nodes (auth, audit, observability, rate-limit) |
| Hard data constraints | 0 | None classified |

> ASR counting follows Bass/Clements/Kazman in spirit but does not formally
> classify each requirement through a workshop process. All NFRs,
> integrations, and MUCs are presumed architecturally significant for sizing.

## Pillar Coverage (from .context/{project}/INDEX.md)

| Pillar | Status | Authoritative sources |
|---|---|---|
| Form | fully covered | architecture/ARCHITECTURE.md, architecture/DOMAIN_MODEL.md |
| Armor | partially covered | architecture/standards/AGENT_IMPLEMENTATION.md (auth + observability only) |
| Proof | uncovered | — |

If no context index exists, all pillars are recorded as "uncovered" and the
TDD is sized to the tier baseline without shrinkage.

## Sections to Reference (Don't Restate)

- Form (fully covered by ARCHITECTURE.md§3 and DOMAIN_MODEL.md§2)
- Armor → auth and observability subsections only (covered by standards/AGENT_IMPLEMENTATION.md§4-5)

## Sections to Write Fully

- Armor → resilience, secrets, integrity subsections (uncovered)
- Proof → entire section (uncovered)

## Notes and Inferred Values

- {Free-form notes from the agent about borderline classifications, low-confidence inferences, or user-supplied overrides}
```

### How downstream skills consume SIZING.md

1. **Read it first** — before generating any artifact.
2. **Honour the tier** — total output ≤ target range, ADRs ≤ expected range.
3. **Apply the Reference / Write split** — each pillar gets the depth recorded.
4. **Refresh if stale** — if source-artifact mtimes are newer than `Generated`, regenerate before proceeding (or surface the staleness to the user and ask).
5. **Honour user edits** — if the user has hand-edited SIZING.md (e.g. overridden tier), downstream skills respect the edits.

---

## Pre-Write Announcement

The skill computing SIZING.md announces to the user before writing the
sizing artifact:

> "Inputs analysed:
>
> - **sFPC ≈ 27** (8 entities, 4 integrations, 9 mutating + 4 deriving + 2 retrieving operations)
> - **ASR count ≈ 17** (6 NFRs, 4 integration-as-ASR, 3 MUCs, 4 cross-cutting)
>
> **Tier: L** (sFPC borderline M/L; ASR clearly L).
>
> Context index coverage:
> - Form: fully covered by `architecture/ARCHITECTURE.md` and `architecture/DOMAIN_MODEL.md` → will reference
> - Armor: partially covered by `architecture/standards/AGENT_IMPLEMENTATION.md` → will fill gap
> - Proof: uncovered → full L-sized Proof section
>
> Target TDD: ~200-300 lines. Expected ADRs: 2-5 (only for genuinely new decisions).
>
> Proceed, adjust tier, or stop?"

The user can confirm, override tier ("treat as M — this work is smaller than
the inputs suggest"), or stop. Their choice is recorded in SIZING.md under
`Tier (confirmed by user)`.

---

## Sizing Self-Check

After the TDD is drafted but before it is written to disk, the agent
reviews the output against the SIZING.md target:

1. **TDD length > 1.5× tier target?** → write a "Why is this big?" paragraph
   appended to the TDD, OR refactor to bring it back in range. Restating
   covered ground is **not** a valid reason — refactor instead.
2. **ADR count > tier maximum?** → write an "ADR rationale" paragraph
   listing each ADR and why it crossed the non-trivial threshold.
3. **Any section restates content from an authoritative source?** → refactor
   the section to a reference. Note the correction in SIZING.md's `Notes`.
4. **Section marked "Reference (Don't Restate)" but actually contains content?**
   → refactor to reference-only.

The self-check is mandatory. The output is the SIZING.md `Notes` section
plus any "Why is this big?" / "ADR rationale" paragraphs appended to the
TDD itself.

---

## Circuit Breakers

When SEA's output exceeds tier expectations, the agent must justify in
writing:

1. **TDD line count > 1.5× tier target** → "Why is this big?" paragraph.
2. **ADR count > tier maximum** → "ADR rationale" paragraph.
3. **Section restates content from an authoritative source** → stop, refactor, log in SIZING.md `Notes`.

These are not soft suggestions. If the agent ships a TDD with a circuit-breaker
violation and no justification, the verify skill will flag it.

---

## Manual Tier Override

The user can override the computed tier at the pre-write announcement.

**Reasons to up-tier:**

- Project is greenfield but expected to grow rapidly — invest in fuller coverage now.
- Team is junior; TDD doubles as onboarding material.
- Regulatory environment requires more documentation than inputs suggest.

**Reasons to down-tier:**

- Project is throwaway (spike, proof-of-concept).
- TDD is internal-team-only with strong pair-programming culture.
- Existing operational knowledge (runbooks, tribal knowledge) carries weight the documentation doesn't need to.

**Down-tiering does not mean skipping pillars.** It means each pillar is
covered more tersely. Form/Armor/Proof are not optional regardless of tier.

The override is recorded in SIZING.md under `Tier (confirmed by user)`.

---

## How Other Skills Use This Standard

**`/sulis:draft-architecture`** — computes SIZING.md on first run; adapts TDD shape per
the tables above; appends a Sizing Report to TDD.md cross-referencing
SIZING.md.

**`/sulis:codebase-audit`** — computes SIZING.md from codebase scan when no
SRD exists; adapts audit-report depth.

**`/sulis:harden-codebase`** — reads SIZING.md; tier informs delta batch size.

**`/sulis:plan-work`** — reads SIZING.md; tier informs WP granularity.

**`/sulis:verify-architecture`** — reads SIZING.md; tier informs perspective sweep depth.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.5.0 | 2026-05-14 | Initial standard. Two-axis sizing: Axis 1 = sFPC (simplified Function Point Count, informed by IFPUG FPA) + ASR count (informed by Bass/Clements/Kazman); Axis 2 = addressable scope per-pillar from context index. File count dropped as a tier driver; retained only as brownfield sanity check. SIZING.md introduced as the persistent sizing artifact. Provenance section cites FPA, ASR, C4, DDD bounded contexts, COCOMO II. |
