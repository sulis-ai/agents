// WP-011 — StartChangeRunner port (FR-29/30/34; ADR-006/007).
//
// THE deterministic, server-side change-start seam. The lesson from WP-010,
// applied: the consequential act (creating a change) is NOT delegated to the
// bridge AGENT — that proved slow + unreliable (the WP-010 agent-delegated mint
// ran 167s and created nothing). Instead, the change-creation is a DETERMINISTIC
// SERVER action behind THIS port, whose real adapter (`SulisChangeStarter`)
// invokes `sulis-change start` + `git clone` directly via child_process.
//
// Hexagonal shape, like SessionBridge + SpineMinter: the cockpit owns this
// interface; the adapter is the one that actually starts processes. The
// start-from-intent orchestrator depends only on the port, so it itself starts
// no process — the read-only gate's per-file process-start rule still passes for
// the orchestrator; only the adapter is allow-listed as the sanctioned site.
//
// Two operations, mirroring the two consequential acts start-from-intent
// performs:
//
//   clone(...)  — LOCAL-FIRST (FR-30): when the Project's repo is absent, clone
//                 it from `source.repo` first (bounded by the subprocess
//                 timeout). A clone failure ⇒ a typed REPO_UNREACHABLE and NO
//                 change is started (all-or-nothing).
//   start(...)  — run `sulis-change start --repo-root <repo> --primitive <p>
//                 --slug <s> --intent <i>` so the change lands at RECON on the
//                 board (FR-29). The resolved primitive + slug come from the
//                 deterministic classifier.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { Change } from "../../shared/api-types";

/** Clone an absent Project repo from its source before starting (FR-30). */
export interface CloneInput {
  /** The Project.source.repo to clone FROM (a URL or a local path). */
  sourceRepo: string;
  /** Where the working copy should land (the absent repo's local path). */
  targetPath: string;
}

/** The clone outcome — a typed failure leaves NO change started (FR-30). */
export type CloneResult =
  | { ok: true; path: string }
  | { ok: false; code: "REPO_UNREACHABLE"; message: string };

/** Start a change against a present (or freshly-cloned) repo (FR-29). */
export interface StartInput {
  /** The repo the change starts against (`--repo-root`). */
  repoRoot: string;
  /** The change primitive resolved from the intent (`--primitive`). */
  primitive: string;
  /** The change slug resolved from the intent (`--slug`). */
  slug: string;
  /** The one-line plain-English intent carried onto the change (`--intent`). */
  intent: string;
}

/** The started change (on success) or a typed failure (all-or-nothing). */
export type StartResult =
  | { ok: true; change: Change }
  | {
      ok: false;
      code: "START_FAILED" | "REPO_UNREACHABLE";
      message: string;
    };

/**
 * The deterministic, server-side change-start seam (ADR-007). The adapter starts
 * processes (`sulis-change start` + `git clone`); the orchestrator depends only
 * on this port and stays process-free.
 */
export interface StartChangeRunner {
  /** Clone an absent Project repo from its source first (local-first, FR-30). */
  clone(input: CloneInput): Promise<CloneResult>;
  /** Start a change so it lands at Recon on the board (FR-29). */
  start(input: StartInput): Promise<StartResult>;
}
