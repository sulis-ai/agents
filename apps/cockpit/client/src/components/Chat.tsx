// WP-013 — <Chat /> — renders the chronological transcript for a change.
//
//   - Loading → "Loading conversation..."
//   - Error → "Could not load the conversation" + retry button (calls
//     queryClient.invalidateQueries internally via refetch()).
//   - Empty → <EmptyTranscript />.
//   - Non-empty → vertical list of <ChatMessage />s.
//
// Auto-scroll: a bottom sentinel calls scrollIntoView when the message
// list grows on initial load. Manual refresh reuses the same effect.

import { useEffect, useRef } from "react";
import { useTranscript } from "../api/useTranscript";
import { ChatMessage } from "./ChatMessage";
import { EmptyTranscript } from "./EmptyTranscript";
import styles from "../styles/Chat.module.css";

interface Props {
  changeId: string;
}

export function Chat({ changeId }: Props) {
  const query = useTranscript(changeId);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const messageCount = query.data?.length ?? 0;

  useEffect(() => {
    if (messageCount > 0) {
      // scrollIntoView is missing in jsdom by default; the file viewer
      // tests install it as a spy. Production browsers always have it.
      const node = bottomRef.current;
      if (node && typeof node.scrollIntoView === "function") {
        node.scrollIntoView({ behavior: "auto", block: "end" });
      }
    }
  }, [messageCount]);

  if (query.isLoading) {
    return (
      <div className={styles.status} data-testid="chat-loading">
        Loading conversation...
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className={styles.status} data-testid="chat-error">
        <p>Could not load the conversation.</p>
        <button
          type="button"
          className={styles.retryButton}
          onClick={() => query.refetch()}
        >
          Retry
        </button>
      </div>
    );
  }

  const messages = query.data ?? [];
  if (messages.length === 0) {
    return <EmptyTranscript />;
  }

  return (
    <div className={styles.chat} data-testid="chat-list">
      {messages.map((m) => (
        <ChatMessage key={m.uuid} message={m} />
      ))}
      <div ref={bottomRef} data-testid="chat-bottom-sentinel" />
    </div>
  );
}
