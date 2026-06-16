# ADR-002 — No new contract artifact for the CLI↔cockpit subprocess seam

> change_id `01KTV4SS9N8BP0XN8GCQAXT6PC` · status: accepted (design) · 2026-06-11

## Decision

This change does not produce a standalone CONTRACT_FIRST contract artifact for
the `sulis-change` CLI ↔ cockpit seam. The existing `RecreateRunner` port (with
its typed `RecreateOutcome` and three error categories TIMEOUT / EXEC_FAIL /
SPAWN_FAIL) **is** the contract; this change amends its method signature only.

## Context

CONTRACT_FIRST_STANDARD (CF-01..CF-08) governs **cross-kind** seams — most often
a `backend` producer and a `frontend` consumer that must agree on a schema before
either ships. This seam is cross-**language** (Python CLI ↔ TypeScript cockpit)
but **same-kind**: both sides are `kind: backend`, the transport is a subprocess
argv invocation, and there is no founder-facing flow or visual surface at the
seam. The port already encodes the contract per CF-02 (output type) and CF-03
(error categories as typed failures). The change is a signature correction
(`handle` → `changeId`), governed by WPB-01 (port discipline), not the
introduction of a new producer/consumer schema.

## Alternatives considered

- **Author a CF contract WP for the seam and make the CLI + cockpit WPs depend on
  it (CF-05 parallel decomposition).** Rejected: CF-05 exists to let a producer
  and consumer of a *new* schema proceed in parallel against a stub. Here the
  schema is unchanged in shape — one typed argument changes meaning — and the
  port + its `FakeRecreateRunner` in-memory adapter already give both sides a
  conformance surface. A contract WP would be ceremony with no parallelism gain.
- **Treat the argv string as an informal contract and skip the port update.**
  Rejected: that is exactly the latent-coupling CF-01 warns against; the port is
  the typed seam and must carry the corrected key.

## Consequences

- Decomposition stays simple: the CLI WP and the cockpit WP each own their side
  of the existing port; the cockpit WP depends on the CLI WP only because the
  `--change-id` entry point must exist before the cockpit can drive it (a real
  data dependency, not a contract-stub dependency).
- If a future change adds a founder-facing flow at this seam, revisit under
  CF-07.5 (the `interaction` contract type). Out of scope here.
