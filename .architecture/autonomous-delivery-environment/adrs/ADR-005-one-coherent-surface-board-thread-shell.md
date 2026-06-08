# ADR-005 — One coherent surface: the board → thread shell, designed as a whole

- **Status:** accepted
- **Date:** 2026-06-03
- **Change:** CH-01KT50 · autonomous-delivery-environment
- **Deciders:** SEA (carries the founder's design-stage constraint)

## Context

The founder's standing instruction for this change: the app experience is
**"lumpy"**, and the design stage must fix it by treating the whole surface
— board, thread, chat, brain view, rendered previews, search — as **one
coherent thing**, not six features bolted on. Today the app has a flat
`Sidebar` + `Dashboard` grid + `ThreadView` with tabs; the six new
surfaces could each be added piecemeal, which is exactly what produced the
lumpiness.

## Decision

**Adopt a single two-level information architecture — the board as the
home, the thread as the one place a change lives — and route all six
surfaces through it, sharing one shell, one token system, one set of
state/empty/error patterns.**

1. **Board (home).** A stage-column Kanban replaces the flat card grid as
   the landing view. Columns are the six lifecycle stages in order
   (`recon → specify → design → implement → review → ship`). Cards are the
   existing `ChangeCard`, restyled to sit in a column. Search + the two
   filters (stage, needs-attention) live in one board toolbar — they
   narrow the *same* board, never a separate results screen.

2. **Thread (the change).** One change opens into one thread with a
   consistent left-to-right reading order: **stage track + plain-English
   status** at the top (always visible, the "where am I"), then the
   working area as named sections rather than disconnected tabs —
   **Conversation/chat**, **Brain**, **Files (with rendered preview)**.
   The chat composer is a persistent dock at the bottom of the thread, so
   "driving" is always one glance away from "reading".

3. **One design language.** Every new surface consumes
   `apps/cockpit/client/src/tokens.css` only — never a raw hex, never a
   bespoke font. Stage colour is one shared scale used identically in the
   board columns, the card badge, and the thread's stage track (today they
   are defined once in `StageBadge.module.css`; the board columns reuse it
   rather than inventing a parallel palette). Liveness and needs-attention
   use one shared indicator vocabulary across board and thread.

4. **One state-pattern set.** Loading skeleton, empty state, error+retry,
   and "server isn't running" (NFR-AVAIL-01) are designed once and reused
   on every surface, so the app never feels half-built in one corner.

This is the **VISUAL CONTRACT** the founder signs off before build: a
real-token mockup of the whole surface, rendered as it will look.

## Alternatives considered

- **Add each surface independently to the existing tabs (rejected).** This
  is the status quo that produced "lumpy". Six independently-styled
  additions is precisely what the founder asked us not to do.
- **A full rebuild of the shell (rejected — violates EP-03).** The
  existing `Shell`, `tokens.css`, `ChangeCard`, `StageBadge`,
  `LivenessDot`, Monaco viewer, and contract-preview renderer are
  battle-tested. We **extend and re-compose** them into the coherent IA,
  not rebuild. The coherence comes from shared tokens + shared patterns +
  one IA, not from new components.
- **Chat as a separate page/modal (rejected).** Detaching chat from the
  thread breaks the "reviewing becomes driving" thesis (north-star). Chat
  is part of the thread, docked, always present.

## Consequences

- The board becomes stage-columned; `Dashboard.tsx` is restyled, not
  replaced; `ChangeCard` gains column placement, not a rewrite.
- `ThreadView` gains the stage-track/status header and the brain section,
  re-homes chat as a persistent composer, and reuses the existing file
  viewer + contract-preview renderer for rendered previews (FR-08/09,
  EP-03).
- Rendered `.md`/`.html` previews **reuse the design-system VIEWER /
  `wpx-render-contract` path** already in the app rather than a new
  renderer (SRD FR-08/09 note).
- Brain-view grouping ships grouped-by-kind (FR-06 confirmed default); the
  visual pass refines ordering/surfacing within the one coherent design.
- The mockup at `mockups/SULIS-APP-surface.mockup.html` is the founder
  sign-off gate; it renders with the real tokens, fonts, and colours.
