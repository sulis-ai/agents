// WP-002 — <ChatStatusLine> (TDD §2.1 + §3, ADR-002 + ADR-004).
//
// One calm status line above the message box, shared by both chats. It reads
// "Sulis is working…" while a reply streams and "Finished — over to you" on
// completion, then returns to the caller's suggestion chips once read. It is
// MUTUALLY EXCLUSIVE with the chips — it renders exactly one of
// {chips, working, finished} at a time.
//
// ADR-002: it adds NO state to useChatStream / useProductChat. It derives the
// slot from the existing hook `state` + a "reply produced this session" flag,
// plus a presentational "dismissed" latch it owns itself. "Finished" is the
// held `replying → ready` transition, not a lifecycle state.
//
// FR-19/FR-22 honesty (load-bearing): on `interrupted` / `failed` the line
// renders NOTHING in the slot — those notes render as their own bands above the
// slot, owned by the caller. The line never claims "finished" on a broken turn.

import { useState } from "react";
import { BoltIcon, CheckCircleIcon } from "@heroicons/react/20/solid";
import type { ChatLifecycle } from "../api/useChatStream";
import styles from "./ChatStatusLine.module.css";

/** The three mutually-exclusive presentational slots (+ the honest empty case). */
export type ChatStatusKind = "chips" | "working" | "finished" | "none";

/** States that mean "the agent is working" — replying plus its honest
 * waking/starting sub-states. */
const WORKING_STATES: ReadonlySet<ChatLifecycle> = new Set<ChatLifecycle>([
  "replying",
  "resuming",
  "spawning",
]);

/**
 * Pure slot derivation — the only new logic in this component. Kept as a
 * standalone, directly-unit-tested function so the JSX is a thin switch.
 *
 *   - working  when state ∈ {replying, resuming, spawning}
 *   - finished when a reply was produced this session, we are back to `ready`,
 *              and the founder has not yet dismissed it
 *   - chips    idle / your-turn, or after dismissal
 *   - none     interrupted / failed — the slot stays empty (caller owns the
 *              band above it); never "finished" on a broken/failed turn.
 */
export function statusSlot(
  state: ChatLifecycle,
  replyProduced: boolean,
  dismissed: boolean,
): ChatStatusKind {
  if (state === "interrupted" || state === "failed") return "none";
  if (WORKING_STATES.has(state)) return "working";
  if (state === "ready" && replyProduced && !dismissed) return "finished";
  return "chips";
}

export interface ChatStatusLineProps {
  /** The existing hook lifecycle (shared enum — not redefined here). */
  state: ChatLifecycle;
  /** True once a reply has been produced this session (drives "finished"). */
  replyProduced: boolean;
  /** The caller's suggestion chips for the idle / your-turn slot. */
  chips: React.ReactNode;
  /** Called when the founder dismisses the "finished" line by acting on it —
   * resets the slot back to chips. */
  onDismissFinished?: () => void;
}

export function ChatStatusLine({
  state,
  replyProduced,
  chips,
  onDismissFinished,
}: ChatStatusLineProps) {
  // The only local state: the presentational "finished was read/dismissed"
  // latch. No chat lifecycle state lives here (ADR-002).
  const [dismissed, setDismissed] = useState(false);

  const slot = statusSlot(state, replyProduced, dismissed);

  if (slot === "working") {
    return (
      <div
        className={`${styles.line} ${styles.working}`}
        role="status"
        aria-live="polite"
        data-testid="status-working"
      >
        <BoltIcon
          className={styles.icon}
          aria-hidden="true"
          data-testid="status-icon-working"
        />
        <span className={styles.label}>Sulis is working…</span>
      </div>
    );
  }

  if (slot === "finished") {
    const dismiss = () => {
      setDismissed(true);
      onDismissFinished?.();
    };
    // The line is the live region (matching the working line); the founder
    // dismisses it by acting on the inline "Got it" control — a real button
    // with a discernible name (the contract's "returns to chips once read").
    return (
      <div
        className={`${styles.line} ${styles.finished}`}
        role="status"
        aria-live="polite"
        data-testid="status-finished"
      >
        <CheckCircleIcon
          className={styles.tick}
          aria-hidden="true"
          data-testid="status-icon-finished"
        />
        <span className={styles.label}>Finished — over to you</span>
        <button
          type="button"
          className={styles.dismiss}
          data-testid="status-finished-dismiss"
          aria-label="Got it — back to suggestions"
          onClick={dismiss}
        >
          Got it
        </button>
      </div>
    );
  }

  // `chips` (idle / your-turn, or after dismissal). `none` (interrupted /
  // failed) renders nothing — the caller owns that band above the slot.
  if (slot === "chips") return <>{chips}</>;
  return null;
}
