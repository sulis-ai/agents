# Visual contract — per-product chat (cockpit)

```yaml
kind: contract
contract_type: visual
surface: product-wide-chat        # "product-wide" = product-scoped + switched like the board
mockup: contracts/visual/product-wide-chat.html
inspiration: contracts/visual/_mobbin-context.md   # named-product (Mobbin tool not exposed to this agent session)
signed_off_at: 2026-06-25T18:40:00Z   # founder signed off (#45 gate cleared)
provenance: production-approved
aggregate_scope_decision: all-products-overview-chat   # founder chose the overview chat (not read-only)
```

## What this surface is

A chat scoped **per product**, switched with the **existing top-left product
switcher** — the same switcher the board already uses ("All products" /
"Unassigned" / each product). Picking a product re-scopes the **board AND the
chat together**: pick "Clinics" → the Clinics board next to the Clinics
conversation. Each product keeps its **own conversation history**; switching
swaps it. You talk to that product's chat; the work it coordinates materialises
as **change cards on that product's board** (AI-01). The **Claude ↔ Antigravity
agent choice lives inside the chat** (foot of the composer, naming the active
agent), and is remembered per product.

## The correction this pass makes

Two prior passes mis-scoped the chat — first as **per-change**, then as a single
**global** chat across everything. Both wrong. The founder's "product-wide" =
**product-scoped + switchable like the board**. This pass ties the chat to the
existing `ProductSwitcher`: one switch moves both surfaces; each product has its
own thread; the chat header echoes the active product's tile so you always know
whose chat you're in.

## Layers

- **Visual:** cockpit `tokens.css` v4.2.0 verbatim (light + dark). Zero invented
  hex. Reuses the top-bar chrome, the `ProductControl`/`ProductSwitcher`
  chip+popover idiom and its neutral tiles (monogram / grid-of-dots for All /
  dashed for Unassigned), the concierge composer (chips + slash hint + neutral
  user bubble), the LiveTerminal honest-status badge, and the agent picker at
  the composer foot.
- **Experience:** the switcher drives board + chat together; per-product
  conversation history; chat header echoes the product tile; dual-mode input
  (chips + free text + slash, AI-02); agent picker with honest active-agent
  identity (AI-07) and a "switching applies to new work" guard (AI-03); confirm
  gate before starting work (AI-03); honest working/idle status; chat→card link.
  Three states shown: loading, empty, error.
- **Cognitive load:** ≤5 primary options at every decision point; each chat has
  one clear job (no blended firehose); the fuller vision (Unassigned triage,
  per-product memory, multi-thread, Auto agent, mid-run pause) staged to "later"
  (CL-02); board kept central so the learned surface doesn't move (CL-05).

## The aggregate-scope design decision (flagged for the founder)

The two non-product scopes resolve to purpose-built chats:
- **All products → a cross-product overview chat** ("what needs me across
  everything?"). It can start work, and asks **which product** the new work
  belongs to before filing the card. It does **not** blend per-product histories
  into one stream.
- **Unassigned → a triage chat** for sorting loose, unfiled work into products.

The main fork offered to the founder: whether "All products" should instead be a
quieter read-only overview with **no** chat at all.

**Founder decision (2026-06-25): "All products" = the cross-product overview chat**
(not the read-only no-chat alternative). The overview chat asks which product new
work belongs to before filing the card; it does not blend per-product histories.

## Accessibility verdict (verified against real tokens, light + dark)

All text pairings clear WCAG AA (4.5:1) in both themes; graphical cues clear 3:1.
Scope is legible without hue (monogram / grid / dashed shapes carry it). Switcher
and agent picker are real menu buttons (`aria-haspopup`/`aria-expanded` →
`role="menu"` with `menuitemradio` + `aria-checked`), full keyboard parity,
visible focus ring. Reduced-motion fallback on the streaming caret + skeleton
shimmer.

## Recommended direction

**Per-product chat tied to the existing switcher; board central, chat docked
right (collapsible).** "All products" = overview chat; "Unassigned" = triage chat.

## Phasing

First surface = per-product chat swapped by the switcher + composer + agent
picker + chat→card + confirm gate + honest status + three states + the "All
products" overview chat. Later = the "Unassigned" triage chat, per-product memory
transparency, multi-thread per product, an "Auto" agent option, mid-run
pause/stop.

## Sign-off

**SIGNED OFF — 2026-06-25.** The founder gave an explicit yes to the per-product
chat (tied to the existing switcher, board + chat moving together, agent choice in
the composer) and chose the "All products" overview chat. `signed_off_at` set,
`provenance: production-approved`. This visual contract is the design artifact the
build verifies against (UX_VISUAL_DESIGN_STANDARD post-build visual check).
```
