# ADR-004 — The mobile lane switcher reuses the existing stage chips as an ARIA tablist

> **Status:** accepted
> **Date:** 2026-06-09
> **Deciders:** SEA (from the signed-off design)

## Context

The signed-off design (IDEAS.md, Concern 4) defines three responsive
breakpoints:

| Name | Width | Layout |
|---|---|---|
| Desktop | ≥ 1100px | six full-height lanes side by side |
| Tablet | 600–1099px | lanes scroll horizontally at a comfortable min-width (~260px) |
| Mobile | < 600px | **one full-width lane at a time**, the stage chips become the lane switcher |

On mobile the design is explicit: the existing Recon/Specify/Design/Implement/
Review/Ship stage chips become the **lane switcher** — tap a chip → that lane
snaps into view; the chips are real **tabs** (`role="tab"` / `aria-selected`
inside `role="tablist"`); "Needs attention" stays in the same rail as a toggle
(`aria-pressed`); each chip shows its lane's count; touch targets ≥ 44px.

## Decision

The mobile lane switcher is the **same stage-chip control reused** as an ARIA
**tablist**, not a new mobile widget:

- The stage chips (already in `SearchBar` as stage filters) gain a tablist role
  at mobile width: each chip is a `<button role="tab" aria-selected
  aria-controls="lane-…">`, wrapped in `role="tablist"` labelled "Pick a stage
  to view". The selected chip drives which single lane is shown.
- Swipe between lanes is supported; the selected chip follows the landed lane
  (the rail reflects position).
- "Needs attention" stays in the rail as a `aria-pressed` toggle.
- The board layout itself is **CSS-media-query-driven** (the mockup proves it
  with real media queries) — desktop grid → tablet horizontal scroll → mobile
  one-lane snap track. The card internals never change across breakpoints.

The top-bar collapse (full "Start something new" → compact "+ New", full label
preserved on the accessible name; settings + theme → icons) is part of the same
responsive WP.

## Why (Convention Preference)

- **W3C ARIA Authoring Practices tabs pattern (CP-01 — W3C standard).** A
  one-of-N view switcher *is* a tablist; using the canonical role/state set
  (`tablist`/`tab`/`aria-selected`/`aria-controls`) is the established
  accessible convention, not a bespoke `<div onClick>` switcher.
- **One mental model across sizes (Jakob's Law, cited in the design).** The
  chips that filter/label stages on desktop are the chips that *pick* a stage on
  mobile. Reusing them means no new concept to learn — and the per-chip count
  does double duty as a "how full is this stage" read.
- **Check before building new (EP-03).** The stage chips exist in `SearchBar`;
  the mobile switcher extends them rather than introducing a parallel control.

## Consequences

- The stage-chip component gains a responsive dual role: filter chips on
  desktop, tabs on mobile. The ARIA roles apply at the mobile breakpoint; the
  desktop filter semantics are preserved. This is one component with a
  width-conditional role, verified by jest-axe at **both** widths.
- Touch-target sizing (≥ 44px), `:focus-visible` ring, and keyboard activation
  are gated by the a11y audit on the switcher (WPF-06).
- The board's one-lane-at-a-time mobile track is pure CSS (scroll-snap); the
  selected-tab ↔ visible-lane sync is the only JS, mirroring the mockup's
  `laneSwitcher` script.

## Alternatives rejected

- **A new bespoke mobile lane-picker widget.** Rejected: a second control for
  "which stage" the founder already reads off the chips; violates one-mental-
  model and EP-03.
- **A native `<select>` dropdown for stage.** Rejected: hides the per-stage
  counts the design wants always-visible, and loses the swipe-follows-rail tie.
- **Styled `<div>`s with click handlers.** Rejected: not keyboard/SR-operable;
  fails WPF-06. The W3C tablist pattern is the convention.
