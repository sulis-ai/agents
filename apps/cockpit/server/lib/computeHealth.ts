// WP-002 — computeHealth: the cheap, honest change-health rollup (ADR-001).
//
// PURE: no I/O. Over { testsState, rigorForStage } it yields the board's
// On-track / Off-track / Unknown verdict. The reasons are a FIXED enumerable
// set — never interpolated from change content (FR-32 / NFR-SEC-2). It NEVER
// emits "worth-a-look": that state is reserved for the deferred OODA-spiral
// drift signal (ADR-001); the wire type carries it, the producer does not.
//
// The rule (ADR-001 + FR-31 + BR-10):
//   1. red tests OR rigorForStage.ok === false → off-track. Tests-red is the
//      most concrete failure and names tests; otherwise the missing artifact
//      names itself (spec / design / tests).
//   2. no test state (unknown) AND rigor cannot be determined
//      (determinable === false) → unknown ("too early to tell"). This is the
//      FR-31 honest read: a fresh change with nothing behind it must NOT
//      masquerade as on-track.
//   3. else → on-track.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { ChangeHealth } from "../../shared/api-types";
import type { MissingArtifact, RigorForStage } from "./readRigorForStage";

/** The recorded CI/test state the rollup reads (from `readTestsState`). */
export type TestsState = "green" | "red" | "unknown";

export interface ComputeHealthInput {
  testsState: TestsState;
  rigorForStage: RigorForStage;
}

/** The fixed reason for a missing artifact — never free text (FR-32). */
const MISSING_REASON: Record<MissingArtifact, string> = {
  spec: "no spec recorded",
  design: "no design recorded",
  tests: "no tests alongside the code",
};

/**
 * Derive a change's health verdict. Pure; never emits "worth-a-look".
 */
export function computeHealth(input: ComputeHealthInput): ChangeHealth {
  const { testsState, rigorForStage } = input;

  // 1. Off-track — tests-red is the most concrete; it names tests. A
  //    determinable rigor failure names its missing artifact.
  if (testsState === "red") {
    return { state: "off-track", reason: "tests failing" };
  }
  if (rigorForStage.ok === false && rigorForStage.missing !== null) {
    return { state: "off-track", reason: MISSING_REASON[rigorForStage.missing] };
  }

  // 2. Unknown — no test signal AND rigor indeterminate (FR-31).
  if (testsState === "unknown" && rigorForStage.determinable === false) {
    return { state: "unknown", reason: "too early to tell" };
  }

  // 3. On-track. Distinguish "a real green test" from "rigor carried it"
  //    so the founder reads an honest reason, both from the fixed set.
  if (testsState === "green") {
    return { state: "on-track", reason: "tests green and on-stage" };
  }
  return { state: "on-track", reason: "on track for this stage" };
}
