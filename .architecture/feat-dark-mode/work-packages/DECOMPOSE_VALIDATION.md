# Decompose Validation — feat-dark-mode (CH-01KTHP)

## At a glance

The dark-mode work breaks into 8 independent pieces — the already-signed-off
look-and-feel sign-off, plus 7 build pieces. The breakdown is sound: nothing
depends on something that doesn't exist, two pieces can start straight away,
and no two pieces fight over the same file. **Ready to build.**

> **Verdict: PASS** — every MUST passes; no SHOULD failures.

---

## Technical detail

> Rubric: `decompose-validation-rubric.md` v0.4.0. Validated against the 8 WP
> files + INDEX.md + TDD.md in `.architecture/feat-dark-mode/`.

### Summary

| Metric | Count |
|---|---|
| WPs validated | 8 (WP-001 sign-off gate + WP-002..008 implementation) |
| Total checks run | 10 phases |
| MUST failures | 0 |
| SHOULD failures | 0 |
| Verdict | **PASS** |

### Phase-by-phase results

| Phase | Result | Notes |
|---|---|---|
| 1 Inventory completeness | PASS | WP-002..008 carry all required sections (Context, Contract, DoD+RGB, Sequence, Token Cost, dependsOn, primitive). WP-001 is a sign-off-gate WP (`verification: na`) — documented exception below. |
| 2 Atomicity | PASS | No " and " in any title (2.06). No conjunction in any purpose (2.01). Touch surface ≤ 8 files each (2.02/2.03). One primitive per WP (2.05). |
| 3 Module naming + clean code | PASS | All filenames match `WP-NNN-{slug}.md`. No abbreviation jargon (`mgr`/`svc`/`_v2`) in Contracts (3.04). Slugs are kebab-case outcome phrases (3.03). |
| 4 Dependency graph correctness | PASS | Acyclic (4.01). All dependsOn targets resolve (4.02). Max depth 2 (4.04). 3 parallel batches exist (4.06). INDEX order is a valid topo sort (4.07). |
| 5 Performance + non-functional | N/A — PASS | No request-handler primitives (add-endpoint/handler/service/route). Client-only presentation change; no SLA-bearing WP. TDD §4 records why Armor is not applicable. |
| 6 Peer-collision risk | PASS | No two WPs create the same file (6.01). Only WP-002 + WP-006 modify `tokens.css`, and they are sequenced (WP-006 dependsOn WP-002), so the same-level-parallel-modify check (6.02) does not fire. |
| 7 ServiceSpec compliance | N/A — PASS | No services introduced (client-only); no `service-specs/` required. |
| 8 Cross-WP identifier canonicalisation | PASS | The one cross-WP shared identifier — the `localStorage` key `cockpit.theme` — is canonicalised in ADR-001 and exported from WP-003's module (WP-004/WP-005 import it, not re-declare). The dark token values are canonical in the signed-off mockup (TDD §6). No ULID/`dna:`/`urn:` literals. |
| 9 P-VER (Verification Plan) | PASS | See P-VER detail below. |
| 10 P-PLAT (Platform Contract) | N/A — PASS | No `touch-class: write\|deploy` WP; no third-party platform touch. Client-only. |

### P-VER detail (Phase 9)

Grandfather sub-phase: `verification_required_from` is empty (pre-merge
dogfood state) → P-VER applies in full; no grandfather skip. Change
`started_at` 2026-06-07T18:39:56Z.

| Check | Result | Evidence |
|---|---|---|
| 9.01 `## Verification Plan` present in TDD | PASS | TDD.md line 190 (heading normalised from `## 7. Verification Plan` to the rubric-literal `## Verification Plan`). No SRD exists (spec-driven change) — the SRD half of 9.01 is N/A by construction; the TDD half passes. |
| 9.02 No placeholder content | PASS | Six subsections, each substantive (no TBD/todo/blank). |
| 9.03 `n/a` subsections justified | PASS | "Infrastructure deferred: none" is justified inline; no bare n/a. |
| 9.04 Named `existing` infra paths resolve | PASS | Cited test paths (`tests/MonacoFile.test.tsx`, `tests/MonacoDiff.test.tsx`) exist; `localStorage`/`matchMedia` are in-jsdom, no external adapter. |
| 9.05 `kind:` has adapter row | PASS | `kind: frontend` → Vitest + RTL adapter. |
| 9.06 Citation to VERIFICATION_QUESTIONS.md present | PASS | TDD.md line 188, immediately before the section. |
| 9.07 Citation version within currency | PASS | Cites v1.0.0; canonical v1.0.0. |
| 9.08 Per-WP `verification:` adapter matches kind | PASS | All 7 implementation WPs declare `verification.adapter: frontend` = change kind. WP-001 carries `na: true` + ≥30-char justification (shape 3, trivial/design-time carveout). |

All WP verification shapes are **concrete** (ADR-003 shape 1) — every WP ships
its own Vitest spec the moment it lands. None deferred, none trivial (except
WP-001's design-time `na`).

### Documented exceptions

- **WP-001 inventory shape (Phase 1).** WP-001 is the visual-contract
  sign-off gate (`kind: frontend`, `primitive: REINFORCE-Document`,
  `verification: na`). Per WP_FRONTEND_STANDARD WP-08.5, a visual contract is
  a design-time artifact whose "test" is founder sign-off, not RGB code. It
  legitimately lacks the Contract/Red-Green-Blue/Sequence sections that
  Phase 1 requires of *executable* WPs. It is already `done`
  (`signed_off_at` + `provenance: production-approved`). Not a defect; the
  Phase 1 MUST checks apply to the 7 executable WPs, all of which pass.

### Methodology

- [✓] **P1 Inventory completeness.** 8 WPs read end-to-end. WP-002..008 carry all required sections. WP-001 exception documented above.
- [✓] **P2 Atomicity.** Titles + purposes parsed; no conjunctions. Touch surface ≤ 8 files/WP. One primitive each.
- [✓] **P3 Module naming.** Filenames + Contract module names scanned; no jargon; outcome-shaped kebab-case slugs.
- [✓] **P4 Dependency graph.** DAG built from dependsOn. Cycles: 0. Orphans: 0 (WP-001 is the foundation gate). Levels: {WP-001} / {WP-002, WP-003} / {WP-004, WP-005, WP-006, WP-007, WP-008}. INDEX order is a valid topo sort.
- [✓] **P5 Performance.** No request-handler-class WP; client-only. N/A.
- [✓] **P6 Peer-collision.** Create-path intersection empty. tokens.css modified only by WP-002 + WP-006, sequenced not parallel.
- [✓] **P7 ServiceSpec.** No services; N/A.
- [✓] **P8 Cross-WP identifiers.** `cockpit.theme` key canonical in ADR-001 + exported from WP-003; dark token values canonical in the signed-off mockup. No invented ULID/dna/urn literals.
- [✓] **P9 P-VER.** 8 checks pass (see detail). Grandfather: not grandfathered; full P-VER applied. SRD half of 9.01 N/A (spec-driven, no SRD).
- [✓] **P10 P-PLAT.** No gated platform touch; N/A.
