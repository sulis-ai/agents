// WP-003 — <ProductChat>: the per-scope transcript + streaming reply (ADR-001).
//
// EXTENDS the concierge composer family by REUSING <ChatMessage> for the
// durable transcript (the same neutral user bubble / assistant blocks the rest
// of the cockpit uses) and rendering the in-flight streamed reply with a caret.
// It is a pure presentational piece — the dock owns the scope, the hook and the
// composer; this renders what the hook produced. The three honest states
// (loading skeleton / empty / error) live in the dock so the chrome is shared.

import type { ChatProvider, TranscriptMessage } from "../../../shared/api-types";
import { PROVIDER_NAME } from "../lib/providerName";
import { ChatMessage } from "./ChatMessage";
import styles from "./ProductChat.module.css";

export interface ProductChatProps {
  messages: TranscriptMessage[];
  /** The running provider — named in the streamed reply's "who" line (AI-07). */
  provider: ChatProvider;
  /** The in-flight streamed reply text (empty when idle). */
  replyText: string;
  isStreaming: boolean;
}

export function ProductChat({
  messages,
  provider,
  replyText,
  isStreaming,
}: ProductChatProps) {
  return (
    <div className={styles.thread} data-testid="product-chat-thread">
      {messages.map((m) => (
        <ChatMessage key={m.uuid} message={m} />
      ))}

      {(isStreaming || replyText.length > 0) && (
        <div className={styles.reply} data-testid="product-chat-reply">
          <div className={styles.who}>
            Sulis
            <span className={styles.ai}>{PROVIDER_NAME[provider]}</span>
          </div>
          <span className={styles.replyText}>
            {replyText}
            {isStreaming && (
              <span className={styles.caret} aria-hidden="true" data-testid="stream-caret" />
            )}
          </span>
        </div>
      )}
    </div>
  );
}
