# WP Backend Standard

> **Sulis-local v0.1.0 (2026-05-26).** The opinionated backend implementation
> doctrine for `kind: backend` Work Packages — the declared-but-unbuilt
> companion to `WORK_PACKAGE_STANDARD.md`'s `kind` enum. It states the
> patterns we **expect to be designed and implemented**, not a menu of
> options. Language-agnostic (pattern-level): the shape holds whether the
> implementation is Python/FastAPI, Node/Express, Go, or otherwise.

<!-- summary -->
Every backend Work Package is designed and implemented to a single
opinionated shape: a **hexagonal core** (pure domain behind ports), a
**handler** as the single source of truth, **adapters** behind those ports
with an **in-memory adapter first**, **authorization at the handler**,
**typed Results** at the boundary, **outside-in TDD**, and a definition of
done that means **wired, not just written**. This standard is the contract
the executor follows for backend WPs and the rubric the reviewer scores
against.
<!-- detail -->

## Severity convention

`MUST` — non-negotiable; violations block the WP. `SHOULD` — default;
deviation requires a one-line rationale in the WP. `MAY` — judgement.

## Relationship to existing standards (reference, do not restate)

This standard adds the **backend-specific execution shape** only. It does
**not** re-state principles already codified — cite them:

- `engineering-principles.md` (EP-02 quality/TDD, EP-03 reuse-first, EP-05
  the hard road, EP-07 SOLID/clean code, EP-08 no bloat, EP-09
  authorization-first) — the universal principles these patterns specialise.
- `boring-code.md` — naming, explicit types, no metaprogramming, no
  module-level state.
- `red-green-blue.md` — the RED → GREEN → BLUE cycle WPB-08 runs.
- `change-primitives.md` — Reuse / Compose / Extend before Create (WPB-01's
  "is there a port already?" precedes any new adapter).
- `WORK_PACKAGE_STANDARD.md` — the WP shape; this is its `kind: backend`
  execution detail.

---

## The patterns

### WPB-01 — Ports & Adapters (hexagonal) boundary · MUST

The system is three layers with dependencies pointing **inward only**:

- **Domain** — pure business logic + entities + value objects. **Zero
  infrastructure dependencies.** No imports of HTTP, DB, SDK, or framework
  code.
- **Application** — use cases + **ports** (interfaces / Protocol classes)
  the domain needs. Ports are owned by the inside, implemented by the
  outside.
- **Infrastructure** — **adapters** implementing the ports (DB, external
  APIs, queues), plus the framework entry points.

> **In practice:** an adapter implements a port the domain defines; the
> domain calls the port, never the adapter. The infrastructure depends on
> the domain, never the reverse.
> **Anti-pattern:** a domain entity importing the database client; business
> logic inside an HTTP controller; a port defined in infrastructure.

### WPB-02 — Repository pattern for persistence · MUST

Persistence sits behind a **repository port**. The domain stores and
retrieves entities through a repository interface and is ignorant of the
storage technology.

> **In practice:** `OrderRepository` (port) with `save` / `find_by_id`;
> `PostgresOrderRepository` / `MemoryOrderRepository` (adapters).
> **Anti-pattern:** SQL strings or ORM models in the domain; a use case
> that knows it's talking to Postgres.

### WPB-03 — In-memory adapter first · MUST

Every port gets an **in-memory adapter** before (or alongside) any
production adapter. The in-memory adapter is the default for local dev and
the substrate for tests. A **factory** selects the implementation by
environment/config. **Never mock what you can implement** — an in-memory
adapter validates behaviour; a mock only validates a call signature.

> **In practice:** `MemoryOrderRepository` is real code with real
> behaviour; tests run against it; a factory returns it unless config
> selects the production adapter.
> **Anti-pattern:** `@mock`/`@patch` of an internal port when an in-memory
> adapter would catch real bugs; a port with only a production adapter and
> no in-memory twin.

### WPB-04 — Handler is the single source of truth · MUST

Each capability has **one handler** that owns its business logic. Every
entry point — HTTP route, agent/workflow tool, CLI, SDK — is a **thin
delegate** that translates transport in/out and calls the handler. Business
logic lives in exactly one place.

> **In practice:** an HTTP route parses the request, calls
> `handler.create(...)`, maps the Result to a status code — nothing more.
> **Anti-pattern:** the same validation/business rule duplicated in a route
> and a tool; logic that exists in the controller and nowhere else.

### WPB-05 — Authorization at the handler · MUST

Authorization is checked **inside the handler, before business logic** —
not only at the HTTP edge — so every entry point (HTTP, tool, SDK,
internal) is protected by the same check. Permissions are **defined before**
the operation is implemented. Permission naming: `{domain}.{resource}:{action}`
(e.g. `orders.order:create`). Tests cover **both allowed and denied**.

> **Anti-pattern:** auth in HTTP middleware only, so a workflow tool or SDK
> path bypasses it; testing only the 200, never the 403; adding auth
> "after it works."

### WPB-06 — Typed Result at the boundary · SHOULD

Handlers return a **typed Result** (`success` + `data` | `error`) rather
than throwing across the boundary. Entry points translate the Result into
their transport (HTTP status, tool payload). Domain-level invariant
violations may still raise inside the domain; they are caught and converted
to a Result at the handler edge.

> **Anti-pattern:** raw exceptions propagating to the HTTP framework's
> default 500 handler; entry points that can't tell "not found" from
> "denied" from "invalid."

### WPB-07 — Composition root + dependency injection · MUST

All wiring happens in **one composition root**. Dependencies are passed in
(constructor injection). No global singletons, service locators, or
module-level mutable state reaching into the domain or application layers.

> **In practice:** `main` builds the adapters, injects them into handlers,
> mounts the entry points. A handler receives its repository; it never
> reaches for a global.
> **Anti-pattern:** a handler importing a module-level DB connection; new
> dependencies wired ad hoc across the codebase instead of at the root.

### WPB-08 — Outside-in (double-loop) TDD · MUST

Backend WPs are built outside-in:

1. **Outer loop** — write the **integration tests first**, against the
   in-memory adapter, and confirm they **fail** (nothing implemented yet).
2. **Inner loop** — RED → GREEN → BLUE per `red-green-blue.md` on domain →
   port → adapter → handler until the outer-loop tests pass.

Both loops run on real in-memory adapters (WPB-03), not mocks.

> **Anti-pattern:** writing implementation first and tests after; skipping
> the failing-integration-test step; unit tests that mock the very
> behaviour under test.

### WPB-09 — Done means wired, not just written · MUST

A backend capability is **not done** until every entry point is **mounted /
registered and covered by an integration test**. Writing a handler or a
route is not completion. The WP's Definition of Done explicitly lists the
wiring: route mounted in the app, tool/SDK method added if user-facing,
integration test registered in CI.

> **In practice:** the WP fails review if a route exists but isn't mounted
> (404 in the deployed app), or a handler has no entry point, or a new
> capability has no integration test in CI.
> **Anti-pattern:** an orphaned router; a handler reachable only from a
> test; "I'll wire it up later."

### WPB-10 — Structured logging + operation tracking · SHOULD

Logs are **structured** (key-value fields, not string interpolation).
Multi-step operations carry an operation/correlation identifier. Security-
sensitive operations (auth denials, mutations) are audited.

> **Anti-pattern:** `logger.info(f"created {x} for {y}")`; no trace across a
> multi-step flow; silent auth denials.

### WPB-11 — Conventional API surface (when exposing HTTP) · SHOULD

When a backend WP exposes HTTP, default to the established conventions
(per `convention-preference-standard.md`): **OpenAPI-first**, conventional
status codes (201 create, 204 delete, 400/404/409), **cursor pagination**,
explicit **versioning** (`/v{n}`), consistent error envelopes. Mobile-/SDK-
specific optimisations are **out of scope** unless the WP requires them.

> **Anti-pattern:** bespoke status-code schemes; offset pagination by
> default; unversioned breaking changes; inventing an error format per
> endpoint.

---

## Verification gates (per `kind: backend`)

From `engineering-principles.md`'s verification-operationalisation mapping,
the backend gates are:

| Gate | Tool class (example) |
|------|----------------------|
| Tests pass | unit + integration test runner (e.g. pytest) |
| Coverage | coverage tool on changed surface |
| Lint | linter (e.g. ruff / eslint) |
| Types | type checker (e.g. mypy / tsc) |
| Security | dependency + SAST scan (e.g. pip-audit / bandit) |

The tools are scope-specific (declared per project); the **gate classes**
are fixed for backend WPs. A backend WP's `verification_gates` default to
`[unit, integration, smoke]` per `WORK_PACKAGE_STANDARD.md`.

---

## Provenance

Consolidated from five reviewed practitioner documents (2026-05-26):

- `ae/.claude/agents/hex-architect.md` — the ports & adapters layer model
  (WPB-01) + composition root (WPB-07) + the architecture checklist.
- `ae/.claude/agents/api-designer.md` — the conventional API surface
  (WPB-11); mobile-/SDK-first scope deliberately **excluded**.
- `ae/.claude/agents/software-developer.md` — GREEN-phase discipline +
  micro-commits (now subsumed by the change-as-primitive model + the
  executor lifecycle).
- `platform/.claude/skills/backend-development/SKILL.md` — handler-centric
  single-source-of-truth (WPB-04), Result pattern (WPB-06), in-memory-first
  + factory (WPB-03), repository (WPB-02), double-loop TDD (WPB-08),
  deployment-completeness / "done means wired" (WPB-09, its section 7A),
  authorization-at-handler (WPB-05), structured logging (WPB-10).
- `platform/methodology/standards/engineering-principles.md` — EP-02/03/05/
  07/08/09 (referenced, not restated) + the per-kind verification gate
  mapping.

**Platform couplings stripped** (not part of this standard): Firestore/GCP
adapters, PolicyResolver, the SulisClient SDK + SDK-first mandate,
`@operation` ontology decorator, Production Guardian, IVS, and all
Python/FastAPI/pydantic-specific templates. The patterns are the contract;
the language and framework are the implementer's choice.

---

## Version history

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-05-26 | Initial sulis-local definition. 11 patterns (WPB-01..WPB-11) consolidated from five practitioner docs into one opinionated, language-agnostic backend implementation doctrine. Companion to WORK_PACKAGE_STANDARD's `kind: backend`. SHOULD-tier patterns (WPB-06/10/11) carry 90-day calibration; promote to MUST on evidence from 3+ backend WP executions. |
