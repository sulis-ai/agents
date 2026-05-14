# Work Package Template

The required structure for `.architecture/{project}/work-packages/WP-NNN-{slug}.md`.
Every WP SEA produces uses this exact shape. Sections may grow; they may
not be omitted.

---

```markdown
---
id: WP-NNN
title: {Imperative, < 70 chars — e.g. "Implement Postgres OrderRepository adapter"}
status: pending                          # pending | in_progress | done | blocked
sequence_id: WP-NNN
dependsOn: [WP-XXX, WP-YYY]              # WPs that must merge before this one
blocks: [WP-ZZZ]                          # WPs unlocked by this one
estimated_token_cost:
  input: Nk                              # rough — includes this WP + dependency WPs + relevant TDD section
  output: Nk                             # rough — implementation + tests
tdd_section: "3.4 (Adapters)"            # the TDD section this WP implements
adrs: [ADR-NNN]                          # ADRs whose decision this WP encodes
pillar: form | armor | proof             # primary pillar this WP advances

# Change primitive — required (see references/change-primitives.md)
primitive: create                        # one of the 22
group: expand                            # expand | reorganise | substitute | contract | reinforce
composite_of: []                         # optional — list of primitives if this WP is a composite

# Required for SUBSTITUTE-Wrap:
# subject_ownership: external | transitional
# justification: "Wrap is permitted only when subject is external OR transitional within Strangle."
# removal_plan: null  # null only when subject_ownership: external

# Required for SUBSTITUTE-Strangle:
# removal_plan: "Legacy OrderService deleted by 2026-09-30 (after 100% traffic migrated)."

# Required for REORGANISE primitives (Move, Refactor, Inline, Merge, Decompose, Abstract):
# characterisation_test: "tests/legacy/characterisation/OrderService.test.ts"
---

## Context

One paragraph. Which part of the architecture this WP touches. Which
PRIMITIVE_TREE nodes it advances. Why this WP exists.

Link to the TDD section: `[TDD §3.4](../TDD.md#34-adapters)`.

## Contract

The exact interfaces, types, and ports this WP introduces or modifies.
Code-level signatures only — not implementation. The Contract is what an
execution agent reads to know what to build.

Use code blocks with realistic types:

\`\`\`typescript
// domain/order/OrderRepository.ts (exists)
export interface OrderRepository {
  save(order: Order, idempotencyKey: IdempotencyKey): Promise<void>;
  findById(id: OrderId): Promise<Order | null>;
}

// infrastructure/persistence/PostgresOrderRepository.ts (this WP creates)
export class PostgresOrderRepository implements OrderRepository { ... }
\`\`\`

State invariants the contract preserves:

- Idempotency: `save()` with same `(id, idempotencyKey)` returns success without re-applying.
- Timeouts: transaction timeout 5s (NFR-04).
- Error mapping: provider errors translate to domain errors (`DuplicateOrderError`, `OrderNotFoundError`).

## Definition of Done

### Red — Failing tests written first

List every failing test by file path and test name. The execution agent
writes these tests before any implementation code.

- [ ] `tests/contracts/OrderRepositoryContract.ts::saves_and_retrieves_order`
- [ ] `tests/contracts/OrderRepositoryContract.ts::idempotent_save_returns_existing`
- [ ] `tests/contracts/OrderRepositoryContract.ts::findById_returns_null_for_missing`
- [ ] `tests/infrastructure/.../postgres-order-repository.test.ts::respects_5s_transaction_timeout` — chaos test, toxiproxy 6s latency
- [ ] `tests/infrastructure/.../postgres-order-repository.test.ts::emits_otel_span_with_table_attribute`
- [ ] `tests/infrastructure/.../postgres-order-repository.test.ts::redacts_pii_in_error_messages`

Include functional, edge-case, AND hardening assertions. Per `references/red-green-blue.md`
RGB-01, the hardening tests live in Red.

### Green — Implementation passes the tests

- [ ] All Red tests pass against ephemeral Postgres (testcontainers).
- [ ] Existing in-memory adapter still passes the shared contract test (no regression).
- [ ] Implementation follows `references/boring-code.md`:
  - Explicit types on public surface
  - No module-level state
  - No metaprogramming / reflection
- [ ] Coverage on new files ≥ 90%.

### Blue — Refactor within scope

- [ ] Duplication removed within file scope (e.g. save/update paths share an internal helper).
- [ ] Shared primitives extracted where ≥2 instances exist in this WP's diff.
- [ ] All tests still green.
- [ ] No new behaviour introduced.

## Sequence

- **dependsOn:** WP-XXX (reason), WP-YYY (reason)
- **blocks:** WP-ZZZ (reason)
- **Parallelisable with:** WP-AAA, WP-BBB (no overlapping file scope)

## Out of Scope

What this WP does NOT do. Helps the execution agent resist scope creep.

- Does NOT implement read-side projections (separate WP).
- Does NOT add the second adapter (separate WP).
- Does NOT change the domain entity (changes there require a new WP).

## Notes for the Executing Agent

Anything else the executor should know. Library choices already made,
gotchas in the existing code, links to relevant ADRs.

- Use `pg` driver (already in package.json).
- The migration for the `orders` table lives in `migrations/001_init.sql`
  from WP-002; no schema changes in this WP.
- See ADR-001 for the persistence trade-off rationale.

## Acceptance Evidence (filled at done)

Filled in by the executing agent at PR merge:

- Commit SHAs: {sha-red}, {sha-green}, {sha-blue}
- PR: {url}
- CI run: {url}
- Coverage delta: {before → after}
```

---

## Why each field exists

| Field | Why |
|---|---|
| `id` + `sequence_id` | Stable reference across the project and in dependency graphs |
| `dependsOn` / `blocks` | Prevents merge conflicts; drives parallelism analysis |
| `estimated_token_cost` | Lets an orchestrator route to the right model tier |
| `tdd_section` / `adrs` | Traceability — what design decision does this WP encode |
| `pillar` | Drives audit and verification — which MECE-3 pillar this WP advances |
| `primitive` | The change primitive (one of 22 in `references/change-primitives.md`); determines WP shape, testing strategy, and risk profile |
| `group` | The Minto-pyramid group (expand / reorganise / substitute / contract / reinforce) — derived from primitive but recorded for clarity |
| `composite_of` | When the WP is a composite (Migrate, Encapsulate, Branch-by-Abstraction etc.), records the recipe |
| `subject_ownership` / `removal_plan` (Wrap WPs) | Enforces "No Band-Aid Wrappers" — Wrap is conditional on external subject or transitional within Strangle |
| `removal_plan` (Strangle WPs) | Prevents stuck Strangles becoming permanent wrapper rot |
| `characterisation_test` (REORGANISE WPs) | Enforces "Characterisation Tests Before Refactor" — no behaviour-preserving change without a test proving behaviour is preserved |
| Context | One-paragraph orientation for the agent picking up the WP |
| Contract | The unambiguous deliverable shape |
| Red checklist | Names the failing tests up front (RGB discipline) |
| Green checklist | Defines "boring code" as the implementation standard |
| Blue checklist | Forces the refactor step that EP-02 makes non-negotiable |
| Out of Scope | Prevents the executing agent expanding scope |
| Acceptance Evidence | Closes the loop — done means measurable |
