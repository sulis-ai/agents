---
id: WP-002
title: Shared ChatStatusLine — working↔finished derived from the existing lifecycle
kind: frontend
status: pending
change: CH-9642DA
primitive: EXPAND-Create
group: expand
dependsOn: [WP-001]
estimated_token_cost: "input: ~6k / output: ~7k"
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ChatStatusLine.test.tsx"
source: spec:chat-experience-both-universal-change (status line) / ADR-002
---

# WP-002 — Shared `ChatStatusLine`

## Context

TDD §2.1 + §3 + ADR-002. The visual contract's centrepiece: one calm status
line that reads "Sulis is working…" while a reply streams and "Finished — over
to you" on completion, then returns to the suggestion chips once read. It must
be **mutually exclusive** with the chips and ship in **both** chats. It derives
from the existing hook lifecycle and adds **no** state to `useChatStream` /
`useProductChat` (ADR-002).

## Contract (public interface)

A new presentational component `components/ChatStatusLine.tsx`:

```ts
type ChatStatusKind = "chips" | "working" | "finished";

interface ChatStatusLineProps {
  /** The existing hook lifecycle (shared enum: "ready" | "resuming" |
   *  "spawning" | "replying" | "interrupted" | "failed"). */
  state: ChatLifecycle;          // reuse the existing type — do not redefine
  /** True once a reply has been produced this session (drives "finished"). */
  replyProduced: boolean;
  /** The chips to show in the idle/your-turn slot (caller supplies its own
   *  suggestion set — the two chats have different chips). */
  chips: React.ReactNode;
  /** Called when the founder dismisses the "finished" line by acting
   *  (focus/typing/sending) — resets the slot back to chips. */
  onDismissFinished?: () => void;
}

export function ChatStatusLine(props: ChatStatusLineProps): JSX.Element;
```

Slot derivation (the only new logic, presentational):

- `working` when `state` ∈ {`replying`, `resuming`, `spawning`}.
- `finished` when `replyProduced` and `state === "ready"` and not yet dismissed.
- `chips` otherwise (idle/your-turn, or after dismissal).
- `interrupted` / `failed` → render **nothing** in the slot (those notes render
  as their own bands above the slot, owned by the caller) — the line never
  claims "finished" on a broken/failed turn (FR-19/FR-22 preserved).

A11y / tokens (carried verbatim from the contract, ADR-004):

- The line is `role="status" aria-live="polite"`.
- working = pulse icon + "Sulis is working…"; finished = tick icon +
  "Finished — over to you" with a **neutral `--foreground`** label (green only
  on the tick + `--bg-positive` tint). Differ by icon **and** wording.
- pulse honours `prefers-reduced-motion: reduce`.
- Colours: `--accent` (+ 9%/28% `color-mix` over `--card`) for working;
  `--bg-positive` / `--bg-positive-border` / `--positive` for finished. No hex.

## Definition of Done

### Red (characterise + failing behaviour)
- [ ] `ChatStatusLine.test.tsx` written, asserting: `replying` → working line
      (no chips); `ready` + `replyProduced` → finished line (no chips);
      `ready` + `!replyProduced` → chips; `interrupted`/`failed` → neither
      working nor finished line in the slot. **Exactly one** of {chips, working,
      finished} renders at any time (mutual exclusivity).
- [ ] axe test: the rendered line has `role="status"` + `aria-live="polite"`
      and no violations.
- [ ] Tests fail (component does not exist yet).

### Green (boring implementation)
- [ ] Implement `ChatStatusLine.tsx` per the contract — a pure function of
      props, no hook calls, no local lifecycle state beyond the "dismissed"
      latch. Heroicons for pulse/tick.
- [ ] Status-line CSS module: tokens only, the exact tokens named above;
      `prefers-reduced-motion: reduce` fallback.
- [ ] Verify in the Red that every token used is already defined in
      `tokens.css` (no invented token).
- [ ] All WP-002 tests green.

### Blue (refactor)
- [ ] Extract the slot-derivation into one small pure helper
      (`statusSlot(state, replyProduced, dismissed): ChatStatusKind`) so the
      JSX is a thin switch and the logic is unit-tested directly.
- [ ] Confirm no duplication with the existing dock `statusWord` logic — note
      for WP-005 that `ProductChatDock`'s header `Working…/Idle` chip is a
      *different* surface (the header), not this slot.
