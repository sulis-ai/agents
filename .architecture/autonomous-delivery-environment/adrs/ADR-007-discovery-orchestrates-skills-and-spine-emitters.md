# ADR-007 — Onboarding orchestrates the existing discovery skills + spine emitters; it reimplements nothing

- **Status:** accepted
- **Date:** 2026-06-04
- **Change:** CH-01KT50 · autonomous-delivery-environment
- **Deciders:** SEA

## Context

Cold-start onboarding (UC-07, FR-27, FR-28, FR-31, FR-32, FR-35, FR-36,
FR-N6, FR-N7, FR-N10, FR-N11, NFR-DISC-01..04, NFR-DISC-06) turns an empty
graph into a confirmed Tenant / Product / Project. A "pick a Product, then a
Project" form is useless against an empty graph — there is nothing to pick —
so onboarding is a **conversation that creates the graph**.

The capability needs to: search a bounded folder, ask clarifying questions,
find-or-create a repo, mint entities, and persist a durable config. Each of
these already exists in the platform:

- directory search + project/context discovery — the `discover-project`,
  `discover-context`, and `codebase-mapping` skills;
- schema-validated entity creation — the Tenant / Product / Project **spine
  emitters** (`sulis-emit-tenant` / `-product` / `-project`);
- intent → primitive classification — the existing `_specify_classifier` +
  change-primitives vocabulary;
- the agent transport — `SessionBridge` (ADR-002), reused (ADR-006).

The temptation is to write a new "onboarding engine" that does its own
filesystem walk and its own entity writes. That duplicates validated code
and creates a second, unvalidated write path into the brain.

## Decision

**Onboarding is an orchestration layer over the existing discovery skills
and the validated spine emitters. It introduces no new discovery mechanism
and no freehand entity write.**

- **Search (FR-N7 / NFR-DISC-01):** bounded to the founder's chosen area.
  Onboarding calls the existing discovery skills, which already carry the
  `codebase-mapping` skip-list (`node_modules`, `.git`, `vendor`, build
  output). The chosen folder is the search root; the agent does not traverse
  to parent or sibling directories. (Search depth within the chosen area is a
  founder-owned question — see the TDD's Open Architecture Questions; the
  recorded safe default is recursive-under-the-chosen-folder-only.)
- **Mint (FR-32 / NFR-DISC-03):** every entity is created through the
  schema-validated spine emitters. No onboarding path writes an entity file
  directly. This is a Form-pillar guarantee: the brain is only ever written
  through the emitter port.
- **Idempotency (FR-31 / NFR-DISC-02):** before minting, onboarding asks the
  emitters / graph whether the Tenant / Product / Project already exists and
  surfaces the existing entity rather than creating a duplicate.
- **Confirm gate (FR-N6 / NFR-DISC-04):** a read-and-propose turn needs no
  confirmation; the **act** of minting or starting requires explicit founder
  confirmation — the same "ask before consequential" discipline as the chat
  relay, not a new approval mechanism.
- **Durable config (FR-36 / NFR-DISC-06):** the Product/Project config —
  including each `Project.source = {repo, path, primary_branch}` — is
  persisted into the **existing change-store/graph model** via the emitters.
  Onboarding adds **no separate config store** (consistent with NFR-DATA-01).
  A later session reads the config back and starts a change with no re-setup.
- **All-or-nothing persistence (FR-N11):** the config is persisted **only**
  after the founder confirms and the repo is found-or-created and reachable.
  A declined or abandoned onboarding leaves the graph unchanged; no
  half-written config (e.g. a Product without its Project's `source`) is ever
  observable on the next session.

## Alternatives considered

- **A bespoke onboarding engine with its own fs-walk + entity writes
  (rejected).** Duplicates the discovery skills and bypasses the emitters'
  schema validation — a second, unvalidated write path into the brain. EP-03
  and NFR-DISC-03 forbid it.
- **Mint optimistically, reconcile later (rejected).** Would leave dangling
  Products on a declined/abandoned flow (FR-N11 violation). The confirm gate
  + all-or-nothing persistence is the safe default.
- **A new config store for Product/Project source (rejected).** Violates
  NFR-DATA-01 / NFR-DISC-06; the graph is already the durable home, and a
  parallel store would break the one-data-model-up-the-ladder moat.

## Consequences

- New code is thin: an orchestrator that sequences existing skills + emitters
  over the bridge, plus the confirm-gate plumbing and the idempotency probe.
- Verified in CI against recorded fixtures (`recording-bridge-discovery-session`,
  `fixture-project-directory`) without a live agent — search-scope (FR-N7),
  dedupe (FR-31), validated-emitter writes (FR-32), confirm gate (FR-N6), and
  all-or-nothing persistence (FR-N11) all assert against fixtures. The full
  live path (real agent, real mint) is verified manually on the founder
  machine.
- The durable-config round-trip (FR-36) verifies from the existing
  change-store fixtures: mint in one test-session, read back `Project.source`
  in a fresh session, start a change with no re-discovery.
