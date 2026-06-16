# WP-012 — Shipped / terminal card: archived treatment (muted, static marker, no live feet)

- **Sequence ID:** WP-012
- **dependsOn:** [WP-005]
- **kind:** frontend
- **primitive:** EXPAND-Create (shipped card variant)
- **group:** expand
- **characterisation_test:** `client/src/tests/ChangeCard.test.tsx` (WP-005's; the in-flight card behaviour is pinned before adding the terminal branch)
- **Estimated token cost:** input ~11k / output ~4k
- **visual_contract:** production-approved (`MOCKUP.html` — shipped/muted card; existing `StageBadge` shipped treatment)

## Context

SRD §7c CS-5. A change in a **terminal stage** (`stage === "shipped"`) reads as
**archived**, not active. The board **excludes** shipped by default (FR-15), so
this state applies **where a shipped card is rendered** — the Sidebar's Shipped
section today, the moment a change ships mid-session before the next poll drops
it (AF-5), and any future "include shipped" view. The archived treatment exists
in the Sidebar/`StageBadge`; the **card-level** archived state is net-new. No new
terminal-detection logic — reuse the existing `stage === "shipped"` predicate.

## Contract

- **Archived treatment (FR-56).** A shipped card is **muted**; its liveness probe
  is **replaced by a static "Shipped" marker** (no working/live/idle, no pulse);
  it shows **no waiting foot and no health foot**; recency reads as a **shipped
  recency** ("shipped Nd ago", Q-7 default) rather than a live-activity age.
- **Terminal detection (BR-27).** Detected from `stage === "shipped"` — the same
  predicate the Sidebar split + `StageBadge` already use. Reused, not reinvented.
- **No live signals (BR-28 — MUST).** A shipped card MUST NOT show any live
  signal: no probe motion/state, no "Waiting on you", no change-health badge, no
  live recency. The static "Shipped" marker + shipped recency are the only status
  reads.
- **Composition (SRD §7c precedence).** Shipped wins the **foot/probe**
  treatment over content + degraded states; any unreadable *identity* fields
  (handle/intent/slug) still fall to their unknown reads + the degraded notice
  (WP-011). Shipped suppresses both live feet — neither waiting nor health shows.
- **Shipped-recency wording** is one string constant (Q-7 default "shipped Nd
  ago"), swappable on founder confirmation.

## Definition of Done

### Red
- [ ] `client/src/tests/ChangeCard.shipped.test.tsx` (seed a `stage:"shipped"`
      change in a view that renders it):
  - the card is muted; the probe is replaced by a static "Shipped" marker (no
    pulse, no working/idle);
  - **no** "Waiting on you" foot and **no** health badge in the DOM (BR-28
    mutual suppression);
  - recency reads "shipped Nd ago", not a live age.
  (**S-36**) **Fails** (no shipped card variant).

### Green
- [ ] Shipped card variant implemented behind the `stage === "shipped"`
      predicate; test passes.
- [ ] jest-axe on the shipped card, light + dark.

### Blue
- [ ] Terminal predicate reused (grep: no second shipped/terminal detector).
- [ ] Shipped-recency wording is one constant (Q-7), swappable.
- [ ] Tokens only — muted treatment via tokens, no literal hex.

## Definition of Done — requirements & scenarios

- **Satisfies:** CS-5 (FR-56, BR-27, BR-28); bounds AF-5 (the terminal read
  until the next poll drops the card); NFR-A11Y-1.
- **Makes pass:** **S-36** (shipped card reads as archived).

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/ChangeCard.shipped.test.tsx
```
