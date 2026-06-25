// WP-001 — CF-07 conformance stub: the CLIENT side of the chat-scope seam.
//
// One of the two conformance consumers the contract test exercises. It stands in
// for the real client funnel (WP-003 builds that for real): it produces the
// request shapes the client SENDS, typed against the shared wire types. Its only
// job here is to prove a consumer can be written against the contract — if the
// shared shape drifts, this stub stops compiling (the CF-07 gate).
//
// NO BEHAVIOUR ships in the contract WP. WP-003 replaces this with the real
// `useProductChat` funnel; this stub exists solely so producer (route stub) and
// consumer (this) agree on the wire by construction.

import type {
  ChatScope,
  ChatMessageRequest,
  ChatProviderRequest,
  ChatProvider,
} from "./api-types";

/** Build the `POST /api/chat/:scope/message` request body the client sends. */
export function stubChatClientFunnel(
  _scope: ChatScope,
  prompt: string,
): ChatMessageRequest {
  return { prompt };
}

/** Build the `PUT /api/chat/:scope/provider` request body the client sends. */
export function stubChatProviderRequest(
  _scope: ChatScope,
  provider: ChatProvider,
): ChatProviderRequest {
  return { provider };
}
