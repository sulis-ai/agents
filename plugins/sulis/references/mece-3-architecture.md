# MECE-3 Architecture Standard

<!-- summary -->
The MECE-3 framework decomposes every architectural decision into three Mutually
Exclusive and Collectively Exhaustive pillars: **Form** (structural integrity),
**Armor** (operational hardening), and **Proof** (verification protocol). Every
component SEA designs or audits is evaluated against all three pillars. A design
that satisfies Form but lacks Armor is incomplete. A design that satisfies Form
and Armor but lacks Proof is unverified speculation.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period

---

## Provenance

This framework synthesises three established practitioner traditions:

- **Form** draws on hexagonal architecture (Cockburn, 2005), Clean Architecture
  (Martin, 2017), and Domain-Driven Design (Evans, 2003).
- **Armor** draws on Release It! (Nygard, 2018), the SRE Workbook (Beyer et al.,
  Google, 2018), and the OWASP Application Security Verification Standard.
- **Proof** draws on the Practical Test Pyramid (Fowler), contract testing
  (Pact / consumer-driven contracts), and Chaos Engineering principles (Netflix).

This is practitioner knowledge, not peer-reviewed research.

---

## Boundary Definition

This standard contains **universal architectural pillars only**. Content belongs
here if and only if it passes the **ProjectX test**: replacing every project
name, file path, and technology with a fictional "ProjectX" equivalent requires
zero semantic changes to the principle statement.

Project-specific architecture decisions (which queue, which database, which
language runtime) belong in the project's `TDD.md`, not here.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification documented in the TDD or ADR. |
| **MAY** | Permitted option. Use judgement. |

---

## Pillar 1: Form — Structural Integrity

The shape of the code. Boundaries between domain logic and infrastructure.
Dependency direction. Module decoupling.

### MEA-01: Domain logic depends on no infrastructure

**Severity:** MUST

The domain layer (entities, value objects, domain services) must not import,
reference, or call into any infrastructure concern: database driver, HTTP
client, message broker, file system, clock, logger, environment variable,
framework. The domain receives these capabilities through ports (interfaces
defined by the domain) and adapters (implementations defined by infrastructure).

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Define `interface OrderRepository` in the domain. Define `class PostgresOrderRepository implements OrderRepository` in infrastructure. The domain knows the interface; only the composition root knows the implementation. |
| **Anti-Pattern** | `import { db } from '../db'` inside a domain entity. Static factory calls from domain code to infrastructure singletons. ORM annotations on domain entities that bind them to a specific persistence layer. |
| **How to verify** | A static check (architecture test) asserts no `domain/**` file imports from `infrastructure/**`. Run on every commit. |

### MEA-02: Dependencies point inward

**Severity:** MUST

The composition root (the outermost wiring layer) knows about every layer
inside it. Each inner layer knows nothing about the layers outside it.
Concretely: infrastructure depends on application; application depends on
domain; domain depends on nothing. Reverse dependencies are forbidden.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Module graph is acyclic and points from outside to inside. Cross-cutting concerns (logging, tracing) are injected at the boundary, not pulled from the centre. |
| **Anti-Pattern** | Domain calling `console.log` directly. Application layer reading environment variables. Domain importing a logger singleton. |
| **How to verify** | Generate the module dependency graph (e.g. `madge`, `dependency-cruiser`). Confirm no edges from inner to outer layers. |

### MEA-03: Modules expose contracts, not implementations

**Severity:** SHOULD

Cross-module communication happens through published interfaces. A module's
internal types, classes, and helpers are not part of its public surface.
Consumers depend on the interface, not the implementation.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Each module has a single `index.ts` (or equivalent) that re-exports the public contract. Internals live in `internal/` and are not exported. |
| **Anti-Pattern** | Importing from deep paths (`@module/internal/helpers/normalise`). Consumers reaching past the contract to grab a utility class. |
| **How to verify** | Lint rule forbidding deep imports across module boundaries. |

---

## Pillar 2: Armor — Operational Hardening

What the system does when things go wrong. Resiliency, security, observability.
Armor is what separates a prototype from a production system.

### MEA-04: Every external call has a timeout, retry, and circuit breaker

**Severity:** MUST

Any call across a process boundary — HTTP, RPC, database, message broker,
filesystem (on networked storage) — is wrapped in three resiliency primitives:

1. **Timeout** — explicit, finite. Never `null` or "default".
2. **Retry** — bounded count, exponential backoff with jitter, idempotency-aware.
3. **Circuit breaker** — open after N failures in window, half-open probe, close on success.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Wrap every adapter in a resilience policy (e.g. `resilience4j`, `Polly`, `cockatiel`, `opossum`). Timeouts are configured per-call, not globally. |
| **Anti-Pattern** | A bare `fetch()` or `axios.get()` in production code. Retries without backoff (thundering herd). Retries on non-idempotent operations without idempotency keys. |
| **How to verify** | Code search for unwrapped HTTP/DB clients. Chaos test: inject latency into a downstream — confirm timeout fires and circuit opens. |

### MEA-05: Secrets never live in source, environment files, or logs

**Severity:** MUST

Secrets (API keys, tokens, passwords, signing keys) are fetched at runtime from
a secrets manager (Vault, AWS Secrets Manager, GCP Secret Manager, Doppler).
They are not committed to source, not stored in `.env` files checked into the
repository, and not present in logs, error messages, or traces.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | A secrets provider abstraction. Local development uses a local secrets backend (1Password CLI, doppler-local) — not a `.env` file. Logging libraries are configured with redaction rules. |
| **Anti-Pattern** | `.env` files containing real values. Secrets in CI/CD environment variables without rotation. Stack traces that leak Authorization headers. |
| **How to verify** | Pre-commit hook scans for entropy (`gitleaks`, `trufflehog`). Log sampling test asserts no secret-shaped strings escape. |

### MEA-06: Inter-service traffic is encrypted and authenticated

**Severity:** SHOULD

Service-to-service traffic uses mTLS (mutual TLS) or equivalent (signed JWTs
over TLS, service mesh identity). "Inside the perimeter" is not a security
boundary. Zero-trust applies inside the cluster.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Service mesh (Istio, Linkerd) handles mTLS termination. Service identity is workload-bound (SPIFFE), not IP-bound. |
| **Anti-Pattern** | Plain HTTP between services in the same VPC. Shared bearer tokens with no rotation. |
| **How to verify** | Network policy denies non-mTLS traffic. Pen test verifies an unauthenticated pod cannot call a service. |

### MEA-07: Every operation emits a trace, a log, and a metric

**Severity:** MUST

Every code path that crosses a boundary (request handler, scheduled job,
event handler) is instrumented with OpenTelemetry:

- **Trace** — span with attributes for the operation, downstream dependencies as child spans
- **Structured log** — JSON, with `trace_id` and `span_id` for correlation
- **Metric** — at minimum the RED triad (Rate, Errors, Duration) per operation; USE triad (Utilisation, Saturation, Errors) for resources

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Use OpenTelemetry SDK. Trace context propagates across all I/O. Logs include `trace_id`. Metrics use semantic conventions. |
| **Anti-Pattern** | `print()` or `console.log` statements. Logs without `trace_id`. Custom metric names that don't follow `service.operation.outcome`. |
| **How to verify** | A request through the system produces a single connected trace in the backend. RED dashboards exist per service. |

---

## Pillar 3: Proof — Verification Protocol

Tests that prove the system works in the presence of failure. Contract tests,
integration tests, and chaos assertions are written as part of the design,
not bolted on after delivery.

### MEA-08: Every port has a contract test

**Severity:** MUST

Every port (interface defined in the domain) has a contract test that any
adapter implementing it must pass. The contract test is the source of truth
for adapter behaviour. New adapters cannot be merged without passing the
contract test for their port.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | A shared test suite per port. The Postgres adapter and the in-memory adapter both pass the same `OrderRepositoryContract` test. |
| **Anti-Pattern** | Different test suites for each adapter that drift in coverage. Adapter behaviour discovered only in production. |
| **How to verify** | The contract test is run against every adapter in CI. A failing contract blocks merge. |

### MEA-09: Integration tests run against real adapters, not mocks

**Severity:** MUST

Integration tests use real infrastructure (testcontainers, ephemeral databases,
local message brokers) — not mocks. Mocking infrastructure hides bugs that
materialise in production. In-memory adapters (purpose-built real
implementations) are preferred for unit-level tests where speed matters.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Postgres via testcontainers. Kafka via local broker. S3 via MinIO. The in-memory adapter is a real implementation, not a mock — it satisfies the same contract test. |
| **Anti-Pattern** | `mockResolvedValue` on a database client. Test suites green in CI but failing on first deploy. |
| **How to verify** | Confirm no mocking library is imported in integration test files. Confirm the in-memory adapter passes the same contract test as the production adapter. |

### MEA-10: Resiliency primitives have chaos tests

**Severity:** SHOULD

Every Armor primitive (timeout, retry, circuit breaker, fallback) has a
corresponding chaos test that injects the failure mode it protects against
and asserts the primitive behaves as designed.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Inject 5s latency into a downstream — assert the 2s timeout fires. Kill the downstream — assert circuit opens after N failures. Restore the downstream — assert circuit closes within recovery window. |
| **Anti-Pattern** | A circuit breaker that has never been exercised. Resiliency code that has only been tested via code review, never via failure injection. |
| **How to verify** | A chaos test exists per primitive. Tests run on a scheduled chaos run (weekly minimum) or on every change to the resilience policy. |

---

## How SEA Applies This Standard

- **`/sea:blueprint`** validates that the proposed TDD addresses all three pillars before writing it.
- **`/sea:codebase-audit`** scans existing code for primitive gaps in each pillar.
- **`/sea:harden`** generates Hardening Deltas that close Armor gaps.
- **`/sea:decompose`** ensures each Work Package's Definition of Done includes Proof from the Verification Pillar.
- **`/sea:verify`** runs the COMPLETENESS_REPORT against this standard.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-12 | Initial standard. All principles in calibration. |
