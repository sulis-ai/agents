// WP-003 — <ProductChat>: the per-scope durable transcript + streaming reply.
//
// REUSES the in-change chat's summary-card primitive (ADR-001): the durable
// transcript is grouped with the same pure `groupTurns()` `Chat.tsx` uses, and
// each agent turn renders as one `<TurnCard>` — summary lead + "show the full
// reply" + folded steps + safe markdown — instead of the old plain-text
// `AssistantBlock` path. No new renderer, no markdown library (EP-03); the
// universal chat inherits `TurnCard`'s safe-render invariant
// (`renderMarkdown`/`renderInlineMarkdown`, escape-before-emit).
//
// Per ADR-003 the card is rendered with NO `summary` prop, so it shows its
// built-in first-sentences fallback (the universal chat is product-scoped and
// has no change-scoped summary endpoint). User messages stay verbatim (spec
// non-goal). The in-flight streamed reply still renders here, plain + caret.
// This is a pure presentational piece — the dock owns the scope, the hook and
// the composer; the three honest states (loading / empty / error) live in the
// dock so the chrome is shared.

import type { ChatProvider, TranscriptMessage } from "../../../shared/api-types";
import { PROVIDER_NAME } from "../lib/providerName";
import { groupTurns } from "../lib/groupTurns";
import { TurnCard } from "./TurnCard";
import { UserBubble } from "./UserBubble";
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
  // Group the flat transcript into the founder's message bubbles + one turn
  // per run of agent messages — the SAME pure transform Chat.tsx uses, so the
  // universal chat groups its product transcript exactly as the in-change chat
  // groups a change transcript (ADR-001).
  const items = groupTurns(messages);

  return (
    <div className={styles.thread} data-testid="product-chat-thread">
      {items.map((item) =>
        item.type === "user" ? (
          // Verbatim user text — never markdown-rendered (spec non-goal). The
          // bubble is the shared <UserBubble> both chats render (EP-03).
          <UserBubble key={item.key} item={item} />
        ) : (
          // No `summary` prop → the card shows its first-sentences fallback
          // (ADR-003); markdown flows through TurnCard's safe renderer.
          <TurnCard key={item.key} turn={item} />
        ),
      )}

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
