---
id: WP-014
title: "Board toolbar: search + stage filter + needs-attention filter"
kind: frontend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: surfaces

atomic_branch: yes
estimate: 5h
blast_radius: low
primitive: EXPAND-Create
group: expand
visual_contract: WP-002
acceptance_criteria:
  - "A single board toolbar hosts the search box + stage filter + needs-attention filter; they narrow the SAME board, never a separate results screen (ADR-005)"
  - "Search by content narrows the board to changes matching conversation/artifact text (FR-10), driven by GET /api/search"
  - "Stage filter narrows to selected stage(s) (FR-11); needs-attention filter shows only blocked/waiting-on-decision/stopped-mid-reply (FR-12)"
  - "Filters compose; clearing them restores the full board; consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/client/src/tests/SearchBar.test.tsx (NEW) — content search narrows; stage filter; needs-attention filter; compose + clear"
  verification:
    - "axe-core a11y on the board toolbar green"
    - "branch-ci green"
verification_gates: [unit, component, visual_diff, a11y, perf_budget]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/SearchBar.test.tsx"

derived_from:
  - finding: "TDD §5 row 5; FR-10/11/12; ADR-005 one board toolbar narrows the same board"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-005, WP-011]   # search route + the board to narrow

child_wps: []
kinds: null

verifies_scenario: "dna:scenario:CP3MAX93563W45W7D547T5FJ80"   # Find a change

rollback: |
  New SearchBar + NeedsAttentionFilter components in the board toolbar. Remove
  them; the board reverts to unfiltered. Revert the commit.
---

# Board toolbar: search + stage filter + needs-attention filter

## Why

UC-05 / FR-10..12. The founder finds a change by content and narrows the board
by stage and "needs attention". Per ADR-005 these live in **one** board toolbar
and narrow the *same* board — there is no separate results screen.

## What changes

- `apps/cockpit/client/src/components/SearchBar.tsx` (NEW, EXPAND-Create) — search box + stage filter chips.
- `apps/cockpit/client/src/components/NeedsAttentionFilter.tsx` (NEW, EXPAND-Create).
- `apps/cockpit/client/src/api/useSearch.ts` (NEW) — query for `GET /api/search` with q / stage[] / needsAttention.
- Board (WP-011) renders the search results in the same column layout when filters are active.

## How

Consume WP-005's search endpoint. Filter chips use the neutral-inverse active
state from the visual contract (no brand fill). Consume `tokens.css` only.

## Tests

`SearchBar.test.tsx` — FR-10 content-search narrowing, FR-11 stage filter,
FR-12 needs-attention filter, composition + clear. axe-core on the toolbar.

## Rollback

Remove the components; board reverts to unfiltered. Revert the commit.
