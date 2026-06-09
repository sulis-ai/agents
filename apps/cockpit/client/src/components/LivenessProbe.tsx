// WP-005 — <LivenessProbe> (was <LivenessDot>).
//
// The stripped-down liveness read on the card's top line: JUST a probe dot +
// a bare relative time. No state WORD is shown visually; the probe carries its
// state by FILL / MOTION / SHAPE (never colour alone) plus a screen-reader-only
// label, and the time is the only visible text.
//
// Four states (TDD §5 + WP Contract):
//   working  → filled dot + a subtle PULSE (recent activity; the only motion).
//   live     → solid filled dot, steady (session running but quiet).
//   idle     → hollow / outline ring (not running).
//   unknown  → a DISTINCT dashed "?" ring (FR-41) — never confused with idle,
//              so the founder is never told "idle" when the truth is "can't tell".
//
// working vs live is derived from `lastActivityAt` recency (the <60s freshness
// window, Q-1 default). No-recency (FR-42): `lastActivityAt === null` renders
// the time slot as a muted em-dash — never "now" or a bogus age — while the
// probe still renders its liveness state. Reduced motion (S-30) drops the pulse
// but keeps the SR label (the static-ring fallback).

import type { Liveness } from "../../../shared/api-types";
import { formatCompactRelativeTime } from "../utils/relativeTime";
import styles from "./LivenessProbe.module.css";

export type LivenessProbeState = "working" | "live" | "idle" | "unknown";

/** Activity newer than this reads as "actively working" (Q-1 default). */
const WORKING_WINDOW_MS = 60_000;

interface ResolvedProbe {
  state: LivenessProbeState;
  /** Screen-reader-only label naming the state (the visible word is dropped). */
  srLabel: string;
}

/**
 * Resolve the probe state from the liveness union + activity recency.
 * `running` splits into `working` (recent) vs `live` (quiet) on the recency
 * window; `not-running` → idle; `unknown` → unknown (its own distinct read).
 */
export function resolveProbeState(
  liveness: Liveness,
  lastActivityAt: string | null,
  now: Date,
): ResolvedProbe {
  if (liveness.status === "running") {
    const working =
      lastActivityAt !== null &&
      now.getTime() - new Date(lastActivityAt).getTime() < WORKING_WINDOW_MS;
    return working
      ? { state: "working", srLabel: "actively working" }
      : { state: "live", srLabel: "session live" };
  }
  if (liveness.status === "not-running") {
    return { state: "idle", srLabel: "idle, not running" };
  }
  return { state: "unknown", srLabel: "liveness unknown" };
}

const DOT_CLASS: Record<LivenessProbeState, string> = {
  working: styles.dotWorking!,
  live: styles.dotLive!,
  idle: styles.dotIdle!,
  unknown: styles.dotUnknown!,
};

const STATE_CLASS: Record<LivenessProbeState, string> = {
  working: styles.working!,
  live: styles.live!,
  idle: styles.idle!,
  unknown: styles.unknown!,
};

export interface LivenessProbeProps {
  liveness: Liveness;
  /** ISO last-activity; null ⇒ no-recency (FR-42) → em-dash, never "now". */
  lastActivityAt: string | null;
  /** "now" override for deterministic tests; defaults to the real clock. */
  now?: Date;
  /**
   * Test-only escape hatch for `prefers-reduced-motion` (jsdom can't evaluate
   * the media query). In the app the CSS media query owns the fallback; this
   * flag lets the unit test assert the static-ring path keeps its SR label.
   */
  reducedMotion?: boolean;
}

export function LivenessProbe({
  liveness,
  lastActivityAt,
  now = new Date(),
  reducedMotion = false,
}: LivenessProbeProps) {
  const { state, srLabel } = resolveProbeState(liveness, lastActivityAt, now);

  // No-recency (FR-42): show a muted em-dash, never a fabricated time.
  const hasRecency = lastActivityAt !== null;
  const timeText = hasRecency
    ? formatCompactRelativeTime(lastActivityAt as string, now)
    : "—";

  return (
    <span
      className={`${styles.probe} ${STATE_CLASS[state]}`}
      data-probe-state={state}
      data-reduced-motion={reducedMotion ? "true" : undefined}
    >
      <span
        className={`${styles.dot} ${DOT_CLASS[state]}`}
        data-probe-dot
        aria-hidden="true"
      />
      <span className={styles.sr}>{srLabel} · </span>
      <span
        className={`${styles.ago} ${hasRecency ? "" : styles.noRecency ?? ""}`}
        aria-hidden={hasRecency ? undefined : "true"}
      >
        {timeText}
      </span>
    </span>
  );
}
