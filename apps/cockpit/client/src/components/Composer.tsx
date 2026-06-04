// <Composer /> — the floating chat dock (chat-B2 signed contract).
//
// Lifted off the bottom edge: a centred, rounded, shadowed box with a
// "Working · pause · stop" status chip just above it (so the live action and
// the input sit in the same comfortable reach — the founder's "hard to look to
// the bottom" fix). Suggestion chips + free text + a slash hint (AI-02), Enter
// sends / Shift+Enter newlines, a live streamed reply with a caret, pause/stop
// controls while replying (AI-03).
//
// It holds NO chat state of its own — `useChatStream` is the one source of
// truth (WPF-04). It reflects honest lifecycle states in plain English (FR-23),
// disables send while THIS change streams (FR-20), shows "reply was
// interrupted" + preserves the partial on a mid-stream break (FR-22), shows a
// clear failure WITHOUT marking delivered when unreachable (FR-19), and shows
// an honest "resumed" indication on a resume (FR-26).
//
// Tokens only — no raw hex. Heroicons for the controls. `streamChat` is
// injectable for tests (defaults to the real relay funnel).

import { useRef, useState, type KeyboardEvent } from "react";
import {
  PauseIcon,
  StopIcon,
  PaperAirplaneIcon,
  ArrowsPointingOutIcon,
  ArrowsPointingInIcon,
} from "@heroicons/react/20/solid";

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
  // Slack-style draft: the box grows with content, and an expand control
  // pops it to a tall draft editor for longer messages.
  const [expanded, setExpanded] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);

  const busy = chat.isStreaming;
  // A send is "active" while it's in flight, interrupted, or failed. On a clean
  // complete (state → ready) the dock's transient bubbles hand off to the main
  // conversation (which the hook refreshes), so we hide them here to avoid
  // showing the reply twice.
  const active = chat.state !== "ready";

  // Grow the textarea to fit its content (capped), the way Slack's draft does.
  const autosize = () => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    const cap = expanded ? 560 : 200;
    el.style.height = `${Math.min(el.scrollHeight, cap)}px`;
  };

  const submit = () => {
    const prompt = draft.trim();
    if (prompt === "" || busy) return;
    setLastSent(prompt);
    setDraft("");
    void chat.send(prompt);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
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
    <div className={styles.composerDock} data-testid="composer">
      {/* The live in-flight turn — shown in the dock only WHILE the send is
          active; on a clean complete it hands off to the main conversation. */}
      {lastSent !== null && active && (
        <div className={styles.composerInner}>
          <div
            className={styles.userMessage}
            data-testid="user-message"
            data-sender="you"
          >
            {lastSent}
          </div>
        </div>
      )}

      {showReply && active && (
        <div className={styles.composerInner}>
          <div className={styles.agentReply} data-testid="agent-reply">
            {chat.replyText}
            {chat.state === "replying" && (
              <span className={styles.caret} aria-hidden="true" />
            )}
          </div>
        </div>
      )}

      <div className={styles.composerInner}>
        {/* Honest "resumed" indication (FR-26). */}
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

        {/* Clear failure (FR-19): NOT shown as delivered. */}
        {chat.state === "failed" && (
          <div className={styles.chatError} data-testid="chat-error" role="alert">
            Couldn't reach this change.{" "}
            {chat.errorMessage ?? "The message was not delivered — try again."}
          </div>
        )}

        {/* The working status chip (AI-03) — pause/stop while replying. */}
        {busy && (
          <div className={styles.statuschip} data-testid="run-controls">
            <span className={styles.wd} aria-hidden="true" />
            <b>Working</b>
            {replyState && <span> · {replyState}</span>}
            <button
              type="button"
              className={styles.ctl}
              aria-label="Pause the agent"
            >
              <PauseIcon aria-hidden="true" />
              Pause
            </button>
            <button
              type="button"
              className={`${styles.ctl} ${styles.stop}`}
              aria-label="Stop the agent"
            >
              <StopIcon aria-hidden="true" />
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

        {/* The floating composer card — bigger, Slack-style expandable draft. */}
        <div
          className={`${styles.composer} ${expanded ? styles.expanded : ""} ${
            busy ? styles.busy : ""
          }`}
        >
          <button
            type="button"
            className={styles.expandBtn}
            aria-label={expanded ? "Shrink the message box" : "Expand the message box"}
            aria-pressed={expanded}
            data-testid="composer-expand"
            onClick={() => {
              setExpanded((v) => !v);
              // re-fit after the min-height changes
              requestAnimationFrame(autosize);
            }}
          >
            {expanded ? (
              <ArrowsPointingInIcon aria-hidden="true" />
            ) : (
              <ArrowsPointingOutIcon aria-hidden="true" />
            )}
          </button>
          <div className={styles.row}>
            <textarea
              ref={taRef}
              className={styles.textarea}
              rows={expanded ? 10 : 3}
              aria-label="Message this change's agent"
              placeholder="Reply to Sulis, or type / for a command…"
              value={draft}
              disabled={busy}
              onChange={(e) => {
                setDraft(e.target.value);
                autosize();
              }}
              onKeyDown={onKeyDown}
            />
            <button
              type="button"
              className={styles.send}
              disabled={busy || draft.trim() === ""}
              onClick={submit}
            >
              <PaperAirplaneIcon aria-hidden="true" />
              Send
            </button>
          </div>
          <div className={styles.foot}>
            <kbd>/</kbd> for commands · <kbd>/sign-off</kbd> · <kbd>/files</kbd>{" "}
            · <kbd>/status</kbd> · <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+
            <kbd>Enter</kbd> for a new line
          </div>
        </div>

        {busy && (
          <div className={styles.busynote}>
            One message at a time — you can send again the moment this reply
            finishes.
          </div>
        )}
      </div>
    </div>
  );
}
