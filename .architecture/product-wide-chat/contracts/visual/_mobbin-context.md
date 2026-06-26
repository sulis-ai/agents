# Inspiration probe — per-product AI chat tied to the cockpit's product switcher

**Surface:** a chat scoped **per product**, switched with the **existing product
switcher** so that picking a product re-scopes the **board AND the chat together**.
Each product has its own conversation history. NOT one global chat; NOT per-change.

## Mobbin MCP status — honest note (UXD-15)

`inspiration: named-product` (NOT Mobbin screen captures).

I attempted the Mobbin tool again this session. Honest, specific result:

- At the CLI level the Mobbin MCP server **is healthy** — `claude mcp list` shows
  `plugin:honest:mobbin` (https://api.mobbin.com/mcp) → **✔ Connected**.
- BUT the tool `mcp__plugin_honest_mobbin__search_screens` is **not exposed to
  this agent's function surface** this session — the only MCP tools wired into
  this sub-agent are `plugin-builder-tools`. So I could not invoke `search_screens`
  from inside this thread, even though the server itself is up. This is a
  tool-exposure gap, not a server outage, and **not** something I can work around
  by fabricating screen URLs (UXD-15 forbids it).

To get real Mobbin references, re-run this from a context where the
`mcp__plugin_honest_mobbin__*` tools are exposed to the running agent (e.g. the
main session, or wire the honest-mobbin server into the ux-designer agent's
allowed tools). The structural recommendations below would then be
**corroborated** with real screens, not changed — these are now industry-standard
patterns. Until then, the grounding is **named, real, verifiable products**, each
cited to a source. **Structure transfers; visual identity does NOT — the
cockpit's `tokens.css` stays authoritative** (no foreign palettes/type stacks).

---

## Pattern 1 — A workspace/scope switcher that re-scopes a chat + board together

**Linear (workspace + team switcher, 2026) and Linear Agent.** Linear — the tool
the cockpit already borrows its board, switcher and property idioms from — scopes
the whole surface (board, issues, and now the agent chat) by the active
team/workspace from one switcher. Switching the scope moves what you see *and*
the assistant's context with it; the chat "understands your roadmap, issues, and
code" for the active scope and lands work as issues on that scope's board (AI-01:
chat coordinates, board delivers). The cockpit's own `ProductSwitcher` /
`ProductControl` is exactly this idiom; the move here is to make the **chat hang
off the same switch** the board already obeys (CL-05 — one product vocabulary, no
new control).
*Source:* https://linear.app/changelog/2026-03-24-introducing-linear-agent ,
https://linear.app/agents

## Pattern 2 — Per-workspace AI assistant with its own conversation

**ChatGPT "Projects" / per-workspace memory and Slack channel-scoped AI (2026).**
The established pattern for "the assistant should know *this* context and keep a
*separate* history per context": each project / workspace / channel has its own
conversation and its own memory, and switching context swaps the conversation
rather than blending everything into one stream. That is the per-product chat
here: switch to Clinics → Clinics' history; switch to Bakery Ops → its own,
never mixed.
*Source:* https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt

## Pattern 3 — Chat docked beside the made thing (board) — chat-left/outcome-right inverted

**Vercel v0 (2026).** "The **left side is the conversation** window… the **right
side is the preview panel**." The canonical AI-native "talk on one side, the made
thing on the other" split. The cockpit keeps the **board central** (its existing,
learned surface) and docks the per-product chat to the **right** — same two-region
split, inverted so the board retains the primacy it already earned (CL-05: don't
move the surface the founder already knows).
*Source:* https://dev.to/pickuma/v0-by-vercel-review-ai-generated-react-components-that-actually-ship

## Pattern 4 — Agent/model selector lives in the composer, at the foot of the input (AI-02/AI-07)

**Cursor (Composer / Chat, 2026).** The model picker is "the **model name at the
bottom of the chat input**" — a quiet picker naming the active agent, with an
"Auto" option. The Claude↔Antigravity choice belongs **inside the chat, at the
foot of the composer**, NOT on a change card. The cockpit's `ProductControl`
chip-trigger + popover is the exact idiom to reuse for it (CL-05 / EP-03).
*Source:* https://www.datacamp.com/tutorial/claude-code-in-cursor

## Pattern 5 — Honest activity log + confirm gate before consequential actions (AI-03/AI-07)

**ChatGPT Agent mode (2026).** "You'll **watch it work**… reasoning and progress
in a transparent log"; "asks confirmation before significant actions". When the
per-product chat spawns work it shows a plain-language activity line ("Started X —
it's on the Clinics board now"), a confirm gate before starting, and honest
working/idle status — the cockpit already speaks this language (the concierge's
"I only looked — nothing changed" honesty tag).
*Source:* https://openai.com/index/introducing-chatgpt-agent/

---

## Synthesis — what transfers into the cockpit (structure only)

1. **One chat per product, switched by the existing switcher together with the
   board** (Linear scope switching) — pick a product → board + chat both move to
   it; each product keeps its own history (CL-05, AI-01).
2. **The chat header echoes the active product's identity** using the switcher's
   own neutral tile (monogram / grid-of-dots for All / dashed for Unassigned) —
   reuse, not a new visual (EP-03, never-colour-alone).
3. **Aggregate scopes resolve to purpose-built chats:** "All products" → a
   cross-product overview chat that asks which product new work belongs to;
   "Unassigned" → a triage chat for filing loose work. Neither blends per-product
   histories into one firehose (a flagged design decision for the founder).
4. **Board central, chat docked right** (v0, inverted) — the board keeps primacy.
5. **Agent picker at the composer foot** (Cursor) + **honest activity / confirm
   gate** (ChatGPT Agent) — Claude↔Antigravity lives in the chat, not on a card.

**Identity does NOT transfer.** Every colour, font, radius and spacing in the
mockup is a cockpit `tokens.css` value. None of these products' palettes or type
stacks appear.
