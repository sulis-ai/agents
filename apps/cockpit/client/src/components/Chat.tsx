// <Chat /> — the Turn-Cards transcript for a change (chat-B2 signed contract).
//
//   - Loading → "Loading conversation..."
//   - Error → "Could not load the conversation" + retry button.
//   - Empty → <EmptyTranscript />.
//   - Non-empty → the transcript grouped into the founder's message bubbles +
//     one Turn Card per agent turn (headline + prose + folded steps).
//
// Auto-scroll: a bottom sentinel calls scrollIntoView when the conversation
// grows on initial load. Manual refresh reuses the same effect.

import { useEffect, useRef } from "react";
import { useTranscript } from "../api/useTranscript";
import { useTurnSummaries } from "../api/useTurnSummaries";
import { EmptyTranscript } from "./EmptyTranscript";
import { TurnCard } from "./TurnCard";
import { groupTurns } from "../lib/groupTurns";
import { formatRelativeTime } from "../utils/relativeTime";
import convo from "../styles/Conversation.module.css";
import styles from "../styles/Chat.module.css";

interface Props {
  changeId: string;
}

export function Chat({ changeId }: Props) {
  const query = useTranscript(changeId);
  const summaries = useTurnSummaries(changeId);
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

  const items = groupTurns(messages);

  return (
    <div className={styles.chat} data-testid="chat-list">
      {items.map((item) =>
        item.type === "user" ? (
          <div key={item.key} className={convo.msgUser} data-testid="chat-message-user">
            <div className={convo.who}>You</div>
            <div className={convo.say}>{item.text}</div>
            <div className={convo.userTime}>
              {formatRelativeTime(item.timestamp)}
            </div>
          </div>
        ) : (
          <TurnCard
            key={item.key}
            turn={item}
            summary={summaries.data?.summaries?.[item.key]}
            generating={summaries.data?.generating?.includes(item.key) ?? false}
          />
        ),
      )}
      <div ref={bottomRef} data-testid="chat-bottom-sentinel" />
    </div>
  );
}
