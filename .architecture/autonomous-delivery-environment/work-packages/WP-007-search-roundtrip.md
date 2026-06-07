---
# Identity (WP-01)
id: WP-007
title: "Journey D round-trip: type in the search/filter bar → the board narrows to matching changes"
kind: full-round-trip
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: vertical-slice
slice_kind: round-trip
journey: "D — Find a change"

atomic_branch: yes
estimate: 9h
blast_radius: low
primitive: EXPAND-Create
group: expand
visual_contract: WP-002

observed_acceptance:
  scenario: "dna:scenario:CP3MAX93563W45W7D547T5FJ80"   # D — Find a change
  observable_result: "The founder types into the board's search box (or picks a stage / needs-attention filter) and the SAME board narrows to the matching changes — search hits content (conversation + created artifacts), not just titles; clearing restores the full board."
  how_observed: "Run the real cockpit app against a store with several changes. Type a word that appears ONLY in one change's conversation (not its title); OBSERVE the board narrows to that change. Pick a stage filter; OBSERVE only that stage's changes remain. Pick needs-attention; OBSERVE only flagged changes remain. Clear; OBSERVE the full board returns. Confirm filters compose."
  not_sufficient: "Green CI / from-graph run alone do NOT satisfy the DoD. Only typing in the running app and watching the board narrow does."
  human_hops: "None — fully observable locally."

acceptance_criteria:
  - "DATA/ROUTE: GET /api/search?q= matches change CONTENT (conversation + created entities/artifacts), not just handle/intent/stage (FR-10); ?stage=design&stage=ship filters to those stages (FR-11, repeated param → array); ?needsAttention=true returns only blocked/waiting-on-decision/stopped-mid-reply, not idle-but-fine (FR-12 — REUSES needsAttention.ts from WP-004, single source of truth); filters compose; response { results: Change[] }; GET-only, gate green, starts no process (FR-N4). Search operates WITHIN the active Product's set (trivial single-Product case; full scope is WP-008)"
  - "UI: a single board toolbar hosts the search box + stage filter + needs-attention filter; they narrow the SAME board, never a separate results screen (ADR-005)"
  - "UI: search by content narrows the board (FR-10); stage filter (FR-11); needs-attention filter (FR-12); filters compose; clearing restores the full board; consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
  - "OBSERVED ROUND-TRIP: with the app running, typing a conversation-only term narrows the board to that change and filters compose/clear (scenario-D observable result), confirmed by driving the app"
test_plan:
  unit:
    - "apps/cockpit/server/tests/searchChanges.test.ts (NEW) — content match (conversation-only + entity-only hits); stage filter; needsAttention filter; composition"
  integration:
    - "apps/cockpit/server/tests/routes.search.test.ts (NEW) — supertest; the FR-10 conversation-only-text acceptance + {results} shape"
    - "apps/cockpit/client/src/tests/SearchBar.test.tsx (NEW) — content search narrows; stage filter; needs-attention filter; compose + clear"
  observed:
    - "MANUAL/DRIVEN (the gate): run server+client, type a conversation-only term + apply filters, OBSERVE the board narrow/compose/clear per observed_acceptance.how_observed"
  verification:
    - "axe-core a11y on the board toolbar green"
    - "branch-ci green"
    - "OBSERVED round-trip recorded — not just CI"
verification_gates: [unit, integration, component, visual_diff, a11y, observed_roundtrip]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.search.test.ts"

derived_from:
  - finding: "Re-slice vertical: Journey D (search). Folds prior horizontal WP-005 (search route + searchChanges) + WP-014 (SearchBar/filter UI) into ONE observable round-trip. TDD §5 row 5; ADR-005 one board toolbar narrows the same board; FR-10/11/12."
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: re-slice-vertical/2026-06-04
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-003, WP-004]
# data contract + visual contract + the board it narrows (WP-003) + needsAttention.ts from the status slice (WP-004)

child_wps: []
kinds: null

verifies_scenario: "dna:scenario:CP3MAX93563W45W7D547T5FJ80"   # D

rollback: |
  New search route + searchChanges lib + SearchBar/NeedsAttentionFilter
  components + useSearch hook in the board toolbar. Remove them; the board reverts
  to unfiltered; remove the route. needsAttention.ts (from WP-004) is untouched.
  Revert the commit.
---

# Journey D round-trip: search/filter → the board narrows

## The round-trip this slice delivers

**Type in the search/filter bar → (action: type a term / pick a filter) →
OBSERVE: the SAME board narrows to the matching changes.** The search route and
the toolbar that drives it ship together. Per ADR-005 the filters narrow the
*same* board — there is no separate results screen — so the consumption half is
the board itself, already built in journey A (WP-003).

## What changes (the whole round-trip, one branch)

- **Route + lib (server):** `lib/searchChanges.ts` (`(changes, transcripts, brain,
  {q, stage[], needsAttention}) → Change[]`; **reuses `needsAttention.ts` from
  WP-004** so FR-12 lives in one place; content match scans conversation +
  created-entity text, not just labels — FR-10); `routes/search.ts`
  (`GET /api/search`). Search operates within the active Product's set (trivial
  single-Product case here; full scope ships in journey K, WP-008).
- **UI (client):** `components/SearchBar.tsx` (search box + stage filter chips);
  `components/NeedsAttentionFilter.tsx`; `api/useSearch.ts` (q / stage[] /
  needsAttention). The board (WP-003) renders the results in the same column
  layout when filters are active. Filter chips use the neutral-inverse active
  state from the visual contract (no brand fill).

## The observed-acceptance gate (MUST)

DoD = the **observed round-trip**: run the real app, type a term that appears
**only** in one change's conversation and **watch** the board narrow to it; apply
stage + needs-attention filters and watch them compose; clear and watch the full
board return. Capture the driven-app evidence. The from-graph run for scenario D
sits on top of the human observation.

**Human/third-party hops:** none — fully observable locally.

## Red / Green / Blue

- **Red:** failing `searchChanges`, `routes.search`, `SearchBar` tests
  (FR-10 conversation-only match the keystone).
- **Green:** boring content scan composing existing reads; reuse needsAttention.
- **Blue:** confirm FR-12 is not re-implemented (reuse WP-004's predicate);
  tokens-only; **then drive the app and watch the board narrow**.

## Rollback

Remove the components + route; board reverts to unfiltered. Revert.
