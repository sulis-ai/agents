// WP-009 — <ConciergeChat /> — the concierge front door (FR-33/34/N8/N9; ADR-006).
//
// The plain-English front door: ask a question, a READ-ONLY answer streams
// back about your world (find a change, report status, Q&A over the change
// store + brain). It REUSES the chat composer idiom + the SSE client (EP-03) —
// not a parallel UI — pointed at /api/concierge/query.
//
// Containment is load-bearing (FR-N8/N9):
//   - the answer wears a "read-only — I only looked" honesty tag; the front
//     door performs NO write/mint/start itself;
//   - when intent is consequential (start work / investigate / empty-world
//     set-up) the concierge OFFERS the confirm-gated next step
//     (onboarding / start-from-intent) — it does NOT act inline. The OFFER
//     fires `onRoute(route)` only on the founder's explicit confirm.
//
// Tokens only — no raw hex (WPF-07 / UXD-04); built to the SIGNED visual
// contract (sulis-app.html, concierge front door). `streamQuery` is injectable
// for tests (defaults to the real read-only funnel).

import { useState, type KeyboardEvent } from "react";

import {
  useConciergeStream,
  type ConciergeRouteHint,
} from "../api/useConciergeStream";
import type { StreamConciergeFn } from "../api/client";
import styles from "../styles/ConciergeChat.module.css";

interface Props {
  /** Injectable for tests; defaults to the real read-only funnel. */
  streamQuery?: StreamConciergeFn;
  /** Optional Product scope for the answer (ADR-009). */
  productId?: string;
  /**
   * Called ONLY when the founder confirms a consequential offer (FR-N9). The
   * host wires this to navigate to onboarding / start-from-intent; the front
   * door never acts inline.
   */
  onRoute?: (route: Exclude<ConciergeRouteHint, null>) => void;
}

/** Suggestion chips (signed contract). Static read-only/start prompts. */
const SUGGESTION_CHIPS = [
  "What needs my attention?",
  "What have I got in flight?",
  "Start something new",
];

/** Plain-English label for a lifecycle state (FR-23 parity). */
function statusLabel(state: ReturnType<typeof useConciergeStream>["state"]): string | null {
  switch (state) {
    case "thinking":
      return "Looking across your work…";
    case "replying":
      return "Answering…";
    default:
      return null;
  }
}

/** The confirm-gated OFFER copy for a route hint (FR-N9 — offer, not act). */
function offerCopy(route: Exclude<ConciergeRouteHint, null>): {
  body: string;
  cta: string;
} {
  if (route === "onboarding") {
    return {
      body: "It looks like nothing's set up yet. I can set you up in a quick conversation — I'll ask before I do anything.",
      cta: "Set me up",
    };
  }
  return {
    body: "That's a piece of work, so I'll give it its own change to live in — tracked, self-contained, and ready to turn into a fix. Nothing happens until you say go.",
    cta: "Start this change",
  };
}

export function ConciergeChat({ streamQuery, productId, onRoute }: Props) {
  const concierge = useConciergeStream({
    ...(streamQuery ? { streamQuery } : {}),
    ...(productId ? { productId } : {}),
  });
  const [draft, setDraft] = useState("");
  const [lastAsked, setLastAsked] = useState<string | null>(null);

  const busy = concierge.isStreaming;

  const submit = () => {
    const question = draft.trim();
    if (question === "" || busy) return;
    setLastAsked(question);
    setDraft("");
    void concierge.ask(question);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const statusText = statusLabel(concierge.state);
  const showAnswer =
    concierge.answerText.length > 0 || concierge.state === "replying";
  // The route OFFER appears once the answer completes (state back to "ready")
  // and a consequential route was hinted — never while still streaming.
  const showOffer =
    concierge.route !== null &&
    concierge.state === "ready" &&
    !busy;

  return (
    <div className={styles.frontdoor} data-testid="concierge">
      <div className={styles.scroll}>
        <div className={styles.hero}>
          <h2>What can I help with?</h2>
          <p>
            I can find a change, tell you where something's up to, answer
            questions about your work, or start something new. I don't do the
            work myself — I set it up and hand it to a change.
          </p>
        </div>

        {/* The founder's own question — neutral bubble, alignment not fill. */}
        {lastAsked !== null && (
          <div
            className={styles.userMessage}
            data-testid="concierge-question"
            data-sender="you"
          >
            {lastAsked}
          </div>
        )}

        {/* The streamed read-only answer + the honesty tag (FR-33/N8). */}
        {showAnswer && (
          <div className={styles.answerWrap}>
            <div className={styles.answer} data-testid="concierge-answer">
              {concierge.answerText}
              {concierge.state === "replying" && (
                <span className={styles.caret} aria-hidden="true" />
              )}
            </div>
            {concierge.state === "ready" && (
              <span className={styles.readonlyTag} data-testid="readonly-tag">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                I only looked — nothing was changed
              </span>
            )}
          </div>
        )}

        {/* Consequential intent: OFFER the confirm-gated next step (FR-N9). */}
        {showOffer && concierge.route !== null && (
          <div className={styles.offer} data-testid="route-offer">
            <p className={styles.offerBody}>{offerCopy(concierge.route).body}</p>
            <div className={styles.offerActions}>
              <button
                type="button"
                className={styles.offerConfirm}
                data-testid="route-confirm"
                onClick={() => {
                  if (concierge.route !== null) onRoute?.(concierge.route);
                }}
              >
                {offerCopy(concierge.route).cta}
              </button>
              <button
                type="button"
                className={styles.offerDecline}
                data-testid="route-decline"
              >
                Not now
              </button>
            </div>
          </div>
        )}

        {/* Honest failure (FR-19) — NOT shown as an answer. */}
        {concierge.state === "failed" && (
          <div
            className={styles.error}
            data-testid="concierge-error"
            role="alert"
          >
            Couldn't reach the concierge.{" "}
            {concierge.errorMessage ?? "Try again in a moment."}
          </div>
        )}
      </div>

      <div className={styles.composerWrap}>
        {busy && statusText && (
          <div className={styles.statusLine} data-testid="concierge-status">
            {statusText}
          </div>
        )}

        <div className={styles.chips}>
          {SUGGESTION_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              className={styles.chip}
              data-testid="concierge-chip"
              disabled={busy}
              onClick={() => setDraft(chip)}
            >
              {chip}
            </button>
          ))}
        </div>

        <div className={`${styles.composer} ${busy ? styles.composerBusy : ""}`}>
          <div className={styles.field}>
            <textarea
              className={styles.textarea}
              aria-label="Ask the concierge"
              placeholder="Ask me anything, or tell me what to start…  —  type / for commands"
              value={draft}
              disabled={busy}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKeyDown}
            />
            <div className={styles.slashhint}>
              <kbd>/</kbd> for commands — <kbd>/find</kbd> · <kbd>/status</kbd> ·{" "}
              <kbd>/start</kbd> &nbsp;·&nbsp; <kbd>Enter</kbd> to send
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
      </div>
    </div>
  );
}
