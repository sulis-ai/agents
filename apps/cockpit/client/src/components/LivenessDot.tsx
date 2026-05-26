// WP-012 — <LivenessDot> (TDD §8, ADR-005). Four states:
// running / terminal / not-running / unknown. State resolution is
// extracted so the component itself stays ≤60 lines.

import type { Liveness } from "../../../shared/api-types";
import styles from "./LivenessDot.module.css";

export type LivenessDotState = "running" | "terminal" | "not-running" | "unknown";

interface ResolvedDot {
  state: LivenessDotState;
  label: string;
  reason: string | null;
}

export function resolveLivenessDotState(
  liveness: Liveness,
  pidKind: string | null | undefined,
): ResolvedDot {
  if (liveness.status === "running") {
    if (pidKind === "terminal") {
      return {
        state: "terminal",
        label: "Terminal alive — Claude state unknown",
        reason: null,
      };
    }
    return { state: "running", label: "Claude session running", reason: null };
  }
  if (liveness.status === "not-running") {
    return { state: "not-running", label: "Not running", reason: null };
  }
  return { state: "unknown", label: "Unknown", reason: liveness.reason };
}

const CLASS_BY_STATE: Record<LivenessDotState, string> = {
  running: styles.running!,
  terminal: styles.terminal!,
  "not-running": styles.notRunning!,
  unknown: styles.unknown!,
};

export interface LivenessDotProps {
  liveness: Liveness;
  /** From the change record; "terminal" surfaces the amber caveat. */
  pidKind?: string | null;
}

export function LivenessDot({ liveness, pidKind }: LivenessDotProps) {
  const { state, label, reason } = resolveLivenessDotState(liveness, pidKind);
  return (
    <span
      className={`${styles.dot} ${CLASS_BY_STATE[state]}`}
      role="status"
      data-state={state}
      aria-label={label}
      title={reason ?? label}
    />
  );
}
