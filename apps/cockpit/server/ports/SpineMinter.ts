// WP-010 (fix-forward) — SpineMinter port (ADR-007 amended; FR-32/35/36/N10/N11).
//
// THE deterministic, server-side mint seam. The original onboarding delegated
// the mint to the bridge AGENT (a headless `claude -p` that hunted for + ran
// the spine emitters) — slow (167s observed) and unreliable (minted NOTHING
// live). ADR-007 is amended: the CONVERSATION (search / clarify / propose)
// stays an agent turn over the bridge; the consequential MINT + `git init` move
// to a deterministic SERVER action behind THIS port.
//
// Hexagonal shape, like SessionBridge: the cockpit owns this interface; the
// adapter (`SpineEmitterMinter`) is the one that actually starts processes (the
// vendored spine-emitter CLIs + `git init`). The orchestrator depends only on
// the port, so it itself starts no process — the read-only gate's per-file
// process-start rule still passes for the orchestrator; only the adapter is
// allow-listed as the new sanctioned site (alongside the SessionBridge adapter).
//
// Two operations, mirroring the two consequential acts onboarding performs:
//
//   findOrCreateRepo(...)  — the FIND vs CREATE branch (FR-35). Local-only
//                            `git init` is the founder-locked safe default
//                            (ADR-008). Returns a RepoOutcome the pure
//                            repoFindOrCreate module interprets (no-dangling-
//                            config, FR-N10/N11).
//   mint(...)              — emit the Tenant / Product / Project through the
//                            validated spine emitters into the active brain.
//                            ALL-OR-NOTHING (FR-N11): a failed emit leaves no
//                            partial graph. IDEMPOTENT (FR-31): deterministic
//                            entity ids ⇒ a re-mint never duplicates.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { ProjectSource, Product } from "../../shared/api-types";
import type { RepoChoice, RepoOutcome } from "../lib/discovery/repoFindOrCreate";

/** What the founder confirmed minting (names + the resolved repo source). */
export interface MintInput {
  /** The Tenant display name (its ULID is derived deterministically from it). */
  tenantName: string;
  /** The Product display name. */
  productName: string;
  /** The Project name/slug. */
  projectName: string;
  /** The founder's chosen area — the emitters' `--repo-root`. */
  chosenArea: string;
  /** The persisted Project.source = {repo, path, primary_branch} (FR-36). */
  source: ProjectSource;
}

/** The minted graph (on success) or a typed failure (all-or-nothing). */
export type MintResult =
  | {
      ok: true;
      tenant: string;
      product: Product;
      project: { projectId: string; source: ProjectSource };
    }
  | { ok: false; code: "MINT_FAILED"; message: string };

/** The find-or-create request the adapter performs (FR-35). */
export interface FindOrCreateRepoInput {
  /** The founder's chosen area — the find root / the create target dir. */
  chosenArea: string;
  /** The founder's repo branch decision (find vs create, local vs hosted). */
  repoChoice?: RepoChoice;
}

/**
 * The deterministic, server-side mint seam (ADR-007 amended). The adapter
 * starts processes (the spine emitters + `git init`); the orchestrator depends
 * only on this port and stays process-free.
 */
export interface SpineMinter {
  /**
   * Find-or-create the repo for the chosen area (FR-35). A CREATE defaults to
   * local-only `git init` (ADR-008). Returns the outcome the pure
   * repoFindOrCreate module interprets (no-dangling-config on failure).
   */
  findOrCreateRepo(input: FindOrCreateRepoInput): Promise<RepoOutcome>;

  /**
   * Mint the Tenant / Product / Project through the validated spine emitters
   * into the active brain (FR-32). All-or-nothing (FR-N11), idempotent (FR-31).
   */
  mint(input: MintInput): Promise<MintResult>;
}
