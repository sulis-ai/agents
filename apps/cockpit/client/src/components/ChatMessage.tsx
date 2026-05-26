// WP-013 — <ChatMessage /> — discriminates by message.kind.
//
//   - "user" → right-aligned bubble; text rendered inside <pre><code>
//     for fidelity (no markdown parsing; founder sees exactly what they
//     typed, per WP-013 Risks & Notes — also prevents HTML/XSS).
//   - "assistant" → left-aligned bubble; iterates blocks, one
//     <AssistantBlock /> per block.
//   - "system" → <SystemChip />.

import type { TranscriptMessage } from "../../../shared/api-types";
import { AssistantBlock } from "./AssistantBlock";
import { SystemChip } from "./SystemChip";
import { formatRelativeTime } from "../utils/relativeTime";
import styles from "../styles/Chat.module.css";

interface Props {
  message: TranscriptMessage;
}

export function ChatMessage({ message }: Props) {
  if (message.kind === "user") {
    return (
      <div
        className={`${styles.bubble} ${styles.bubbleUser}`}
        data-testid="chat-message-user"
      >
        <pre className={styles.userText}>
          <code>{message.text}</code>
        </pre>
        <time
          className={styles.bubbleTime}
          dateTime={message.timestamp}
          title={message.timestamp}
        >
          {formatRelativeTime(message.timestamp)}
        </time>
      </div>
    );
  }

  if (message.kind === "assistant") {
    return (
      <div
        className={`${styles.bubble} ${styles.bubbleAssistant}`}
        data-testid="chat-message-assistant"
      >
        {message.blocks.map((block, idx) => (
          <AssistantBlock key={idx} block={block} />
        ))}
        <time
          className={styles.bubbleTime}
          dateTime={message.timestamp}
          title={message.timestamp}
        >
          {formatRelativeTime(message.timestamp)}
        </time>
      </div>
    );
  }

  // system
  return (
    <SystemChip
      subtype={message.subtype}
      text={message.text}
      timestamp={message.timestamp}
    />
  );
}

