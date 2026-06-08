---
id: WP-011
title: "Board: stage-column Kanban (refactor Dashboard) + states + tokens refresh"
kind: frontend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: surfaces

atomic_branch: yes
estimate: 8h
blast_radius: medium
primitive: REORGANISE-Refactor   # Dashboard.tsx → Board (characterisation test required)
group: reorganise
visual_contract: WP-002
characterisation_test: "apps/cockpit/client/src/tests/Dashboard.test.tsx (existing) — pinned green before refactor; Board behaviour added"
acceptance_criteria:
  - "Dashboard becomes the stage-column board: six columns recon→specify→design→implement→review→ship in order; each change card in its stage column (FR-01)"
  - "Each card shows handle, intent, stage, liveness (reuses ChangeCard, StageBadge, LivenessDot — EP-03 restyle, not rebuild) (FR-02)"
  - "Shipped changes do NOT appear as in-flight cards in the six columns (FR-15)"
  - "Empty board shows the empty state guiding how to start a change (FR-03); loading skeleton + error+retry reuse the one state-pattern set (ADR-005)"
  - "The board is scoped to the ACTIVE Product: it reads only the active Product's changes (server-side roll-up via WP-018) and never shows another Product's change (FR-37, ADR-009); single-Product Tenant is the trivial case; it hosts the product switcher (WP-024)"
  - "Surface consumes tokens.css only (no raw hex); tokens.css regenerated to the signed neutral-dominant + single-accent set first; matches the SIGNED visual contract (WP-002)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/client/src/tests/Board.test.tsx (NEW + the migrated Dashboard cases) — three changes at three stages land in three columns; shipped excluded; empty/loading/error states"
  verification:
    - "axe-core a11y on the board surface (e2e) green"
    - "branch-ci green"
verification_gates: [unit, component, visual_diff, a11y, perf_budget]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/Board.test.tsx"

derived_from:
  - finding: "ADR-005 board IA; TDD §2.2 Board REORGANISE-Refactor; FR-01/02/03/15"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-005-one-coherent-surface-board-thread-shell.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-018]    # contract types + SIGNED visual contract (#45 gate) + active-Product scope (server-side roll-up, ADR-009)
# AMENDED (expanded scope): now reads the ACTIVE Product (FR-37, ADR-009); hosts the product switcher (WP-024).

child_wps: []
kinds: null

verifies_scenario: "dna:scenario:Y6Z1EJPF6GY1BAQ96WGA86TDHS"   # See everything in flight at a glance

rollback: |
  Refactor of Dashboard.tsx + new StageColumn component + tokens.css regen.
  Characterisation test pins prior behaviour; revert the commit restores the
  flat grid.
---

# Board: stage-column Kanban (refactor Dashboard) + states + tokens refresh

## Why

ADR-005: the board is the home, a stage-column Kanban that reads left-to-right as
the lifecycle. This replaces the flat card grid that helped produce the "lumpy"
feel. EP-03: extend and recompose the shipped `ChangeCard` / `StageBadge` /
`LivenessDot` — do not rebuild.

This is **REORGANISE-Refactor** (Dashboard → Board), so a **characterisation
test** pins the current Dashboard behaviour green before the refactor (EP-07,
catalogue MUST).

## What changes

- `apps/cockpit/client/src/pages/Dashboard.tsx` → board layout (renamed/retitled Board per TDD §2.2).
- `apps/cockpit/client/src/components/StageColumn.tsx` (NEW) — one column per stage; reuses the StageBadge palette (no parallel palette).
- `apps/cockpit/client/src/tokens.css` (MODIFY) — regenerate to the signed neutral-dominant + single-accent set (the open token-refresh follow-up; the signed mockup is the colour source).
- Reuse EmptyState / skeleton / error+retry as the one state-pattern set.

## How

Group the existing `useChangesWithLiveness` data by stage client-side. **Amended
for the expanded scope:** `GET /api/changes` is now scoped to the **active
Product** server-side (WP-018, ADR-009) — the client receives only that
Product's changes and never filters cross-Product data itself (the seam owns
scope). The board hosts the product switcher (WP-024). Shipped filtered out of
the six columns (FR-15). Consume `tokens.css` only.

## Tests

`Board.test.tsx` — the migrated Dashboard cases + the new column-placement cases
(FR-01 acceptance: three stages → three columns in order), FR-15 exclusion, and
the four states. axe-core on the board.

## Scenario linkage

Verifies `dna:scenario:Y6Z1EJPF6GY1BAQ96WGA86TDHS` — "See everything in flight at a glance".

## Rollback

Revert the commit; the characterisation test guarantees the flat grid behaviour
is restorable.
