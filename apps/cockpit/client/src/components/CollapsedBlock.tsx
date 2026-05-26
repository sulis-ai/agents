// WP-013 — <CollapsedBlock /> — shared accordion used by both the
// tool-use and tool-result variants of <AssistantBlock /> (WP-013 Blue
// checklist: "one reusable component; no duplication").
//
// Defaults to collapsed; clicking the header toggles the body. Body is
// not in the DOM when collapsed (assertable via queryByTestId).

import { useState, type ReactNode } from "react";
import styles from "../styles/Chat.module.css";

interface Props {
  header: ReactNode;
  /** Test id for the outer wrapper — lets the caller distinguish
   *  tool-use vs tool-result accordions in tests. */
  wrapperTestId: string;
  /** The body content (rendered only when expanded). */
  children: ReactNode;
}

export function CollapsedBlock({ header, wrapperTestId, children }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <div className={styles.collapsedBlock} data-testid={wrapperTestId}>
      <button
        type="button"
        className={styles.collapsedHeader}
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        <span className={styles.collapsedChevron}>{open ? "▼" : "▶"}</span>
        {header}
      </button>
      {open && (
        <div className={styles.collapsedBody} data-testid="collapsed-block-body">
          {children}
        </div>
      )}
    </div>
  );
}
