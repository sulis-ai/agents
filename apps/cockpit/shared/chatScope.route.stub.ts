// WP-001 — CF-07 conformance stub: the SERVER side of the chat-scope seam.
//
// The second conformance consumer the contract test exercises. It stands in for
// the real server route (WP-002 builds that for real): it produces the response
// shapes the server SERVES, typed against the shared wire types. Like the client
// stub, its only job is to prove a producer can be written against the contract
// — drift in the shared shape breaks compilation (the CF-07 gate).
//
// NO BEHAVIOUR ships in the contract WP. The productId resolution here is a fixed
// stub (overview scope → null, else a placeholder id); WP-002 replaces it with
// the real `resolve_chat_thread(chatScope)` over `LocalThreadStore` (ADR-002).

import type { ChatScope, ChatThreadResponse, ChatProvider } from "./api-types";
import { ALL_SCOPE } from "./chatScope";

/**
 * Stub the `GET /api/chat/:scope/thread` response. The overview scope
 * (`product:__all__`) resolves `productId` to null; any other scope resolves to
 * a placeholder product id. The default provider is `pty` (Claude) per ADR-003's
 * safe fallback. Real history + the remembered provider land in WP-002.
 */
export function stubChatThreadRoute(scope: ChatScope): ChatThreadResponse {
  const isOverview = scope === `product:${ALL_SCOPE}`;
  const provider: ChatProvider = "pty";
  return {
    messages: [],
    provider,
    productId: isOverview ? null : "dna:product:01HZX9",
  };
}
