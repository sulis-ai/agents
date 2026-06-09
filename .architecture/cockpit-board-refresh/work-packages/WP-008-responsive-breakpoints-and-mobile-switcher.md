# WP-008 — Responsive: 3 breakpoints + mobile stage-chip lane switcher (tablist)

- **Sequence ID:** WP-008
- **dependsOn:** [WP-004, WP-006]
- **kind:** frontend
- **primitive:** REORGANISE-Refactor (`Board` CSS + `StageChips` dual role) + EXPAND-Create (mobile lane-switcher tablist behaviour)
- **group:** reorganise
- **characterisation_test:** `client/src/tests/SearchBar.test.tsx` (pins current stage-chip filter behaviour before the dual-role change)
- **Estimated token cost:** input ~18k / output ~8k
- **visual_contract:** production-approved (`MOCKUP.html` — real media queries + `.laneSwitcher` tablist)

## Context

TDD §1 + ADR-004 + IDEAS.md Concern 4. Three breakpoints: desktop ≥1100px (six
lanes, unchanged from WP-004); tablet 600–1099px (lanes scroll horizontally,
~260px min-width; top bar condenses, chip row scrolls); mobile <600px (one
full-width lane at a time; stage chips become an ARIA tablist lane switcher;
top bar drops to "+ New" + icons). Depends on WP-004 (lanes) and WP-006 (the
Start button it collapses to "+ New").

## Contract

- `Board.module.css`: media-query-driven layout — desktop grid → tablet
  horizontal-scroll row (lane min-width ~260px, snap) → mobile one-lane snap
  track (each lane one screen wide). Card internals **never change** across
  breakpoints.
- `StageChips` (in `SearchBar`): dual role.
  - Desktop: filter chips (current behaviour — preserved).
  - Mobile: `role="tablist"` aria-label "Pick a stage to view"; each chip
    `<button role="tab" aria-selected aria-controls="lane-…">` showing its
    lane's count; tap → that lane snaps in. Swipe between lanes → selected chip
    follows the landed lane. "Needs attention" stays in the rail as
    `aria-pressed` toggle. Search collapses to a 44px icon tap-target.
- Top bar (`WorkspaceTopBar`): tablet/mobile collapse — "Start something new" →
  "+ New" (full label preserved on the **accessible name**), product/Board
  labels fold to icons, settings + theme stay as icons, one fixed-height row
  (never wraps/clips at 390px).
- Touch targets ≥ 44px on every mobile control; `:focus-visible` ring survives
  every size; keyboard activation of the tabs.

## Definition of Done

### Red
- [ ] Characterisation `SearchBar.test.tsx` pins desktop filter behaviour →
      passes before.
- [ ] New tests:
  - At mobile width the chips expose `role="tab"` / `aria-selected` inside a
    `role="tablist"`; activating a tab selects its lane; "Needs attention" is a
    `aria-pressed` toggle.
  - The Start button's accessible name is "Start something new" even when the
    visible text is "+ New".
  - Playwright journey: at 390px, the top bar does not wrap/clip; tapping a
    stage chip switches the visible lane; swipe updates the selected chip
    (**S-8**).
  - **Mobile switch to a zero-change stage (AF-4 / S-13):** tapping a chip whose
    lane has 0 changes snaps that lane in showing its sticky header + count `0` +
    "Nothing here yet"; no blank screen, no error.
  **All fail.**

### Green
- [ ] Three breakpoints implemented (CSS) + the mobile tablist behaviour (JS for
      tab↔lane sync only).
- [ ] **Playwright-axe at all three viewports** (desktop / tablet / mobile)
      passes; jest-axe on `StageChips` in **both** roles (filter + tablist).
- [ ] Desktop filter semantics preserved (the dual role didn't break filtering).

### Blue
- [ ] One `StageChips` component with a width-conditional role (not a parallel
      mobile widget — ADR-004 / EP-03).
- [ ] Tokens only; touch-target sizes via tokens; no literal px colour.
- [ ] Characterisation test still green (filtering intact).

## Definition of Done — requirements & scenarios

- **Satisfies:** UC-7, AF-4; NFR-RESPONSIVE-1/2/3, NFR-A11Y-2 (tablet+mobile),
  NFR-A11Y-5 (keyboard tabs), NFR-A11Y-6 (tablist semantics + 44px targets).
- **Makes pass:** **S-8** (mobile one-lane + chip switcher), **S-13** (mobile
  switch to a zero-change stage), **S-28** (board axe at tablet + mobile
  breakpoints; no 390px overflow — completing the desktop slice from WP-007),
  **S-29** (mobile switcher is a real tablist).

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/SearchBar.test.tsx
```
