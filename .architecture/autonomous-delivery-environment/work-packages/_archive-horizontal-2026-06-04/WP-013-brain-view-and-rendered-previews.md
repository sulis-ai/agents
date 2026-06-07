---
id: WP-013
title: "Brain view (grouped) + rendered previews (reuse renderer) in the thread"
kind: frontend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: surfaces

atomic_branch: yes
estimate: 7h
blast_radius: low
primitive: EXPAND-Create        # new BrainView component; previews REUSE the existing renderer
group: expand
visual_contract: WP-002
acceptance_criteria:
  - "Brain section lists the change's entities grouped by kind, with a readable detail view per item (FR-06/07), from GET /api/changes/:id/brain"
  - "Empty brain shows a plain note (FR-06 empty)"
  - "Renderable files (.md/.html) show a rendered view with a rendered/source toggle (FR-08/09) — REUSING the existing design-system VIEWER / contract-preview renderer (EP-03), not a new renderer"
  - "Both sit inside the coherent thread shell (WP-012); brain + files share one rail showing ONE section at a time (CL-02); consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/client/src/tests/BrainView.test.tsx (NEW) — grouped render; empty note; detail open (FR-06/07)"
    - "apps/cockpit/client/src/tests/RenderedPreview.test.tsx (NEW) — rendered .md; toggle to raw and back (FR-08/09)"
  verification:
    - "axe-core a11y on brain + preview surfaces green"
    - "branch-ci green"
verification_gates: [unit, component, visual_diff, a11y, perf_budget]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/BrainView.test.tsx"

derived_from:
  - finding: "TDD §5 rows 3+4; FR-06/07/08/09; ADR-005 brain section + reuse renderer"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-004, WP-012]   # brain route + thread shell to host the section

child_wps: []
kinds: null

verifies_scenario: "dna:scenario:65JX0VABSE53NJJCVP8NQRTMXH"   # See what the agent has created
# Also exercises: dna:scenario:00VX23T9WP4T6W7XXN39FMT6YH (Read a document rendered)

rollback: |
  New BrainView + preview-wiring components consuming the existing renderer.
  Remove the section mounts; revert the commit. Files panel reverts to current.
---

# Brain view (grouped) + rendered previews (reuse renderer) in the thread

## Why

UC-03 + UC-04. The brain (requirements, workflows the agent created) shown
grouped by kind, read-only, with readable detail (FR-06/07); and renderable
files shown rendered with a raw toggle (FR-08/09). Per ADR-005 + EP-03, the
preview **reuses** the existing design-system VIEWER / `wpx-render-contract`
path already in the app — not a new renderer.

## What changes

- `apps/cockpit/client/src/components/BrainView.tsx` (NEW, EXPAND-Create) — grouped-by-kind list + detail; empty note.
- `apps/cockpit/client/src/api/useBrain.ts` (NEW) — query for `GET /api/changes/:id/brain`.
- `apps/cockpit/client/src/components/FilesPanel.tsx` (MODIFY) / a small RenderedPreview wrapper — wire the rendered/source toggle onto the existing renderer (reuse `ContractLinks` / Monaco + the VIEWER path).
- Both hosted as named sections in the WP-012 thread shell (brain + files share one rail, one section at a time — CL-02).

## How

Consume WP-004's brain endpoint and the existing contract-preview/VIEWER path.
No new renderer. Consume `tokens.css` only.

## Tests

`BrainView.test.tsx` (FR-06/07 grouped + empty + detail), `RenderedPreview.test.tsx`
(FR-08/09 rendered + toggle). axe-core on both.

## Rollback

Remove the section mounts; revert the commit.
