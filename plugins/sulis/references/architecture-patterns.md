# Architecture Patterns Catalogue

<!-- summary -->
The pattern catalogue SEA draws from when generating TDDs and selecting
implementation approaches. Each pattern has a triggering condition (when to
use), a contract (the shape it imposes), an anti-pattern (the failure mode
it prevents), and a verification signature (the test that confirms it).
SEA selects patterns from this catalogue based on the NFRs and PRIMITIVE_TREE
produced by SRD, not based on familiarity or fashion. A pattern that is not
in this catalogue may still be used — but its TDD section must document why.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period

---

## Provenance

Synthesised from:
- Patterns of Enterprise Application Architecture (Fowler, 2002)
- Domain-Driven Design (Evans, 2003)
- Hexagonal Architecture (Cockburn, 2005)
- Release It! (Nygard, 2018) — for resiliency patterns
- Building Microservices (Newman, 2021) — for distributed patterns

This is practitioner knowledge, not peer-reviewed research.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Pattern is required when its triggering condition holds. |
| **SHOULD** | Default when the triggering condition holds; deviation needs justification. |
| **MAY** | Permitted when the triggering condition holds; alternatives also acceptable. |

---

## Form Patterns (Structural Integrity)

### AP-01: Hexagonal Architecture (Ports & Adapters)

**Severity:** MUST (when system has any external I/O)

**When:** The system has any persistent storage, network call, message broker,
or external API.

**Contract:**
- Domain layer defines **ports** (interfaces for what it needs).
- Infrastructure layer provides **adapters** (implementations).
- The composition root wires them together.
- Domain never imports infrastructure.

**Anti-Pattern:** Domain entities import the database driver directly.
ORM annotations on domain entities. "Service locator" pattern that pulls
infrastructure from a static registry.

**Verification:** Architecture test — `domain/**` imports nothing from
`infrastructure/**`. The in-memory adapter and production adapter both pass
the same contract test (MEA-08).

---

### AP-02: Dependency Inversion

**Severity:** MUST (corollary of AP-01)

**When:** Any cross-layer dependency exists.

**Contract:** High-level modules depend on abstractions; low-level modules
implement those abstractions. Concretely: the domain owns the interface; the
infrastructure owns the implementation.

**Anti-Pattern:** The application service depends directly on
`PostgresOrderRepository` instead of `OrderRepository`. Inability to swap an
adapter without changing application code.

**Verification:** Confirm the interface lives in the domain package and the
implementation lives in the infrastructure package. Confirm the composition
root is the only place that names the concrete class.

---

### AP-03: Anti-Corruption Layer (ACL)

**Severity:** SHOULD (when integrating with a legacy system or third-party API)

**When:** An external system uses different vocabulary, different invariants,
or different consistency model than our domain.

**Contract:** A dedicated module translates between the external system's
model and our domain model. The translation is two-way and total — every
inbound message is mapped to a domain concept; every outbound message is
mapped to the external system's vocabulary.

**Anti-Pattern:** Letting the external system's terminology leak into the
domain (e.g. domain entities with field names from a third-party CRM).

**Verification:** Translation function has a test suite that exhaustively
maps both directions. No domain code imports the external system's SDK.

---

### AP-04: Strangler Fig (for brownfield migration)

**Severity:** MAY (when replacing a legacy system in production)

**When:** Replacing an existing system that cannot be turned off during the
migration. Big-bang rewrites are off the table.

**Contract:** A facade routes traffic between old and new implementations.
Functionality migrates one slice at a time. The facade is removed only when
the legacy system is fully retired.

**Anti-Pattern:** Branching the legacy codebase, modifying it in parallel,
and trying to merge two divergent trees back.

**Verification:** Routing rules in the facade are tested. Each migrated
slice has both a contract test (against the new implementation) and a
parallel-run test (asserting old and new behaviour matches for production
traffic during migration).

---

## Armor Patterns (Operational Hardening)

### AP-05: Circuit Breaker

**Severity:** MUST (on every external dependency call)

**When:** Calling any service outside the local process.

**Contract:** Wraps a call. Tracks failure count over a sliding window.
States: **closed** (calls flow through), **open** (calls fail fast), **half-open**
(probe call permitted). Configurable thresholds for open/close transitions.

**Anti-Pattern:** Retrying indefinitely against a dead downstream. Bare
`fetch()` with no breaker. Cascading failure where one slow downstream takes
out the entire service.

**Verification:** Chaos test — kill the downstream, assert breaker opens
within N failures. Restore the downstream, assert breaker closes within the
recovery window. (MEA-10.)

---

### AP-06: Bulkhead

**Severity:** SHOULD (when one workload's failure can starve another)

**When:** Multiple workloads share a resource (thread pool, connection pool,
memory). One workload's failure mode (slow downstream, runaway loop) should
not starve unrelated workloads.

**Contract:** Each workload gets its own pool with a fixed quota. Quota
exhaustion fails that workload's requests, not the entire service.

**Anti-Pattern:** A single shared connection pool for the database, the
payment provider, and the recommendation service. One slow downstream
exhausts the pool and takes everyone down.

**Verification:** Saturate one workload's pool with synthetic load; assert
unrelated workloads still meet their SLO.

---

### AP-07: Idempotent Receiver

**Severity:** MUST (on every state-changing endpoint that supports retries)

**When:** An endpoint that changes state may be retried — by clients, by
retries inside a circuit breaker, by a message broker's at-least-once delivery.

**Contract:** Endpoint accepts an idempotency key (client-supplied UUID,
message ID, or natural business key). Repeated requests with the same key
return the same result without re-applying the state change.

**Anti-Pattern:** A `POST /orders` that creates a duplicate order on retry.
A consumer that processes the same event twice and double-charges a customer.

**Verification:** Test — same idempotency key, two requests, one row created,
both responses identical. (MEA-09 integration test.)

---

### AP-08: Outbox Pattern

**Severity:** SHOULD (when a state change must produce a downstream event)

**When:** Writing to a database AND publishing an event/message about that
write must be atomic. The "dual write" problem.

**Contract:** Write the state change and the event to the same database
transaction (the "outbox" table). A separate process polls the outbox and
publishes events to the broker, marking them as published on success.

**Anti-Pattern:** Calling `db.commit()` and then `broker.publish()` — if
the broker call fails, state and message diverge permanently.

**Verification:** Test — kill the broker between commit and publish, assert
the event is published on broker recovery. No event is published before
the transaction commits.

---

## Proof Patterns (Verification)

### AP-09: Consumer-Driven Contract Testing

**Severity:** SHOULD (when service A's contract is consumed by service B)

**When:** Multiple services depend on a shared API contract.

**Contract:** The consumer (B) writes a contract (a test specifying what it
expects from A). The producer (A) runs the consumer's contract test as part
of A's CI. A's release is gated on the contract test passing.

**Anti-Pattern:** A breaks its contract; B finds out in production. Contract
documents written in markdown and never verified.

**Verification:** Pact (or equivalent) contract files exist for every cross-
service call. CI runs them on every change to either side.

---

### AP-10: Characterisation Test (for brownfield)

**Severity:** MUST (before any non-mechanical refactor on existing code)

**When:** Refactoring existing code that lacks tests. Per EP-07 in
CLAUDE.md.

**Contract:** Before changing the code, write a test that captures its
current behaviour (whether or not that behaviour is correct). Confirm the
test passes. Then refactor. Confirm the test still passes.

**Anti-Pattern:** "I'll just clean this up real quick" — refactoring code
with no tests, breaking subtle behaviour, finding out weeks later in
production.

**Verification:** Git history shows the characterisation test commit
preceding the refactor commit.

---

## Pattern Selection by NFR

SEA selects patterns based on the NFR.md produced by SRD. A non-exhaustive map:

| NFR signal | Patterns triggered |
|---|---|
| "Must remain available when payment provider is degraded" | AP-05 (CB), AP-06 (bulkhead), AP-08 (outbox if events involved) |
| "Must replace legacy ordering system without downtime" | AP-04 (strangler), AP-10 (characterisation) |
| "Must integrate with third-party CRM" | AP-03 (ACL) |
| "Must support at-least-once message delivery" | AP-07 (idempotent receiver), AP-08 (outbox) |
| "Must allow swapping persistence layer" | AP-01 (hexagonal), AP-02 (DI) |
| "Must guarantee multi-team contract stability" | AP-09 (consumer-driven contracts) |

---

## When Not in This Catalogue

If a TDD proposes a pattern not in this catalogue:

1. Document the pattern in the TDD with the same four fields (When, Contract, Anti-Pattern, Verification).
2. Justify why an existing catalogue pattern does not fit.
3. After the TDD is implemented and proven, propose adding the pattern to this catalogue (minor version bump).

This keeps the catalogue grounded in patterns that have actually been used,
not patterns that someone read about.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-12 | Initial catalogue. 10 patterns across Form, Armor, Proof. |
