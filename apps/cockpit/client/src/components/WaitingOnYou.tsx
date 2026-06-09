// WP-005 — <WaitingOnYou>.
//
// The loud, full-width centered foot read shown ONLY when the change is
// waiting on the founder (the single-foot-verdict rule — health is hidden).
// Warning-triangle icon + bold "Waiting on you" + a short `why`. Stands out by
// WEIGHT (1.5px warning border + bold label), never colour alone, so it reads
// as the loud "act on me" state even in greyscale. The `why` truncates first;
// the icon + label never wrap-drop (TDD §5 / WP Contract).

import styles from "./WaitingOnYou.module.css";

export interface WaitingOnYouProps {
  /** the short reason the change needs the founder (truncates first). */
  why: string;
}

export function WaitingOnYou({ why }: WaitingOnYouProps) {
  return (
    <span className={styles.waiting}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path
          d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"
          strokeLinejoin="round"
        />
      </svg>
      <span className={styles.label}>Waiting on you</span>
      {why ? (
        <span className={styles.why} data-waiting-why>
          — {why}
        </span>
      ) : null}
    </span>
  );
}
