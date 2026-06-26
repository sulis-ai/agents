---
founder_facing: true
---

# Spec — Product-wide (per-product) chat experience

**Change:** CH-G3Y4RM · create · builds on CH-GJ9KQR (portable context / thread store) + CH-M7WSQ4 (agy adapter) + the shipped cockpit product switcher

> The **signed-off visual contract** is the design artifact:
> `.architecture/product-wide-chat/contracts/visual/product-wide-chat.contract.md`
> (`signed_off_at` set, `provenance: production-approved`) + its mockup
> `product-wide-chat.html`. Where this spec and the mockup disagree, the mockup
> wins on look and this spec wins on behaviour. Real cockpit `tokens.css` only —
> no new colours.

## Intent

Give the founder a **chat experience scoped per product**, sitting alongside the
Kanban board of changes. The chat is the conversational front door to Sulis; the
board is where the work it coordinates shows up (agentic-interface AI-01: chat
coordinates, the board delivers outcomes). The founder switches between products'
chats with the **same product switcher the board already uses** — picking a
product re-scopes the board AND swaps to that product's conversation. The
**Claude ↔ Antigravity agent choice lives inside the chat**, remembered per
product.

## Scope (Phase 1 — the smallest coherent surface, per the signed contract)

- **Per-product chat, driven by the existing `ProductSwitcher`.** Selecting a
  product re-scopes the board AND swaps the chat to that product's conversation.
  The chat header echoes the active product's tile (you always know whose chat).
- **Each product has its own conversation history**, persisted via the shipped
  **thread store** (one thread per product; the same durable store the portable
  context uses). Switching products swaps the thread; nothing is blended.
- **The composer** (extend the existing concierge `Composer`): dual-mode input —
  suggestion chips + free text + slash commands (AI-02).
- **The agent picker at the composer foot** — choose Claude or Antigravity for
  this product's chat (drives the session provider: `pty` / `agy`, replacing the
  hardcoded `{provider:"pty"}` in the cockpit server). Honest active-agent
  identity + status (AI-07); switching on a running session is a guarded confirm
  (AI-03).
- **Chat → card link (AI-01).** When the conversation means "do some work", the
  chat asks the founder to confirm (AI-03 gate), then a **change card appears on
  that product's board**; clicking the card focuses it.
- **"All products" → a cross-product overview chat** (founder decision): one
  conversation ("what needs me across everything?"); when it starts work it asks
  **which product** the new card belongs to before filing it. It does NOT blend
  the per-product histories.
- **Honest states:** loading, empty, error (per the mockup).

## Non-goals (later phases — captured, not dropped)

- The **"Unassigned" triage chat** (sorting loose work into products).
- **Per-product memory transparency**, multiple threads per product, an "Auto"
  agent option, mid-run pause/stop.
- The **failover trigger** (auto Claude→agy on outage) — that is the agy Phase 2,
  separate.
- No change to the board's own scoping logic or the data model.

## Acceptance

Observable behaviour (verified against the signed mockup, light + dark):

- Picking a product in the switcher re-scopes the board **and** swaps the chat to
  that product's conversation; the chat header shows that product's tile.
- Each product's chat shows **its own** history; switching away and back returns
  the same conversation; histories never blend.
- The composer offers suggestion chips + free text + slash; the agent picker at
  its foot names the active agent (Claude / Antigravity) and switching it on a
  running session asks first.
- Asking the chat to start work surfaces a **confirm**, then a **card on that
  product's board**; the card is clickable through to the change.
- "All products" shows the overview chat; starting work there **asks which
  product** before filing the card.
- Accessibility holds (WCAG AA both themes; switcher + agent picker are real
  keyboard-navigable menus with visible focus; status by glyph+word, not colour).

## Constraints

- **Reuse, don't rebuild.** Extend the existing cockpit chat components
  (`ConciergeChat` / `Chat` / `Composer` / `ChatMessage` / `useChatStream`), the
  `ProductSwitcher`, the durable **thread store** (CH-GJ9KQR), and the **agy
  adapter** (CH-M7WSQ4, now on main) — this is overwhelmingly composition.
- **The agent picker drives the real provider seam** — pass the selected provider
  (`pty` Claude / `agy` Antigravity) into the session open, replacing the
  hardcoded `{provider:"pty"}` (apps/cockpit/server/index.ts).
- **Real tokens only** (the signed visual contract); AA both themes; ≤5 primary
  options per decision point (CL-04); each chat one clear job (no firehose).
- **The signed visual contract governs the look** (UX_VISUAL_DESIGN_STANDARD
  post-build visual check against `product-wide-chat.html`).

## Verification Plan

The journeys the founder can run, each with an observable outcome (authored as
living Scenarios for the scenario gate — this is a user-facing change):

- **Switch product → both surfaces move:** pick "Clinics" → see the Clinics board
  AND the Clinics conversation; pick another → both swap; histories don't blend.
- **Talk → card:** ask the chat to start a piece of work → confirm → see a card
  appear on that product's board → click into it.
- **Pick / switch the agent:** set a product's chat to Antigravity → the composer
  names it; switch it mid-session → see the confirm; the session runs on the
  chosen provider.
- **Overview chat (All products):** in "All products", ask to start work → it asks
  which product → the card lands on that product's board.
- **Accessibility:** keyboard path through switcher + agent picker; states (load /
  empty / error) legible without colour; AA both themes.

**Third-party platform touch:** none new (the agy adapter already landed its
Platform Contract; this change consumes the existing provider seam).

## Open questions for design

- Where the chat dock lives in the layout shell (right dock, collapsible) and how
  it shares space with the board responsively.
- The per-product thread keying in the store (product id → thread) and how the
  cockpit server resolves the active product's thread + provider on open.
- The chat→card creation path (does the chat call the existing change-start flow?).
