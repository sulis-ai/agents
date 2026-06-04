// WP-010 — repo find-or-create (FR-35 / FR-N7 / FR-N10 / FR-N11; ADR-008).
//
// A PURE decision module. The actual `git init` / repo configure runs INSIDE
// the agent session over the bridge (ADR-007) — this module owns only the
// DECISION and the OUTCOME INTERPRETATION, never fs/git/process:
//
//   planRepo(choice)         — the FIND vs CREATE branch (FR-35) + the
//                              create-LOCATION default. Local-only `git init`
//                              is the FOUNDER-LOCKED safe default (ADR-008);
//                              hosted-remote is honoured ONLY when separately
//                              + explicitly confirmed, never by silence.
//
//   resolveRepoSource(plan, outcome)
//                            — the NO-DANGLING-CONFIG rule (FR-N10/N11): a
//                              ProjectSource is produced ONLY when the repo is
//                              found-or-created AND reachable. A FAILED create
//                              yields REPO_CREATE_FAILED and NO source — the
//                              graph is left exactly as it was.
//
// Pure: no fs / git / process, no clock, no randomness.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { ProjectSource } from "../../../shared/api-types";

/** The founder's repo branch decision (mirrors OnboardingRequest.repoChoice). */
export interface RepoChoice {
  mode?: "find" | "create";
  /** Local-only is the safe default (ADR-008). */
  createTarget?: "local" | "hosted-remote";
}

/** The repo plan shown in the proposal (matches OnboardingStreamEvent). */
export type RepoPlan =
  | "found-existing"
  | "will-create-local"
  | "will-create-hosted-remote";

export interface RepoPlanResult {
  repoPlan: RepoPlan;
  /** True only for a create branch (a find never creates). */
  willCreate: boolean;
  /** The create location when willCreate; undefined for a find. */
  createTarget?: "local" | "hosted-remote";
}

export interface PlanRepoContext {
  /** The founder's chosen area — the create target dir / the find root. */
  chosenArea: string;
}

/**
 * Decide the FIND vs CREATE branch and the create location. An absent choice,
 * or `mode: "find"`, is the safe NON-CREATING branch (configure an existing
 * repo). A create defaults to LOCAL-ONLY (founder-locked); hosted-remote is
 * honoured only when explicitly chosen.
 */
export function planRepo(
  choice: RepoChoice | undefined,
  _ctx: PlanRepoContext,
): RepoPlanResult {
  if (!choice || choice.mode !== "create") {
    // FIND (or unspecified) — configure an existing repo, no creation.
    return { repoPlan: "found-existing", willCreate: false };
  }
  // CREATE — local-only is the recorded safe default (ADR-008). Hosted-remote
  // is honoured ONLY when explicitly + separately chosen, never by silence.
  const createTarget = choice.createTarget === "hosted-remote" ? "hosted-remote" : "local";
  return {
    repoPlan:
      createTarget === "hosted-remote"
        ? "will-create-hosted-remote"
        : "will-create-local",
    willCreate: true,
    createTarget,
  };
}

/**
 * The reported outcome of the (agent-performed) find-or-create:
 *   - `reachable`     — the repo exists / was created and is reachable;
 *   - `create-failed` — a confirmed create failed (FR-N10);
 *   - `unreachable`   — a found repo could not be reached.
 */
export interface RepoOutcome {
  outcome: "reachable" | "create-failed" | "unreachable";
  /** The repo path/URL (when reachable). */
  repo?: string;
  /** The primary branch (when reachable). */
  primaryBranch?: string;
  /** A sub-path within the repo, if any. */
  path?: string;
}

export type ResolveRepoSourceResult =
  | { ok: true; source: ProjectSource }
  | { ok: false; code: "REPO_CREATE_FAILED" | "REPO_UNREACHABLE"; message: string };

/**
 * Turn an outcome into a persistable ProjectSource — or a failure that persists
 * NOTHING (FR-N10/N11). The config is produced ONLY on a reachable outcome; a
 * failed create / unreachable repo yields a typed failure and NO source, so the
 * graph is left exactly as it was before the attempt.
 */
export function resolveRepoSource(
  plan: RepoPlanResult,
  outcome: RepoOutcome,
): ResolveRepoSourceResult {
  if (outcome.outcome === "create-failed") {
    return {
      ok: false,
      code: "REPO_CREATE_FAILED",
      message: "I couldn't create the repo — nothing was saved.",
    };
  }
  if (outcome.outcome === "unreachable") {
    return {
      ok: false,
      code: "REPO_UNREACHABLE",
      message: plan.willCreate
        ? "The new repo couldn't be reached — nothing was saved."
        : "That repo couldn't be reached — nothing was saved.",
    };
  }
  // reachable — produce the durable source.
  return {
    ok: true,
    source: {
      repo: outcome.repo ?? "",
      path: outcome.path ?? "",
      primary_branch: outcome.primaryBranch ?? "main",
    },
  };
}
