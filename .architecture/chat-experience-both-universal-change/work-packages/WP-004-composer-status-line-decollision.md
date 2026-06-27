---
id: WP-004
title: In-change Composer — mount status line + bottom-dock de-collision fix
kind: frontend
status: pending
change: CH-9642DA
primitive: REORGANISE-Refactor
group: reorganise
dependsOn: [WP-001, WP-002]
estimated_token_cost: "input: ~8k / output: ~8k"
characterisation_test: "apps/cockpit/client/src/tests/Composer.test.tsx (existing FR-19/22/26 cases are the characterisation gate)"
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/Composer.test.tsx"
source: spec:chat-experience-both-universal-change (status line + de-collision) / ADR-002 / ADR-004
---

# WP-004 — In-change Composer: status line + de-collision

## Context

TDD §2.1 + §3 + ADR-002 + ADR-004. Mount the shared `ChatStatusLine` (WP-002)
in the single row above the message box in `Composer.tsx`, **in place of** the
suggestion chips. Fix the reported overlap bug: the in-flight user/agent bubbles
+ the `resumedNote` currently crowd the bottom strip with tight gaps, so a fresh
streaming reply reads as buried under "This change was resumed…". Per the
contract's de-collision section: the resumed note lives **only** in the status
slot and **only** when `state` is ready/your-turn; the instant a new turn starts
(`state !== "ready"`) the working line takes the slot and the resumed note is
gone — not stacked. Interrupted/failed notes render as their own band **above**
the slot.

This is `REORGANISE-Refactor` on `Composer`: the existing honest-state notes
move position; behaviour (which state shows which note) is preserved.

## Contract

`Composer.tsx`:
- Replace the standalone `.chips` block with `<ChatStatusLine state={chat.state}
  replyProduced={…} chips={<the existing suggestion chips>}
  onDismissFinished={…} />`.
- `replyProduced` is true once a non-empty reply has streamed this session
  (derive from `chat.replyText` having been non-empty, or a completed turn).
- The `resumedNote` (FR-26) renders **inside the chips/idle slot only** — i.e.
  it is shown by the chips branch when `chat.resumed && chat.state === "ready"`,
  never while a turn is active. When a new send starts, the working line owns the
  slot → the resumed note is not rendered (not merely visually hidden).
- The `interruptedNote` (FR-22) and `chatError` (FR-19) render as their own bands
  **above** the slot, paired with the preserved partial reply — unchanged
  wording, new position.
- The keyboard-hint footer stays inside the composer card (unchanged).

## Definition of Done

### Red (characterisation first — EP-07)
- [ ] Confirm the **existing** `Composer.test.tsx` FR-19/22/26 cases pass
      against current code — they are the characterisation gate for the honest
      states this refactor must not regress.
- [ ] Add failing cases: (a) while `state === "replying"`, the row above the box
      shows the working line and the suggestion chips are **not** present;
      (b) on complete (`replying → ready` with a produced reply), the row shows
      "Finished — over to you", then returns to chips after a dismiss
      interaction; chips and status line are never both present;
      (c) **de-collision**: render with `resumed` true + `state === "ready"`
      (resumed note shown), then send → assert the working line holds the slot
      and `resumed-note` is **not** in the document (stepped aside, not buried).

### Green
- [ ] Mount `ChatStatusLine`; move the resumed note into the chips/idle slot;
      move interrupted/failed notes to bands above the slot.
- [ ] All new WP-004 cases green; **all existing `Composer.test.tsx` cases pass
      unchanged** (FR-19/22/26 regression gate).

### Blue
- [ ] Composer's bottom region reads as: [above-slot bands: interrupted/failed]
      → [single slot: chips | working | finished | resumed-note] → [composer
      card]. One row, one thing at a time.
- [ ] No duplicated status logic — the slot decision lives entirely in
      `ChatStatusLine` (WP-002).
