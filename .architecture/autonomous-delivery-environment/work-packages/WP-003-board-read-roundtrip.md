---
# Identity (WP-01)
id: WP-003
title: "Journey A round-trip: open the app → see every in-flight change on the stage board"
kind: full-round-trip
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: vertical-slice
slice_kind: round-trip
journey: "A — See everything in flight at a glance"

# Scope (WP-02..04)
atomic_branch: yes
estimate: 10h
blast_radius: medium
# Spans data + (read scope) + UI. The proves-the-pattern slice.
primitive: REORGANISE-Refactor   # Dashboard.tsx → stage-column Board (characterisation test required)
group: reorganise
visual_contract: WP-002
characterisation_test: "apps/cockpit/client/src/tests/Dashboard.test.tsx (existing) — pinned green before refactor; Board behaviour added"

# THE OBSERVED-ACCEPTANCE GATE (MUST)
observed_acceptance:
  scenario: "dna:scenario:Y6Z1EJPF6GY1BAQ96WGA86TDHS"   # A — See everything in flight
  observable_result: "The founder opens the running cockpit app and sees their real in-flight changes laid out in six stage columns (recon→specify→design→implement→review→ship), each change in its column, shipped ones not shown as in-flight."
  how_observed: "Run the real cockpit app (server + client) against a real change store with at least one in-flight change at a known stage. Open http://127.0.0.1:<port>/ in a browser. OBSERVE the change appears as a card in the correct stage column. Move/seed a second change at a different stage; OBSERVE it lands in its column. Confirm a shipped change does NOT appear as an in-flight card."
  not_sufficient: "Green CI, green deploy, and a green `sulis-verify-acceptance --scenario` run are NOT sufficient on their own. The DoD is satisfied only by driving the app and seeing the board render the real changes."
  human_hops: "None — this round-trip is fully observable by running the local app. No live claude session, no third-party hop."

acceptance_criteria:
  - "DATA: the slice reads the active Product's change set server-side (a minimal scope roll-up; the single-Product Tenant is the trivial case — one Product, implicitly active). The board never receives another Product's change (FR-37 honoured for the trivial case; the switcher itself is journey K, WP-008)."
  - "UI: Dashboard becomes the stage-column board — six columns recon→specify→design→implement→review→ship in order; each change card (handle, intent, stage, liveness) in its stage column, reusing ChangeCard/StageBadge/LivenessDot (EP-03 restyle, not rebuild) (FR-01, FR-02)"
  - "UI: shipped changes do NOT appear as in-flight cards (FR-15); empty board shows the empty state guiding how to start a change (FR-03); loading skeleton + error+retry reuse the one state-pattern set (ADR-005)"
  - "UI: consumes tokens.css only (no raw hex), regenerated to the signed neutral-dominant + single-accent set; matches the SIGNED visual contract (WP-002)"
  - "OBSERVED ROUND-TRIP: with the app running against a real store, opening the app shows the real changes in their stage columns (the scenario-A observable result), confirmed by driving the app — not by unit-green alone"
test_plan:
  unit:
    - "apps/cockpit/client/src/tests/Board.test.tsx (NEW + the migrated Dashboard cases) — three changes at three stages → three columns in order; shipped excluded; empty/loading/error states"
  integration:
    - "apps/cockpit/server/tests/routes.changes.test.ts (EXTEND) — GET /api/changes returns the active Product's change set (trivial single-Product case returns all); shape unchanged"
  observed:
    - "MANUAL/DRIVEN (the gate): run server+client, open the app, OBSERVE real changes in stage columns per observed_acceptance.how_observed"
  verification:
    - "axe-core a11y on the board surface (e2e) green"
    - "branch-ci green"
    - "OBSERVED round-trip recorded (screenshot / driven-app capture) — not just CI"
verification_gates: [unit, component, visual_diff, a11y, observed_roundtrip]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/Board.test.tsx"

# Lineage (WP-06)
derived_from:
  - finding: "Re-slice vertical: Journey A (board READ). Folds prior horizontal WP-011 (board UI) + the read half of WP-018 (server-side Product scope, trivial case) + GET /api/changes into ONE observable round-trip. ADR-005 board IA; ADR-009 server-side scope; FR-01/02/03/15/37."
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-005-one-coherent-surface-board-thread-shell.md
    severity_at_discovery: n/a
generated_by:
  activity: re-slice-vertical/2026-06-04
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

# Lifecycle (WP-07)
status: pending
depends_on: [WP-001, WP-002]   # data contract + SIGNED visual contract (#45 gate)

child_wps: []
kinds: null

verifies_scenario: "dna:scenario:Y6Z1EJPF6GY1BAQ96WGA86TDHS"   # A

rollback: |
  Refactor of Dashboard.tsx + new StageColumn component + a minimal read-scope
  helper + tokens.css regen. The characterisation test pins prior Dashboard
  behaviour; revert the commit restores the flat grid. GET /api/changes returns
  to unscoped (trivial — single Product).
---

# Journey A round-trip: open the app → see every in-flight change on the stage board

## The round-trip this slice delivers

**Open the app → (action: just open it) → OBSERVE: your real in-flight changes,
laid out by stage.** This is the thinnest fully-observable round-trip in the
plan and it is sequenced FIRST: it proves the vertical pattern end-to-end with
the least external dependency. There is no live agent, no third-party hop — the
founder runs the local app and immediately sees real data rendered.

It deliberately folds together what the old horizontal plan split across a route
WP and a UI WP (and an integration WP at the very end): the data read, its
server-side scope (trivial single-Product case), and the board UI that consumes
it — so the consumption half cannot go missing.

## Why this is FIRST and thinnest

- **Fully observable by just running the app** — no `claude` session, no recorded
  fixture needed for the human to see the result. Seed a real change, open the
  app, see it on the board.
- **Proves the vertical seam** — data contract (WP-001) → existing
  `GET /api/changes` (lightly scoped) → React board. Every later slice reuses
  this exact shape (data → route → UI in one branch, observed by driving).
- **Lowest risk** — it's a refactor of an existing read surface plus a thin scope
  helper, not a new write path or a new external process.

## What changes (the whole round-trip, one branch)

- **Data/scope (server):** a minimal active-Product scope on `GET /api/changes`.
  For this slice the single-Product Tenant is the trivial case (one Product,
  implicitly active) — the full `productScope` roll-up and the switcher ship in
  journey K (WP-008). The seam owns scope so the client never filters
  cross-Product data (ADR-009, NFR-ARCH-01).
- **UI (client):** `pages/Dashboard.tsx` → stage-column board (renamed/retitled
  Board, TDD §2.2); new `components/StageColumn.tsx` (reuses the StageBadge
  palette — no parallel palette); `tokens.css` regenerated to the signed
  neutral-dominant + single-accent set. Reuse EmptyState / skeleton / error+retry
  as the one state-pattern set. Group `useChangesWithLiveness` data by stage.

This is **REORGANISE-Refactor** (Dashboard → Board), so a **characterisation
test** pins the current Dashboard behaviour green before the refactor (EP-07,
catalogue MUST).

## The observed-acceptance gate (MUST — this is the Definition of Done)

Green CI is necessary but **not** the DoD. The DoD is the **observed round-trip**:
run the real cockpit app against a real change store, open it in a browser, and
**see** the in-flight changes in their stage columns — scenario A's observable
result. Capture the driven-app evidence (screenshot). Then the from-graph
`sulis-verify-acceptance --scenario dna:scenario:Y6Z1EJPF6GY1BAQ96WGA86TDHS`
run is the recorded acceptance on top of the human observation — never instead of
it.

**Human/third-party hops:** none. This slice is fully observable locally.

## Red / Green / Blue

- **Red:** pin `Dashboard.test.tsx` (characterisation, current flat-grid
  behaviour) green; write the failing `Board.test.tsx` column-placement cases and
  the failing `routes.changes.test.ts` scope-case.
- **Green:** boring stage-column layout grouping existing data; minimal read
  scope; reuse existing card/badge/dot/state components. Make the tests pass.
- **Blue:** extract the StageColumn + the read-scope helper cleanly (the scope
  helper is the seed journey K's `productScope` extends); confirm tokens.css is
  the only colour source; **then drive the app and observe the board**.

## Rollback

Revert the commit; the characterisation test guarantees the flat grid is
restorable.
