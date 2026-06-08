// WP-P10 — <OriginBadge /> — the worded change-origin badge.
//
// The shared glance-level idiom across the Files rows, the open-file panel and
// the Provenance lens. Worded, never colour-alone (WCAG 1.4.1): each kind pairs
// a Heroicon with a spelled-out word.
//
//   autonomous → "⚡ Autonomous"          (bolt)
//   assisted   → "💬 Assisted · likely"   (chat-bubble) — the "· likely" hedge
//                appears ONLY when attribution === "inferred"; dropped when
//                "recorded" (the badge flips with no other UI change — ADR-012).
//   unknown    → "Origin unknown"          (question-mark-circle)
//
// The hedge is driven by the backend's `attribution` flag — never guessed
// client-side (CF-06). When `onToggle` is supplied the badge is a button with a
// caret + aria-expanded (progressive disclosure); otherwise it is a static
// label (the Files-row glance).

import type { ReactNode } from "react";
import type { Origin } from "../../../shared/api-types";
import {
  BoltIcon,
  ChatBubbleIcon,
  QuestionMarkCircleIcon,
  ChevronDownIcon,
} from "./originIcons";
import styles from "../styles/Origin.module.css";

export interface OriginBadgeProps {
  origin: Origin;
  /** When set, the badge is an expand/collapse button (caret + aria-expanded). */
  onToggle?: () => void;
  /** Whether the disclosure it controls is open (only with `onToggle`). */
  expanded?: boolean;
  /** The id of the region this badge controls (aria-controls, with `onToggle`). */
  controls?: string;
}

/** The badge's worded label + kind class. The "· likely" hedge is part of the
 *  assisted label and shows only for an inferred attribution. */
function descriptor(origin: Origin): {
  kind: "auto" | "assist" | "unknown";
  word: string;
  hedge: string | null;
  icon: ReactNode;
} {
  switch (origin.kind) {
    case "autonomous":
      return {
        kind: "auto",
        word: "Autonomous",
        hedge: null,
        icon: <BoltIcon />,
      };
    case "assisted":
      return {
        kind: "assist",
        word: "Assisted",
        hedge: origin.attribution === "inferred" ? "· likely" : null,
        icon: <ChatBubbleIcon />,
      };
    case "unknown":
      return {
        kind: "unknown",
        word: "Origin unknown",
        hedge: null,
        icon: <QuestionMarkCircleIcon />,
      };
  }
}

export function OriginBadge({
  origin,
  onToggle,
  expanded,
  controls,
}: OriginBadgeProps) {
  const d = descriptor(origin);
  const cls = `${styles.root} ${styles.badge} ${styles[d.kind]}`;
  const label = (
    <>
      {d.icon}
      {d.word}
      {d.hedge && <span className={styles.qual}>{" "}{d.hedge}</span>}
    </>
  );

  if (onToggle) {
    return (
      <button
        type="button"
        className={`${cls} ${styles.btn}`}
        onClick={onToggle}
        aria-expanded={expanded ?? false}
        aria-controls={controls}
        data-testid="origin-badge"
        data-kind={origin.kind}
      >
        {label}
        <ChevronDownIcon className={styles.caret} aria-hidden="true" />
      </button>
    );
  }

  return (
    <span
      className={cls}
      data-testid="origin-badge"
      data-kind={origin.kind}
    >
      {label}
    </span>
  );
}
