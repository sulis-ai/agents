# TDD Template

The required structure for `.architecture/{project}/TDD.md`. Every TDD SEA
produces uses this template. Sections may grow; they may not be skipped.
Skipped sections are gaps that go in the `Open Questions` section, not
silent omissions.

---

```markdown
# {Project Name} — Technical Design Document

> **ARCH ID:** ARCH-NNN
> **Status:** designed
> **Sourced from:** [.specifications/{project}/SPEC.yaml](../../.specifications/{project}/SPEC.yaml)
> **Date:** YYYY-MM-DD

---

## 1. Overview

One paragraph. What system is being designed. What problem it solves. What
the success criterion looks like in production.

---

## 2. Source Specification

| Artifact | Path | Notes |
|---|---|---|
| Requirements (SRD) | `.specifications/{project}/SRD.md` | {key sections relied on} |
| Non-functional requirements | `.specifications/{project}/NFR.md` | {key NFRs driving design} |
| Primitive tree | `.specifications/{project}/PRIMITIVE_TREE.jsonld` | {node count, types} |
| Diagrams | `.specifications/{project}/diagrams/` | {which diagrams informed which sections} |

---

## 3. Form — Structural Design

### 3.1 Component Inventory

One table per component. Each component is a node from `PRIMITIVE_TREE.jsonld`
or a derivation explained in 3.5.

| Component | Type | Owns | Depends on (ports) |
|---|---|---|---|
| Order Application Service | application-service | use-case orchestration | `OrderRepository`, `PaymentGateway`, `NotificationPort` |
| Order Domain Model | domain-entity | invariants of Order | (none — domain) |
| Postgres Order Adapter | infrastructure-adapter | persistence | (implements `OrderRepository`) |
| Payment Provider Adapter | infrastructure-adapter | payment provider integration | (implements `PaymentGateway`) |

### 3.2 Module Boundaries

```
domain/                          # entities, value objects, ports — no I/O
  order/
    Order.ts
    OrderRepository.ts          (interface)
    PaymentGateway.ts           (interface)
  index.ts                      (public contract)

application/                     # use-case orchestration
  CreateOrder.ts
  index.ts

infrastructure/                  # adapters — implementations of ports
  persistence/
    PostgresOrderRepository.ts
    InMemoryOrderRepository.ts   (testing adapter, satisfies same contract)
  payments/
    StripePaymentGateway.ts
  index.ts

composition/                     # composition root — wires the system together
  app.ts
```

State the rules:

- Domain depends on nothing.
- Application depends on domain only.
- Infrastructure depends on domain (it implements domain ports) — never the
  other way around.
- Composition root is the only module that imports concrete classes from
  infrastructure.

### 3.3 Ports (Domain Interfaces)

For each port, give the full signature, the invariants it protects, and the
contract test name.

```typescript
// domain/order/OrderRepository.ts

export interface OrderRepository {
  /** Persists a new order. Throws DuplicateOrderError if an order with this
   *  id already exists. Idempotent on (id, idempotencyKey). */
  save(order: Order, idempotencyKey: IdempotencyKey): Promise<void>;

  /** Returns the order or null. Never throws on not-found. */
  findById(id: OrderId): Promise<Order | null>;
}
```

Contract test: `tests/contracts/OrderRepositoryContract.ts` — both
`PostgresOrderRepository` and `InMemoryOrderRepository` must pass it.

### 3.4 Adapters

For each adapter: the port it implements, the technology, the consistency
guarantees, the failure modes it must handle.

### 3.5 Composition Root

Where every concrete dependency is constructed and wired. Show the wiring
order. Show how environment-specific overrides happen (test vs production).

---

## 4. Armor — Operational Hardening

### 4.1 External Dependencies

Every cross-process call. Each row is non-negotiable.

| Dependency | Protocol | Timeout | Retry | Circuit Breaker | Bulkhead | Idempotency |
|---|---|---|---|---|---|---|
| Stripe Payment API | HTTPS | 2s | 2x exp backoff w/ jitter | 5 failures / 30s window | Yes — dedicated pool, 20 connections | Client-supplied key |
| PostgreSQL | TCP | 1s (query), 5s (transaction) | 0 (caller decides) | App-level on connection acquisition | Yes — connection pool, 50 connections | Natural key |
| Internal notification service | gRPC/mTLS | 500ms | 3x exp backoff | 10 failures / 60s | Yes | Idempotency-Key header |

### 4.2 Security

| Boundary | Authentication | Authorisation | Transport |
|---|---|---|---|
| External HTTP API (clients) | OIDC bearer JWT | RBAC + tenant scoping | TLS 1.3 |
| Service-to-service | mTLS (SPIFFE workload identity) | Service-level claims | mTLS |
| Database | Cert-based | DB-level role per service | TLS |
| Payment provider | API key from vault | (provider-managed) | TLS 1.3 |

### 4.3 Secrets

- All secrets fetched from {Vault | AWS Secrets Manager | …} at startup.
- No secrets in `.env` or environment variables baked into images.
- Rotation: {policy}. Per-secret rotation cadence in `secrets.yaml`.
- Logs/traces are scrubbed via {redaction library/config}.

### 4.4 Observability

- **Traces:** OpenTelemetry SDK. Every handler creates a root span. Adapter
  calls are child spans. Trace context propagates across all I/O.
- **Logs:** Structured JSON. Every log line includes `trace_id`, `span_id`,
  `service.name`, `operation.name`. Levels: error, warn, info, debug.
- **Metrics:**
  - Per-handler RED: `{service}.{operation}.requests`, `{...}.errors`, `{...}.duration`
  - Per-resource USE: pool saturation, queue depth
  - Business metrics: `orders.created`, `orders.failed`, `payments.refused`
- **Dashboards:** one per service, predefined panel set (RED, USE, error budget).
- **Alerts:** symptom-based, not cause-based. Burn-rate alerts on SLO.

---

## 5. Proof — Verification Protocol

### 5.1 Contract Tests

One file per port. Both production and in-memory adapter pass it. Test file
paths are stable so adapters in any package can run them.

| Port | Contract test file |
|---|---|
| `OrderRepository` | `tests/contracts/OrderRepositoryContract.ts` |
| `PaymentGateway` | `tests/contracts/PaymentGatewayContract.ts` |
| `NotificationPort` | `tests/contracts/NotificationPortContract.ts` |

### 5.2 Integration Tests

Real adapters, real infrastructure (testcontainers). No mocks for internal
services. Mocks permitted only for third-party HTTP APIs (Stripe sandbox is
preferred where available).

### 5.3 Chaos Assertions

One per resiliency primitive in 4.1.

| Primitive | Chaos test |
|---|---|
| Stripe timeout (2s) | `chaos/payments.test.ts::timesOutWithin2sOnSlowProvider` (toxiproxy 5s latency) |
| Stripe circuit breaker | `chaos/payments.test.ts::opensCircuitAfter5Failures` |
| Postgres connection pool | `chaos/persistence.test.ts::failsWithinTimeoutOnPoolExhaustion` |

---

## 6. Trade-offs

A short table of patterns chosen vs alternatives rejected, with the reason.
Detailed reasoning lives in the ADRs; this section is the index.

| Decision | Chose | Rejected | Reason | ADR |
|---|---|---|---|---|
| Persistence | PostgreSQL + logical replication | DynamoDB | Need ACID for multi-row order writes | ADR-001 |
| Async messaging | Outbox + Kafka | Direct broker publish | Avoid dual-write inconsistency | ADR-002 |
| Service mesh | Linkerd | Istio | Lower operational overhead | ADR-003 |

---

## 7. Open Questions

Anything the SRD does not specify that the architecture needs. These are
gaps to resolve before decomposition.

- [ ] {Question} — needs input from {who}.
- [ ] {Question} — escalate to `srd:requirements-analyst`.

---

## 8. Implementation Sequence

A short paragraph naming the order in which Work Packages should be
sequenced. Cross-reference `work-packages/INDEX.md` once `/sulis:plan-work`
has run.
```
