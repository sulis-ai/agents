# ADR-014 — Provenance replaces the Brain front door (deprecate-then-delete the flat view)

- **Status:** accepted
- **Date:** 2026-06-05
- **Change:** CH-01KT50 · feature: provenance-and-origin
- **Deciders:** SEA

## Decision

The Provenance design **replaces** the current flat group-by-kind front door.
Concretely:

- **Rename Brain → Provenance** in the left nav, the route, and the header line
  ("Provenance — what Sulis did, and why").
- The new front door is `ProvenanceDashboard` (digest tiles), with the
  run-log and coverage-map as its two doors (the brainstorm's **ship C, then B,
  then A**).
- `BrainView.tsx` + `BrainSection.tsx` (the flat client front door) are
  **deprecated then deleted** within this feature set — they are production-
  reachable client code, so **deprecate-before-delete** (change-primitives MUST):
  the new ProvenanceView lands and is observed first; the old components are
  removed in the same slice once the replacement is wired, not left as dead code.

The **server `…/brain` endpoint and `readBrain` stay** — the provenance
projection composes them (ADR-011). Only the **client front door** is replaced.

## Why this is the convention

The founder-approved brainstorm explicitly chose the summary-first dashboard
(C) as the front door with run-log (A) and coverage-map (B) as its two depths,
resolving the A-vs-B tension. Building the dashboard *alongside* the flat view
would leave two competing front doors — the exact thing the design rejects. The
flat view has no remaining job once the dashboard ships.

## Alternatives considered

- **Keep `BrainView` as a fourth "browse everything" view (partially adopted).**
  The design keeps a quiet subordinate "Browse everything (N items)" link — but
  that is a *subordinate link off the dashboard*, not the front door, and can
  reuse the grouped list internally without `BrainView` being the entry point.
  Keeping the old component as a co-equal view is rejected; reusing its grouped-
  list rendering behind the subordinate link is fine.
- **Leave `BrainView` in place, dead (rejected).** Dead production code rots and
  confuses the next reader. Deprecate-then-delete in the same slice.

## Consequences

- One `SUBSTITUTE-Replace` (the client front door) + a deprecate-then-delete of
  two components, recorded here and gated by the new ProvenanceView being
  observed first.
- The nav/route rename is a small, mechanical change; the header copy is the
  approved "Provenance — what Sulis did, and why".
