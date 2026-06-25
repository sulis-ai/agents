---
id: WP-003
title: Frontend — per-product chat dock, agent picker, switcher tie-in, chat→card, three states
kind: frontend
primitive: Create
group: expand
status: pending
dependsOn: [WP-001]
blocks: [WP-004]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ProductChatDock.axe.test.tsx::dock menus + keyboard + colour-independent status"
estimated_token_cost: "input: ~40k / output: ~18k"
source: tdd:product-wide-chat#2.1
---

# WP-003 — Frontend: the per-product chat dock

## Context

TDD §2.1, ADR-001, ADR-004. Builds the right-docked, collapsible chat against the WP-001
contract and the **SIGNED visual contract** (`product-wide-chat.html` is the design
artifact — real cockpit `tokens.css` only, verified post-build). Extends the concierge
composer family; does NOT rebuild a chat.

## Contract

- `ProductChatDock` — right-docked collapsible region; header echoes the active product
  tile via the `ProductControl` neutral tile (monogram / all-grid / unassigned-dashed).
  Reads `useActiveProduct()` so **one switch moves board + chat together** (no new control).
- `ProductChat` — extends `ConciergeChat`/`ChatMessage` + chips + slash hint + neutral user
  bubble; consumes `useProductChat(chatScope)` (streams the scope's thread per WP-001 GET +
  POST). Switching scope swaps the conversation; histories never blend in the UI.
- `AgentPicker` (composer foot) — `ProductControl` menu (`menuitemradio`/`aria-checked`),
  ≤5 options; names the **running** provider (AI-07 honest identity); switching on a running
  session shows the AI-03 confirm and calls `PUT /provider` (applies to new work).
- chat→card — embeds `useStartFromIntent`; per-product chat passes the known `productId`;
  the **overview chat** (`product:__all__`) shows a "which product?" menu before `propose`
  (ADR-004), then the existing confirm UI; on `started`, a plain-language activity line +
  link to `/c/:changeId`.
- **Three states** per the mockup: loading (skeleton + reduced-motion fallback), empty, error.

## Definition of Done

**Red**
- [ ] `ProductChatDock.axe.test.tsx` (jest-axe) — switcher tile, agent picker, and dock are
      real menus (`role=menu`, `menuitemradio`, `aria-checked`), full keyboard parity, visible
      focus, status legible by glyph+word (not colour); reduced-motion fallback. Fails before
      the dock exists. **A11y is a gate (WPF-13).**
- [ ] `ProductChatSwitch.test.tsx` — selecting a product in the switcher swaps the dock's
      thread (history A → history B), and back returns history A unchanged (no blend).
- [ ] `AgentPicker.test.tsx` — picker names the running provider; switching mid-session opens
      the confirm; confirming calls `PUT /provider`.
- [ ] `OverviewChatToCard.test.tsx` — in `product:__all__`, "start work" asks which product
      before `propose`; per-product chat skips the ask.

**Green**
- [ ] `ProductChatDock`, `ProductChat`, `AgentPicker`, `useProductChat` implemented against
      WP-001 types; chat→card via `useStartFromIntent`; three states rendered.
- [ ] `tokens.css` only — zero invented hex; CSS modules consume token vars.
- [ ] All Red green.

**Blue**
- [ ] No duplicated menu primitive — `AgentPicker` and the header tile both reuse
      `ProductControl` (extract no second popover).
- [ ] No second active-product store — the dock reads `useActiveProduct()`, the same one the
      board reads.
- [ ] Post-build visual check vs `product-wide-chat.html` (light + dark) recorded
      (UX_VISUAL_DESIGN_STANDARD); discrepancies fixed or noted.

## Acceptance Evidence

- Branch: wp/create-product-wide-chat/wp-003-frontend-chat-dock (deleted post-merge)
- Completed: `2026-06-25T22:16:59Z` (Step 12 by calling session)
