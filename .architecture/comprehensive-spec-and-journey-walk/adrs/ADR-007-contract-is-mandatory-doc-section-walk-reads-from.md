---
title: The interface contract is a mandatory doc section the tool-walk reads operations from
status: accepted
kind: adr
---

# ADR-007 — The interface contract is a mandatory doc section the tool-walk reads operations from

## Context

FR-18 requires the comprehensive document to carry an interface-contract
section (the ServiceSpec / schema layer) as a MANDATORY part of Solution Design
(§7.x) for any change that introduces or modifies a tool surface, carrying per
operation the schema layer (operations/types/three-category errors per CF-03)
AND the four CF-10 founder-reviewable dimensions (auth/permissions; audience;
plain-language user guide; error fixes). FR-19 requires, for cross-kind
producer/consumer seams, that the contract is specified FIRST (CF-01/CF-05) and
that the tool-surface walk (FR-08/FR-09) treats the contract as the **source of
the operations it walks** — every walked operation names a contract operation,
and the binding cited for EXISTS (FR-09) is the wiring of a contract operation.
MUC-07 is the bypass this closes: contract-as-afterthought, or a schema-only
contract integratable-but-not-reviewable. NFR-D03 requires the contract
persisted and the walk operations ⊆ contract operations.

`draft-architecture/SKILL.md` already emits a ServiceSpec manifest (step 10)
and references CF-10; the platform's `architecture/SERVICE_SPECIFICATION.md` is
the reference shape (where present, the ServiceSpec IS the contract).

## Decision

Make the interface contract a **mandatory §7.x section** of the comprehensive
document for any tool-surface change, carrying the schema layer + all four
CF-10 dimensions per operation. The tool-surface walk (ADR-003) **reads its
operations from this section** (FR-19) — it does not invent operations. A walked
operation absent from the contract is a contract gap that must be added to the
contract first (UC-04 2a). Enforce the relationship with a
`_assert_walk_subset_of_contract.py` check: every tool-walk operation appears in
the contract (walk ⊆ contract, NFR-D03). A tool-surface change with no contract
section, or a contract missing any CF-10 dimension, does not complete the
design stage (structure check / P-VER blocks it, NR-07/NR-08). A change with no
tool surface carries an explicit `n/a — <justification>`, never a bare omission.

## Options Considered

- **Mandatory §7.x section + walk-reads-from-it + subset assertion (CHOSEN).**
  Closes MUC-07 at the structure level; ties the walk to the contract so the
  two can't diverge; reuses the existing ServiceSpec shape (CF-10).
- **Contract discovered at integration time (status quo)** — rejected: this IS
  MUC-07, the CF-01 anti-pattern (build the backend, design the consumer
  against what it returned).
- **Schema-only contract (no CF-10 dimensions)** — rejected: integratable but
  not founder-reviewable (the hollow-contract pre-mortem 4); violates FR-18 and
  the CF-10 MUST-for-founder-reviewed-surfaces bar.

## Consequences

- **Positive:** the founder can review the seam before anything is built; the
  walk and contract are kept in lockstep (subset assertion); contract-first
  (CF-01/CF-05) is enforced for cross-kind seams.
- **Negative:** the contract section + the subset assertion are net-new (Phase
  3); the CF-10 "Lovable Test" substance is hand-held until decompose-validation
  P7 mechanises it (pre-mortem 4 — a known, recorded limitation).
- **Neutral:** where a ServiceSpec already exists, it IS the contract (CF-10) —
  no second artifact; the section references it.
