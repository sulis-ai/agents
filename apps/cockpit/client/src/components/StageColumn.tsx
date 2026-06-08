// WP-003 — <StageColumn> — one lifecycle-stage column on the board.
//
// Matches the SIGNED visual contract (sulis-app.html, board panel): a
// neutral column with a header carrying a small stage-colour dot + the
// stage name + a count, and a vertical list of <ChangeCard>s (or a quiet
// "nothing here yet" note when empty). The dot is the board's only colour
// (ADR-005) and is decorative reinforcement — the stage is also carried by
// the column name + its left-to-right position, so colour is never the
// sole cue (WCAG 1.4.1); the dot is aria-hidden and the name is the label.
//
// Reuses ChangeCard (EP-03 — restyle/compose, not rebuild). The stage
// colour comes from the shared --stage-* tokens (tokens.css), the same
// scale the StageBadge palette draws on — no parallel palette.

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
      className={styles.col}
      data-testid="stage-column"
      data-stage={stage}
      aria-label={`${name} — ${changes.length} ${
        changes.length === 1 ? "change" : "changes"
      }`}
    >
      <header className={`${styles.colhead} ${styles[stage]}`}>
        <span className={styles.sdot} aria-hidden="true" />
        <span className={styles.colname}>{name}</span>
        <span className={styles.colcount}>{changes.length}</span>
      </header>
      <div className={styles.collist} data-testid={`stage-column-${stage}`}>
        {changes.length === 0 ? (
          <p className={styles.colEmpty}>Nothing here yet</p>
        ) : (
          changes.map((change) => (
            <ChangeCard key={change.changeId} change={change} />
          ))
        )}
      </div>
    </section>
  );
}
