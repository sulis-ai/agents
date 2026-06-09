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
//
// WP-011 — the DEGRADED / PARTIAL composition (FR-54 / FR-55 / BR-26 / S-35).
// A malformed or partial record renders PER-FIELD: every readable field renders
// normally; every unreadable field falls to its EXISTING unknown read (health →
// "Not assessed yet" FR-31; liveness → the distinct unknown "?" probe FR-41;
// recency → "—" FR-42; missing slug/intent → an honest FIXED placeholder). The
// card STILL renders and STILL links (so the founder can go investigate), and a
// quiet, FIXED-STRING, aria-announced "Some details couldn't be read" notice
// names the partial state in words — reinforcement of the per-field reads
// (BR-3), never echoing the malformed content (NFR-SEC-03 / FR-32). One bad
// record degrades INDEPENDENTLY: it never drops a sibling or breaks the lane
// (BR-26). The unknown reads REUSE the WP-005 components — no second unknown
// implementation (EP-03).
//
// WP-012 — the SHIPPED / TERMINAL composition (FR-56 / BR-27 / BR-28 / S-36).
// A change in the terminal stage (`stage === "shipped"`, the SAME predicate the
// Sidebar split + StageBadge use — BR-27, reused not reinvented) reads as
// ARCHIVED, not active. The card is MUTED; the LivenessProbe is REPLACED by a
// static "Shipped" marker (no working/live/idle, no pulse); BOTH live feet are
// suppressed (BR-28 MUST — neither "Waiting on you" nor the change-health badge
// renders); and recency reads "shipped Nd ago" (the Q-7 one-constant archival
// wording from formatShippedRecency), NOT a live-activity age. Shipped wins the
// foot/probe treatment over the degraded reads (SRD §7c precedence), but any
// unreadable IDENTITY field (slug/intent) still falls to its WP-011 unknown
// read + the degraded notice — the per-field honesty is orthogonal to the
// terminal treatment.

import { Link } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { stageStepNumber, STAGE_COUNT } from "./StageBadge";
import { LivenessProbe } from "./LivenessProbe";
import { ChangeHealthBadge } from "./ChangeHealthBadge";
import { WaitingOnYou } from "./WaitingOnYou";
import { formatShippedRecency } from "../utils/relativeTime";
import styles from "./ChangeCard.module.css";

export interface ChangeCardProps {
  change: Change;
  /** WP-009 — "open this change's terminal" action. When provided, the card
   *  renders an "Open terminal" button that opens the change's in-cockpit
   *  Terminal tab via this callback. Omitted → no terminal action rendered
   *  (existing dashboard usages unchanged). */
  onOpenTerminal?: (changeId: string) => void;
  /** "now" override for deterministic tests; defaults to the real clock.
   *  Forwarded to the live probe (the working/live recency split) and the
   *  shipped-recency ("shipped Nd ago") read so both bucket against one clock. */
  now?: Date;
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

/**
 * WP-011 — the FIXED degraded vocabulary (FR-55 / FR-32 / MUC-3). Every string
 * here is a constant from the enumerable set — none is interpolated from the
 * record's content (NFR-SEC-03). The notice is the single source the card
 * surfaces; the per-field unknown reads carry the primary signal (BR-3).
 */
export const DEGRADED_NOTICE = "Some details couldn't be read";
/** Honest placeholders for content fields that came back unreadable. Fixed
 *  strings — never the (possibly malformed) row content itself. */
const INTENT_UNREADABLE = "Details couldn't be read";
const SLUG_UNREADABLE = "slug unavailable";

/**
 * WP-011 — is this a malformed / partial record (FR-54)? Two honest signals:
 *
 *  1. A readable CONTENT field is missing — an empty/blank slug or intent. A
 *     well-formed record always carries both; their absence means the row could
 *     not be fully read.
 *  2. The COMBINED unknown signal — liveness AND health both came back
 *     `unknown`. A SINGLE unknown read is the honest fresh-change case ("too
 *     early to tell") and is NOT degraded; both unknown together is the
 *     malformed-record shape (the producer's never-throw output, WP-002).
 *
 * Pure, no I/O — a render-time predicate over the wire `Change`. Exported so the
 * card test and any future consumer share ONE definition (CF-02 / DRY).
 */
export function isDegraded(change: Change): boolean {
  const missingContent =
    change.slug.trim() === "" || change.intent.trim() === "";
  const bothUnknown =
    change.liveness.status === "unknown" && change.health.state === "unknown";
  return missingContent || bothUnknown;
}

/**
 * WP-012 — the TERMINAL predicate (BR-27). A change in the terminal stage reads
 * as ARCHIVED, not active. This is the SAME `stage === "shipped"` test the
 * Sidebar split + StageBadge already use — reused, never a second detector.
 * Exported so the card test and any future consumer share ONE definition.
 */
export function isShipped(change: Change): boolean {
  return change.stage === "shipped";
}

/**
 * WP-012 — the static "Shipped" marker that REPLACES the LivenessProbe on a
 * terminal card (FR-56 / BR-28). It carries NO probe dot, NO motion, NO
 * working/live/idle state — a shipped change has no live session to read. The
 * word "Shipped" carries the meaning in text (never colour/placement alone), so
 * a screen reader hears "archived", not silence.
 */
function ShippedMarker() {
  return (
    <span
      className={styles.shippedMarker}
      data-testid="shipped-marker"
      data-shipped-marker
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.9}
        aria-hidden="true"
      >
        {/* an archive box — the calm "filed away" glyph */}
        <path
          d="M3 7h18M5 7v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7M3 7l2-3h14l2 3M10 12h4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      Shipped
    </span>
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

export function ChangeCard({ change, onOpenTerminal, now }: ChangeCardProps) {
  const step = stageStepNumber(change.stage);
  const flagged = change.needsAttention.flagged;
  const degraded = isDegraded(change);
  // WP-012 — terminal/archived treatment. Shipped wins the foot/probe over the
  // live + degraded reads (SRD §7c precedence); the per-field identity reads
  // below still apply (an unreadable slug/intent still falls to its placeholder).
  const shipped = isShipped(change);

  // Per-field degraded fallbacks (FR-54): readable fields render verbatim;
  // unreadable content fields fall to a FIXED placeholder — never blank, never
  // the (possibly malformed) row text. The aria-label keeps an honest name even
  // when the intent is unreadable.
  const intentText =
    change.intent.trim() === "" ? INTENT_UNREADABLE : change.intent;
  const slugText = change.slug.trim() === "" ? SLUG_UNREADABLE : change.slug;
  const ariaIntent =
    change.intent.trim() === ""
      ? "some details couldn't be read"
      : change.intent;

  return (
    <Link
      to={`/c/${change.changeId}`}
      className={`${styles.card} ${degraded ? styles.degraded : ""} ${shipped ? styles.shipped : ""}`}
      data-testid="change-card"
      data-degraded={degraded ? "true" : undefined}
      data-shipped={shipped ? "true" : undefined}
      aria-label={`Change ${change.handle}: ${ariaIntent}`}
    >
      <div className={styles.topLine}>
        <span className={styles.handle}>{change.handle}</span>
        {/* WP-012 — a shipped card REPLACES the live probe with the static
         * "Shipped" marker (BR-28 — no live signal on a terminal card). */}
        {shipped ? (
          <ShippedMarker />
        ) : (
          <LivenessProbe
            liveness={change.liveness}
            lastActivityAt={change.lastActivityAt}
            now={now}
          />
        )}
      </div>

      <StepDots step={step} />

      {/* Intent is clamped to 2 lines in CSS so the card stays a calm fixed
       * shape; the full text stays reachable via the title + the card aria-label. */}
      <p className={styles.intent} title={intentText}>
        {intentText}
      </p>

      <div className={styles.cardMeta}>
        <span className={styles.slug}>{slugText}</span>
        {/* WP-012 — shipped recency: the archival "shipped Nd ago" read (Q-7),
         * NOT a live age. Derived from `updatedAt` (the shipped-at time; always
         * present, unlike the nullable lastActivityAt). */}
        {shipped ? (
          <span className={styles.shippedRecency} data-testid="shipped-recency">
            {formatShippedRecency(change.updatedAt, now)}
          </span>
        ) : null}
      </div>

      {/* THE ONE FOOT VERDICT — waiting XOR health, never both (single branch).
       * WP-012 — SUPPRESSED entirely on a shipped card: a terminal change shows
       * NEITHER live foot (BR-28 mutual suppression). The static "Shipped"
       * marker + the shipped recency are its only status reads. */}
      {shipped ? null : (
        <div
          className={`${styles.footRow} ${flagged ? styles.waitingFoot : ""}`}
        >
          {flagged ? (
            <WaitingOnYou why={attentionWhy(change.needsAttention.reason)} />
          ) : (
            <ChangeHealthBadge health={change.health} />
          )}
        </div>
      )}

      {/* WP-011 — the quiet, FIXED-STRING degraded notice (FR-55). Reinforcement
       * of the per-field unknown reads (BR-3); role="status" announces it so it
       * is never colour-/placement-alone (NFR-A11Y-4). Never interpolates the
       * row content (NFR-SEC-03). */}
      {degraded ? (
        <div className={styles.degradedNote} role="status">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.8}
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
          </svg>
          {DEGRADED_NOTICE}
        </div>
      ) : null}

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
