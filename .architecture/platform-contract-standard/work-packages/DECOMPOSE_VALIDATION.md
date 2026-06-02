# Decompose Validation Report — platform-contract-standard

**Date:** 2026-06-02
**Rubric:** decompose-validation-rubric (live P1..P8; P-VER Phase 9 + P-PLAT Phase 10 not self-applicable — see note)
**WP set:** 8 WPs

## Verdict: **PASS**

All MUSTs pass. Two PASS-WITH-RATIONALE shapes (P2 file-count on WP-007; P3
title-clause on WP-003) are logged below, matching the established
verification-by-design anchor cases.

> **Self-application note (MUST read).** This change *creates* P-PLAT (Phase 10,
> WP-004) and consumes P-VER (Phase 9). **Neither can be applied to validate
> this WP set** — P-PLAT does not yet exist at decompose time, and a gate cannot
> grade the change that builds it. This set is validated against the live
> P1..P8 rubric. After merge, future gated-platform WP sets are validated
> against P-PLAT. The dogfood that *this* set's P-PLAT works is WP-007
> (`test_pplat_fails_no_contract`) + WP-008 — they assert P-PLAT against
> synthetic fixtures, not against this WP set.

---

## P1 — Inventory completeness (MUST)

Every WP has: Context, Contract, DoD (Red/Green/Blue), Sequence, Token cost,
Dependencies, ADRs, TDD section, the `verification:` frontmatter field, and (on
gated WPs) the `platform:` / `touch-class:` field.

| WP | Context | Contract | RGB DoD | Sequence | Token | Deps | ADRs | TDD § | `verification:` | `platform:`* |
|---|---|---|---|---|---|---|---|---|---|---|
| WP-001 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a |
| WP-002 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a |
| WP-003 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a |
| WP-004 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a |
| WP-005 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a |
| WP-006 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (github-actions / read-only) |
| WP-007 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a |
| WP-008 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a |

\* `platform:` is this change's own new field; only set where a WP touches a
third-party platform (WP-006 only). INDEX.md lists every WP file; Mermaid
dependency graph present.

**P1: PASS.**

---

## P2 — Atomicity (MUST)

Single responsibility per WP; touch surface ≤ 15 files (MUST), ≤ 8 (SHOULD);
no bundling "and".

| WP | Single responsibility | Files touched | Note |
|---|---|---|---|
| WP-001 | Author the standard | 1 | — |
| WP-002 | Create storage dir + INDEX | 2 (dir placeholder + INDEX) | — |
| WP-003 | Wire gate + harness glue into the two design skills | 2 | "+" enumerates two clauses of one cohesive change — see rationale |
| WP-004 | Append P-PLAT phase | 1 | — |
| WP-005 | Emit `platform:` / `touch-class:` from plan-work | 1 | — |
| WP-006 | Produce the GitHub Actions contract | 2 (contract + INDEX row) | — |
| WP-007 | Structural/conformance + harness tests | ~10 (test files + 3 fixtures) | PASS-WITH-RATIONALE — see below |
| WP-008 | n=1 dogfood acceptance | 1 | — |

**WP-003 two-clause rationale.** The title bundles "gate wiring + harness glue"
because both clauses edit the *same two files* (`specify/SKILL.md`,
`draft-architecture/SKILL.md`) along one axis: the design phase's handling of a
third-party touch. **Splitting would create the shared-file collision the
discover-project lesson warns against** — both the gate prose and the
harness-glue touch `draft-architecture/SKILL.md`. Bundling gives that file
exactly one owner. One engineer, one branch, one PR. **PASS-WITH-RATIONALE**
(logged in WP-003 §Notes).

**WP-007 file-count rationale.** WP-007 creates several test files + three
fixture artifacts (~10 files). Per the verification-by-design WP-007 anchor
case, fixture data counts toward touch surface, but the unit of work is "one
test suite + its fixtures" — splitting fragments the suite from the fixtures it
asserts against. **PASS-WITH-RATIONALE** matching the established anchor-case
pattern (logged in WP-007 §Notes).

**P2: PASS (two PASS-WITH-RATIONALE).**

---

## P3 — Dependency correctness (MUST)

DAG is acyclic; every `dependsOn` is justified; `blocks` is the inverse of
`dependsOn`; no WP depends on a WP that depends on it.

- WP-001 → {002, 003, 004, 007}: all conform to / enforce / test the schema. ✓
- WP-004 → 005: `plan-work` emits the field whose meaning P-PLAT owns. ✓
- {002, 003} → 006: the contract lands in the storage dir (002) and is produced
  by running the harness glue (003). ✓
- {001, 002, 004, 006} → 007: tests read the standard, storage, rubric, contract. ✓
- {006, 007} → 008: the dogfood asserts the contract (006) using the shared
  validator + fixtures (007). ✓

Graph verified acyclic (Mermaid in INDEX). No back-edges. `blocks`/`dependsOn`
are mutually consistent across all eight files.

**Shared-file collision check (the discover-project lesson):** every
shared/modified file has exactly one WP owner —
`draft-architecture/SKILL.md` + `specify/SKILL.md` → WP-003 only;
`decompose-validation-rubric.md` → WP-004 only; `plan-work/SKILL.md` → WP-005
only; `platform-contracts/INDEX.md` → created by WP-002, single row appended by
WP-006 (sequenced: WP-002 before WP-006, no concurrent write). No two WPs edit
the same file at the same depth.

**P3: PASS.**

---

## P4 — Contract clarity (MUST)

Each WP's Contract names the exact files created/modified, the artifact shape,
and (for methodology WPs) the prose sections. The claim-entry schema is defined
once (WP-001) and referenced by WP-002/006/007 — no schema duplication.
Test WPs (007, 008) name exact pytest nodeids.

**P4: PASS.**

---

## P5 — RGB discipline (MUST)

Every WP has Red (failing test first), Green (implementation), Blue
(refactor/polish). The methodology WPs' Red phases write structural-assertion
stubs that WP-007 then owns as full tests — the Red stub is the failing test;
WP-007 is its primary home. WP-007 Blue extracts the shared claim-entry
validator (EP-02 REFACTOR). No WP skips Blue.

**P5: PASS.**

---

## P6 — Token budget sanity (SHOULD)

Per-WP budgets sit in the 4k-11k total range; the largest (WP-001, WP-006) are
~11k — within single-context limits. Total ~70k across 8 WPs. No WP exceeds a
single execution context. Matches the dispatch budget (~20k in / ~14k out for
the *decomposition*; the *implementation* totals ~70k as expected for tier L).

**P6: PASS.**

---

## P7 — Design-contract coverage (MUST)

> P7 checks the four design-stage contracts (Data / Visual / ServiceSpec /
> Platform) are addressed where applicable.

- **Data contract:** n/a — no backend↔frontend data seam introduced.
- **Visual contract:** n/a — `founder_facing: false`; ships methodology, no UI.
- **ServiceSpec:** n/a — no new service.
- **Platform contract:** **this change IS the Platform Contract standard.** Its
  own first instance (`github-actions.md`, WP-006) is the design-stage Platform
  Contract for the one platform this change touches. Covered.

**P7: PASS.**

---

## P8 — Canonical identifier discipline (MUST)

> No inline minting; cite the TDD's Canonical Identifiers by anchor.

All identifiers used in the WP set trace to **TDD §Canonical Identifiers**
(lines 19-63), cited by name — none minted inline:

| Identifier | Source anchor | Used in |
|---|---|---|
| Claim-entry schema (`inferred`, `load_bearing`, `probe-result`, …) | TDD lines 24-44 | WP-001 (defines), WP-002/006/007 (reference) |
| Storage path `platform-contracts/<platform>.md` + `INDEX.md` | TDD lines 46-50 | WP-002, WP-006 |
| Standard path `standards/PLATFORM_CONTRACT_STANDARD.md` | TDD line 48 | WP-001 |
| Rubric phase id `P-PLAT` (cited by name, not position) | TDD lines 52-55 | WP-004, WP-005, WP-007 |
| `scratch-github-actions-probe-repo` | TDD line 62 | WP-006, WP-008 |
| `paid-private-repo-for-branch-protection-probe` | TDD line 62 | WP-006 |
| `platform-contract-staleness-reprobe` | TDD line 63 | (named deferred; ADR-003) |
| `platform:` / `touch-class:` WP frontmatter field | TDD OAQ-4 (line 206) | WP-004 (meaning), WP-005 (emit), WP-006 (dogfood) |

No identifier was invented during decomposition. The `PC-NN` requirement IDs
(WP-001) and the `P-PLAT.NN` / `10.NN` check IDs (WP-004) are *new* sequences
introduced by the artifacts those WPs author — they are not cross-WP canonical
identifiers and are minted within their owning artifact per the standard /
rubric numbering conventions (analogous to P-VER's `9.NN`).

**P8: PASS.**

---

## Summary

| Phase | Verdict |
|---|---|
| P1 Inventory completeness | PASS |
| P2 Atomicity | PASS (2 PASS-WITH-RATIONALE: WP-003 clause, WP-007 fixtures) |
| P3 Dependency correctness | PASS (shared-file collision avoided) |
| P4 Contract clarity | PASS |
| P5 RGB discipline | PASS |
| P6 Token budget | PASS |
| P7 Design-contract coverage | PASS |
| P8 Canonical identifiers | PASS |
| P-VER (Phase 9) | **not self-applicable** — consumed, dogfooded by `verification:` field on all 8 WPs |
| P-PLAT (Phase 10) | **not self-applicable** — created by this change (WP-004); cannot grade the change that builds it. Dogfooded via WP-007/008 fixtures + WP-006's `platform:` field. |

**Overall: PASS.** Ready for `/sulis:run-all` (or `/sulis:run-wp` per WP).
