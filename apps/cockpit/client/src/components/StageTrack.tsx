// WP-004 — <StageTrack> — the thread's "where am I" track (FR-04).
//
// The six lifecycle stages in order (recon→specify→design→implement→
// review→ship), with the change's current stage marked "now", earlier
// stages "done", later stages "pending". A terminal "shipped" change
// reads as all-six-done (the workflow is complete).
//
// Colour is decorative reinforcement only (ADR-005 / the SIGNED visual
// contract): each step carries the stage NAME and a STATE WORD (done /
// now / pending), so the track is fully legible without colour
// (WCAG 1.4.1). The per-stage hue comes from the shared --stage-* tokens
// (tokens.css) — the same scale the board columns + card badge use, no
// parallel palette. The current step gets aria-current="step".

import type { WorkflowStage } from "../../../shared/api-types";
import styles from "./StageTrack.module.css";

/** The six in-workflow stages, in order (terminal "shipped" excluded). */
const TRACK_STAGES: Exclude<WorkflowStage, "shipped">[] = [
  "recon",
  "specify",
  "design",
  "implement",
  "review",
  "ship",
];

const STAGE_NAME: Record<Exclude<WorkflowStage, "shipped">, string> = {
  recon: "Recon",
  specify: "Specify",
  design: "Design",
  implement: "Implement",
  review: "Review",
  ship: "Ship",
};

type StepState = "done" | "now" | "pending";

const STATE_WORD: Record<StepState, string> = {
  done: "Done",
  now: "Now",
  pending: "Pending",
};

export interface StageTrackProps {
  stage: WorkflowStage;
}

export function StageTrack({ stage }: StageTrackProps) {
  // A shipped change is past the workflow — every step reads as done.
  const currentIndex =
    stage === "shipped" ? TRACK_STAGES.length : TRACK_STAGES.indexOf(stage);

  return (
    <ol
      className={styles.track}
      data-testid="stage-track"
      aria-label="Change progress"
    >
      {TRACK_STAGES.map((s, i) => {
        const state: StepState =
          i < currentIndex ? "done" : i === currentIndex ? "now" : "pending";
        return (
          <li
            key={s}
            className={styles.step}
            data-testid="stage-step"
            data-stage={s}
            data-state={state}
            aria-current={state === "now" ? "step" : undefined}
          >
            <span className={styles.dot} aria-hidden="true" />
            <span className={styles.name}>{STAGE_NAME[s]}</span>
            <span className={styles.stateWord}>{STATE_WORD[state]}</span>
          </li>
        );
      })}
    </ol>
  );
}
