// WP-001 — Settings wire-contract example stubs (CF-04; ADR-019/020/021).
//
// CF-04 requires the contract ship example stubs covering happy AND error AND
// empty cases. These are the canonical settings fixtures every consumer mock
// (e.g. the WP-007 client contract test) and producer test reuses — one place
// the example shapes live, so no two tests hand-roll a divergent SettingsTree.
//
// No runtime behaviour — pure typed literals against the shapes in
// `../api-types`. If a shape drifts, these stop compiling (the tsc gate).
//
// References:
// - ../api-types.ts (the shapes these fixtures instantiate).
// - CONTRACT_FIRST_STANDARD CF-04 (stubs include happy + error + empty).

import type {
  ApiError,
  RepoLink,
  SettingsErrorCode,
  SettingsProduct,
  SettingsProject,
  SettingsTree,
} from "../api-types";

// ── HAPPY — one editable product, one project, one present:true repo ─────────

const happyRepo: RepoLink = {
  localPath: "/Users/founder/code/alpha",
  primaryBranch: "main",
  present: true,
};

const happyProject: SettingsProject = {
  projectId: "dna:project:01HAPPYPROJECT",
  name: "Alpha web",
  repo: happyRepo,
};

const happyProduct: SettingsProduct = {
  productId: "dna:product:01HAPPYPRODUCT",
  name: "Alpha",
  editable: true,
  projects: [happyProject],
};

/** A populated, editable settings tree (the happy case). */
export const happySettingsTree: SettingsTree = {
  products: [happyProduct],
};

// ── EMPTY — the single implicit product (editable:false, no projects) ────────

const implicitProduct: SettingsProduct = {
  productId: "dna:product:01IMPLICITSINGLE",
  name: "My product",
  // The synthesised implicit single product is read-only until it becomes real
  // (ADR-020). A write against it returns IMMUTABLE_IMPLICIT.
  editable: false,
  projects: [],
};

/** The empty case — only the implicit, non-editable product exists. */
export const emptySettingsTree: SettingsTree = {
  products: [implicitProduct],
};

// ── ERROR — one ApiError per SettingsErrorCode value (all three categories) ──

/**
 * One `ApiError` envelope per settings error code (CF-03/04). Keyed by code so
 * a consumer test can assert the exact envelope it expects per failure.
 */
export const settingsErrorFixtures: Record<SettingsErrorCode, ApiError> = {
  // Protocol.
  NOT_FOUND: { error: "No such product or project.", code: "NOT_FOUND" },
  // Expected.
  VALIDATION_FAILED: {
    error: "That name didn't pass validation.",
    code: "VALIDATION_FAILED",
  },
  PATH_NOT_FOUND: {
    error: "That folder doesn't exist on disk.",
    code: "PATH_NOT_FOUND",
  },
  PATH_NOT_A_REPO: {
    error: "That folder isn't a git repo yet.",
    code: "PATH_NOT_A_REPO",
  },
  IMMUTABLE_IMPLICIT: {
    error: "The default product can't be edited yet.",
    code: "IMMUTABLE_IMPLICIT",
  },
  // Internal.
  WRITE_FAILED: { error: "Saving that change failed.", code: "WRITE_FAILED" },
};
