---
id: WP-012
title: "Thread shell: stage track + plain-English status header (refactor ThreadView)"
kind: frontend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: surfaces

atomic_branch: yes
estimate: 7h
blast_radius: medium
primitive: REORGANISE-Refactor   # ThreadView tabs → coherent one-shell sections (characterisation test)
group: reorganise
visual_contract: WP-002
characterisation_test: "apps/cockpit/client/src/tests/ThreadView.test.tsx (existing) — pinned green before refactor; coherent-shell behaviour added"
acceptance_criteria:
  - "Thread shows the six-stage track with the current stage marked, earlier done, later pending (FR-04)"
  - "Thread shows the plain-English read-time status header from GET /api/changes/:id/status (FR-05)"
  - "The thread is re-homed to the coherent reading order (stage track + status at top; Conversation / Brain / Files as named sections, chat docked) per ADR-005 — not disconnected tabs"
  - "Loading / 404-gone / error states reuse the one state-pattern set; consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/client/src/tests/ThreadView.test.tsx (EXTEND) — stage track marks current/done/pending; status header renders the headline + needs-attention; gone/loading/error"
    - "apps/cockpit/client/src/tests/StageTrack.test.tsx (NEW)"
    - "apps/cockpit/client/src/tests/StatusHeader.test.tsx (NEW)"
  verification:
    - "axe-core a11y on the thread surface green"
    - "branch-ci green"
verification_gates: [unit, component, visual_diff, a11y, perf_budget]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ThreadView.test.tsx"

derived_from:
  - finding: "ADR-005 thread IA; TDD §2.2 ThreadView REORGANISE-Refactor; FR-04/05"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-005-one-coherent-surface-board-thread-shell.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-003]    # status route supplies the header data

child_wps: []
kinds: null

verifies_scenario: "dna:scenario:1PB20WWQY89W9GTE9HKS45YP06"   # Understand where a change is

rollback: |
  Refactor of ThreadView + two new presentational components. Characterisation
  test pins prior tab behaviour; revert the commit restores it.
---

# Thread shell: stage track + plain-English status header (refactor ThreadView)

## Why

ADR-005: a change lives in one thread with a consistent reading order — stage
track + status at the top (the "where am I"), then the working area as named
sections rather than disconnected tabs. This is the spine the chat dock (WP-015)
and the brain/files sections (WP-013) plug into. **REORGANISE-Refactor**, so a
characterisation test pins ThreadView's current behaviour first (EP-07).

## What changes

- `apps/cockpit/client/src/pages/ThreadView.tsx` (MODIFY) — re-home tabs into the coherent shell; mount the stage track + status header above the working area.
- `apps/cockpit/client/src/components/StageTrack.tsx` (NEW) — six stages, current marked, reusing the StageBadge palette + the colour-independent indicators from the visual contract.
- `apps/cockpit/client/src/components/StatusHeader.tsx` (NEW) — renders `ChangeStatus.headline` + the needs-attention badge.
- `apps/cockpit/client/src/api/useStatus.ts` (NEW) — TanStack query for `GET /api/changes/:id/status`.

## How

Consume WP-003's status endpoint. Keep the existing Chat (transcript) + Files
panels as sections; WP-015 later replaces the read-only Chat dock with the
two-way composer. Consume `tokens.css` only.

## Tests

`StageTrack.test.tsx`, `StatusHeader.test.tsx`, and the extended
`ThreadView.test.tsx` (FR-04 current/done/pending; FR-05 header). axe-core on the
thread.

## Rollback

Revert the commit; characterisation test guarantees the tab behaviour is
restorable.
