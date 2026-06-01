---
name: fixture-discover-project
description: Fixture skill for drift-detector parity testing.
---

# Fixture discover-project skill

## Phase 1 — Detect

<!-- canonical:step:read-repo-root -->
Read the repo root.

## Phase 2 — Infer

<!-- canonical:step:infer-configuration -->
Run the LLM-backed inferrer.

<!-- canonical:step:gather-ambiguous-fields -->
Surface ambiguous fields to the consumer for confirmation.

## Phase 3 — Derive

<!-- canonical:step:derive-tenant -->
Derive the consumer tenant ULID.

<!-- canonical:step:derive-slug -->
Derive the project slug.

## Phase 4 — Mint

<!-- canonical:step:atomic-mint -->
Write the Project entity atomically.

## Phase 5 — Verify

<!-- canonical:step:verify-drift -->
Invoke the drift detector against the minted entity.

<!-- canonical:step:rollback-on-drift -->
On verify failure, unlink the just-written entity.

<!-- canonical:step:surface-success -->
On verify success, surface the Project ULID + path.
