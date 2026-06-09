# Cockpit Board Refresh — Verifiable Scenarios

> Authored **outside-in**: each scenario is a driven journey from the founder's first
> action to a **final observable result**, with a single observable **pass condition**
> the executor can drive (RTL/Playwright against the real interface, seeded with
> `FakeChangeStoreReader`). This is the testable-state intake. Brain entity IDs (`dna:scenario:…`)
> are minted at intake; the `verifies` column lists the FRs/BRs each scenario proves.

Driver legend: **RTL** = React Testing Library (jsdom component/page), **PW** =
Playwright (real browser, viewport-driven), **axe** = jest-axe / Playwright-axe,
**SRV** = server Vitest against `FakeChangeStoreReader`.

## Happy-path journeys

| ID | Scenario | Driven steps | Observable pass condition | Verifies | Driver |
|---|---|---|---|---|---|
| **S-1** | See everything in flight, laid out by stage | Seed 6 changes across stages; render board | All six lanes render full-height with sticky headers; each change appears as a card in its stage lane; shipped changes absent | UC-1, FR-15 | RTL/PW |
| **S-2** | A waiting card stands out and opens | Seed one change with `needsAttention.flagged=true, reason="blocked"`; render | That card's foot is the full-width centered "Waiting on you — blocked"; clicking it navigates to `/c/:id` | UC-2, BR-1, BR-2 | RTL |
| **S-3** | Spot the off-track change | Seed one change tests=red, one healthy; render | The red change's foot shows the "Off track" health badge (warning shape); the healthy one shows "On track" (check) | UC-3, BR-10 | RTL |
| **S-4** | Read alive + staleness | Seed: running+fresh, running+quiet, not-running; render | Probe renders pulsing / solid / hollow respectively; recency reads `now` / `Nm` / `Nh`; no state word visible | UC-4, BR-13 | RTL/axe |
| **S-5** | Start something new (button) | Click "Start something new" in top bar | Navigates to the start-from-intent flow; no mutation fired | UC-5, BR-7 | RTL/PW |
| **S-6** | Start something new (hotkey) | Press ⌘N (and ⌘K) on the board | Same navigation as S-5 | UC-5 | RTL |
| **S-7** | Filter narrows the same board | Type a query; tap a stage chip; tap "Needs attention" | Board narrows in place to the matching subset in the same six-lane layout; clearing all filters restores the full board | UC-6, BR-5 | RTL/PW |
| **S-8** | Mobile: one lane + chip switcher | Render at 390px; tap the "Design" chip; swipe | One full-width lane shows at a time; tapping a chip snaps that lane in; swiping moves lanes and the selected chip follows; chips show per-lane counts | UC-7 | PW/axe |
| **S-9** | First-run empty board | Seed zero changes, no filter | `<EmptyState>` guide renders; the six-lane board does not | UC-8, AF-1 | RTL |

## The single-foot-verdict rule (the founder's load-bearing rule)

| ID | Scenario | Driven steps | Observable pass condition | Verifies | Driver |
|---|---|---|---|---|---|
| **S-10** | Waiting hides health | Seed a change that is BOTH waiting AND off-track | The foot shows ONLY "Waiting on you"; the health badge is absent from the DOM (asserted mutually exclusive) | BR-1, AF-3 | RTL |
| **S-11** | Non-waiting always shows health | Seed a non-flagged change | The foot shows exactly one health badge; no waiting element in the DOM | BR-1, FR-22 | RTL |

## Alternate flows

| ID | Scenario | Driven steps | Observable pass condition | Verifies | Driver |
|---|---|---|---|---|---|
| **S-12** | Empty lane renders full-height | Seed changes leaving "Specify" empty | The Specify lane renders full-height with sticky header, count `0`, and "Nothing here yet" | AF-2 | RTL |
| **S-13** | Mobile switch to a zero-change stage | At 390px, tap a chip whose lane has 0 changes | That lane snaps in showing the sticky header + count `0` + "Nothing here yet"; no blank screen, no error | AF-4 | PW |
| **S-14** | Shipped change disappears | Seed a change, then re-seed it as shipped; re-poll | The card disappears on the next poll with no error | AF-5, FR-15 | RTL |
| **S-15** | A large lane scrolls | Seed 200 changes in one lane | The lane's internal scroll holds all 200; header count reads 200; scroll is smooth (no jank threshold breach) | AF-6, NFR-PERF-2 | PW |

## The unknown states (the sharpest gap — design only drew the healthy ends)

| ID | Scenario | Driven steps | Observable pass condition | Verifies | Driver |
|---|---|---|---|---|---|
| **S-16** | Health unknown (fresh change) | Seed a Recon change with no tests run and no artifacts | The foot shows the neutral "Health unknown" badge (NOT "On track", NOT "Off track"); `health.reason` explains why | FR-31, BR-11 | RTL/SRV |
| **S-17** | Liveness unknown | Seed a change whose `session.json` is missing/malformed | The probe renders the DISTINCT unknown shape (not a hollow "Idle" dot); SR label says "liveness unknown" | FR-41 | RTL/SRV |
| **S-18** | No recency | Seed a change with `lastActivityAt = null` | The recency text is omitted / shown as "—" (never "now" or a bogus age); the probe still renders its liveness state | FR-42 | RTL |
| **S-19** | computeHealth unknown combination | Unit: `computeHealth({ testsState:"unknown", rigorForStage:"unknown" })` | Returns an `unknown`-equivalent state with a reason, not a default "on-track" | FR-30, FR-31 | SRV |

## Error / failure states

| ID | Scenario | Driven steps | Observable pass condition | Verifies | Driver |
|---|---|---|---|---|---|
| **S-20** | Feed fails → retry | Make `GET /api/changes` error | The error box + Retry button render; no partial board; Retry refetches | EF-1 | RTL |
| **S-21** | Partial enrichment | Seed a feed where some rows have health/attention and some have absent/unknown fields | Each card degrades independently: unknown-field cards show unknown reads; the rest render normally; feed returns 200 | EF-2, BR-11 | RTL/SRV |
| **S-22** | Poll fails mid-session | Render board; force the next refetch to fail | Cards keep last-good probe/recency; no flicker to the error box; manual Refresh still works; next interval retries | EF-3 | RTL |
| **S-23** | One worktree is gone | Seed a change whose worktree path doesn't exist | Its liveness→unknown, health→unknown, attention→not-flagged; the board does NOT 500; other cards unaffected | EF-5, BR-11 | SRV |

## Misuse / abuse

| ID | Scenario | Driven steps | Observable pass condition | Verifies | Driver |
|---|---|---|---|---|---|
| **S-24** | Malformed feed row | Seed a record with a garbage stage / missing fields / malformed session.json | The row degrades to unknown reads; the feed does not throw or 500; the other rows render | MUC-1, BR-11 | SRV |
| **S-25** | Pathological change count | Seed hundreds of changes | The enrichment fan-out completes within the bounded `Promise.all`; the feed returns; no unbounded loop / no timeout | MUC-2, NFR-PERF-3 | SRV |
| **S-26** | reason never echoes content | Seed a change whose transcript contains markup/secret-looking text | `health.reason` and attention `reason` are from the fixed enumerable set; no transcript text appears in any reason field | MUC-3, FR-32 | SRV |

## Accessibility (testable NFRs)

| ID | Scenario | Driven steps | Observable pass condition | Verifies | Driver |
|---|---|---|---|---|---|
| **S-27** | Card axe, light + dark | Render each card variant (waiting / on-track / off-track / unknown) in both themes | jest-axe reports zero violations in both themes; all text labels clear AA, graphical signals clear 3:1 | NFR-A11Y | axe |
| **S-28** | Board axe at 3 breakpoints | Playwright-axe the board at ≥1100 / 600–1099 / <600 | Zero violations at each breakpoint; top bar does not overflow at 390px | NFR-A11Y, NFR-RESPONSIVE | PW/axe |
| **S-29** | Mobile switcher is a real tablist | At <600px inspect the switcher | It is `role="tablist"` with `role="tab"` + `aria-selected` children, keyboard-focusable, ≥44px targets; "Needs attention" is `aria-pressed` | NFR-A11Y, UC-7 | PW/axe |
| **S-30** | Reduced motion | Render a Working card with `prefers-reduced-motion: reduce` | The pulse is replaced by a static ring; the SR label still names "actively working" | BR-14, NFR-A11Y | RTL |
| **S-31** | Dark elevation reads as three layers | Render the board in dark mode | page → lane → card are three distinct surfaces (card lightest); an automated luminance-ordering assertion passes against the tokens | NFR-A11Y (dark) | RTL/PW |

## Alternate card states (the five the founder named — §7c)

| ID | Scenario | Driven steps | Observable pass condition | Verifies | Driver |
|---|---|---|---|---|---|
| **S-32** | Selected card is marked when its change is open | Render the board with the active route at `/c/:id` for one seeded change | That change's card is marked selected (`aria-current="true"` + a non-colour-only marker); no other card is marked; with the route at `/` no card is marked | CS-1, FR-50, BR-20, BR-21 | RTL |
| **S-33** | Keyboard-focus a card and activate it | Tab to a card; assert the focus ring; press Enter | The focused card shows a visible `:focus-visible` ring and is in tab order; Enter navigates to `/c/:id`; no signal depends on hover | CS-2, FR-51, BR-22, BR-23 | RTL |
| **S-34** | Loading shows per-card skeletons, then no jump | Render with the feed pending (`isLoading`); then resolve it with real changes | While pending: per-card skeletons render (not the empty guide), board carries `aria-busy`; on resolve, real cards replace them with **no layout jump** (same lane scaffold + card box metrics; CLS≈0; no long-frame > 50ms) | CS-3, FR-52, FR-53, BR-24, NFR-PERF-5 | RTL/PW |
| **S-35** | Degraded card renders per-field and the board is unaffected | Seed a feed where one row is malformed/partial (some fields unreadable) | That card renders per-field: readable fields normal, unreadable ones as unknown reads (health-unknown / liveness-unknown shape / recency "—"); it still links to `/c/:id`; a quiet fixed-string "some details couldn't be read" notice shows; every other card renders normally and the feed returns 200 | CS-4, FR-54, FR-55, BR-26 | RTL/SRV |
| **S-36** | Shipped card reads as archived | Seed a `stage="shipped"` change in a view that renders it | The card is muted; the liveness probe is replaced by a static "Shipped" marker (no working/idle, no pulse); no "Waiting on you" foot and no health foot; recency reads "shipped Nd ago" | CS-5, FR-56, BR-27, BR-28 | RTL |
</content>
