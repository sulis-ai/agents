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

  /**
   * Append one chat turn to the scope's durable thread — the persistence
   * round-trip (WP-004, folded CONCERN DAT-PERSIST-01). The turn is persisted
   * through the REDACTING store path (the Python `LocalThreadStore` scrub), so
   * (a) the scope's history actually persists and `getThread` returns it, and
   * (b) chat content is scrubbed of secrets before any byte lands. The wire
   * `role` ("user" | "assistant") maps onto the shipped ThreadMessage
   * participant union; turns are appended at the next monotonic offset.
   */
  appendTurn(
    scope: ChatScope,
    role: "user" | "assistant",
    content: string,
  ): Promise<void>;

  /**
   * The REAL directory the scope's chat session runs in (WP-004, folded
   * ADV-CWD-01). Returns the scope's existing chat-store root, creating it if
   * absent, so the relay never runs in the server's own dir (the prior
   * `resolveChange(scope) === null → cwd:""` failure). Distinct scopes ground
   * to distinct directories (histories physically separate, ADR-002).
   */
  groundCwd(scope: ChatScope): Promise<string>;

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

  /**
   * Remember the per-CHANGE picker's chosen provider (CH-R5EE44 Fix 3, AI-03:
   * applies to the change's next session-open, never a hot-swap). A change id is
   * NOT a `ChatScope` — the per-change provider memory reuses the SAME on-disk
   * substrate as `rememberProvider` under a distinct `change/` root.
   */
  rememberChangeProvider(changeId: string, provider: ChatProvider): Promise<void>;

  /**
   * Resolve which provider to OPEN a CHANGE's session on (CH-R5EE44 Fix 3): the
   * change's remembered choice if registered, else the safe default `pty`. This
   * is the value the terminal sidecar's `resolveProvider(changeId)` consumes at
   * session-open (replacing the hardcoded `() => "pty"` literal).
   */
  resolveChangeProvider(changeId: string): Promise<ChatProvider>;
}
