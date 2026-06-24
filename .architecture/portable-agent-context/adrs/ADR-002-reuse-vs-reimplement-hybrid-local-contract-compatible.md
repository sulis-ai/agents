# ADR-002 — Reuse vs reimplement: a local-first store that conforms to the platform contract (HYBRID)

> **Status:** accepted · **Date:** 2026-06-24 · **Change:** CH-GJ9KQR
> **This is the central design ruling of the change.**

## Context

The platform already runs a hosted `communication-service` that owns Thread /
ThreadMessage / ThreadMemory with a REST + SDK contract, JWT auth, and
participant-scoped access (NFR-SEC05). We could lean on it, copy it, or split
the difference. Three options:

- **(a) CALL the platform communication-service** — the cockpit makes REST/SDK
  calls to the hosted service as its thread/message/memory store.
- **(b) ADOPT the model in a purely local store** — re-implement the platform's
  entity model in a cockpit-local store, no contract alignment beyond the
  shapes.
- **(c) HYBRID** — a local-first store that **conforms to the platform
  thread-sdk contract** (same operations, same types, same three-category
  errors), expressed transport-agnostically so it runs over a local binding
  now and is syncable to the hosted service later.

Constraints that decide it:

- The cockpit is **local-first today** — `127.0.0.1`, single-founder, no JWT,
  no `platform_id`, no participant auth. The hosted communication-service is a
  **multi-tenant authenticated service** that **may not be reachable locally**.
- The **remote-cockpit / platform boundary is PARKED** (founder's call). This
  change must not depend on un-parking it.
- The whole point of the change is to **build the portable-context value NOW**
  (provider-independent resume + audit), locally, and have it **compose later**
  with the platform.

## Decision

**Choose (c) HYBRID.** Build a **cockpit-local, append-only thread/memory
store** whose **contract conforms to the platform thread-sdk shape** (ADR-001
types; the platform's `createThread` / `getThread` / `listThread` /
`getThreadMemory` operation surface; the three-category error model). The
contract is **transport-agnostic** (CONTRACT_FIRST CF-02, lightweight internal
tier): today it binds to a **local subprocess/library call inside the cockpit**
(no network, no JWT); later it can bind to the hosted communication-service's
REST transport with **no contract change** — only a transport swap and an
auth/`platform_id` mapping.

Local-first specifics that the contract tolerates by design:

- `platform_id` is a **local constant** (e.g. `"local"`) today; the field
  exists so the hosted binding can populate it from JWT later.
- `participant_type` is `studio_agent` for the agent and `user` for the
  founder — the platform's two values, used as-is.
- Participant-scoped auth (NFR-SEC05) is **not enforced locally** (single
  founder, loopback) but the contract carries the `PermissionError` so a hosted
  binding enforces it without a contract change.

## Rejected alternatives

- **(a) CALL the hosted service.** Rejected: creates a hard runtime dependency
  on unbuilt/unreachable infrastructure (the hosted service may not run on the
  founder's laptop; remote boundary is parked). It would block the
  local-first value behind a deployment decision the founder deliberately
  deferred. It also imports JWT/`platform_id`/participant auth into a
  single-founder loopback context that has no use for them yet.
- **(b) ADOPT locally with no contract alignment.** Rejected: builds the value
  now but forks the model — the later sync to the platform becomes a
  translation/migration project instead of a transport swap. Violates EP-03
  (don't rebuild what exists) at the contract level even while reusing the
  shapes.

## Consequences

- The store + assembler + discovery seam are built as a **contract-first
  internal seam** (CONTRACT_FIRST lightweight tier): a `kind: contract` WP
  first, then producer (store/assembler) and consumer (cockpit/adapter) WPs in
  parallel against a mock, then an integration WP that swaps mock→real and runs
  the conformance check (CF-07) + the seam-close real-data drive (CF-12).
- **Connection to the parked remote decision (noted, not depended on):** when
  the founder un-parks remote hosting, the hosted communication-service binding
  is a **new transport adapter** behind the same contract + a sync job — no
  re-architecture. This ADR records the seam that makes that cheap; it does not
  schedule it.
- Building the second provider / failover (the eventual *consumer* of portable
  context) stays out of scope — this ADR builds the enabler, not the failover.
