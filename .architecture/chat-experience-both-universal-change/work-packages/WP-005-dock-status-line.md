---
id: WP-005
title: Universal ProductChatDock — mount the shared status line in the chips row
kind: frontend
status: pending
change: CH-9642DA
primitive: EXPAND-Extend
group: expand
dependsOn: [WP-001, WP-002]
estimated_token_cost: "input: ~6k / output: ~6k"
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ProductChatDock.states.test.tsx"
source: spec:chat-experience-both-universal-change (status line, both chats) / ADR-002
---

# WP-005 — Universal dock: status line in the chips row

## Context

TDD §2.1 + ADR-002. The status line ships in **both** chats. `ProductChatDock`
has its own composer with a `.chips` row (`SUGGESTION_CHIPS`) and its own
lifecycle via `useProductChat` (same enum as `useChatStream`). Mount the same
shared `ChatStatusLine` (WP-002) in that chips row so the universal chat gets the
identical working↔finished behaviour and vocabulary (contract CL-05).

`EXPAND-Extend`: the dock gains the shared line via its existing chips slot; no
new state, no hook change.

## Contract

`ProductChatDock.tsx`:
- Replace the standalone `.chips` block in the composer with
  `<ChatStatusLine state={chat.state} replyProduced={…}
  chips={<the dock's existing chip buttons>} onDismissFinished={…} />`.
- `replyProduced` derived from `chat.replyText` / a completed reply this session.
- The dock **header** `Working…/Idle` status chip (`agent-status`) is a
  **separate** surface and is **left unchanged** — it is the "whose agent is
  live" header indicator, not the conversation-anchored working↔finished line.
  (Noted so the implementer does not conflate the two; the existing
  `ProductChatDock.axe.test.tsx` asserts the header chip's word — keep it green.)
- The dock's loading/empty/error states and chat→card flow are untouched.

## Definition of Done

### Red
- [ ] Add failing cases to `ProductChatDock.states.test.tsx`: while streaming,
      the composer's row shows the working line and the dock suggestion chips are
      not present; on complete it shows "Finished — over to you" then returns to
      chips; chips and the line are never both present.
- [ ] Confirm the existing `ProductChatDock.axe.test.tsx` header `agent-status`
      word assertion still holds (header chip unchanged).

### Green
- [ ] Mount `ChatStatusLine` in the dock composer's chips row.
- [ ] All new WP-005 cases green; existing `ProductChatDock.*` tests pass
      unchanged (header chip, switch, axe).

### Blue
- [ ] Same `ChatStatusLine` instance shape as `Composer` (WP-004) — one
      component, one vocabulary, both chats; only the `chips` prop differs.
