---
id: WP-004
title: "GET /api/changes/:id/brain — entities + workflows grouped by kind"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: reads

atomic_branch: yes
estimate: 4h
blast_radius: low
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "GET /api/changes/:id/brain returns 200 + BrainView (groups by kind, empty groups omitted) for a known change; 404 for unknown (FR-06)"
  - "Each BrainEntity carries enough detail for the readable detail view (FR-07)"
  - "Brain data is reached through the seam only — never the client filesystem (NFR-ARCH-01); reading it starts no claude process (FR-N4)"
  - "Empty case: a change with no brain entities returns { groups: [] } (FR-06 empty)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/readBrain.test.ts (NEW) — grouping by kind; empty case"
  integration:
    - "apps/cockpit/server/tests/routes.brain.test.ts (NEW) — supertest; 200 grouped, 200 empty, 404; uses seed-brain-entities-fixture"
  verification:
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.brain.test.ts"

derived_from:
  - finding: "TDD §5 surface map row 3 (brain); FR-06, FR-07; openapi.yaml /api/changes/{id}/brain + BrainView"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001]

child_wps: []
kinds: null

# Deferred infrastructure need surfaced by the SRD/TDD — needed for the integration test.
infrastructure_needs:
  - id: seed-brain-entities-fixture
    why: "fixture brain entities so the brain view verifies from a fresh clone (FR-06/07)"

rollback: |
  New route + one read lib + tests; not wired elsewhere. Remove the mount and
  files; revert the commit.

verifies_scenario: "dna:scenario:65JX0VABSE53NJJCVP8NQRTMXH"   # See what the agent has created
---

# GET /api/changes/:id/brain — entities + workflows grouped by kind

## Why

UC-03 / FR-06+FR-07: a change's brain (requirements, workflows, designs,
decisions the agent created) shown grouped by kind, read-only, each item with a
readable detail. Reached through the seam, never the client filesystem
(NFR-ARCH-01).

## What changes

- `apps/cockpit/server/lib/readBrain.ts` (NEW, EXPAND-Create) — reads the change's brain entities, groups by kind, omits empty groups, returns `BrainView`.
- `apps/cockpit/server/routes/brain.ts` (NEW, EXPAND-Create) — `router.get("/", …)`; mounted at `/api/changes/:id/brain`; reuses `_change-lookup` for 404.

## How

Read-only composition over the on-disk brain for the change (same seam
discipline as the transcript reads). Grouping-by-kind is the confirmed default
(FR-06); ordering refinement is the frontend visual pass's concern (WP-013), not
this WP's.

## Tests

- `readBrain.test.ts` — two requirements + one workflow ⇒ a requirements group of 2 and a workflows group of 1; no entities ⇒ `groups: []`.
- `routes.brain.test.ts` — supertest against the `seed-brain-entities-fixture` (deferred need): 200 grouped, 200 empty, 404 unknown.

## Rollback

Remove the mount + files; revert the commit.
