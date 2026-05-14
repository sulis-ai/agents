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

1. **Read inputs** — `TDD.md`, `PRIMITIVE_TREE.jsonld`, any existing
   `HANDOVER.md` from SRD, any prior WPs.
2. **Inventory** — list every component, port, adapter, and resilience
   primitive mentioned in the TDD. Each becomes a candidate WP.
3. **Atomise** — for each candidate, ask: can this be implemented in one
   commit/PR by one agent? If no, split. Typical sizes:
   - One port definition + its contract test = 1 WP
   - One adapter implementing a port = 1 WP
   - One application service / use case = 1 WP
   - One observability primitive (e.g. "wire up OpenTelemetry") = 1 WP
   - One resilience policy (timeout + retry + CB for one dependency) = 1 WP
4. **Build the dependency graph** — for each WP, identify what must exist
   first (`dependsOn`) and what it unlocks (`blocks`).
5. **Estimate token cost** — rough. Input ≈ WP itself + dependency WPs +
   relevant TDD section. Output ≈ implementation files + tests. Round to
   nearest 1k. This is for orchestrator routing, not billing.
6. **Write WPs** — one file per WP, using the template above.
7. **Write `INDEX.md`** — list all WPs, their statuses, the dependency
   graph (as a markdown table and a Mermaid `graph TD` diagram), and the
   recommended implementation order (topological sort of the graph).
8. **Report** — total WP count, critical path length, parallelisation
   opportunity (how many WPs can be implemented simultaneously at peak).

---

## INDEX.md Structure

```markdown
# Work Package Index — {Project}

> **TDD:** [TDD.md](../TDD.md)
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

| ID | Title | Status | Depends On | Blocks | Token (in/out) | TDD § |
|---|---|---|---|---|---|---|
| WP-001 | Order entity | pending | — | WP-003, WP-008 | 4k / 2k | 3.1 |
| WP-003 | OrderRepository port | pending | WP-001 | WP-004, WP-007 | 3k / 1k | 3.3 |
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
