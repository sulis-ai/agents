---
id: WP-004
title: Integration — close the seam; drive the authored Scenarios green
kind: frontend
primitive: Create
group: expand
status: pending
dependsOn: [WP-002, WP-003]
blocks: []
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/e2e/product-wide-chat.spec.ts::switch product swaps board and chat"
estimated_token_cost: "input: ~30k / output: ~10k"
source: tdd:product-wide-chat#4
---

# WP-004 — Integration: close the seam

## Context

TDD §4–5. Wires the live frontend (WP-003) to the live backend (WP-002) across the WP-001
contract (CF-07/CF-12 seam close) and drives the founder-facing journeys end-to-end through
the real interface. This is where the authored **Scenarios** go green (the scenario ship gate
for `founder_facing: true`).

## Contract

The end-to-end behaviours from the spec's Verification Plan, exercised against the real app
(real session-manager daemon via the CI fake-child seam; real `LocalThreadStore` on a temp
root; real `start-from-intent`):

1. Switch product → board AND chat both swap; histories don't blend.
2. Talk → confirm → card on that product's board → click into it.
3. Pick / switch the agent → composer names it; mid-session switch shows confirm; the session
   runs on the chosen provider.
4. Overview chat ("All products") → starting work asks which product → card lands on it.
5. Accessibility: keyboard path through switcher + agent picker; states legible without
   colour; AA both themes.

## Definition of Done

**Red**
- [ ] `product-wide-chat.spec.ts` (Playwright + Playwright-axe) encodes Scenarios 1–5; fails
      before the seam is wired (e.g. switching swaps the board but not the chat).

**Green**
- [ ] Client funnel calls the WP-002 routes with the WP-001 shapes; `useProductChat` resolves
      `chat_scope` from active product; provider picked in the dock reaches `SessionSpec.provider`.
- [ ] All five Scenarios drive green through the real interface; the authored Scenario files
      record observed evidence (do X → observe Y).
- [ ] CF-07 conformance check run and recorded (client + server agree on the seam).

**Blue**
- [ ] No client-side product filtering of the board (server scope owns it — ADR-004); the dock
      adds no parallel scoping logic.
- [ ] Honest active-agent identity verified end-to-end — the composer foot reflects the
      *actually running* provider, not the picked-but-unapplied one.
- [ ] Post-build visual check vs `product-wide-chat.html` re-run on the integrated surface,
      light + dark.

> Notes folded from WP-002/003 security review (the integration WP MUST close these):
> - CONCERN DAT-PERSIST-01: chat turns are NOT yet persisted to the per-product
>   scope thread at runtime — `getThread` reads `~/.sulis/chat/{scope}/threads/{scope}.messages.jsonl`
>   but nothing appends to it (the relay transcript lands only in claude's own
>   ~/.claude/projects). WP-004 MUST close the round-trip: append each chat turn to
>   the scope thread via the REDACTING store path (the Python LocalThreadStore
>   scrub / chat_scope_store), so per-product history actually persists AND
>   redaction-on-write applies to chat content. Scenario 1 (switch product → see
>   that product's history) depends on this being real.
> - ADV-CWD-01: the relay cwd resolves to '' for a chat scope (resolveChange(scope)
>   returns null → cwd:''), so the chat session would run in the server's dir. WP-004
>   must ground the relay cwd to a real directory for the scope.

## Acceptance Evidence

- Branch: wp/create-product-wide-chat/wp-004-integration-seam-close (deleted post-merge)
- Completed: `2026-06-25T23:43:21Z` (Step 12 by calling session)
