---
# Identity (WP-01)
id: WP-004
title: "Journey B round-trip: open a change → see where it is (stage track + plain-English status)"
kind: full-round-trip
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: vertical-slice
slice_kind: round-trip
journey: "B — Understand where a change is"

atomic_branch: yes
estimate: 11h
blast_radius: medium
primitive: REORGANISE-Refactor   # ThreadView tabs → coherent one-shell sections (characterisation test)
group: reorganise
visual_contract: WP-002
characterisation_test: "apps/cockpit/client/src/tests/ThreadView.test.tsx (existing) — pinned green before refactor; coherent-shell behaviour added"

observed_acceptance:
  scenario: "dna:scenario:1PB20WWQY89W9GTE9HKS45YP06"   # B — Understand where a change is
  observable_result: "The founder opens a change from the board and sees a six-stage track with the current stage marked (earlier done, later pending) and a plain-English 'what's happening' status header — and, when relevant, a needs-attention badge."
  how_observed: "Run the real cockpit app. Click a real change from the board to open its thread. OBSERVE the stage track marks the change's actual current stage, and the status header shows a human-readable status derived at read time. Seed a blocked/waiting change; OBSERVE the needs-attention badge appears. Seed an idle-but-fine change; OBSERVE it is NOT flagged."
  not_sufficient: "Green CI / deploy / from-graph scenario run alone do NOT satisfy the DoD. Only opening a real change in the running app and seeing its stage + status does."
  human_hops: "None — fully observable by driving the local app against a real change store."

acceptance_criteria:
  - "DATA/ROUTE: GET /api/changes/:id/status returns 200 + ChangeStatus for a known change; 404 + {error,code:NOT_FOUND} for unknown. lib/computeStatus.ts derives the plain-English headline at READ time from the change record + conversation/journal — never from a stored periodic post (FR-05). lib/needsAttention.ts flags blocked OR waiting-on-decision OR stopped-mid-reply; idle-but-fine is NOT flagged (FR-12). GET-only; read-only gate green; no claude process starts on this read (NFR-SEC-05/FR-N4)"
  - "UI: the thread shows the six-stage track with current marked, earlier done, later pending (FR-04), and the plain-English status header from the status route (FR-05); the needs-attention badge renders when flagged"
  - "UI: the thread is re-homed to the coherent reading order (stage track + status at top; Conversation / Brain / Files as named sections) per ADR-005 — not disconnected tabs; loading / 404-gone / error states reuse the one state-pattern set; consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
  - "OBSERVED ROUND-TRIP: with the app running, opening a real change shows its actual stage on the track and a real plain-English status (the scenario-B observable result), confirmed by driving the app"
test_plan:
  unit:
    - "apps/cockpit/server/tests/computeStatus.test.ts (NEW) — headline for representative states (design-in-progress, blocked, waiting-on-decision)"
    - "apps/cockpit/server/tests/needsAttention.test.ts (NEW) — the three flagged reasons each flag; idle-but-fine does NOT (FR-12)"
  integration:
    - "apps/cockpit/server/tests/routes.status.test.ts (NEW) — supertest vs createApp with FakeChangeStoreReader; 200 shape + 404"
    - "apps/cockpit/client/src/tests/ThreadView.test.tsx (EXTEND) — stage track marks current/done/pending; status header renders headline + needs-attention; gone/loading/error"
    - "apps/cockpit/client/src/tests/StageTrack.test.tsx (NEW); apps/cockpit/client/src/tests/StatusHeader.test.tsx (NEW)"
  observed:
    - "MANUAL/DRIVEN (the gate): run server+client, open a real change, OBSERVE stage track + plain-English status + needs-attention badge per observed_acceptance.how_observed"
  verification:
    - "axe-core a11y on the thread surface green"
    - "branch-ci green"
    - "OBSERVED round-trip recorded — not just CI"
verification_gates: [unit, integration, component, visual_diff, a11y, observed_roundtrip]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.status.test.ts"
  # the UI half is verified by ThreadView/StageTrack/StatusHeader frontend tests + the observed round-trip

derived_from:
  - finding: "Re-slice vertical: Journey B (status READ). Folds prior horizontal WP-003 (status route + computeStatus/needsAttention libs) + WP-012 (thread shell stage-track/status-header UI) into ONE observable round-trip. ADR-005 thread IA; FR-04/05/12."
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-005-one-coherent-surface-board-thread-shell.md
    severity_at_discovery: n/a
generated_by:
  activity: re-slice-vertical/2026-06-04
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-003]
# data contract + signed visual contract + the board you open the change FROM (WP-003)

child_wps: []
kinds: null

verifies_scenario: "dna:scenario:1PB20WWQY89W9GTE9HKS45YP06"   # B

rollback: |
  New status route + two pure libs (computeStatus, needsAttention) + the
  ThreadView refactor + two presentational components (StageTrack, StatusHeader)
  + useStatus hook. Characterisation test pins prior tab behaviour; revert the
  commit restores the tabs and removes the route. needsAttention.ts is reused by
  journey D (search) — do not remove it there.
---

# Journey B round-trip: open a change → see where it is

## The round-trip this slice delivers

**Open a change from the board → (action: click it) → OBSERVE: a marked stage
track + a plain-English status of what's happening.** The consumption half (the
thread shell that renders the stage track and status header) ships in the SAME
slice as the status route that feeds it — they cannot drift apart.

It builds directly on journey A: the board (WP-003) is what you open the change
*from*, so this slice depends on it.

## What changes (the whole round-trip, one branch)

- **Route + libs (server):** `lib/computeStatus.ts` (pure: record + transcript →
  headline, read-time); `lib/needsAttention.ts` (pure: record + signals →
  `{flagged, reason}`; reason ∈ blocked|waiting-on-decision|stopped-mid-reply|null;
  idle-but-fine ⇒ not flagged); `routes/status.ts` (`GET /api/changes/:id/status`,
  reuses `_change-lookup` for 404). Composes existing reads — no new port.
- **UI (client):** `pages/ThreadView.tsx` re-homed to the coherent shell (stage
  track + status header above named Conversation/Brain/Files sections — not tabs);
  `components/StageTrack.tsx` (six stages, current marked, reuses the StageBadge
  palette + colour-independent indicators); `components/StatusHeader.tsx` (renders
  the headline + needs-attention badge); `api/useStatus.ts` (query for the route).

**REORGANISE-Refactor** (ThreadView tabs → coherent shell), so a characterisation
test pins ThreadView's current behaviour first (EP-07).

`needsAttention.ts` is the single source of truth for FR-12 — journey D (search,
WP-006) reuses it; do not re-implement it there.

## The observed-acceptance gate (MUST)

DoD = the **observed round-trip**: run the real app, open a real change, and
**see** its actual stage on the track and a real plain-English status. Seed a
blocked change and see the needs-attention badge; seed an idle-but-fine change
and see it is NOT flagged. Capture the driven-app evidence. The from-graph
`sulis-verify-acceptance --scenario dna:scenario:1PB20WWQY89W9GTE9HKS45YP06` run
sits on top of the human observation, not instead of it.

**Human/third-party hops:** none — fully observable locally.

## Red / Green / Blue

- **Red:** pin `ThreadView.test.tsx` (characterisation); write failing
  `computeStatus`, `needsAttention`, `routes.status`, `StageTrack`, `StatusHeader`
  tests.
- **Green:** boring read-time status; pure attention predicate; coherent shell.
- **Blue:** factor the status header + stage track cleanly into the shell;
  confirm tokens-only; **then drive the app and observe stage + status**.

## Rollback

Revert; characterisation test guarantees the tab behaviour is restorable.
