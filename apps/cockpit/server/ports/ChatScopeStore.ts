// WP-002 — ChatScopeStore port (TDD §2.2; ADR-002, ADR-003).
//
// The domain-owned seam between the per-product chat routes and the durable,
// chat-scoped thread store. EXPAND-Create (a port the cockpit domain owns + one
// local adapter), NOT a wrap: the public face is THIS interface; the production
// adapter (adapters/LocalChatScopeStore) binds it to the SHIPPED Python
// `_session_manager.chat_scope_store` resolver over `LocalThreadStore` rooted at
// `~/.sulis/chat/{scope-key}/threads/` (ADR-002). Tests inject a fake so the
// routes are exercised with no shell-out and no daemon.
//
// Hexagonal shape mirrors `SessionBridge` / `ConversationIdentity`: the routes
// depend on this interface, never on an adapter. The scope vocabulary +
// validator are the shared `ChatScope` / `parseChatScope` (shared/chatScope.ts);
// the store keys by the validated scope.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces)
import type {
  ChatProvider,
  ChatScope,
  ChatThreadResponse,
} from "../../shared/api-types";

/**
 * The durable per-product chat store the routes read/write through (ADR-002).
 *
 * - `getThread` returns the scope's transcript + its resolved provider +
 *   productId (the `GET /thread` body). The overview scope (`product:__all__`)
 *   resolves `productId` to `null`.
 * - `rememberProvider` stamps the picker's choice per scope
 *   (`participant_context.provider`) — remembered, no schema fork.
 * - `resolveProvider` is the ADR-003 fallback order (picked → remembered →
 *   `pty`); it only ever yields a registered key, never a free-form string.
 *
 * Every method is async because the production adapter crosses the
 * library/process boundary into the Python store; the fake resolves
 * synchronously behind the same async shape.
 */
export interface ChatScopeStore {
  /** The scope's durable thread (messages + resolved provider + productId). */
  getThread(scope: ChatScope): Promise<ChatThreadResponse>;

  /** Remember the picker's chosen provider for the scope (AI-03: new work). */
  rememberProvider(scope: ChatScope, provider: ChatProvider): Promise<void>;

  /**
   * Resolve which provider to OPEN the scope's session on (ADR-003): `picked`
   * if registered, else the scope's remembered choice if registered, else the
   * safe default `pty`. `picked` is `null` when the caller has no explicit
   * choice (the message route resolves the remembered/default provider).
   */
  resolveProvider(
    scope: ChatScope,
    picked: ChatProvider | null,
  ): Promise<ChatProvider>;
}
