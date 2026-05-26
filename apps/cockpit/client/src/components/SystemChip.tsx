// WP-013 — <SystemChip /> — small full-width chip rendering a transcript
// "system" message (subtype + text).
//
// Visually distinct from the conversation bubbles so the founder sees
// system records as "system noise" rather than dialogue (WP-013 Risks &
// Notes section).

import styles from "../styles/Chat.module.css";

interface Props {
  subtype: string;
  text: string;
  timestamp: string;
}

export function SystemChip({ subtype, text, timestamp }: Props) {
  return (
    <div className={styles.systemChip} data-testid="system-chip">
      <span className={styles.systemSubtype}>{subtype}</span>
      <span className={styles.systemText}>{text}</span>
      <time className={styles.systemTime} dateTime={timestamp}>
        {formatTime(timestamp)}
      </time>
    </div>
  );
}

function formatTime(iso: string): string {
  // Minimal "HH:MM" rendering for the chip — the relative-time helper
  // owned by <ChatMessage /> is for bubbles; system chips stay terse.
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}
