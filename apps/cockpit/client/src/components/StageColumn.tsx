// WP-004 — <StageColumn> — one lifecycle-stage column rendered as a
// FULL-HEIGHT LANE (REORGANISE-Refactor).
//
// Matches the production-approved visual contract
// (.design/cockpit-board-refresh/MOCKUP.html — .lane / .laneHead /
// .laneList / .laneFoot / .laneEmpty): the lane fills the board row top to
// bottom, its header is sticky (stays put while the cards scroll), and its
// card list is the internal-scroll container — so each lane scrolls on its
// own and the board no longer scrolls as one page. An empty lane keeps its
// full height, its header, its count (0), and shows a quiet "Nothing here
// yet" note inside the lane (S-12 / AF-2) — it is never collapsed or hidden.
//
// The Recon lane (and only Recon) carries a quiet "Start here" foot
// affordance that routes to /start, because changes start at Recon. It is a
// keyboard-reachable <Link> with a visible focus ring (never mouse-only,
// never outline:none — WPF-06).
//
// The lane stays a labelled region (aria-label="Recon — N changes"); the dot
// is the board's only colour (ADR-005), is decorative reinforcement
// (aria-hidden), and the stage is also carried by the name + position so
// colour is never the sole cue (WCAG 1.4.1). Card internals are out of scope
// here (WP-005 owns the card redesign); this WP is layout only. Reuses
// ChangeCard (EP-03 — restyle/compose, not rebuild); the stage colour comes
// from the shared --stage-* tokens (tokens.css), the same scale the
// StageBadge palette draws on — no parallel palette.

import { Link } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import type { BoardStage } from "../lib/groupChangesByStage";
import { ChangeCard } from "./ChangeCard";
import styles from "./StageColumn.module.css";

/** Title-cased display name for each board stage. */
const STAGE_NAME: Record<BoardStage, string> = {
  recon: "Recon",
  specify: "Specify",
  design: "Design",
  implement: "Implement",
  review: "Review",
  ship: "Ship",
};

export interface StageColumnProps {
  stage: BoardStage;
  changes: Change[];
}

export function StageColumn({ stage, changes }: StageColumnProps) {
  const name = STAGE_NAME[stage];
  return (
    <section
      className={`${styles.lane} ${styles[stage]}`}
      data-testid="stage-column"
      data-stage={stage}
      aria-label={`${name} — ${changes.length} ${
        changes.length === 1 ? "change" : "changes"
      }`}
    >
      <header className={styles.laneHead}>
        <span className={styles.sdot} aria-hidden="true" />
        <span className={styles.laneName}>{name}</span>
        <span className={styles.laneCount}>{changes.length}</span>
      </header>

      <div className={styles.laneList} data-testid={`stage-column-${stage}`}>
        {changes.length === 0 ? (
          <p className={styles.laneEmpty}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              aria-hidden="true"
            >
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <path d="M3 9h18" strokeLinecap="round" />
            </svg>
            Nothing here yet
          </p>
        ) : (
          changes.map((change) => (
            <ChangeCard key={change.changeId} change={change} />
          ))
        )}
      </div>

      {/* Pinned bottom action — RECON ONLY, because changes start at Recon.
       * A quiet outline secondary so it never competes with the top-bar
       * primary; a keyboard-reachable Link to /start with a visible focus
       * ring (WPF-06). The other five lanes have no foot. */}
      {stage === "recon" && (
        <div className={styles.laneFoot}>
          <Link to="/start" className={styles.startHere}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M12 5v14M5 12h14" strokeLinecap="round" />
            </svg>
            Start here
          </Link>
        </div>
      )}
    </section>
  );
}
