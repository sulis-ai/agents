# Inspiration probe — working↔finished status signal + turn cards in BOTH chats

**Surface:** two chat surfaces in the cockpit — the **universal (product-wide)
chat** and the **in-change chat** — brought to parity (same turn-summary cards,
same markdown/code rendering) plus a shared, prominent **"where things stand"
signal**: *still processing…* vs *done — your turn*.

## Mobbin MCP status — honest note (UXD-15)

`inspiration: named-product` (NOT Mobbin screen captures).

The Mobbin MCP server is **up** — `claude mcp list` shows
`plugin:honest:mobbin` (https://api.mobbin.com/mcp) → **✔ Connected**. BUT the
tool `mcp__plugin_honest_mobbin__search_screens` is **not exposed to this
agent's function surface** this session (the only MCP tools wired into this
sub-agent are `plugin-builder-tools`). I could not invoke `search_screens` from
inside this thread, and I will **not** fabricate screen URLs (UXD-15 forbids
it). This is the same tool-exposure gap recorded in the product-wide-chat probe,
not a server outage.

To corroborate with real screens, re-run from a context where the
`mcp__plugin_honest_mobbin__*` tools are exposed to the running agent. The
structural findings below would be **confirmed**, not changed — these are now
industry-standard patterns. Until then the grounding is **named, real,
verifiable products**, each cited. **Structure transfers; visual identity does
NOT — the cockpit's `tokens.css` stays authoritative** (no foreign palettes or
type stacks).

---

## The load-bearing question: how to signal "working" vs "done — your turn"

Two families exist in shipped agent products. I probed both.

### Family A — a calm, persistent live indicator (ambient)

**Claude / ChatGPT / Cursor streaming caret + shimmer (2026).** While the model
streams, a **blinking caret** trails the text and the in-progress block carries a
subtle **shimmer/pulse**; when the turn ends the caret simply disappears and the
text settles. The signal is *ambient* — present without words, gone when done.
Low chrome, never shouts. The cockpit already ships exactly this caret in the
universal chat (`ProductChat.module.css .caret`), so Family A is partly built.
*Strength:* quiet, never nags. *Weakness:* "done" is the **absence** of a
signal — a founder who looks away and back can't tell "finished" from "idle/empty"
at a glance. The founder's stated pain ("you cannot tell whether it's your move")
is precisely this weakness.

### Family B — an explicit status line that changes state (named)

**ChatGPT Agent mode / Linear Agent / Devin / Manus (2026).** A short
**status line** sits with the conversation and names the state in words:
*"Working…"* → *"Thinking…"* → on completion it flips to an explicit
**done state** — a checkmark + "Finished" / "Ready for review" / "Over to you".
The transition from working→done is a **positive event the founder can see**, not
an absence. Linear Agent and ChatGPT Agent both make "I've finished, it's your
move" an explicit, legible line (often with a confirm/next-step affordance).
*Strength:* answers "whose move is it?" unambiguously, at a glance, after looking
away. *Weakness:* if oversized it adds chrome; must stay calm (CL-01) — one quiet
line, not a banner.
*Sources:* https://openai.com/index/introducing-chatgpt-agent/ ,
https://linear.app/agents , https://docs.devin.ai/ , https://manus.im/

### Family C — a "stop / pause" working chip (control-led)

**Cursor Composer / v0 (2026).** While running, a **Stop** button replaces Send;
the presence of Stop *is* the "working" signal, and its disappearance is "done".
The cockpit's in-change composer already carries a "working · pause · stop" chip
(chat-B2 signed contract, decision 5). *Strength:* gives the founder control mid-
run. *Weakness:* it lives in the composer (bottom), away from where the reply is
read (the founder's own "hard to look to the bottom" complaint) — so as the
*primary* where-things-stand cue it repeats the original problem.

---

## Synthesis — what transfers (structure only)

1. **Make "done" a positive, named event, not an absence** (Family B). The
   sharpest founder pain is "I can't tell if it's my move." Only an explicit
   done-state answers that after looking away. The ambient caret (Family A)
   stays as the *live texture during* streaming, but it is not load-bearing for
   "finished."
2. **One calm status line per chat, anchored to the conversation** (not buried in
   the dock header, not only in the composer). It reads two states:
   *"Sulis is working…"* (live, with a gentle pulse) → *"Finished — over to
   you"* (settled, with a check). Same component, same words, **both chats**
   (CL-05 — one vocabulary).
3. **Keep it quiet** (CL-01): a single line with one small motion element, using
   `--accent` for working and `--positive` for done — never a full-width banner.
   `prefers-reduced-motion` drops the pulse to a static dot.
4. **Reuse, don't invent** (EP-03): the in-change chat already has a working/idle
   notion in its composer chip and a "summarising…" pulse; the universal dock
   already has a `Working… / Idle` header chip and the streaming caret. This
   change **promotes one consistent line to the conversation** and gives "done"
   real words — it does not add a new colour or a new control.
5. **Turn cards + markdown carry over verbatim** from the signed chat-B2 Turn-
   Cards contract — the universal chat adopts the exact card the in-change chat
   already uses (summary lead + rendered markdown body + "show full reply" +
   folded steps), via the one shared `renderMarkdown.ts`.

**Identity does NOT transfer.** Every colour, font, radius and spacing in the
mockup is a cockpit `tokens.css` value. None of these products' palettes or type
stacks appear.

---

## Recommendation carried into the mockup

**Family B, kept calm** — an explicit, named status line anchored to the
conversation, reading *"Sulis is working…"* → *"Finished — over to you"*, with
the ambient caret retained as live texture during streaming. Rationale: it is the
only option that turns "done" into something the founder can *see* after looking
away, which is the exact pain they named; kept to one quiet line it costs almost
no chrome. The mockup shows this as the centerpiece, in both chats, in both
states.
