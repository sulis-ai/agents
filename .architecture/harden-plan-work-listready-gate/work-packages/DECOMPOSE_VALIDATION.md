# Decompose Validation — harden-plan-work-listready-gate (CH-01KTMJ)

> **Rubric version:** 0.4.0 (Active — Calibration)
> **Validated:** 2026-06-08
> **WP set:** 1 WP (engineering-architect-light harden; SPEC.md + AUDIT.md as
> design input, no TDD by design).

## Verdict

**PASS-WITH-RATIONALE** — every MUST passes. One SHOULD-class item carries a
documented rationale (P9 TDD-absence; see below). No blocking gaps.

## Summary

| Metric | Count |
|---|---|
| WPs validated | 1 |
| Total checks applied | 10 phases |
| PASS | 9 phases |
| PASS-WITH-RATIONALE | 1 phase (P9) |
| FAIL (MUST) | 0 |

## Phase-by-phase results

| Phase | Verdict | Notes |
|---|---|---|
| 1 Inventory completeness | PASS | All required sections present in WP-001. |
| 2 Atomicity | PASS | One sentence, one primitive, ≤15 files. |
| 3 Module naming + clean code | PASS | Descriptive kebab-case slug; no jargon-invention. |
| 4 Dependency graph correctness | PASS | Single node, acyclic, valid topo order; single-kind so CF cross-kind checks N/A. |
| 5 Performance + non-functional | PASS | Not a handler/endpoint primitive; no SLA owed. |
| 6 Peer-collision risk | PASS | Single WP — no peers, no shared-artifact producers. |
| 7 ServiceSpec compliance | N/A | No services introduced (in-repo tooling harden). |
| 8 Cross-WP identifier canonicalisation | PASS | Single WP — no cross-WP shared identifiers. |
| 9 P-VER (Verification Plan) | PASS-WITH-RATIONALE | WP-level 9.08 passes; SRD/TDD checks scoped out (no TDD by design). |
| 10 P-PLAT (Platform Contract) | PASS | No gated third-party write/deploy touch; no `platform:`/`touch-class:`. |

## Detailed findings per check

### Phase 1 — Inventory completeness (PASS)

- **1.01–1.05** PASS — WP-001 has `## Context`, `## Contract`,
  `## Definition of Done` (Red/Green/Blue), `## Sequence` (Sequence ID),
  `## Estimated token cost` (numeric).
- **1.06** PASS — `dependsOn: []` declared in frontmatter.
- **1.07** PASS — INDEX.md lists WP-001; directory contains exactly
  `WP-001-listready-roundtrip-gate.md`. Set equality holds.
- **1.08** PASS — INDEX.md has a `## Dependency Graph` Mermaid section.
- **1.09** PASS — `primitive: harden` (REINFORCE group) from the catalogue.
- **1.10** PASS-by-substitution — no TDD exists (light change); the Context
  section maps to `.changes/…SPEC.md` and `.AUDIT.md` instead, and names the
  exact source functions/line anchors. The intent of 1.10 (the WP is traceable
  to its design source) is satisfied.

### Phase 2 — Atomicity (PASS)

- **2.01** PASS — purpose is one move: "fold a list-ready round-trip into
  `wpx-index lint`". The title's "so the decompose gate drives the real
  consumer" is a purpose clause, not a second deliverable.
- **2.02 / 2.03** PASS — touch surface: `wpx-index` (modify `cmd_lint`),
  one new test module, one SKILL.md prose note = 3 files (≤8, ≤15).
- **2.05** PASS — single primitive `harden`.
- **2.06** PASS — title contains no ` and `.
- **2.07** note — Red has 6 items (>5 MAY soft-ceiling). Rationale: the SPEC's
  acceptance is a fixed 4-variant matrix + a no-false-positive depchain case +
  a wiring assertion; each is a distinct, named pinning test. Collapsing them
  would weaken the test-first proof the change exists to deliver. MAY, not
  blocking.

### Phase 3 — Module naming (PASS)

- **3.01** PASS — `WP-001-listready-roundtrip-gate.md` matches the pattern.
- **3.02–3.05** PASS — slug is descriptive kebab-case; no invented
  abbreviations. The only prefixed names (`wpx-index`, `_wpxlib`, `cmd_lint`)
  are **existing** identifiers the WP consumes, not new jargon it mints —
  3.07's "unless the WP's purpose is to USE that prefix" exemption applies.

### Phase 4 — Dependency graph (PASS)

- **4.01** PASS — single node, no edges → acyclic.
- **4.02** PASS — `dependsOn: []`; nothing to resolve.
- **4.05** PASS — WP-001 is the foundation (and only) WP; isolated-node check
  N/A for a single-WP set.
- **4.07** PASS — Recommended Order `[WP-001]` is a valid topological sort.
- **4.08 / 4.09** N/A — single-kind (`backend`) set; no cross-kind seam, so no
  data-contract WP owed and no cross-kind edge possible.

### Phase 5 — Performance + non-functional (PASS)

- **5.01–5.06** N/A/PASS — `harden` is not an `add-endpoint`/`add-handler`/
  `add-service`/`add-route` primitive; no SLA section owed. No DB schema,
  no external-API consumption, no new tables. The change is a pure in-process
  parse round-trip over an already-read file.

### Phase 6 — Peer-collision risk (PASS)

- **6.01–6.06** PASS — one WP, no peers. No two WPs create the same file; no
  shared logical artifact with multiple producers (CF-11 N/A).

### Phase 7 — ServiceSpec compliance (N/A)

No services introduced or modified — this is in-repo build-tooling hardening.
No `service-specs/` directory owed (7.01 vacuously satisfied: the design
introduces zero services).

### Phase 8 — Cross-WP identifier canonicalisation (PASS)

- **8.01–8.06** PASS/N/A — single WP, so no identifier appears in ≥2 WP
  Contracts. No ULID-shape, `dna:*:*`, or `urn:*:*` literals invented inline.

### Phase 9 — P-VER (Verification Plan) (PASS-WITH-RATIONALE)

**Grandfather sub-phase.** `verification_required_from` is empty (pre-merge
dogfood state) → P-VER applies. `started_at: 2026-06-08T21:36:44Z` → not
grandfathered.

- **9.08** PASS (the directly-checkable WP-level gate) — WP-001's frontmatter
  carries `verification:` as a **Shape 1 (concrete)** field: `adapter: backend`
  + `artifact:` pinning the pytest nodeid
  `…/test_wpx_index_roundtrip.py::test_status_vocab_all_nonpending_fails_gate`.
  `verification.adapter` (`backend`) equals the change `kind:` (`backend`). ✓
- **9.01 / 9.06 / 9.07** scoped-out with rationale — these check `## Verification
  Plan` section presence + the canonical citation + version currency in the
  **SRD and TDD**. This change is **engineering-architect-light by explicit
  brief**: no TDD is produced and no SRD exists; the design input is
  `.changes/…SPEC.md`, which **does** carry a `## Verification Plan` (the
  4-variant matrix, the wiring check, the observable outcome). The TDD-side
  P-VER section the rubric expects has no artifact to live in because the brief
  deliberately omits the TDD. The substantive intent of P-VER — *verification
  is designed up front, not bolted on* — is fully met: the SPEC's variant matrix
  IS the verification design, and the WP's Red step encodes it test-first with a
  concrete `verification:` artifact. **Rationale recorded; not a blocking gap
  for a light change.** Were this a full greenfield TDD flow, 9.01/9.06/9.07
  would be hard MUSTs against the TDD.
- **9.02–9.05** PASS/N/A against the SPEC's Verification Plan — no placeholder
  content (the matrix is concrete); no bare `n/a`; `existing` infrastructure
  paths cited (`_collect_status_across_tables`, `_resolve_deps`, `cmd_lint`,
  the three existing test modules) all resolve in-repo (verified during
  authoring); `kind: backend` has an adapter row in the canonical.

### Phase 10 — P-PLAT (Platform Contract) (PASS)

**Grandfather.** `platform_contract_required_from` empty → P-PLAT applies.
No gated third-party write/deploy touch — pure in-repo Python tooling. WP-001
carries no `platform:` / `touch-class:` (correct: nothing to declare).
Schema-invariant checks (10.03–10.06) N/A; no freshness claims.

## Methodology

- [✓] **P1 Inventory completeness.** 1 WP read end-to-end. Required sections found: Context, Contract, DoD (Red/Green/Blue), Sequence, Token cost, dependsOn. Gaps: none. 1.10 satisfied by SPEC/AUDIT source-mapping (no TDD by design).
- [✓] **P2 Atomicity.** Purpose = one move; one primitive; 3-file touch surface (≤8). 0 WPs exceed bounds. Title has no "and". 2.07 MAY soft-ceiling noted with rationale.
- [✓] **P3 Module naming.** Slug descriptive kebab-case; the only prefixed names are existing consumed identifiers (3.07 exemption). 0 findings.
- [✓] **P4 Dependency graph.** Single-node DAG. Cycles: 0. Orphans: 0 (foundation WP). Topo order valid. Cross-kind checks N/A (single-kind).
- [✓] **P5 Performance + non-functional.** Primitive `harden` is not a handler/endpoint class. 0 WPs owe an SLA.
- [✓] **P6 Peer-collision risk.** Single WP. 0 collision pairs; 0 multi-producer shared artifacts.
- [—] **P7 ServiceSpec compliance.** 0 manifests — no services introduced. 7.01 vacuously satisfied.
- [✓] **P8 Cross-WP identifier canonicalisation.** 0 cross-WP shared identifiers (single WP). 0 inline ULID/dna/urn literals.
- [✓] **P9 P-VER (Verification Plan).** Grandfather: applies (not grandfathered). Per-WP `verification:` field: 1 pass (9.08, Shape 1 concrete, adapter `backend` == kind). SRD/TDD section + citation + currency (9.01/9.06/9.07): scoped out with rationale — engineering-architect-light, no TDD by design; SPEC.md carries the Verification Plan. PASS-WITH-RATIONALE.
- [✓] **P10 P-PLAT (Platform Contract).** 1 WP scanned. Gated third-party touches: 0. `platform:`/`touch-class:` correctly absent. Schema-invariant + freshness: N/A. Grandfather: applies.
