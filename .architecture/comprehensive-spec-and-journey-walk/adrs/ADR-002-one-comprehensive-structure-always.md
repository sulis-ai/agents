---
title: One comprehensive-document structure, emitted always, modelled on the canonical
status: accepted
kind: adr
---

# ADR-002 — One comprehensive-document structure, emitted always, modelled on the canonical

## Context

FR-05/FR-11 require the design artifact to be restructured from the legacy
seven-part TDD shape (Overview/Form/Armor/Proof/Trade-offs/Open-questions/
Verification-Plan) toward the comprehensive `DESIGN.md` shape, matching the
canonical `features/entity-crud/DESIGN.md` (C-01). Today
`requirements-templates/SKILL.md` has SRD / UC / NFR / Verification-Plan
templates but **no comprehensive DESIGN.md template** — there is nothing to
emit the Target Structure from. The `## Verification Plan` heading is fixed
verbatim by ADR-001 of the verification-by-design change (C-02).

## Decision

Add a single comprehensive **DESIGN.md Target-Structure template** to
`requirements-templates/SKILL.md` carrying §1 Executive Summary, §2 Problem
Discovery, §3 Stakeholders/Personas, §4 Requirements (incl. §4.2 measurable
NFR and §4.6 STRIDE), §5 Scope, §6 Use Cases (main/alternate/exception),
§7 Solution Design (incl. architecture-at-levels and the §7.x interface
contract), §8 ADRs+BDRs, §9 Migration/Rollback/Security/Performance, and the
verbatim §10 `## Verification Plan`. Section names and ordering follow the
canonical (C-01), not invented. Inapplicable sections carry `n/a —
<justification>`, never a bare omission. Detail is depth-sized (ADR-001); the
structure is invariant.

## Options Considered

- **One canonical-matching template, always emitted (CHOSEN).** Single source
  of structure truth; matches the agreed target (A-01); the dogfood proof is
  that this very design follows it.
- **Keep the legacy TDD shape, bolt STRIDE/C4/BDR on** — rejected: the
  Form/Armor/Proof shape doesn't map cleanly to the canonical's problem-
  discovery / use-case / solution-design spine; bolting on produces a hybrid
  that matches neither (C-01 violated).
- **Per-depth templates** — rejected: reintroduces the doc-shape-on-depth
  coupling ADR-001 removes.

## Consequences

- **Positive:** one structure to maintain, matching the canonical; downstream
  SEA always receives use cases + NFR + contract + threat model. The structure
  is the same one P-VER's `## Verification Plan` check already anchors on (C-02).
- **Negative:** the legacy TDD shape is retired for new changes; the template
  is sizeable net-new authoring (Phase 1 + Phase 3 sub-templates for
  STRIDE/C4/BDR/contract).
- **Neutral:** existing `TDD.md` artifacts are not rewritten — the new
  structure applies to changes specified after this ships (§9.1 migration).
