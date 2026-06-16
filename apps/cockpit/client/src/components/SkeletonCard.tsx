// WP-010 — <SkeletonCard> — the per-card loading placeholder.
//
// What a card looks like WHILE the feed is resolving, before any real data
// exists. Transcribed from the production-approved visual contract
// (.design/cockpit-board-refresh/MOCKUP.html — "Alternate card states" →
// LOADING / SKELETON): calm placeholder bars where the handle · probe · step
// dots · two title lines · foot will be — NEVER a spinner. A gentle
// left-to-right shimmer reads as "loading"; under `prefers-reduced-motion:
// reduce` the sweep drops and the calm muted bars stay (BR-25).
//
// NO LAYOUT JUMP (BR-24 / NFR-PERF-5): the skeleton occupies the SAME card box
// as a real <ChangeCard> — same border, radius, padding, background — so when
// the real card replaces it the box does not move (CLS ≈ 0). The box metrics
// are the shared card-box tokens (SkeletonCard.module.css consumes the same
// values the real card's frame does), not duplicated magic dimensions (EP-03).
//
// INERT (§7c precedence — no real card exists yet): the whole card is
// `aria-hidden` (a screen reader is told the region is loading by the lane's
// aria-busy + SR line, not by reading meaningless bars), and it contains
// nothing focusable — it is never a tab stop.

import styles from "./SkeletonCard.module.css";

/**
 * A single loading placeholder card. Decorative + inert: render N of these in
 * a lane while the feed is pending. The bars echo the real card's structure so
 * the box is identical to the card that will replace it.
 */
export function SkeletonCard() {
  return (
    <div
      className={styles.skeleton}
      data-testid="skeleton-card"
      aria-hidden="true"
    >
      <div className={styles.skTop}>
        <span className={`${styles.sk} ${styles.skHandle}`} data-skeleton-bar />
        <span className={`${styles.sk} ${styles.skProbe}`} data-skeleton-bar />
      </div>
      <span className={`${styles.sk} ${styles.skSteps}`} data-skeleton-bar />
      <span className={`${styles.sk} ${styles.skTitle}`} data-skeleton-bar />
      <span
        className={`${styles.sk} ${styles.skTitle} ${styles.skTitleShort}`}
        data-skeleton-bar
      />
      <span className={`${styles.sk} ${styles.skFoot}`} data-skeleton-bar />
    </div>
  );
}
