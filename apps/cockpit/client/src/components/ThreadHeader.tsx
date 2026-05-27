// WP-013 — <ThreadHeader /> — top strip of the thread view.
//
//   - Left: handle + slug.
//   - Centre: stage badge + liveness dot.
//   - Right: one-line intent (truncated with ellipsis via CSS).
//
// References: WP-013 Contract (<ThreadHeader>), TDD §6.

import type { Change } from "../../../shared/api-types";
import styles from "../styles/Thread.module.css";
import { stageLabel } from "./StageBadge";

interface Props {
  change: Change;
}

export function ThreadHeader({ change }: Props) {
  return (
    <header className={styles.header} data-testid="thread-header">
      <div className={styles.left}>
        <span className={styles.handle}>{change.handle}</span>
        <span className={styles.slug}>{change.slug}</span>
      </div>
      <div className={styles.center}>
        <span className={styles.stage} data-stage={change.stage}>
          {stageLabel(change.stage)}
        </span>
        <span
          className={styles.liveness}
          data-status={change.liveness.status}
          title={livenessTitle(change.liveness)}
        />
      </div>
      <div className={styles.right}>
        <span className={styles.intent} title={change.intent}>
          {change.intent}
        </span>
      </div>
    </header>
  );
}

function livenessTitle(liveness: Change["liveness"]): string {
  if (liveness.status === "running") return `running (pid ${liveness.pid})`;
  if (liveness.status === "not-running") return "not running";
  return `unknown — ${liveness.reason}`;
}
