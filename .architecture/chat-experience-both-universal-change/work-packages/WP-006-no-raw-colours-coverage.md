---
id: WP-006
title: Extend no-raw-colours coverage to the new status-line colour surfaces
kind: frontend
status: pending
change: CH-9642DA
primitive: REINFORCE-Test
group: reinforce
dependsOn: [WP-002, WP-004, WP-005]
estimated_token_cost: "input: ~4k / output: ~4k"
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/no-raw-colours.thread-chat.test.ts"
source: spec:chat-experience-both-universal-change (no raw colours) / ADR-004
---

# WP-006 — No-raw-colours coverage for the status line

## Context

TDD §3 + ADR-004. The hard constraint: tokens only, theme-aware, and the
existing `no-raw-colours.thread-chat.test.ts` must stay green. The status line
introduces new coloured surfaces (working tile, finished tint/tick) in the
status-line CSS module + `Composer.module.css`. Those modules are **not** in the
existing test's `MODULES` array today, so a raw colour there would slip past the
named gate. Bring the new surfaces under the same characterisation test.

`REINFORCE-Test`: this WP adds no product behaviour — it widens the existing
characterisation test so the constraint is enforced in spirit, not just letter.

## Contract

`tests/no-raw-colours.thread-chat.test.ts`:
- Extend the `MODULES` array to include the new status-line CSS module and
  `Composer.module.css` (additive — `Thread.module.css` + `Chat.module.css`
  stay covered, so the test stays green for them).
- The same four assertions apply to the added modules: no hex, no `rgb()/hsl()`,
  no named-colour value, and references only tokens defined in `tokens.css`.

## Definition of Done

### Red
- [ ] Extend `MODULES`; run the test. If WP-002/004/005 introduced any raw
      colour or invented token in the added modules, the test **fails** here —
      that is the gate doing its job.

### Green
- [ ] Fix any flagged literal in the status-line / Composer modules by replacing
      with the nearest contract-named token (`--accent`, `--card`,
      `--bg-positive`, `--bg-positive-border`, `--foreground`, `--positive`) or a
      `color-mix` over tokens. No new token (a new token needs founder sign-off).
- [ ] The extended test passes for **all** listed modules.

### Blue
- [ ] Confirm `ProductChatDock.axe.test.tsx`'s hex guard still passes (the dock
      status line uses the same tokens). One colour vocabulary across both
      chats.
- [ ] Leave a one-line note in the test header recording that the status-line
      surfaces are now covered (so a future reader knows the array was widened
      deliberately, per ADR-004).
