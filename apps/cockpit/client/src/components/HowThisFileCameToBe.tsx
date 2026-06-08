// WP-P10/P11 — <HowThisFileCameToBe /> — the open-file provenance panel.
//
// Sits under the file content in the open-file view. Calls
// useFileOrigin(changeId, path) for the selected file's inferred origin and
// shows the worded badge + its one-click trace (the OriginTrace card):
//   autonomous → run label + confidence, a jump to the Provenance run log;
//   assisted   → the conversation Turn Card summary + "Open conversation →";
//   unknown    → the plain reason (honest, never a guess).
//
// Collapsible (progressive disclosure — the badge is the glance, the trace is
// one click): the header is a button with aria-expanded, the body is the trace.
// Defaults open so the trace is visible the first time. Loading + a calm empty
// state are handled. `onSelectView` switches the change view (to the
// conversation, or to Provenance for the run log) — optional; when absent the
// jumps are hidden but the trace still renders.

import { useState } from "react";
import type { ChangeView } from "./ChangeNav";
import { useFileOrigin } from "../api/useOrigin";
import { OriginBadge } from "./OriginBadge";
import { OriginTrace } from "./OriginTrace";
import { ClockIcon, ChevronDownIcon } from "./originIcons";
import styles from "../styles/Origin.module.css";

interface Props {
  changeId: string;
  /** Worktree-relative path of the open file. */
  path: string;
  /** Switch the change view (conversation / provenance) for the trace jumps. */
  onSelectView?: (view: ChangeView) => void;
}

const PANEL_BODY_ID = "how-this-file-came-to-be";

export function HowThisFileCameToBe({ changeId, path, onSelectView }: Props) {
  const [open, setOpen] = useState(true);
  const query = useFileOrigin(changeId, path);

  if (query.isLoading) {
    return (
      <div className={`${styles.root} ${styles.panel}`} data-testid="file-origin-panel">
        <div className={styles.loadnote} role="status" aria-live="polite">
          <ClockIcon aria-hidden="true" />
          Working out how this file came to be…
        </div>
      </div>
    );
  }

  // A genuine fetch failure or no origin → say so calmly; never a red banner.
  // Guard the shape too: a malformed/absent origin gets the same calm fallback
  // rather than a crash (defensive — the badge needs a discriminated `kind`).
  const origin = query.data?.origin;
  if (query.isError || !origin || typeof origin.kind !== "string") {
    return (
      <div className={`${styles.root} ${styles.panel}`} data-testid="file-origin-panel">
        <div className={styles.loadnote}>
          We couldn’t work out how this file came to be yet.
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.root} ${styles.panel}`} data-testid="file-origin-panel">
      <button
        type="button"
        className={styles.panelHead}
        aria-expanded={open}
        aria-controls={PANEL_BODY_ID}
        onClick={() => setOpen((o) => !o)}
        data-testid="file-origin-toggle"
      >
        <span className={styles.pk}>
          <span className={styles.pt}>How this file came to be</span>
          <span className={styles.ps}>Where this file’s change came from</span>
        </span>
        <span className={styles.badgeWrap}>
          <OriginBadge origin={origin} />
        </span>
        <ChevronDownIcon className={styles.caret} aria-hidden="true" />
      </button>
      {open && (
        <div className={styles.panelBody} id={PANEL_BODY_ID}>
          <OriginTrace
            origin={origin}
            onOpenConversation={
              onSelectView ? () => onSelectView("conversation") : undefined
            }
            onOpenRunLog={
              onSelectView ? () => onSelectView("provenance") : undefined
            }
          />
        </div>
      )}
    </div>
  );
}
