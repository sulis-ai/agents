---
id: WP-003
title: Universal chat renders TurnCards (summary parity + markdown) via groupTurns
kind: frontend
status: pending
change: CH-9642DA
primitive: SUBSTITUTE-Replace
group: substitute
dependsOn: [WP-001]
estimated_token_cost: "input: ~7k / output: ~7k"
characterisation_test: "apps/cockpit/client/src/tests/ProductChat.characterisation.test.tsx"
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ProductChat.turncard.test.tsx"
source: spec:chat-experience-both-universal-change (turn parity + markdown) / ADR-001 / ADR-003
---

# WP-003 — Universal chat: TurnCard parity + markdown

## Context

TDD §2.1 + ADR-001 + ADR-003. The universal chat renders agent text as a raw
wall of plain text today (`ProductChat` → `ChatMessage` → `AssistantBlock`
`kind:"text"`). Bring it to parity with the in-change chat by **reusing
`TurnCard`** (the existing summary-card + safe-markdown primitive), grouping the
durable transcript with the existing pure `groupTurns()`.

This is `SUBSTITUTE-Replace` on `ProductChat`'s assistant-rendering path: we
replace the per-message `ChatMessage`/`AssistantBlock` render of **agent turns**
with a grouped `TurnCard` render. `AssistantBlock`'s own contract is unchanged
(ADR-001) — we change what `ProductChat` renders, not `AssistantBlock`.

## Contract

`ProductChat.tsx`:
- Group `messages` with `groupTurns()` (same call `Chat.tsx` uses).
- Render `item.type === "user"` as the neutral user bubble (keep verbatim user
  text — spec non-goal: user messages unchanged).
- Render `item.type === "turn"` as `<TurnCard turn={item} />` — **no `summary`
  prop**, so the card shows its built-in first-sentences fallback (ADR-003).
- The in-flight **streamed reply** continues to render in `ProductChat` as today
  (plain streaming text + caret); only the durable transcript switches to cards.
- `ChatMessage` / `AssistantBlock` keep their existing contract and tests.

## Definition of Done

### Red
- [ ] **Characterisation test** `ProductChat.characterisation.test.tsx`: pins
      today's behaviour — an assistant text block renders as plain text inside
      `chat-message-assistant`. Confirm it passes against current code (Fowler
      EP-07), then it is updated/superseded by the behaviour test below.
- [ ] **Behaviour test** `ProductChat.turncard.test.tsx`: given a product
      transcript whose assistant turn contains a heading, a bold word, a list,
      and a fenced code block, assert the rendered turn shows `turn-card`, a
      `turn-full-toggle`; clicking it reveals `turn-full-text`; the heading is an
      `<h_>`, the list is `<li>`s, the code is in `<pre><code>` — **no raw `**`
      or backticks** in the rendered text. User messages still render verbatim.
- [ ] Behaviour test fails against current plain-text code.

### Green
- [ ] Wire `groupTurns()` + `TurnCard` into `ProductChat` per the contract.
- [ ] Keep the streamed-reply render + caret + `product-chat-reply` testid.
- [ ] All WP-003 tests green; the existing `ChatMessage.test.tsx` and
      `ProductChatDock.*` tests stay green (AssistantBlock untouched).

### Blue
- [ ] Confirm `ProductChat` reads as the same shape as `Chat.tsx`'s turn loop —
      no copy-pasted divergence; if a tiny shared "render a conversation item"
      helper is warranted by genuine duplication, extract it (else leave inline:
      one reuse site is not an extraction trigger, EP-03).
- [ ] Verify the safe-render invariant: all card markdown flows through
      `renderMarkdown`/`renderInlineMarkdown` (inherited from `TurnCard`).
