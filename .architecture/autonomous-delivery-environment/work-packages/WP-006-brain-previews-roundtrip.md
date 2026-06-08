---
# Identity (WP-01)
id: WP-006
title: "Journey F+E round-trip: open a change → see what the agent created (brain) + read a document rendered"
kind: full-round-trip
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: vertical-slice
slice_kind: round-trip
journey: "F — See what the agent has created (brain); E — Read a document rendered (previews)"

atomic_branch: yes
estimate: 11h
blast_radius: low
primitive: EXPAND-Create        # new brain route + BrainView component; previews REUSE the existing renderer
group: expand
visual_contract: WP-002

observed_acceptance:
  scenario: "dna:scenario:65JX0VABSE53NJJCVP8NQRTMXH"   # F — See what the agent has created
  also_exercises: "dna:scenario:00VX23T9WP4T6W7XXN39FMT6YH"   # E — Read a document rendered
  observable_result: "Inside a change, the founder sees the brain entities the agent created (requirements, workflows, designs, decisions) grouped by kind with a readable detail per item; and can open a renderable document (.md/.html) shown RENDERED, with a one-click toggle to the raw source."
  how_observed: "Run the real cockpit app against a change that has real brain entities. Open the change, open the Brain section. OBSERVE the entities grouped by kind with readable detail. Open a renderable file. OBSERVE it shows rendered; toggle to raw and back. Open a change with no brain entities; OBSERVE the plain empty note."
  not_sufficient: "Green CI / from-graph run alone do NOT satisfy the DoD. Only driving the app and seeing the grouped brain + the rendered document does."
  human_hops: "None — fully observable locally against a change with real brain entities (the from-graph CI run uses the seed-brain-entities-fixture; the human observation uses real entities)."

acceptance_criteria:
  - "DATA/ROUTE: GET /api/changes/:id/brain returns 200 + BrainView (groups by kind, empty groups omitted) for a known change; 404 unknown; empty change ⇒ {groups:[]} (FR-06). Each BrainEntity carries enough detail for the readable detail view (FR-07). Reached through the seam only (NFR-ARCH-01); reading it starts no claude process (FR-N4)"
  - "UI (brain): the Brain section lists the change's entities grouped by kind with a readable detail per item (FR-06/07); empty brain shows a plain note"
  - "UI (previews): renderable files (.md/.html) show a rendered view with a rendered/source toggle (FR-08/09) — REUSING the existing design-system VIEWER / contract-preview renderer (EP-03), NOT a new renderer"
  - "UI: both sit inside the coherent thread shell (WP-004); brain + files share one rail showing ONE section at a time (CL-02); consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
  - "OBSERVED ROUND-TRIP: with the app running, opening a change with real brain entities shows them grouped + a document rendered with a working raw toggle (scenarios F+E observable results), confirmed by driving the app"
test_plan:
  unit:
    - "apps/cockpit/server/tests/readBrain.test.ts (NEW) — grouping by kind; empty case"
  integration:
    - "apps/cockpit/server/tests/routes.brain.test.ts (NEW) — supertest; 200 grouped, 200 empty, 404; uses seed-brain-entities-fixture"
    - "apps/cockpit/client/src/tests/BrainView.test.tsx (NEW) — grouped render; empty note; detail open (FR-06/07)"
    - "apps/cockpit/client/src/tests/RenderedPreview.test.tsx (NEW) — rendered .md; toggle to raw and back (FR-08/09)"
  observed:
    - "MANUAL/DRIVEN (the gate): run server+client, open a change with real brain entities + a renderable file, OBSERVE grouped brain + rendered document + raw toggle per observed_acceptance.how_observed"
  verification:
    - "axe-core a11y on brain + preview surfaces green"
    - "branch-ci green"
    - "OBSERVED round-trip recorded — not just CI"
verification_gates: [unit, integration, component, visual_diff, a11y, observed_roundtrip]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.brain.test.ts"

infrastructure_needs:
  - id: seed-brain-entities-fixture
    why: "fixture brain entities so the brain view (FR-06/07) verifies from a fresh clone in CI; the human observation uses real entities"

derived_from:
  - finding: "Re-slice vertical: Journeys F + E. Folds prior horizontal WP-004 (brain route + readBrain) + WP-013 (BrainView + rendered previews UI) into ONE observable round-trip. Brain (F) and previews (E) ship together because both live in the thread brain/files rail and share the shell. TDD §5 rows 3+4; ADR-005; FR-06/07/08/09."
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: re-slice-vertical/2026-06-04
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-004]
# data contract + signed visual contract + the thread shell (WP-004) that hosts the brain/files sections

child_wps: []
kinds: null

verifies_scenario:
  - "dna:scenario:65JX0VABSE53NJJCVP8NQRTMXH"   # F
  - "dna:scenario:00VX23T9WP4T6W7XXN39FMT6YH"   # E

rollback: |
  New brain route + readBrain lib + BrainView component + RenderedPreview wiring
  (consuming the existing renderer) + useBrain hook. Remove the section mounts +
  route; revert the commit. Files panel reverts to current; the thread shell
  (WP-004) is unaffected.
---

# Journey F+E round-trip: see what the agent created + read a document rendered

## The round-trip this slice delivers

**Open a change → (action: open the Brain section / open a document) → OBSERVE:
the entities the agent created, grouped and readable; and a document shown
rendered with a one-click raw toggle.** The route and the UI that consumes it
ship together. F and E are one slice because both render inside the thread's
brain/files rail and share the WP-004 shell — splitting them would split a single
observable surface.

## What changes (the whole round-trip, one branch)

- **Route + lib (server):** `lib/readBrain.ts` (reads the change's brain entities,
  groups by kind, omits empty groups → `BrainView`); `routes/brain.ts`
  (`GET /api/changes/:id/brain`, reuses `_change-lookup` for 404). Read-only
  composition over the on-disk brain, same seam discipline as the transcript
  reads.
- **UI (client):** `components/BrainView.tsx` (grouped-by-kind list + detail;
  empty note); `api/useBrain.ts`; a small RenderedPreview wrapper +
  `components/FilesPanel.tsx` modification wiring the rendered/source toggle onto
  the **existing** renderer (reuse `ContractLinks` / Monaco + the VIEWER path —
  EP-03, no new renderer). Both hosted as named sections in the WP-004 thread
  shell (brain + files share one rail, one section at a time — CL-02).

## The observed-acceptance gate (MUST)

DoD = the **observed round-trip**: run the real app against a change with real
brain entities, open the Brain section and **see** them grouped with readable
detail; open a renderable file and **see** it rendered, toggle to raw and back;
open an empty change and **see** the plain note. Capture the driven-app evidence.
The from-graph runs for scenarios F and E (using `seed-brain-entities-fixture`
in CI) sit on top of the human observation.

**Human/third-party hops:** none — fully observable locally.

## Red / Green / Blue

- **Red:** failing `readBrain`, `routes.brain`, `BrainView`, `RenderedPreview`
  tests.
- **Green:** boring grouping; reuse the existing renderer for previews.
- **Blue:** confirm the preview reuses (does not fork) the renderer; tokens-only;
  **then drive the app and observe grouped brain + a rendered document**.

## Rollback

Remove the section mounts + route; revert. The thread shell is unaffected.
