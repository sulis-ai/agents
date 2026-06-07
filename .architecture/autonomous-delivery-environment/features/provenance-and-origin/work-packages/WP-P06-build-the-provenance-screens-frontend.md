---
id: WP-P06
title: "Build the Provenance screens: dashboard → run-log → coverage-map (frontend)"
kind: frontend
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Create
group: expand
estimate: 9h
blast_radius: low
dependsOn: [WP-P01]
visual_contract: "contracts/visual/brain-redesign/provenance-prototype.html (approved)"
adr: [ADR-011, ADR-014]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ProvenanceDashboard.test.tsx"
estimated_token_cost: { input: "~30k", output: "~20k" }
status: pending
---

## Context
The founder-approved three-layer Provenance UI: the digest **dashboard** front
door (ship C), the **coverage-map** lens (B, built next), the **run-log** lens
(A, after) — per `_brain-brainstorm.md`. Consumer side; builds against the
WP-P01 mock parallel to WP-P05 (CF-05). Build target: the approved
`provenance-prototype.html`. Governed by `cognitive-load.md` (CL-01..06).

## Contract (the components this WP adds)
- `ProvenanceView.tsx` — the rail/route container; header "Provenance — what
  Sulis did, and why"; renders the dashboard, switches to a lens on a door click.
- `ProvenanceDashboard.tsx` — four plain-English tiles (what it did / covered /
  decided / flagged); the **flagged** tile carries the real gap + self-critique;
  two door-buttons (See the run log / See the coverage map) + a quiet "Browse
  everything (N)" link; empty + loading states.
- `RunLogLens.tsx` — vertical run timeline; expand a run → its steps; click a
  step → right detail rail (produced / gap / self-critique); worded outcome +
  worded confidence chip.
- `CoverageMapLens.tsx` — Why → What → How → Tested columns w/ count pills; the
  requirements column is the one searchable list; clicking a requirement draws a
  **single focused trace** (never an all-edges blob).
- `api/useProvenance.ts` — typed client over `GET …/provenance` (+ `?focus=`).

## Definition of Done
### Red
- [ ] `ProvenanceDashboard.test.tsx` etc. **fail** (components absent).
### Green
- [ ] Dashboard: four tiles + two doors + browse link; flagged tile shows the real gap; empty + loading states render.
- [ ] Run-log: run→steps→detail; worded outcome + worded confidence (never colour-alone).
- [ ] Coverage: four columns + count pills; focused trace per selected requirement; search scopes the requirements list.
- [ ] axe-core passes on each lens; worded status everywhere (WCAG 1.4.1).
### Blue
- [ ] ≤5 primary options at any point; progressive disclosure (dashboard→doors→detail) — CL-02/04.
- [ ] Tokens only, stage-palette tinting per kind; matches the approved prototype (L-13).
- [ ] Conforms to WP-P01 shapes verbatim (CF-06); the focused-trace fetch uses `?focus=` (server-side resolve, ADR-011).
