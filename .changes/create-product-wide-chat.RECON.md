# Recon — product-wide (per-product) chat experience (CH-G3Y4RM)

Build the signed-off per-product chat (visual contract at
.architecture/product-wide-chat/contracts/visual/product-wide-chat.contract.md,
signed/production-approved): a chat scoped per PRODUCT, switched by the existing
ProductSwitcher (board + chat move together), each product its own conversation,
Claude↔Antigravity agent choice in the composer, "All products" = cross-product
overview chat. founder_facing: TRUE → verification Scenarios REQUIRED.

## It COMPOSES existing pieces (not from scratch — good)
- **Existing cockpit chat components** (apps/cockpit/client/src): ConciergeChat,
  Chat, Composer, ChatMessage, useChatStream, OnboardingChat (+ their .module.css
  + tests). The per-product chat EXTENDS the concierge composer (chips + slash +
  user bubble) the contract references — not a new chat from zero.
- **ProductSwitcher.tsx** (+ ProductControl) — the tie-in point. The switcher must
  drive BOTH the board scope AND the chat context (swap conversation per product).
- **Portable-context thread store** (shipped, on main): thread_store_local +
  thread_contract + durable_sink + context_payload. Per-product conversation
  HISTORY builds on this (one thread per product; messages persisted; the same
  store the resume brief uses).
- **Session manager provider selection**: the cockpit hardcodes provider "pty"
  (apps/cockpit/server/index.ts:275 `{provider:"pty", cwd}`). The chat's agent
  picker must drive this — pass the selected provider ("pty" Claude / "agy"
  Antigravity) instead of the hardcode.

## THE DEPENDENCY (sequencing — flag to founder)
The Claude↔Antigravity picker needs the **agy adapter**, which is BUILT + security-
clean but NOT on main yet (CH-M7WSQ4, on its branch; main/adapters has only
claude_pty + claude). So the agy adapter should SHIP to main FIRST, then this chat
builds on a main that has it. (Design can proceed in parallel; the build's
provider-picker WP needs the adapter merged.)

## Shape (for SEA design)
Cross-kind, contract-first: FRONTEND (the per-product chat dock + composer + agent
picker + switcher tie-in + chat→card + the "All products" overview chat, all
against the signed visual contract) + BACKEND (per-product chat sessions; per-
product thread/conversation via the thread store; provider selection replacing the
"pty" hardcode; chat→change-card link). The signed visual contract is the design
artifact the build verifies against (UX_VISUAL_DESIGN_STANDARD post-build check).

## Suggested next
1. Ship the agy adapter (CH-M7WSQ4) to main (it's review-clean) so the chat builds on it.
2. /sulis:specify (founder_facing, deep — author the verification Scenarios for the
   journeys: switch product → board+chat swap; talk → card; pick/switch agent; the
   overview chat asks which product).
3. SEA design (TDD + WPs + contract-first) against the signed visual contract.
