// WP-011 — <StartFromIntent /> — say what you want → a change starts at Recon
// (Journeys H + J; FR-29/30/34; FR-N6/N9; the SIGNED visual contract, WP-002).
//
// Say what you want in plain English → see the PROPOSAL (primitive + slug + repo
// plan) → CONFIRM → the new change appears at Recon. The surface is reached from
// the concierge front door's route-offer (WP-009 → /start) OR used directly as
// an intent box. It REUSES the composer idiom + the SSE client (EP-03), pointed
// at /api/changes/start-from-intent.
//
// The flow + the load-bearing rules baked in:
//   1. type an intent → the PROPOSAL is shown BEFORE any change starts (the
//      confirm gate, FR-N6); a reset starts nothing;
//   2. an investigation is framed as "I'll create a change to look into this" —
//      a CONTAINED change, never inline work (FR-34 / FR-N9);
//   3. an ambiguous intent surfaces ONE clarifying question (never a guess);
//   4. on confirm the change is started server-side (deterministic — the WP-010
//      lesson) and shown at Recon.
//
// Tokens only — no raw hex (WPF-07 / UXD-04). `streamStartFromIntent` is
// injectable for tests (defaults to the real funnel).

import { useEffect, useState, type KeyboardEvent } from "react";

import { useStartFromIntent } from "../api/useStartFromIntent";
import type { StreamStartFromIntentFn } from "../api/client";
import styles from "../styles/StartFromIntent.module.css";

interface Props {
  /** The Product whose Project repo the change starts against (FR-29). */
  productId: string;
  /** investigation frames the offer as a contained investigation (FR-N9). */
  kind?: "change" | "investigation";
  /** Injectable for tests; defaults to the real funnel. */
  streamStartFromIntent?: StreamStartFromIntentFn;
  /** Called once the change has started (host may navigate to the board). */
  onStarted?: (changeId: string) => void;
}

export function StartFromIntent({
  productId,
  kind,
  streamStartFromIntent,
  onStarted,
}: Props) {
  const start = useStartFromIntent({
    productId,
    ...(kind ? { kind } : {}),
    ...(streamStartFromIntent ? { streamStartFromIntent } : {}),
  });
  const [draft, setDraft] = useState("");

  const busy = start.isStreaming;
  const isInvestigation = kind === "investigation";

  const submit = () => {
    const intent = draft.trim();
    if (intent === "" || busy) return;
    void start.propose(intent);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const confirmAndNotify = async () => {
    await start.confirm();
  };

  // Surface the started change once it lands (the host wires onStarted to nav).
  // In an effect — never in the render body — so it fires exactly once per
  // started change and never triggers a parent state update during render.
  const startedChangeId =
    start.state === "started" && start.started ? start.started.changeId : null;
  useEffect(() => {
    if (startedChangeId !== null && onStarted) onStarted(startedChangeId);
  }, [startedChangeId, onStarted]);

  return (
    <section className={styles.frontdoor} aria-label="Start from intent">
      <div className={styles.scroll}>
        <header className={styles.hero}>
          <h2>{isInvestigation ? "Look into something" : "Start something new"}</h2>
          <p>
            {isInvestigation
              ? "Tell me what to look into, in plain English. I'll create a change to look into this — nothing runs until you confirm."
              : "Say what you'd like to do, in plain English. I'll work out what it is and start a change — nothing happens until you confirm."}
          </p>
        </header>

        {/* The PROPOSAL — shown before any change starts (the confirm gate). */}
        {start.proposal && start.state !== "started" && (
          <div className={styles.proposal} data-testid="start-proposal">
            <p className={styles.proposalLead}>
              {isInvestigation
                ? "I'll create a change to look into this:"
                : "Here's what I'll start:"}
            </p>
            <dl className={styles.recap}>
              <div className={styles.recapRow}>
                <dt>Kind</dt>
                <dd>{start.proposal.primitive}</dd>
              </div>
              <div className={styles.recapRow}>
                <dt>Name</dt>
                <dd>{start.proposal.slug}</dd>
              </div>
              {start.proposal.willCloneRepo && (
                <div className={styles.recapRow}>
                  <dt>Repo</dt>
                  <dd>I'll fetch a copy of the repository first.</dd>
                </div>
              )}
            </dl>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.confirm}
                disabled={busy}
                onClick={() => void confirmAndNotify()}
              >
                {isInvestigation ? "Create the change" : "Start it"}
              </button>
              <button
                type="button"
                className={styles.secondary}
                disabled={busy}
                onClick={start.reset}
              >
                Not yet
              </button>
            </div>
          </div>
        )}

        {/* The STARTED end state — the change is at Recon. */}
        {start.state === "started" && start.started && (
          <div className={styles.started} data-testid="start-started">
            <p className={styles.startedLead}>
              Done — your change <strong>{start.started.handle}</strong> has
              started.
            </p>
            <p className={styles.startedDetail}>
              It's at <strong>Recon</strong> on the board now.
            </p>
          </div>
        )}

        {/* A typed error — ambiguous intent's clarifying question, etc. */}
        {start.state === "failed" && start.errorMessage && (
          <div className={styles.error} role="alert" data-testid="start-error">
            {start.errorMessage}
          </div>
        )}
      </div>

      {/* The intent box — always available to (re)state what you want. */}
      <div className={styles.composer}>
        <label className={styles.srOnly} htmlFor="start-intent">
          {isInvestigation ? "What should I look into?" : "What would you like to do?"}
        </label>
        <textarea
          id="start-intent"
          className={styles.input}
          placeholder={
            isInvestigation
              ? "e.g. look into why checkout is slow"
              : "e.g. fix the login redirect loop"
          }
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={busy}
          rows={2}
        />
        <button
          type="button"
          className={styles.send}
          onClick={submit}
          disabled={busy || draft.trim() === ""}
        >
          Continue
        </button>
      </div>
    </section>
  );
}
