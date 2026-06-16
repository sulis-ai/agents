// WP-013 — <ThreadHeader /> — top strip of the thread view.
//
// Leads with the PLAIN-ENGLISH headline (the change's intent) — the signed
// visual contract's treatment ("Drive a change from the app", with
// "drive-a-change · create" as a quiet mono kicker above it). The code-y
// bits are demoted: the slug · primitive kicker, and the one canonical
// handle as a small muted reference on the right. A non-technical founder
// reads the sentence, not the ID. (CH-01KT50 copy fix.)
//
//   - Kicker:   {slug} · {primitive}   (quiet mono, above the title)
//   - Headline: {intent}               (the sentence the founder reads)
//   - Right:    stage badge · liveness dot · {handle} (demoted reference)
//
// References: WP-013 Contract (<ThreadHeader>), TDD §6, signed visual
// contract (sulis-app.html panel 4).

import type { Change } from "../../../shared/api-types";
import styles from "../styles/Thread.module.css";
import { stageLabel } from "./StageBadge";
import { ProductPicker } from "./ProductPicker";

interface Props {
  change: Change;
}

export function ThreadHeader({ change }: Props) {
  return (
    <header className={styles.header} data-testid="thread-header">
      <div className={styles.headLeft}>
        <span className={styles.kicker}>
          {change.slug} · {change.primitive}
        </span>
        <h1 className={styles.title} title={change.intent}>
          {change.intent}
        </h1>
      </div>
      <div className={styles.headMeta}>
        <span className={styles.stage} data-stage={change.stage}>
          {stageLabel(change.stage)}
        </span>
        <span
          className={styles.liveness}
          data-status={change.liveness.status}
          title={livenessTitle(change.liveness)}
        />
        {/* The one canonical handle, demoted to a small muted reference. */}
        <span className={styles.handle}>{change.handle}</span>
        {/* Assign (or change) this change's product — the board filter scopes
            by it. Hidden until the founder has a product to assign to. */}
        <ProductPicker
          changeId={change.changeId}
          currentProductId={change.forProduct}
        />
      </div>
    </header>
  );
}

function livenessTitle(liveness: Change["liveness"]): string {
  if (liveness.status === "running") return `running (pid ${liveness.pid})`;
  if (liveness.status === "not-running") return "not running";
  return `unknown — ${liveness.reason}`;
}
