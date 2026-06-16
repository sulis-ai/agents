# Cockpit Board Refresh — Work Package Index

> **Change:** CH-084CAN · tier M · **13 WPs** (revised from 8) · visual contract
> production-approved.
> **Revision:** the first 8 WPs were decomposed from the **design alone**, before
> the requirements pass. This set covers everything the complete spec added: the
> unknown/degraded states (FR-31/41/42), the five alternate card states
> (§7c CS-1..5), the empty/loading/error/degraded behaviour, never-500
> degradation (BR-11), and the NFRs folded into each WP's Definition of Done.
> Order maximises parallelism: four WPs are immediately ready and run in
> parallel; the rest unlock as their dependencies land.

## What changed vs the original 8

- **Extended in place (no new file):** WP-001 (wire now carries the `unknown`
  health + liveness states + nullable recency), WP-002 (producer now **emits
  unknown**, and owns the never-500 degradation / malformed-row / worktree-gone /
  reason-containment / bounded-fan-out scenarios), WP-005 (probe + health badge
  now render the **four** states incl. the unknown reads + no-recency + reduced
  motion), WP-007 (now owns the board-level error / poll-failure / filter /
  shipped-disappears async behaviour), WP-003/004/006/008 (scenario coverage made
  explicit).
- **Five new WPs for the alternate card states + the behaviours the design never
  drew:** WP-009 (selected + interaction/focus), WP-010 (loading skeletons +
  no-layout-jump + first-run empty), WP-011 (degraded/partial card), WP-012
  (shipped/terminal card), WP-013 (lane scale / 200-card scroll perf).

## Sequence graph

```
WP-001 (wire types: + unknown states) ─┬─► WP-002 (server health + enrich; emits unknown; never-500) ─┐
                                        └─► WP-005 (redesigned card; 4 probe/health states) ─┬─────────┤
                                                                                             │         ├─► WP-007 (wire enriched card → live board; error/poll/filter/shipped-drop)
WP-004 (full-height lanes; empty lane) ──────────────────────────────────────────────────── │ ────────┘
                                                                                             │
WP-005 ─┬─► WP-009 (selected + focus card states)                                            │
        ├─► WP-012 (shipped/terminal card)                                                   │
        └─► WP-011 (degraded/partial card) ◄── WP-002 ────────────────────────────────────── │
WP-004 ─┬─► WP-010 (loading skeletons + no-jump + first-run) ◄── WP-005                       │
        └─► WP-013 (lane scale 200-card perf) ◄── WP-007 ──────────────────────────────────── ┘
WP-004 ─┐
WP-006 (revive start button) ─┴─► WP-008 (responsive + mobile switcher)
WP-003 (dark-mode tokens) ── independent ───────────────────────────────────────────────────────────
```

## Ready now (no dependencies — run in parallel)

| WP | Purpose | kind |
|----|---------|------|
| **WP-001** | Widen the `Change` wire type — attention + health + last-activity, **incl. the `unknown` health/liveness states + nullable recency** | backend |
| **WP-003** | Apply the dark-mode `tokens.css` changes (3-layer elevation) | frontend |
| **WP-004** | Full-height lanes (sticky header, internal scroll, empty-lane note) | frontend |
| **WP-006** | Revive the "Start something new" button + ⌘N/⌘K + chips | frontend |

## Unlocks after WP-001

| WP | Purpose | dependsOn |
|----|---------|-----------|
| **WP-002** | Server: derive health (**emits unknown**) + enrich feed; never-500 degradation | WP-001 |
| **WP-005** | Redesigned card — single foot verdict + **four** probe/health states (unknown reads, no-recency, reduced motion) | WP-001 |

## Card-state tier (after the card lands)

| WP | Purpose | dependsOn |
|----|---------|-----------|
| **WP-009** | Card states: selected (route-derived) + interaction/focus ring | WP-005 |
| **WP-010** | Loading skeletons (per-card) + no-layout-jump + first-run empty | WP-004, WP-005 |
| **WP-011** | Degraded / partial card — per-field unknown reads + quiet notice | WP-002, WP-005 |
| **WP-012** | Shipped / terminal card — archived treatment, no live feet | WP-005 |

## Integration tier (after the producers + surfaces land)

| WP | Purpose | dependsOn |
|----|---------|-----------|
| **WP-007** | Wire the enriched feed into the card on the live board; error / poll-failure / filter / shipped-drop async behaviour | WP-002, WP-004, WP-005 |
| **WP-008** | Responsive: 3 breakpoints + mobile stage-chip tablist switcher | WP-004, WP-006 |
| **WP-013** | Lane scale: 200-card internal scroll at 60fps (virtualise only if breached) | WP-004, WP-007 |

## Scenario → WP coverage (all 36 mapped)

> Every scenario S-1..S-36 maps to at least one WP. No scenario is unmapped.

| Scenario | WP(s) | Scenario | WP(s) |
|---|---|---|---|
| S-1 lanes by stage | WP-004, WP-007 | S-19 computeHealth unknown combo | WP-002 |
| S-2 waiting stands out + opens | WP-005, WP-007 | S-20 feed fails → retry | WP-007 |
| S-3 spot off-track | WP-002, WP-005, WP-007 | S-21 partial enrichment | WP-002, WP-011 |
| S-4 alive + staleness | WP-005 | S-22 poll fails mid-session | WP-007 |
| S-5 start button | WP-006 | S-23 worktree gone | WP-002 |
| S-6 start hotkey | WP-006 | S-24 malformed row | WP-002 |
| S-7 filter narrows same board | WP-007 | S-25 pathological count | WP-002 |
| S-8 mobile one-lane + switcher | WP-008 | S-26 reason never echoes | WP-002 |
| S-9 first-run empty | WP-010 | S-27 card axe light+dark | WP-005 |
| S-10 waiting hides health | WP-005 | S-28 board axe 3 breakpoints | WP-007, WP-008 |
| S-11 non-waiting shows health | WP-005 | S-29 mobile tablist | WP-008 |
| S-12 empty lane full-height | WP-004 | S-30 reduced motion | WP-005 |
| S-13 mobile zero-change stage | WP-008 | S-31 dark elevation 3 layers | WP-003 |
| S-14 shipped disappears | WP-007 | S-32 selected card | WP-009 |
| S-15 large lane scrolls | WP-013 | S-33 keyboard focus + activate | WP-009 |
| S-16 health unknown | WP-002, WP-005 | S-34 loading skeletons + no jump | WP-010 |
| S-17 liveness unknown | WP-002, WP-005 | S-35 degraded card per-field | WP-002, WP-011 |
| S-18 no recency | WP-005 | S-36 shipped card archived | WP-012 |

**Coverage verdict: complete — all 36 scenarios mapped, none orphaned.**

## Severity / risk

| WP | Primitive | Risk note |
|----|-----------|-----------|
| WP-001 | EXPAND-Create | Low — type-only; compiler-gated. Adds the `unknown` members. |
| WP-002 | EXPAND-Create + REORGANISE | **High** — the never-500 degradation discipline is load-bearing (BR-11). The degradation + reason-containment + bounded-fan-out suites are the MUST gates (S-19/21/23/24/25/26). |
| WP-003 | REORGANISE | Low — token values; elevation-ordering test proves it. |
| WP-004 | REORGANISE | Medium — layout refactor; characterisation tests pin the async states + empty lane. |
| WP-005 | REORGANISE + EXPAND | **High** — biggest UI WP; the single-foot-verdict rule + the four-state probe/health (incl. unknown reads) + dual-theme axe across all variants are the gates. |
| WP-006 | SUBSTITUTE-port | Low — porting already-reviewed components; re-run their tests. |
| WP-007 | REORGANISE | Medium — integration seam; owns the board-level error/poll/filter/shipped-drop behaviour + the "reachable in running app" gate. |
| WP-008 | REORGANISE + EXPAND | Medium — three-viewport axe + the dual-role chips + mobile empty-lane are the gates. |
| WP-009 | EXPAND + REORGANISE | Low-medium — route-derived selection (reuses `useMatch`) + the visible focus ring; additive composition assertion. |
| WP-010 | REORGANISE + EXPAND | Medium — the **no-layout-jump** guarantee (BR-24 / NFR-PERF-5) is the load-bearing gate; skeleton box metrics must equal real-card metrics. |
| WP-011 | EXPAND + REORGANISE | Medium — card-level composition of the unknown reads; the board-unaffected MUST (BR-26) is the gate. |
| WP-012 | EXPAND-Create | Low-medium — shipped variant; the no-live-signals MUST (BR-28) mutual-suppression is the gate. |
| WP-013 | REINFORCE-Harden | Medium — perf budget; virtualise **only if** the 200-card budget is breached (Q-6), not speculatively. |

## Founder-owned open decisions that parameterise (not block) these WPs

The recommended defaults are wired in; each is a swappable constant, tunable on
confirmation (see `OPEN_DECISIONS.md` Q-1..Q-7):

- **Q-1** Working/Live freshness window (<60s) → WP-002/WP-005.
- **Q-2** Recency buckets → WP-005.
- **Q-3** Empty-board CTA (button beside the CLI hint) → WP-010.
- **Q-4** Stale-data hint (stay silent, keep last-good) → WP-007.
- **Q-5** Health-unknown wording ("Too early to tell") → WP-005.
- **Q-6** Lane-overflow policy (plain scroll to 200) → WP-013.
- **Q-7** Shipped-card recency wording ("shipped Nd ago") → WP-012.

The **non-negotiable** that is not an open decision: the unknown/degraded states
(FR-31/41/42) and never-throw-never-500 degradation (BR-11) are requirements, not
options — they close the design's sharpest gap and are gated in WP-002/005/011.

## Deferred (not a WP in this change)

- **scope-drift + "Worth a look"** — consume `change-stage-ooda-spiral`'s drift
  signal (ADR-001). Need id: `health-drift-ooda-signal`. The wire type already
  carries the third (`worth-a-look`) state; the producer simply doesn't emit it
  yet. Additive when it lands — no re-layout.
