# WP-013 — Lane scale: 200-card internal scroll at 60fps (virtualisation threshold)

- **Sequence ID:** WP-013
- **dependsOn:** [WP-004, WP-007]
- **kind:** frontend
- **primitive:** REINFORCE-Harden (perf budget on the lane scroll) + EXPAND-Create (virtualisation only if the budget is breached)
- **group:** reinforce
- **characterisation_test:** `client/src/tests/StageColumn.test.tsx` (WP-004's; pins the lane render + count before the scale test)
- **Estimated token cost:** input ~12k / output ~5k
- **visual_contract:** production-approved (`MOCKUP.html` — lane internal scroll)

## Context

SRD AF-6 + NFR-PERF-2 + MUC-2 (client side). A single lane must absorb a large
change count via its **internal scroll** at 60fps with no jank. The full-height
lane (WP-004) is the mechanism; this WP **proves the perf budget** and only adds
virtualisation **if** the budget is breached at the default threshold (Q-6:
plain scroll to 200, then revisit). It depends on WP-004 (the scrolling lane) and
WP-007 (the live enriched cards being scrolled).

## Contract

- **Lane scale (NFR-PERF-2 / AF-6).** A single lane holding **up to 200 cards**
  scrolls at **60fps** with **no long-frame > 50 ms** during a programmatic
  scroll. The lane's internal scroll absorbs the count; the header count reflects
  the **true total** (not a windowed subset).
- **Virtualisation is conditional (Q-6).** Default is **plain internal scroll to
  200** — virtualisation is **not** built unless the 200-card budget is breached
  on the target hardware. If breached, virtualise behind the same lane API (cards
  unchanged), keeping the header count truthful. This WP records the measured
  result; it does **not** speculatively virtualise (boring-code: don't add
  machinery the budget doesn't demand).
- **Bounded, no per-card request.** Scrolling adds **no** network request (the
  feed is one 10s poll — NFR-POLL-1); rendering more cards must not trigger N+1
  fetches. Pairs with the server-side bounded fan-out (WP-002 / S-25).

## Definition of Done

### Red
- [ ] `client/src/tests/Board.scale.spec.ts` (Playwright): seed **200 changes in
      one lane**; programmatically scroll the lane; assert the internal scroll
      holds all 200, the header count reads **200**, and **no long-frame > 50 ms**
      during the scroll (**S-15 / NFR-PERF-2**). **Fails** if the plain-scroll
      lane janks at 200.

### Green
- [ ] The 200-card lane meets the budget on plain internal scroll **or**
      virtualisation is added behind the lane API to meet it; the test passes.
- [ ] The header count reflects the true total in both cases.
- [ ] No per-card network request introduced by scrolling (grep + PW network
      assertion).

### Blue
- [ ] If virtualisation was needed, it sits behind the existing lane API (cards
      unchanged — EP-03); if not, no virtualisation machinery was added (the
      measured result is recorded in the WP/PR).
- [ ] Characterisation test (`StageColumn.test.tsx`) still green.

## Definition of Done — requirements & scenarios

- **Satisfies:** AF-6, NFR-PERF-2, MUC-2 (client/render side), NFR-POLL-1
  (no per-card fetch on scroll).
- **Makes pass:** **S-15** (a large lane scrolls — 200 cards at 60fps, count
  truthful).

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/Board.scale.spec.ts
```
