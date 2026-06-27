---
founder_facing: true
---

# Spec — Align the universal chat with the in-change chat (summaries, formatting, and a clear "where things stand" signal)

**Change:** CH-9642DA · feat

## Intent

Make the product-wide (universal) chat feel like the in-change chat, and give
both a clear signal for whether the agent is still working or has finished.
Three connected pieces:

1. **Turn-summary parity.** The in-change chat condenses each agent turn into a
   short summary card (a 2–3 sentence summary, the full reply behind a "show
   full reply" toggle, tool steps folded). The universal chat shows raw,
   unsummarised text today. Bring the same summary-card treatment to the
   universal chat.
2. **Markdown + code rendering.** Agent replies render markdown and fenced code
   blocks as formatted HTML in both chats, reusing the app's single existing
   safe renderer (`apps/cockpit/client/src/lib/renderMarkdown.ts`) rather than
   adding a new library.
3. **A clear "where things stand" status line.** One calm, single-line
   indicator in the row directly above the message box: reads
   "Sulis is working…" while a reply streams, flips to "Finished — over to you"
   when the turn completes. It shares that row with the suggestion chips
   (mutually exclusive — only one shows at a time). This also fixes a layout
   bug where a new reply was crammed under the "This change was resumed…" note.

The look-and-feel is fixed by the signed visual contract (see Acceptance).

## Scope

- Wire the universal chat's assistant rendering (`ProductChat.tsx` →
  `ChatMessage.tsx` → `AssistantBlock.tsx`) to the same summary-card + markdown
  treatment the in-change chat uses (`Chat.tsx` → `TurnCard.tsx`), reusing the
  existing turn-summary generation the in-change chat already relies on.
- Render agent replies through the shared `renderMarkdown()` /
  `renderInlineMarkdown()` in both chats (the in-change chat already does;
  the universal chat is the gap).
- Add the working↔finished status line to the chat dock, placed in the row
  above the input box, sharing that row with the suggestion chips
  (chips when it's your turn → "Sulis is working…" while streaming →
  "Finished — over to you" when done → back to chips once read).
- Fix the bottom-region overlap so a new turn's bubbles get clear space and the
  "This change was resumed…" note steps aside when a new turn begins
  (`Composer.tsx` + `Composer.module.css`).

## Non-goals

- **User-typed messages stay verbatim.** Your own messages keep rendering
  exactly as typed in both chats — deliberate existing behaviour; not changed.
- **No new markdown/syntax-highlighting library.** Reuse the existing safe
  renderer (EP-03). Anything outside its supported subset renders as legible
  escaped text, never executable.
- **No redesign of the in-change chat's card visuals** beyond adding the status
  line and the overlap fix — the universal chat is brought up to match it.
- **No change to the summary-generation engine itself** — the universal chat
  reuses the same summaries the in-change chat already produces.

## Acceptance

The signed visual contract is the authoritative look-and-feel:
`.architecture/chat-experience-both-universal-change/contracts/visual/chat-both-status.contract.md`
(mockup: `…/chat-both-status.html`), signed 2026-06-27, light + dark.

Observably true when done:

- In the universal chat, an agent reply appears as a summary card with a
  "show full reply" toggle — the same shape as the in-change chat — not a raw
  wall of text.
- Agent replies in both chats render markdown (headings, lists, bold, italic,
  links) and fenced code blocks as formatted, highlighted HTML; inline code is
  formatted.
- While a reply streams, the row above the input reads "Sulis is working…";
  when the turn completes, it reads "Finished — over to you", then returns to
  the suggestion chips once read. The chips and the status line never show at
  the same time.
- On sending a message while a change shows the "This change was resumed…"
  note, the new message and streaming reply get clear space and the resumed
  note steps aside — nothing is buried under it.
- Light and dark both render correctly with no raw colour literals
  (token system only).

## Constraints

- **Reuse the one shared renderer** — `lib/renderMarkdown.ts` (EP-03); do not
  fork or add a markdown library.
- **No raw colours** — every colour resolves through the token system
  (`var(--*)` or `color-mix` over existing tokens), theme-aware; enforced by
  `tests/no-raw-colours.thread-chat.test.ts`.
- **Honest lifecycle states preserved** — the existing FR-19/22/26 behaviours
  (clear failure without false "delivered", interrupted-reply partial kept,
  honest "resumed" indication) must keep working.
- **Stay continuous with the signed chat-B2 "Turn Cards" contract** the founder
  already approved; this extends it, it doesn't diverge.
- **Front-end build gate** won't release this work until it points back to the
  now-signed visual contract.

## Verification Plan

- **Foundational.** Verified at the real React component interface
  (Vitest + Testing Library, the app's existing harness under
  `apps/cockpit/client/src/tests/`), exercising the rendered DOM the founder
  actually sees — not internal helpers in isolation.
- **Per-integration.** No new third-party platform touch (no GitHub/Stripe/
  email/cloud API) — `existing` in-app rendering + state only; no Platform
  Contract required.
- **Per-kind (frontend).** Characterisation tests first for the touched
  components (`AssistantBlock`, `ProductChat`, `Composer`) per the no-regression
  rule, then the new behaviour: (a) universal-chat assistant reply renders as a
  summary card with working "show full reply"; (b) markdown + fenced code render
  as formatted HTML in both chats; (c) the status line shows "Sulis is working…"
  while `state === "replying"` and "Finished — over to you" on completion, and
  is mutually exclusive with the suggestion chips; (d) on a new send the resumed
  note yields and the in-flight bubbles are not occluded; (e) the existing
  no-raw-colours test still passes; (f) light + dark both render. Accessibility:
  the existing axe test coverage extends to the new status line.
- **How we'll know it's done.** All of the Acceptance bullets above are
  observably true in the running app and covered by passing tests, and the
  frontend gate confirms the work points back to the signed visual contract.
