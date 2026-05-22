---
name: decompose
description: >
  Use after /sea:blueprint has produced a TDD. Decomposes the TDD into atomic
  Work Packages (WP-NNN-*.md) that an execution agent (Claude Code, GSD,
  engineering team) can implement one at a time without merge conflicts.
  Each WP has Context, Contract, Definition of Done (Red-Green-Blue),
  Sequence ID with dependsOn graph, and Estimated Token Cost. Produces
  work-packages/INDEX.md showing the dependency graph and recommended order.
---

# Decompose — TDD to Atomic Work Packages

When invoked, read the project's `TDD.md` and `PRIMITIVE_TREE.jsonld` and
produce one Work Package per atomic, parallelisable unit of work.

If arguments are provided, treat them as the project name. If not, infer
from the most recently modified folder in `.architecture/`.

If no TDD exists, stop and tell the user to run `/sea:blueprint` first.

---

## What a Work Package Is

A Work Package (WP) is the **atomic unit of execution**. One execution agent
picks up one WP, implements it end-to-end, and merges. Other agents can be
working on parallel WPs simultaneously.

**Atomicity rules:**

1. A WP can be implemented without reading any other WP's content. The
   Context and Contract sections are sufficient.
2. A WP introduces exactly one logical capability or change. "Add the order
   creation port" is one WP. "Add the order creation port and the payment
   port" is two.
3. A WP's Definition of Done is verifiable in CI. There is a green/red signal.
4. A WP's changes do not collide with other WPs at the merge level — enforced
   by the Sequence ID `dependsOn` graph.

---

## What a Work Package Contains

```markdown
---
id: WP-007
title: Implement Postgres OrderRepository adapter
status: pending                  # pending | in_progress | done | blocked
sequence_id: WP-007
dependsOn: [WP-001, WP-003]      # the domain entity and the port must exist first
blocks: [WP-012]                 # the application service uses this adapter
estimated_token_cost:
  input: 8k                      # rough budget for the executing agent
  output: 3k
tdd_section: 3.4 (Adapters)
adrs: [ADR-001]
---

## Context

What part of the architecture this WP touches. One paragraph. Link to the
TDD section and any relevant ADRs. Name the components from the
PRIMITIVE_TREE this WP advances.

## Contract

The exact interfaces, types, and ports this WP introduces or modifies.
Code-level signatures (not implementation).

```typescript
// domain/order/OrderRepository.ts (already exists — this WP implements it)
export interface OrderRepository {
  save(order: Order, idempotencyKey: IdempotencyKey): Promise<void>;
  findById(id: OrderId): Promise<Order | null>;
}

// infrastructure/persistence/PostgresOrderRepository.ts (this WP creates)
export class PostgresOrderRepository implements OrderRepository { ... }
```

State invariants the contract must preserve:
- `save()` is idempotent on `(order.id, idempotencyKey)`.
- `findById()` never throws on not-found; returns `null`.
- `save()` honours the 5s transaction timeout from TDD section 4.1.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/contracts/OrderRepositoryContract.ts::saves_and_retrieves_order` — applies to this adapter
- [ ] `tests/contracts/OrderRepositoryContract.ts::idempotent_save_returns_existing_on_duplicate_key`
- [ ] `tests/contracts/OrderRepositoryContract.ts::findById_returns_null_for_missing_id`
- [ ] `tests/infrastructure/persistence/postgres-order-repository.test.ts::respects_5s_transaction_timeout` (chaos: toxiproxy 6s latency on postgres)
- [ ] `tests/infrastructure/persistence/postgres-order-repository.test.ts::emits_otel_span_with_table_name_attribute`

### Green — Implementation makes tests pass
- [ ] All Red tests pass against ephemeral Postgres (testcontainers).
- [ ] In-memory adapter still passes the shared contract test (regression safety).
- [ ] Implementation follows `references/boring-code.md` — explicit types, no module-level state, no metaprogramming.
- [ ] Coverage on `PostgresOrderRepository.ts` ≥ 90%.

### Blue — Refactor complete
- [ ] Duplication between save/update paths removed (single internal `upsert`).
- [ ] Shared connection-acquisition logic extracted if a second adapter (in a later WP) will reuse it.
- [ ] No new behaviour introduced in Blue.
- [ ] All tests still green after refactor.

## Sequence

- **dependsOn:** WP-001 (`Order` entity exists), WP-003 (`OrderRepository` port exists)
- **blocks:** WP-012 (`CreateOrder` application service depends on this adapter)
- **Parallelisable with:** WP-008 (Payment adapter — different file scope, different test scope)

## Estimated Token Cost

- **Input:** ~8k (this WP + the two dependency WP outputs + relevant TDD section)
- **Output:** ~3k (implementation file + adapter test file + contract test additions)
- **Total:** ~11k

## Notes

- Use `pg` driver (already in package.json from WP-001 setup).
- The 5s transaction timeout is non-negotiable per NFR-04.
```

---

## Workflow

1. **Read inputs** — `TDD.md`, `PRIMITIVE_TREE.jsonld`, `SIZING.md`,
   `.context/{project}/INDEX.md`, any existing `HANDOVER.md` from SRD, any
   prior WPs.
2. **Inventory** — list every component, port, adapter, and resilience
   primitive mentioned in the TDD. Each becomes a candidate WP.
3. **Assign primitive (MUST).** Per `references/change-primitives.md`,
   walk the cross-group decision priority for each candidate WP:
   ```
   1. Can I Reuse existing code?
   2. Can I Compose existing pieces?
   3. Can I Extend through an extension point?
   4. ✱ Before Wrap over internal: try Refactor/Move/Decompose instead
   5. Should I Replace rather than wrap?
   6. Do I need Strangle (gradual replace)?
   7. Wrap (only if subject is external or transitional in Strangle)
   8. Should I Contract (deprecate, then delete)?
   9. Must I Generate / Create net-new?
   REINFORCE runs orthogonally.
   ```
   
   **Ports & Adapters check (MUST).** Before assigning `wrap`, apply the
   discriminator question from `references/change-primitives.md`: *"Whose
   interface is the public face of this new code?"* If the WP creates a
   new module that implements a port defined inside the domain (e.g.
   `StripePaymentGateway implements PaymentGateway`), the primitive is
   **`create`** — you're writing an adapter, not wrapping. The Stripe SDK
   is called *by* the adapter; the adapter is not a wrapper at the
   architecture level. See "Ports & Adapters vs Wrappers" in the
   catalogue.
   
   Record the chosen primitive in WP frontmatter (`primitive:`, `group:`).
   For composites, record `composite_of:`. Apply mandatory fields per
   primitive:
   - **SUBSTITUTE-Wrap:** `subject_ownership` + `justification` + `removal_plan`
   - **SUBSTITUTE-Strangle:** `removal_plan` with target date
   - **REORGANISE-***: `characterisation_test` path
4. **Atomise** — for each candidate, ask: can this be implemented in one
   commit/PR by one agent? If no, split. Typical sizes:
   - One port definition + its contract test = 1 WP
   - One adapter implementing a port = 1 WP
   - One application service / use case = 1 WP
   - One observability primitive (e.g. "wire up OpenTelemetry") = 1 WP
   - One resilience policy (timeout + retry + CB for one dependency) = 1 WP
5. **Build the dependency graph** — for each WP, identify what must exist
   first (`dependsOn`) and what it unlocks (`blocks`). Note: REINFORCE-Test
   WPs are dependencies of any REORGANISE WPs that operate on the same
   subject (characterisation tests must exist first).
6. **Estimate token cost** — rough. Input ≈ WP itself + dependency WPs +
   relevant TDD section. Output ≈ implementation files + tests. Round to
   nearest 1k. This is for orchestrator routing, not billing.
7. **Wrap audit (MUST).** Scan the proposed WP set for SUBSTITUTE-Wrap
   primitives. For each:
   - Confirm `subject_ownership` is `external` OR `transitional`
   - For `transitional`, confirm there's a paired Strangle in the dep graph
     with a `removal_plan` date
   - For any Wrap on the same subject as an existing wrapper in the
     codebase (detected via `.context/{project}/INDEX.md` or
     `CODE_INTELLIGENCE.md` if present): **escalate to user before
     finalising**:

     > "Proposed WP-NNN would wrap `{subject}`. Existing wrappers detected:
     > `{path1}`, `{path2}`. Adding another defers the real fix.
     > Recommendation: Refactor `{subject}` directly (REORGANISE-Refactor),
     > or Replace with a new implementation and Delete existing wrappers.
     > Proceed with Wrap anyway? (Y/N)"
8. **Write WPs** — one file per WP, using the template above.
9. **Write `INDEX.md`** — list all WPs, their statuses, primitive
   distribution, the dependency graph (as a markdown table and a Mermaid
   `graph TD` diagram), the recommended implementation order (topological
   sort of the graph), and the wrap audit summary.
10. **Report** — total WP count, critical path length, parallelisation
    opportunity (how many WPs can be implemented simultaneously at peak),
    primitive distribution, wrap audit result.

11. **Validate** — apply the
    [Decompose Validation Rubric](../../references/decompose-validation-rubric.md)
    (v0.1.0+; SEA v0.19.0+) to the produced WP set. Write the
    validation report to
    `.architecture/{project}/work-packages/DECOMPOSE_VALIDATION.md`.

    The rubric runs six phases mechanically where possible:
    - **P1 Inventory completeness** — every WP has Context, Contract,
      DoD/RGB, Sequence, Token cost, Dependencies
    - **P2 Atomicity** — single responsibility per WP; touch surface
      ≤ 15 files (MUST), ≤ 8 (SHOULD); no "and" in titles or purpose
    - **P3 Module naming + clean code** — no jargon prefixes, no
      single-letter abbreviations, descriptive kebab-case slugs
    - **P4 Dependency graph correctness** — no cycles, all targets
      exist, transitive depth ≤ 8, valid topological order
    - **P5 Performance + non-functional reqs** — endpoint/handler WPs
      have a `## Performance` section with measurable bounds
    - **P6 Peer-collision risk** — no two WPs `Create` the same file
      (catches the `loader/__init__.py` collision class at breakdown
      time, before any executor dispatches)

    Verdict is computed deterministically:
    - **PASS** — every MUST passes; no SHOULD failures
    - **PASS-WITH-RATIONALE** — every MUST passes; SHOULD failures
      with documented rationale
    - **FAIL** — ≥1 MUST failure

    On `FAIL`: do NOT declare the decompose done. Surface the blocking
    gaps in plain English to the founder and return to the appropriate
    step (e.g., a peer-collision failure means re-running step 5
    "Detect overlaps + atomicity violations" with the rubric's
    findings in hand).

    On `PASS` / `PASS-WITH-RATIONALE`: report the validation outcome
    in the chat summary so the founder sees that the breakdown was
    formally validated, not just produced.

---

## INDEX.md Structure

```markdown
# Work Package Index — {Project}

> **TDD:** [TDD.md](../TDD.md)
> **SIZING:** [SIZING.md](../SIZING.md)
> **Total WPs:** N
> **Critical path:** WP-001 → WP-003 → WP-007 → WP-012 → WP-015 (5 packages)
> **Peak parallelism:** 6 (after WP-003 completes, WP-004 through WP-009 are unblocked)

## Status Summary

| Status | Count |
|---|---|
| pending | N |
| in_progress | 0 |
| done | 0 |
| blocked | 0 |

## Primitive Distribution

| Group | Primitive | Count | WPs |
|---|---|---|---|
| EXPAND | Reuse | 2 | WP-005, WP-009 |
| EXPAND | Compose | 1 | WP-012 |
| EXPAND | Extend | 3 | WP-002, WP-006, WP-011 |
| EXPAND | Create (incl. adapters) | 5 | WP-001, WP-003, WP-004, WP-007, WP-008 |
| REORGANISE | Refactor | 2 | WP-013, WP-014 |
| REORGANISE | Decompose | 1 | WP-015 |
| SUBSTITUTE | Wrap | 0 | — |
| REINFORCE | Test | 2 | WP-016, WP-017 |
| REINFORCE | Instrument | 1 | WP-018 |
| REINFORCE | Harden | 1 | WP-019 |

> Adapters for ports are counted as Create. WP-004 (Stripe adapter for the
> `PaymentGateway` port) is Create, not Wrap — see "Ports & Adapters vs
> Wrappers" in `references/change-primitives.md`.

## Wrap Audit

> All Wrap WPs reviewed for No-Band-Aid-Wrappers compliance.

| WP | Subject | Ownership | Removal Plan | Status |
|---|---|---|---|---|
| (none) | — | — | — | — |

No Wraps proposed. No wrapper rot detected on existing modules.

(If Wraps appear, they would be listed here with `subject_ownership` and
`removal_plan` validated against the No-Band-Aid-Wrappers rule.)

## Dependency Graph

\`\`\`mermaid
graph TD
  WP001[WP-001 Order entity] --> WP003[WP-003 OrderRepository port]
  WP001 --> WP008[WP-008 PaymentGateway port]
  WP003 --> WP007[WP-007 Postgres adapter]
  WP003 --> WP004[WP-004 InMemory adapter]
  WP007 --> WP012[WP-012 CreateOrder service]
  WP004 --> WP012
  WP008 --> WP012
\`\`\`

## WP Table

| ID | Title | Primitive | Status | Depends On | Blocks | Token (in/out) | TDD § |
|---|---|---|---|---|---|---|---|
| WP-001 | Order entity | create | pending | — | WP-003, WP-008 | 4k / 2k | 3.1 |
| WP-003 | OrderRepository port | create | pending | WP-001 | WP-004, WP-007 | 3k / 1k | 3.3 |
| WP-004 | Stripe adapter for PaymentGateway port | create (adapter) | pending | WP-003 | WP-012 | 2k / 2k | 3.4 |
| WP-013 | Refactor OrderService | refactor | pending | WP-016 | WP-015 | 3k / 2k | 3.6 |
| WP-016 | Characterise OrderService | test | pending | — | WP-013 | 2k / 2k | — |
| ... |

## Recommended Implementation Order

1. WP-001 (no deps)
2. WP-002, WP-003 (parallel, both depend only on WP-001)
3. WP-004, WP-007, WP-008 (parallel, depend on WP-003)
4. ...
```

---

## Adapting Depth

- **Quick** ("just give me a WP list") — atomise and write WPs with skeletons; full Red-Green-Blue checklists deferred until the WP is picked up. Useful for sprint planning.
- **Full** (default) — fully populated WPs with named Red tests, ready for an execution agent to pick up.
- **Single** (`/sea:decompose WP-012`) — decompose only one TDD section into WPs. Useful when a TDD section was added/changed mid-project.

**Tier-aware granularity.** Read tier from `.architecture/{project}/SIZING.md`
if present, falling back to `TDD.md`'s Sizing Report appendix. Per
`references/right-sizing.md`:

- Tier S: 3-8 WPs covering the whole TDD.
- Tier M: 8-20 WPs; one WP per significant component or contract.
- Tier L: 20-60 WPs; one WP per port + per adapter + per resilience primitive.
- Tier XL: 60+ WPs organised by bounded context; per-context INDEX.md.

Resist over-decomposition. If a "WP" would have a single line of work in
its DoD, it should be merged into a sibling WP. The dependsOn graph
captures ordering — multiple WPs for one component should be the
exception, not the rule.

---

## Gotchas

- **Atomicity is not negotiable.** If you find yourself writing "WP-007 also needs to update X in WP-008", you have not atomised. Split.
- **Sequence IDs prevent merge conflicts.** A WP's `dependsOn` predecessors must merge first. The `INDEX.md` order is the merge order.
- **Don't decompose by file.** Decompose by capability. One capability may touch several files; one file may be touched by several WPs (sequenced via `dependsOn`).
- **Token cost is rough.** It's a routing signal, not a contract. Round to 1k; do not optimise.
- **Mermaid renders in GitHub.** Use it for the dependency graph — readers will see the visual.
- **Cross-reference ADRs.** If a WP implements a decision made in an ADR, name the ADR in frontmatter. Drift between WPs and ADRs is a maintenance trap.

---

## See Also

- `references/work-package-template.md` — the full WP template
- `references/red-green-blue.md` — the cycle the DoD enforces (plugin root)
