# WP-007 — Wire the enriched feed into the redesigned card on the live board

- **Sequence ID:** WP-007
- **dependsOn:** [WP-002, WP-004, WP-005]
- **kind:** frontend
- **primitive:** REORGANISE-Refactor (integration seam: `Board` → `StageColumn` → `ChangeCard`)
- **group:** reorganise
- **characterisation_test:** `client/src/tests/Board.test.tsx` (already pinned in WP-004; re-asserted here with real fields)
- **Estimated token cost:** input ~12k / output ~4k
- **visual_contract:** production-approved (`MOCKUP.html`)

## Context

WP-002 produces the enriched feed; WP-004 builds the lanes; WP-005 builds the
card against the contract mock. This WP is the **integration seam**: feed the
**real** `needsAttention` / `health` / `lastActivityAt` fields from the live
feed through `StageColumn` into the redesigned `ChangeCard`, replacing any mock
wiring. This is the "done means reachable in the running app" gate (WPF-11).

## Contract

- `StageColumn` passes the full `Change` (incl. the new fields) to `ChangeCard`
  (already does — assert the fields flow through untouched).
- `Board.tsx` renders the enriched cards in the full-height lanes; the 10s poll
  (`useChangesWithLiveness`) carries the enriched shape (no second poll, ADR-002).
- The empty/loading/error states (WPF-05) still render correctly with the wider
  shape. This WP owns the **board-level async-state behaviour** with the enriched
  feed:
  - **Feed-fail → retry (EF-1):** the initial-load error box + **Retry** button
    render; no partial board; Retry refetches. (Existing branch — re-assert it
    survives the wider shape.)
  - **Poll-fails-mid-session (EF-3 / NFR-DEGRADE-3):** on a failed background
    refetch TanStack Query keeps the **last-good** data; cards keep their
    last-known probe/recency; no flicker to the error box; the next interval
    retries; manual Refresh still works.
  - **Filter narrows the same board (UC-6 / BR-5):** with a filter active the
    board renders the search results in the **same** six-lane layout (never a
    separate screen); clearing all filters restores the full board; zero matches
    shows an empty six-lane board (not the first-run guide).
  - **Shipped disappears (AF-5 / FR-15):** a change re-seeded as shipped drops
    off the in-flight board on the next poll with no card error.

## Definition of Done

### Red
- [ ] `Board.test.tsx`: a fixture change with `needsAttention.flagged: true`
      renders the **waiting** foot (not health); a fixture with `flagged: false`
      + `health.state: "off-track"` renders the **health** badge; the probe
      reflects `lastActivityAt`. **Fails** until wired end-to-end.
- [ ] **Async-state suite** (board-level, against the enriched shape):
  - feed error → error box + Retry render; Retry refetches; no partial board
    (**S-20 / EF-1**).
  - successful load, then forced refetch failure → cards keep last-good
    probe/recency; no flicker to the error box; manual Refresh works (**S-22 /
    EF-3**).
  - filter active → results render in the same six-lane layout; clearing
    restores the full board (**S-7 / UC-6**).
  - a change re-seeded as `shipped` drops off on the next poll, no error
    (**S-14 / AF-5**).
  **All fail / under-asserted until wired.**

### Green
- [ ] Real feed fields flow Board → StageColumn → ChangeCard; tests pass.
- [ ] Loading / error / empty states intact with the wider shape.
- [ ] Playwright-axe on the board page (desktop) passes (**S-28 desktop**).

### Blue
- [ ] No mock wiring left in the board path (the contract mock stays test-only).
- [ ] Still one feed poll (grep: no new per-card fetch — NFR-POLL-1).

## Definition of Done — requirements & scenarios

- **Satisfies:** UC-1 (cards in lanes), UC-2/UC-3 wired (waiting XOR health on
  the live board), UC-6 (filter same board), FR-15, AF-5, EF-1, EF-3;
  NFR-DEGRADE-3, NFR-POLL-1, NFR-A11Y-2 (desktop).
- **Makes pass:** **S-1** (cards appear in lanes — integration side), **S-2**
  (waiting opens, live board), **S-3** (off-track, live board), **S-7** (filter
  narrows same board), **S-14** (shipped disappears), **S-20** (feed fails →
  retry), **S-22** (poll fails mid-session), **S-28** desktop slice.

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/Board.test.tsx
```
