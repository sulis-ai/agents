---
id: ADR-001
title: Per-product chat dock — extend the concierge surface, board central + chat docked right
status: accepted
date: 2026-06-25
change: CH-G3Y4RM
---

# ADR-001 — Chat-dock layout and which chat surface to extend

## Context

The cockpit has **two** existing chat surfaces:

1. **Concierge** (`ConciergeChat` + `useConciergeStream` → `POST /api/concierge/query {question, product}`) — already product-scoped via a `productId` prop. Question-per-request, with suggestion chips + slash hint + neutral user bubble.
2. **Per-change chat** (`Composer` + `useChatStream` → `POST /api/changes/:id/chat {prompt}`) — keyed strictly by `changeId`, no product awareness, runs over the Claude-only `StreamJsonSessionBridge`.

The signed visual contract requires: board central (the founder's learned surface, CL-05), chat **docked right, collapsible**, header echoing the active product's tile, composer with chips + slash + free text, agent picker at the composer foot.

## Decision

**Build the per-product chat dock by extending the concierge composer family** (`ConciergeChat` / `Composer` / `ChatMessage` shared presentational pieces + the `ProductControl` popover idiom), **not** the per-change `Composer`.

Layout: **board central, chat dock right, collapsible** — exactly the v0/Linear inverted split named in the inspiration probe. The dock is a sibling region in the layout shell, not a modal; it shares horizontal space with the board responsively (board yields width when the dock is open; on narrow viewports the dock overlays).

The dock header reuses the `ProductSwitcher`/`ProductControl` neutral tile (monogram / grid-of-dots for All / dashed for Unassigned) so "whose chat" is always legible and reuses an existing visual (EP-03), never a new colour.

## Why this lead

- **The concierge is already product-scoped** (`ConciergeChat` threads `productId` through). Extending it is the smallest change to reach per-product scoping (EP-03: extend before build).
- **Board-central is a CL-05 constraint** — the founder already learned the board; the chat docks beside it rather than displacing it.
- **The `ProductControl` popover** is the exact reusable idiom for both the header tile echo and the agent picker (one menu primitive, two homes).

## Alternatives rejected

- **Extend the per-change `Composer` instead.** Rejected: it is keyed by `changeId`, has no product dimension, and rides the provider-blind `StreamJsonSessionBridge`. Retro-fitting product + provider onto it is more work than extending the already-product-scoped concierge, and conflates "chat about one change" with "chat for a product".
- **A full-screen chat that replaces the board on product select.** Rejected: violates CL-05 (moves the learned surface) and the signed contract's board-central recommendation.
- **A new chat component from zero.** Rejected: the spec and contract both mandate composition; `ChatMessage`, the chips, the slash hint, the user bubble and the popover all already exist.

## Consequences

- The dock consumes `tokens.css` verbatim (no new hex) and is verified post-build against `product-wide-chat.html` (UX_VISUAL_DESIGN_STANDARD).
- A11y: the dock header tile, the switcher, and the agent picker are real menu buttons (`aria-haspopup`/`aria-expanded` → `role="menu"` + `menuitemradio`/`aria-checked`), full keyboard parity, visible focus ring, reduced-motion fallback on caret + skeleton — inherited from `ProductControl`.
- The dock is collapsible; collapsed state must remain keyboard-reachable.
