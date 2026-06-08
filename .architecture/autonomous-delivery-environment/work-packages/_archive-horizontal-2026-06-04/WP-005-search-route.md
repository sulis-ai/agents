---
id: WP-005
title: "GET /api/search — content search + stage + needs-attention filters"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: reads

atomic_branch: yes
estimate: 5h
blast_radius: low
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "GET /api/search?q= matches change CONTENT (conversation + created entities/artifacts), not just handle/intent/stage (FR-10)"
  - "GET /api/search?stage=design&stage=ship filters to those stages (FR-11, repeated query param → array)"
  - "GET /api/search?needsAttention=true returns only blocked / waiting-on-decision / stopped-mid-reply changes; not idle-but-fine (FR-12)"
  - "Filters compose (q + stage + needsAttention narrow the same set); response shape is { results: Change[] }"
  - "GET-only; read-only gate green; reading search starts no claude process (FR-N4)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/searchChanges.test.ts (NEW) — content match (conversation-only + entity-only hits); stage filter; needsAttention filter; composition"
  integration:
    - "apps/cockpit/server/tests/routes.search.test.ts (NEW) — supertest; the FR-10 conversation-only-text acceptance"
  verification:
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.search.test.ts"

derived_from:
  - finding: "TDD §5 surface map row 5 (search); FR-10/11/12; openapi.yaml /api/search"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-003]      # reuses needsAttention.ts from WP-003 (FR-12 single source of truth)

child_wps: []
kinds: null

rollback: |
  New route + one search lib + tests. Remove the mount and files; revert.

verifies_scenario: "dna:scenario:CP3MAX93563W45W7D547T5FJ80"   # Find a change
---

# GET /api/search — content search + stage + needs-attention filters

## Why

UC-05 / FR-10..FR-12: find a change by what is *in* it (conversation +
created artifacts), and narrow the board by stage and by "needs attention". The
filters narrow the *same* board — there is no separate results screen (ADR-005),
so the client (WP-014) renders these results in the board layout.

## What changes

- `apps/cockpit/server/lib/searchChanges.ts` (NEW, EXPAND-Create) — `(changes, transcripts, brain, { q, stage[], needsAttention }) → Change[]`. Reuses `needsAttention.ts` (WP-003) for the FR-12 rule so the definition lives in one place.
- `apps/cockpit/server/routes/search.ts` (NEW, EXPAND-Create) — `router.get("/", …)`; mounted at `/api/search`.

## How

Compose existing reads (change list + transcript parse + brain read). Content
match scans conversation text and created-entity text, not just labels (FR-10).
`depends_on: WP-003` because the needs-attention predicate is shared — do not
re-implement FR-12 here.

## Tests

- `searchChanges.test.ts` — text appearing **only** in conversation still matches (FR-10 acceptance); text only in a brain entity matches; stage filter; needsAttention filter; all three compose.
- `routes.search.test.ts` — supertest for the FR-10 conversation-only acceptance + `{ results }` shape.

## Rollback

Remove the mount + files; revert the commit.
