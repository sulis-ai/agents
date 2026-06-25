---
id: WP-001
title: Per-product chat-scope seam contract (client↔server API + contract test)
kind: backend
primitive: Create
group: expand
status: pending
dependsOn: []
blocks: [WP-002, WP-003, WP-004]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/contract/chatScope.contract.test.ts::request-response shapes agree"
estimated_token_cost: "input: ~25k / output: ~8k"
source: tdd:product-wide-chat#2.3
---

# WP-001 — Chat-scope seam contract

## Context

TDD §2.3 (the client↔server seam). This is the **contract-first** WP (CF-07/CF-12): it
defines the wire shape the per-product chat client sends and the server resolves, so the
frontend (WP-003) and backend (WP-002) build against it in parallel. No behaviour ships
here beyond the shape + its conformance test.

## Contract

Define `ChatScope` and the API in `apps/cockpit/shared/api-types.ts` (the shared wire types
both sides import — the single source of truth):

```ts
type ChatScope = `product:${string}`;          // "product:{id}" | "product:__all__" | "product:__unassigned__"(reserved)
type ChatProvider = "pty" | "agy";             // pty=Claude, agy=Antigravity

interface ChatThreadResponse {                  // GET /api/chat/:scope/thread
  messages: TranscriptMessage[];                // reuse existing TranscriptMessage union
  provider: ChatProvider;                       // the scope's remembered/resolved provider
  productId: string | null;                     // null for product:__all__
}
interface ChatMessageRequest { prompt: string } // POST /api/chat/:scope/message → SSE state|chunk*|complete
interface ChatProviderRequest { provider: ChatProvider } // PUT /api/chat/:scope/provider
interface ChatProviderResult { provider: ChatProvider; applied: "new-work" } // AI-03: applies to new work
```

Chat→card REUSES `StartFromIntentRequest`/`start-from-intent` verbatim (ADR-004) — no new
shape; the contract documents that the overview chat (`product:__all__`) must supply
`productId` before `propose`.

`scope` path param validates as `product:[A-Za-z0-9_-]+` (mirrors `validate_store_id`).

## Definition of Done

**Red**
- [ ] `chatScope.contract.test.ts` asserts the request/response shapes for all four routes,
      fails against an absent/empty type module. Test names the exact field set per shape.

**Green**
- [ ] `ChatScope`, `ChatProvider`, and the four interfaces land in `shared/api-types.ts`.
- [ ] A `parseChatScope(s): ChatScope | null` validator (rejects traversal, accepts the three
      forms) with its own unit test.
- [ ] The contract test passes; both a stub client funnel and a stub route import the shared
      types so the conformance check (CF-07) has two consumers.

**Blue**
- [ ] No duplicated scope vocabulary — `__all__`/`__unassigned__` sentinels are defined once
      and reused from `lib/productCounts.ts` where they already exist (no second source).
- [ ] Types are explicit and boring (no string-typed provider free-form; the union is closed).
