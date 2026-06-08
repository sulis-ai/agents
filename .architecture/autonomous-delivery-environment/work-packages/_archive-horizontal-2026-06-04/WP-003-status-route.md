---
id: WP-003
title: "GET /api/changes/:id/status — plain-English read-time status"
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
  - "GET /api/changes/:id/status returns 200 + ChangeStatus for a known change; 404 + {error,code:NOT_FOUND} for an unknown id"
  - "lib/computeStatus.ts derives the plain-English headline at read time from the change record + conversation/journal — never from a stored periodic post (FR-05)"
  - "lib/needsAttention.ts flags blocked OR waiting-on-decision OR stopped-mid-reply; idle-but-fine is NOT flagged (FR-12)"
  - "The route is GET-only; read-only gate stays green; no claude process starts on this read (NFR-SEC-05/FR-N4)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/computeStatus.test.ts (NEW)"
    - "apps/cockpit/server/tests/needsAttention.test.ts (NEW) — the three flagged reasons + the idle-but-fine non-flag"
  integration:
    - "apps/cockpit/server/tests/routes.status.test.ts (NEW) — supertest against createApp with FakeChangeStoreReader; 200 + 404"
  verification:
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.status.test.ts"

derived_from:
  - finding: "TDD §5 surface map row 2 (status); FR-05, FR-12; openapi.yaml /api/changes/{id}/status + ChangeStatus"
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

rollback: |
  New route + two pure lib files + tests; not wired into any other path.
  Remove the app.use mount and the files. Revert the commit.

# Scenario linkage (from-graph verification)
verifies_scenario: "dna:scenario:1PB20WWQY89W9GTE9HKS45YP06"   # Understand where a change is
---

# GET /api/changes/:id/status — plain-English read-time status

## Why

UC-02 / FR-04+FR-05: opening a change shows a marked stage track and a
human-readable "what's happening" status. The status is computed **on read**
from the change's state + conversation/journal — the periodic auto-publish beat
is a non-goal (SRD Non-goals). FR-12's "needs attention" rule lives here too
because the board search/filter (WP-005) and the thread status header (WP-012)
both consume it.

## What changes

- `apps/cockpit/server/lib/computeStatus.ts` (NEW, EXPAND-Create) — pure: `(record, transcript/journal) → ChangeStatus.headline`.
- `apps/cockpit/server/lib/needsAttention.ts` (NEW, EXPAND-Create) — pure: `(record, signals) → { flagged, reason }`. Reason ∈ blocked | waiting-on-decision | stopped-mid-reply | null. Idle-but-fine ⇒ `{ flagged: false, reason: null }`.
- `apps/cockpit/server/routes/status.ts` (NEW, EXPAND-Create) — `router.get("/", …)`; mounted at `/api/changes/:id/status` in `server/app.ts`; reuses `_change-lookup` for the 404 path and the existing transcript-location read.

## How

Compose existing reads (`ChangeStoreReader.readChangeRecord` + the existing
transcript locate/parse). No new port — reads only (TDD §2.1). The headline is
deterministic given the same inputs so the unit test pins it.

## Tests

- `computeStatus.test.ts` — headline for representative states (design-in-progress, blocked, waiting-on-decision).
- `needsAttention.test.ts` — the three flagged reasons each flag; an idle-but-fine change does NOT (FR-12 acceptance, verbatim).
- `routes.status.test.ts` — supertest: 200 + shape for a seeded change; 404 for unknown.

## Rollback

Remove the mount + files; revert the commit.
