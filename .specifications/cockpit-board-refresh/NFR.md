# Cockpit Board Refresh — Non-Functional Requirements

> All targets measurable and testable. Thresholds are defensible defaults grounded in
> the board's real shape (single-founder, localhost read seam, ≤ tens of in-flight
> changes, one 10s poll). Where a number is a judgement call, it is flagged for founder
> confirmation in [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md).

## Performance

- **NFR-PERF-1 — board first paint.** On a realistic in-flight set (**≤ 50 changes**),
  the board renders its lanes + cards within **150 ms** of the feed response (client-side,
  measured from query-success to committed paint). Test: PW performance trace on a seeded
  50-change board.
- **NFR-PERF-2 — lane scale / scroll.** A single lane holding **up to 200 cards** scrolls
  at **60 fps** with no dropped-frame jank. Beyond 200 cards a lane MAY virtualise; it is
  not required at ≤ 200. Test: PW with a 200-card lane; assert no long-frame > 50 ms during
  a programmatic scroll.
- **NFR-PERF-3 — feed enrichment cost.** The added server-side per-change derivation
  (health reads + recency) keeps the enriched `GET /api/changes` **p95 within +50%** of
  today's liveness-only feed for **≤ 50 changes**. The per-record fan-out stays inside the
  existing bounded `Promise.all` — **no unbounded loop, no N+1 per-card request** (A-1).
  Test: SRV benchmark, liveness-only vs enriched, on a seeded 50-change fake store.
- **NFR-PERF-5 — no layout jump on skeleton→data (CS-3 / BR-24).** When the loading
  skeletons are replaced by the real feed, there is **no layout shift**: the skeleton
  cards and lane scaffold occupy the same box metrics (lane width, sticky header, card
  height/clamp, internal-scroll container) as real cards, so the swap is in-place.
  **Cumulative Layout Shift contribution of the skeleton→data swap is ≈ 0** and the swap
  produces no long-frame > 50 ms. Test: PW — measure layout-shift across the
  pending→resolved transition on a seeded board; assert no card box moves and no
  long-frame. (Complements NFR-RESPONSIVE-3, which covers lane-switch and breakpoint
  jank; this pins the loading→loaded swap specifically.)
- **NFR-PERF-4 — payload growth.** Each row grows by exactly the three new fields
  (`needsAttention` object, `health` object, `lastActivityAt` string). No transcript or
  diff body is added to the feed. Test: SRV assert the enriched row shape is the wire
  `Change` and carries no extra free-text body.

## Responsiveness

- **NFR-RESPONSIVE-1 — breakpoints.** The board re-lays-out correctly at the three
  breakpoints: **≥ 1100px** (six full-height lanes), **600–1099px** (sideways-scrolling
  lanes at ~260px min-width), **< 600px** (one full-width lane + chip switcher). Test: PW
  at representative viewports.
- **NFR-RESPONSIVE-2 — no chrome overflow at 390px.** At a 390px phone width the top bar
  does **not** wrap or clip; the stage-chip rail scrolls rather than overflowing; "Start
  something new" condenses to "+ New". Test: PW at 390px; assert no element overflows the
  viewport box.
- **NFR-RESPONSIVE-3 — no jank on layout change.** Switching lanes (mobile) or crossing a
  breakpoint produces no layout jank (no long-frame > 50 ms). Test: PW frame trace across a
  resize and a chip-tap.

## Accessibility (testable)

- **NFR-A11Y-1 — axe clean, both themes.** Every changed/new component (card, waiting chip,
  health badge, liveness probe, lane, mobile switcher) passes **jest-axe with zero
  violations in BOTH light and dark**. Test: jest-axe per component × 2 themes.
- **NFR-A11Y-2 — board axe at all breakpoints.** The board page passes **Playwright-axe
  with zero violations** at desktop / tablet / mobile widths.
- **NFR-A11Y-3 — contrast.** All text labels clear **WCAG AA (4.5:1)**; all graphical
  signals (probe shapes, waiting border, health icons) clear **WCAG 1.4.11 (3:1)** against
  the real `tokens.css` values in both themes. The IDEAS.md contrast table is the
  design-time target; axe + a token-contrast assertion are the build-time gate.
- **NFR-A11Y-4 — never colour-alone.** Every signal is carried by word + shape/icon (health,
  waiting) or fill/motion/shape + SR label (probe). Test: stripping colour (greyscale
  snapshot) still distinguishes every state; SR labels present.
- **NFR-A11Y-5 — keyboard + focus.** Cards, the Start button, the chips, and the mobile
  tab switcher are keyboard-reachable with a visible `:focus-visible` ring; nothing depends
  on hover. Test: RTL/PW keyboard navigation.
- **NFR-A11Y-6 — mobile switcher semantics.** The mobile lane switcher is a real ARIA
  `tablist` (`role="tab"` + `aria-selected`); "Needs attention" is `aria-pressed`; touch
  targets ≥ **44px**. Test: PW + axe role assertions.
- **NFR-A11Y-7 — reduced motion.** With `prefers-reduced-motion: reduce`, the Working pulse
  is replaced by a static ring; the SR label still names the state. Test: RTL with the media
  query forced.

## Reliability / graceful degradation

- **NFR-DEGRADE-1 (MUST) — never-throw, never-500.** Every derived read (`computeHealth`,
  `readRigorForStage`, `readTestsState`, recency) is best-effort and read-only. A missing
  worktree / artifact dir / unreadable CI state resolves to an **unknown** read — never an
  exception. A single bad record never 500s the feed. Test: SRV — seed a gone-worktree and
  a malformed record; assert 200 + unknown reads for those rows, normal reads for the rest.
- **NFR-DEGRADE-2 — independent per-card degradation.** Partial enrichment degrades each
  card independently; an unknown-field card never blocks or hides the others (EF-2).
- **NFR-DEGRADE-3 — last-good on poll failure.** On a failed poll the board keeps the last
  successful data and retries on the next interval; it does not flicker to the error box
  (the error box is for the *initial* load failure only). Test: RTL force a refetch error
  after a successful load.

## Security / safety (carry-over, no new surface)

- **NFR-SEC-1 — read-only.** This change introduces **no write path, no mutating endpoint,
  no external call, no new secret, no service-to-service traffic**. The Start button
  navigates; it does not mutate (BR-7). Test: the existing read-only inventory gate
  (`read-only-inventory.test.ts`) stays green.
- **NFR-SEC-2 — no content leakage in reasons.** Health/attention `reason` strings come
  from a fixed enumerable set; they never echo transcript or reply body (FR-32 / A-2).
  Test: SRV — seed a transcript with markup/secret-looking text; assert no reason field
  contains it.
- **NFR-SEC-3 — path containment.** The new worktree reads stay within the change's own
  worktree (reuse `safeJoin` discipline); no read escapes the worktree, no write, no
  process spawn. Test: SRV symlink-escape fixture.

## Polling / freshness

- **NFR-POLL-1 — single poll preserved.** Exactly one 10s feed poll
  (`LIVENESS_POLL_MS`, ADR-007's permitted exception). Enriching the feed keeps it **one
  call** — no second poll, no per-card request (A-3). Test: SRV/PW assert one `/api/changes`
  request per interval.
- **NFR-POLL-2 — staleness is bounded by the interval.** Board data is "as of last
  successful poll" (≤ 10s under normal operation). Whether to *surface* staleness is an open
  decision (Q-4); the bound itself is the existing contract.
</content>
