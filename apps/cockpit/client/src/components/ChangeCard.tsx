// WP-005 — <ChangeCard> — the redesigned change card (production-approved
// MOCKUP). One card per change on the board; click navigates to /c/:changeId.
//
// EVERY card has the SAME reading order, top to bottom (identical every card):
//   topLine : handle (left) · LivenessProbe = probe dot + bare time (right)
//   steps   : slim ·N/6 step dots (role="img" aria-label="Step N of 6")
//   intent  : clamped to 2 lines (the calm fixed shape)
//   slug    : the meta line (the time lives on the top line, not duplicated)
//   foot    : EXACTLY ONE verdict — WaitingOnYou (flagged) XOR ChangeHealthBadge
//             (not flagged). Never both (the founder's load-bearing rule, TDD §5
//             / BR-1), enforced by a single branch.
//
// Dropped from the old card: the StageBadge pill (the lane already says the
// stage), the top banner, the left colour stripe.
//
// A11y: rendered as a <Link> whose accessible name carries the FULL handle +
// intent ("Change CH-… : <intent>"). The intent is clamped visually only — the
// full text stays reachable via the aria-label + title.

import { Link } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { stageStepNumber, STAGE_COUNT } from "./StageBadge";
import { LivenessProbe } from "./LivenessProbe";
import { ChangeHealthBadge } from "./ChangeHealthBadge";
import { WaitingOnYou } from "./WaitingOnYou";
import styles from "./ChangeCard.module.css";

export interface ChangeCardProps {
  change: Change;
  /** WP-009 — "open this change's terminal" action. When provided, the card
   *  renders an "Open terminal" button that opens the change's in-cockpit
   *  Terminal tab via this callback. Omitted → no terminal action rendered
   *  (existing dashboard usages unchanged). */
  onOpenTerminal?: (changeId: string) => void;
}

/** The slim "·N/6" step dots — the one non-redundant part of the old stage
 *  pill, kept as a tiny progress indicator with an SR text label. A terminal
 *  stage (no step number) renders the rail with no current dot. */
function StepDots({ step }: { step: number | null }) {
  const label =
    step !== null ? `Step ${step} of ${STAGE_COUNT}` : "Past the workflow";
  return (
    <div className={styles.steps} role="img" aria-label={label}>
      {Array.from({ length: STAGE_COUNT }, (_, i) => {
        const n = i + 1;
        const cls =
          step !== null && n === step
            ? `${styles.step} ${styles.stepCur}`
            : step !== null && n < step
              ? `${styles.step} ${styles.stepOn}`
              : styles.step;
        return <span key={n} className={cls} />;
      })}
    </div>
  );
}

/** Plain-English why-text for the waiting chip, from the fixed reason set.
 *  Never echoes any reply body (NFR-SEC-03) — these are enumerable shapes. */
function attentionWhy(reason: Change["needsAttention"]["reason"]): string {
  switch (reason) {
    case "blocked":
      return "blocked — needs a decision";
    case "waiting-on-decision":
      return "picking an approach";
    case "stopped-mid-reply":
      return "stopped mid-reply";
    case null:
    default:
      return "needs you";
  }
}

export function ChangeCard({ change, onOpenTerminal }: ChangeCardProps) {
  const step = stageStepNumber(change.stage);
  const flagged = change.needsAttention.flagged;

  return (
    <Link
      to={`/c/${change.changeId}`}
      className={styles.card}
      data-testid="change-card"
      aria-label={`Change ${change.handle}: ${change.intent}`}
    >
      <div className={styles.topLine}>
        <span className={styles.handle}>{change.handle}</span>
        <LivenessProbe
          liveness={change.liveness}
          lastActivityAt={change.lastActivityAt}
        />
      </div>

      <StepDots step={step} />

      {/* Intent is clamped to 2 lines in CSS so the card stays a calm fixed
       * shape; the full text stays reachable via the title + the card aria-label. */}
      <p className={styles.intent} title={change.intent}>
        {change.intent}
      </p>

      <div className={styles.cardMeta}>
        <span className={styles.slug}>{change.slug}</span>
      </div>

      {/* THE ONE FOOT VERDICT — waiting XOR health, never both (single branch). */}
      <div className={`${styles.footRow} ${flagged ? styles.waitingFoot : ""}`}>
        {flagged ? (
          <WaitingOnYou why={attentionWhy(change.needsAttention.reason)} />
        ) : (
          <ChangeHealthBadge health={change.health} />
        )}
      </div>

      {onOpenTerminal ? (
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.openTerminal}
            // The action lives inside the card's <Link>; stop the click from
            // also navigating to the change page — "open terminal" is a
            // distinct action from "open change".
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onOpenTerminal(change.changeId);
            }}
          >
            Open terminal
          </button>
        </div>
      ) : null}
    </Link>
  );
}
