// WP-P10 — <OriginTrace /> — the one-click trace card for an Origin.
//
// The shared trace body behind the open-file panel AND the Provenance lens
// detail (EP-03 — one trace renderer, two surfaces):
//
//   autonomous → the run row: run label (workflow) + outcome + confidence,
//                a link to the Provenance run log.
//   assisted   → the conversation Turn Card summary + an "Open conversation →"
//                jump (reuses the chat Turn Card idiom).
//   unknown    → the plain-English reason — honest, never a fabricated guess.
//
// When the origin is `inferred`, an honest "inferred from timing" note sits
// under the trace (the badge already carries the "· likely" hedge). The
// `onOpenConversation` / `onOpenRunLog` jumps are optional: when absent the
// trace still renders (read-only), it just omits the jump.

import type { Origin } from "../../../shared/api-types";
import {
  BoltIcon,
  UserIcon,
  ArrowRightIcon,
  CheckIcon,
  QuestionMarkCircleIcon,
  ClockIcon,
} from "./originIcons";
import styles from "../styles/Origin.module.css";

interface Props {
  origin: Origin;
  /** Jump to the conversation (assisted). Absent → the jump is hidden. */
  onOpenConversation?: () => void;
  /** Jump to the Provenance run log (autonomous). Absent → the row is static. */
  onOpenRunLog?: () => void;
}

/** Confidence may arrive 0–1 or 0–100; normalise to a whole percent. */
function confidencePct(n: number | null): string | null {
  if (n === null) return null;
  const v = n <= 1 ? Math.round(n * 100) : Math.round(n);
  return `${v}% confident`;
}

/** The honest "inferred from timing" note — only for an inferred attribution. */
function InferredNote({ attribution }: { attribution: Origin["attribution"] }) {
  if (attribution !== "inferred") return null;
  return (
    <div className={styles.tip} data-testid="origin-inferred-note">
      <ClockIcon aria-hidden="true" />
      “Likely” means we inferred it from timing — it isn’t stamped yet.
    </div>
  );
}

export function OriginTrace({
  origin,
  onOpenConversation,
  onOpenRunLog,
}: Props) {
  if (origin.kind === "autonomous") {
    const conf = confidencePct(origin.confidence);
    const runLabel = origin.run.workflow ?? "Autonomous run";
    return (
      <div data-testid="origin-trace">
        <div className={`${styles.tracecard} ${styles.autoT}`}>
          <div className={styles.th}>
            <BoltIcon aria-hidden="true" />
            <span className={styles.tk}>Made by an autonomous run</span>
            <span className={styles.tt}>no human in the loop for this change</span>
          </div>
          {onOpenRunLog ? (
            <button
              type="button"
              className={`${styles.runrow} ${styles.runlink}`}
              onClick={onOpenRunLog}
              data-testid="origin-open-runlog"
            >
              <span className={styles.ri} aria-hidden="true">
                <BoltIcon />
              </span>
              <span className={styles.rx}>
                <span className={styles.rn}>{runLabel}</span>
                <span className={styles.rm}>
                  Outcome: {origin.run.outcome} — open the run log to walk it.
                </span>
              </span>
              <span className={styles.minichips}>
                <span className={`${styles.mchip} ${styles.done}`}>
                  <CheckIcon aria-hidden="true" />
                  {origin.run.outcome}
                </span>
                {conf && <span className={`${styles.mchip} ${styles.conf}`}>{conf}</span>}
              </span>
            </button>
          ) : (
            <div className={styles.runrow}>
              <span className={styles.ri} aria-hidden="true">
                <BoltIcon />
              </span>
              <span className={styles.rx}>
                <span className={styles.rn}>{runLabel}</span>
                <span className={styles.rm}>Outcome: {origin.run.outcome}.</span>
              </span>
              <span className={styles.minichips}>
                <span className={`${styles.mchip} ${styles.done}`}>
                  <CheckIcon aria-hidden="true" />
                  {origin.run.outcome}
                </span>
                {conf && <span className={`${styles.mchip} ${styles.conf}`}>{conf}</span>}
              </span>
            </div>
          )}
        </div>
        <InferredNote attribution={origin.attribution} />
      </div>
    );
  }

  if (origin.kind === "assisted") {
    const summary =
      origin.conversation.summary ??
      "Shaped with you in a chat session on this change.";
    return (
      <div data-testid="origin-trace">
        <div className={styles.tracecard}>
          <div className={styles.th}>
            <UserIcon aria-hidden="true" />
            <span className={styles.tk}>Assisted in conversation</span>
            <span className={styles.tt}>a working chat session on this change</span>
          </div>
          <div className={styles.body}>
            <div className={styles.turncard}>
              <span className={styles.av} aria-hidden="true">
                <UserIcon />
              </span>
              <div className={styles.tcx}>
                <div className={styles.q}>“{summary}”</div>
                <div className={styles.meta}>
                  turn {origin.conversation.turn} · you + the agent
                </div>
              </div>
            </div>
          </div>
          {onOpenConversation && (
            <div className={styles.traceact}>
              <button
                type="button"
                className={styles.openconv}
                onClick={onOpenConversation}
                data-testid="origin-open-conversation"
              >
                Open conversation
                <ArrowRightIcon aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
        <InferredNote attribution={origin.attribution} />
      </div>
    );
  }

  // unknown — honest, never a fabricated guess.
  return (
    <div data-testid="origin-trace">
      <div className={styles.tracecard}>
        <div className={styles.unkmsg}>
          <QuestionMarkCircleIcon aria-hidden="true" />
          {origin.reason}
        </div>
      </div>
    </div>
  );
}
