// WP-005 — <ChangeHealthBadge>.
//
// The quieter foot read, shown ONLY when the change is NOT waiting on the
// founder (the single-foot-verdict rule). Word + SHAPE (never colour alone) +
// an SR reason. Renders all four states; data drives which:
//   on-track     → check
//   off-track    → warning triangle
//   worth-a-look → dash / minus (the carried deferred-input read)
//   unknown      → a NEUTRAL outline circle + "Not assessed yet" (FR-31) —
//                  the honest "not enough signal yet" read, never a green lie
//                  (on-track) and never a red alarm (off-track).
//
// Left-aligned, content-width — the quiet default. Thin 1px border; the reason
// is appended SR-only and truncates first so the foot stays one line.

import type { ChangeHealth, ChangeHealthState } from "../../../shared/api-types";
import styles from "./ChangeHealthBadge.module.css";

/**
 * The unknown-health wording — the founder default (Q-5), a single swappable
 * string constant. Tunable on confirmation without touching the render logic.
 */
export const HEALTH_UNKNOWN_LABEL = "Not assessed yet";

const WORD: Record<ChangeHealthState, string> = {
  "on-track": "On track",
  "off-track": "Off track",
  "worth-a-look": "Worth a look",
  unknown: HEALTH_UNKNOWN_LABEL,
};

const STATE_CLASS: Record<ChangeHealthState, string> = {
  "on-track": styles.onTrack!,
  "off-track": styles.offTrack!,
  "worth-a-look": styles.look!,
  unknown: styles.unassessed!,
};

function HealthIcon({ state }: { state: ChangeHealthState }) {
  switch (state) {
    case "on-track":
      // a check
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} aria-hidden="true">
          <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "off-track":
      // a warning triangle
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" strokeLinejoin="round" />
        </svg>
      );
    case "worth-a-look":
      // a dash / minus
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} aria-hidden="true">
          <path d="M5 12h14" strokeLinecap="round" />
        </svg>
      );
    case "unknown":
    default:
      // a hollow outline circle — an empty gauge, "nothing measured yet"
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
        </svg>
      );
  }
}

export interface ChangeHealthBadgeProps {
  health: ChangeHealth;
}

export function ChangeHealthBadge({ health }: ChangeHealthBadgeProps) {
  const { state, reason } = health;
  return (
    <span
      className={`${styles.health} ${STATE_CLASS[state]}`}
      data-health-state={state}
    >
      <HealthIcon state={state} />
      {WORD[state]}
      <span className={styles.sr}> — {reason}</span>
    </span>
  );
}
