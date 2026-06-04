// WP-005 — <Composer /> — the docked write surface (signed visual contract; ADR-005).
//
// The thread's persistent chat dock. Built to the SIGNED contract
// (contracts/visual/sulis-app.html, panel 4): suggestion chips + free text + a
// slash-command hint (AI-02 dual-mode input), Enter sends / Shift+Enter
// newlines, a live streamed reply with a caret, pause/stop run-controls while
// the agent replies (AI-03 human-in-the-loop), and the founder's own message
// in a NEUTRAL bubble (alignment, not a brand fill).
//
// It holds NO chat state of its own — `useChatStream` is the one source of
// truth (WPF-04). It reflects honest lifecycle states in plain English (FR-23),
// disables send while THIS change streams (FR-20), shows "reply was
// interrupted" + preserves the partial on a mid-stream break (FR-22), shows a
// clear failure WITHOUT marking delivered when unreachable (FR-19), and shows
// an honest "resumed" indication on a resume (FR-26 — never "silently
// continued").
//
// Tokens only — no raw hex (WPF-07 / UXD-04). `streamChat` is injectable for
// tests (defaults to the real relay funnel).

import { useState, type KeyboardEvent } from "react";

import { useChatStream } from "../api/useChatStream";
import type { StreamChatFn } from "../api/client";
import styles from "../styles/Composer.module.css";

interface Props {
  changeId: string;
  /** Injectable for tests; defaults to the real relay funnel. */
  streamChat?: StreamChatFn;
}

/** Contextual suggestion chips (AI-02). Static set per the signed contract. */
const SUGGESTION_CHIPS = [
  "Sign off on the design",
  "What's left before build?",
  "Adjust the board layout",
];

/** Map a lifecycle state to a plain-English status line (FR-23). */
function statusLabel(
  state: ReturnType<typeof useChatStream>["state"],
): string | null {
  switch (state) {
    case "resuming":
      return "Waking the change up…";
    case "spawning":
      return "Starting this change up…";
    case "replying":
      return "Agent is replying…";
    default:
      return null;
  }
}

export function Composer({ changeId, streamChat }: Props) {
  const chat = useChatStream(changeId, streamChat ? { streamChat } : {});
  const [draft, setDraft] = useState("");
  const [lastSent, setLastSent] = useState<string | null>(null);

  const busy = chat.isStreaming;

  const submit = () => {
    const prompt = draft.trim();
    if (prompt === "" || busy) return;
    setLastSent(prompt);
    setDraft("");
    void chat.send(prompt);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends; Shift+Enter inserts a newline (signed contract).
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const replyState = statusLabel(chat.state);
  const showReply =
    chat.replyText.length > 0 ||
    chat.state === "replying" ||
    chat.state === "interrupted";

  return (
    <div className={styles.composerWrap} data-testid="composer">
      {/* The conversation tail this send adds to: the founder's neutral bubble,
          then the streamed agent reply. The full transcript lives in <Chat />;
          this is the live in-flight turn. */}
      {lastSent !== null && (
        <div
          className={styles.userMessage}
          data-testid="user-message"
          data-sender="you"
        >
          {lastSent}
        </div>
      )}

      {showReply && (
        <div className={styles.agentReply} data-testid="agent-reply">
          {chat.replyText}
          {chat.state === "replying" && (
            <span className={styles.caret} aria-hidden="true" />
          )}
        </div>
      )}

      {/* Honest "resumed" indication (FR-26) — never "silently continued". */}
      {chat.resumed && chat.state === "ready" && (
        <div className={styles.resumedNote} data-testid="resumed-note">
          This change was resumed — it picked up where it left off.
        </div>
      )}

      {/* Mid-stream break (FR-22): the partial above is preserved. */}
      {chat.state === "interrupted" && (
        <div className={styles.interruptedNote} data-testid="interrupted-note">
          The reply was interrupted. The part received so far is kept above.
        </div>
      )}

      {/* Clear failure (FR-19): NOT shown as delivered (no agent bubble). */}
      {chat.state === "failed" && (
        <div className={styles.chatError} data-testid="chat-error" role="alert">
          Couldn't reach this change.{" "}
          {chat.errorMessage ?? "The message was not delivered — try again."}
        </div>
      )}

      {/* Run-controls (AI-03): pause/stop while replying. */}
      {busy && (
        <div className={styles.runbar} data-testid="run-controls">
          <span className={styles.runLabel}>{replyState ?? "Working…"}</span>
          <button
            type="button"
            className={styles.iconbtn}
            aria-label="Pause the agent"
          >
            Pause
          </button>
          <button
            type="button"
            className={`${styles.iconbtn} ${styles.stop}`}
            aria-label="Stop the agent"
          >
            Stop
          </button>
        </div>
      )}

      {/* Suggestion chips (AI-02). */}
      <div className={styles.chips}>
        {SUGGESTION_CHIPS.map((chip) => (
          <button
            key={chip}
            type="button"
            className={styles.sugchip}
            data-testid="suggestion-chip"
            disabled={busy}
            onClick={() => setDraft(chip)}
          >
            {chip}
          </button>
        ))}
      </div>

      {/* The composer: free text + slash hint + Send (the one blue action). */}
      <div className={`${styles.composer} ${busy ? styles.busy : ""}`}>
        <div className={styles.field}>
          <textarea
            className={styles.textarea}
            aria-label="Message this change's agent"
            placeholder="Message this change's agent…  —  type / for commands"
            value={draft}
            disabled={busy}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <div className={styles.slashhint}>
            <kbd>/</kbd> for commands — <kbd>/sign-off</kbd> · <kbd>/files</kbd>{" "}
            · <kbd>/status</kbd> &nbsp;·&nbsp; <kbd>Enter</kbd> to send,{" "}
            <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
          </div>
        </div>
        <button
          type="button"
          className={styles.send}
          disabled={busy || draft.trim() === ""}
          onClick={submit}
        >
          Send
        </button>
      </div>

      {busy && (
        <div className={styles.busynote}>
          One message at a time — you can send again the moment this reply
          finishes.
        </div>
      )}
    </div>
  );
}
