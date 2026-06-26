---
wp: WP-001
change_id: 01KW1B4SG8X19J2ZT2TE16KJG3
title: Fix four real-viewport chat UX bugs (picker drop-up, collapsed rail, board no-shrink, optimistic send)
kind: frontend
source: fix
primitive: reinforce-harden
group: reinforce
status: pending
dependsOn: []
estimated_token_cost: { input: ~30k, output: ~14k }
platform: web
touch-class: read-write
docs_to_update: []
verification:
  adapter: frontend
  artifact: apps/cockpit/client/src/tests/useProductChat.test.tsx
fixtures_created: []
---

# WP-001 — Fix four real-viewport chat UX bugs

## Context

The product-wide chat shipped (main has it). The founder, using the live
cockpit, found four real viewport + real-streaming bugs the route-intercepted
e2e + a11y tests did not catch. This WP corrects real-viewport behaviour the
signed visual mockup implied. Files are under `apps/cockpit/client/src`.

Constraints: real `tokens.css` only (no new colours); light + dark; keep
WCAG AA + keyboard (the a11y gate). Reuse existing components/primitives.

## Contract

### Fix 1 — Agent picker dropdown opens UPWARD at the composer foot
`ProductControl`'s popover (`.pmenu`) is hard-coded `top: calc(100% + 6px)`
(opens DOWN), off-screen at the composer foot. Add a `placement?: "down" | "up"`
option to `ProductControl` (default `"down"`), exposed as a drop-up `.pmenuUp`
variant. `AgentPicker` passes `placement="up"`. The top-of-page usages
(switcher / change-nav / which-product) keep opening DOWN (default).

Files: `components/ProductControl.tsx`, `components/ProductControl.module.css`,
`components/AgentPicker.tsx`.

### Fix 2 — Collapsed chat is a thin right rail, not empty white space
`ProductChatDock` `.dock.collapsed` leaves an empty column. Collapsed = a slim
vertical RAIL on the right: a thin strip carrying the expand affordance + the
agent identity, not empty space.

Files: `components/ProductChatDock.tsx`, `components/ProductChatDock.module.css`.

### Fix 3 — Board keeps its size and scrolls horizontally when chat opens
`WorkspaceShell` layout gives the chat a column that squeezes the board. Opening
the chat must NOT shrink the board: the board keeps its natural width and the
board area becomes horizontally scrollable (`overflow-x`) beside the fixed-width
docked chat panel.

Files: `layouts/WorkspaceShell.module.css`.

### Fix 4 — Optimistic user message on send + stable panel
`useProductChat.send` does NOT optimistically render the user's submitted turn —
it only invalidates/refetches AFTER the reply completes, so the user's own
message is invisible during streaming and then pops in with a layout jump. Fix:
optimistically append the user's submitted message to the displayed transcript
IMMEDIATELY on send (mirroring `useChatStream`'s instant-user-turn pattern);
reconcile with the durable thread on completion (no duplicate). Stabilize the
panel so it does not resize/jump on send or stream.

Files: `api/useProductChat.ts`, plus a layout-stability tweak in
`components/ProductChatDock.module.css` / `components/ProductChat.module.css` as
needed.

## Definition of Done

### Red (failing tests first)
- a. `useProductChat.test.tsx` — send renders the user's submitted message
  immediately (before any reply chunk), via the thread query cache.
- b. `useProductChat.test.tsx` — on `complete` the optimistic message is
  reconciled against the durable thread with no duplicate.
- c. `AgentPicker.test.tsx` — the picker's menu is rendered with the drop-up
  placement (the `pmenuUp` variant marker is present on the menu).
- d. `ProductChatDock.states.test.tsx` — collapsed renders a rail with the
  expand affordance + agent identity (not an empty dock).

### Green
- `ProductControl` gains a `placement` prop + `.pmenuUp` CSS; `AgentPicker`
  passes `placement="up"`.
- `useProductChat.send` writes the optimistic user turn into the
  `["product-chat", scope]` cache and reconciles on complete.
- `ProductChatDock` renders a collapsed rail.
- `WorkspaceShell` board no longer shrinks; board area scrolls horizontally.

### Blue
- The optimistic-cache write helper is the one shape; no duplicated cache logic.

## Cost
~30k in / ~14k out.
