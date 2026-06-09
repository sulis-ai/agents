// WP-011 — resolveProjectRepo: a productId → its Project repo (FR-29/30).
//
// start-from-intent starts a change against the active Product's Project repo.
// This pure READ over the on-disk brain resolves the productId to its Project's
// full `source = {repo, path, primary_branch}` and tells the orchestrator
// whether the working copy is already present locally (else clone-first, FR-30).
//
// It reuses the brain-fs read helpers + the same `dna:product`/`dna:project`
// layout `readProducts` reads (EP-03 — no second brain reader). Pure read: no
// process start, no write (the read-only gate proves no mutation here). Fail-
// soft: an absent brain / malformed entity yields null (the route maps null to
// a clean REPO_UNREACHABLE — no change started).

import { existsSync } from "node:fs";
import { join } from "node:path";

import type { ResolvedProject } from "../discovery/startFromIntent";
import { listDirs, listEntityFiles, readJsonldEntity } from "../brainFs";
import { isActiveStatus } from "./isActiveStatus";

/** The brain layout the Tenant's entities live under (mirrors readProducts). */
const BRAIN_INSTANCES = [".brain", "instances"];

export interface ResolveProjectRepoOptions {
  /** ~/.sulis (or a test override). */
  sulisStateDir: string;
  /** The Product to resolve a Project repo for. */
  productId: string;
}

/**
 * Resolve the productId → its Project's repo source. Returns null when no
 * Project for that Product carries a usable source (the route refuses cleanly,
 * starting no change). When more than one Project belongs to the Product, the
 * first with a usable source wins (single-Project-per-Product is the common
 * case; UC-08 presumes one).
 */
export async function resolveProjectRepo(
  opts: ResolveProjectRepoOptions,
): Promise<ResolvedProject | null> {
  const instancesDir = join(opts.sulisStateDir, ...BRAIN_INSTANCES);
  const target = normaliseProductId(opts.productId);

  for (const entity of await readEntitiesOfKind(instancesDir, "project")) {
    const ref = entity.belongs_to_product_ref;
    if (typeof ref !== "string" || normaliseProductId(ref) !== target) continue;
    const source = parseSource(entity.source);
    if (source === null) continue;
    // The working copy is "present" when the local path has a .git dir; else the
    // orchestrator clones from source.repo first (FR-30).
    const present = source.path.length > 0 && existsSync(join(source.path, ".git"));
    return {
      repo: source.repo,
      path: source.path,
      primaryBranch: source.primaryBranch,
      present,
    };
  }
  return null;
}

/** Normalise a product ref/id to its bare-comparable form (full `dna:product:`). */
function normaliseProductId(idOrRef: string): string {
  return idOrRef.startsWith("dna:product:") ? idOrRef : `dna:product:${idOrRef}`;
}

/** Project.source is a JSON-encoded `{repo, path, primary_branch}` string. */
function parseSource(
  source: unknown,
): { repo: string; path: string; primaryBranch: string } | null {
  if (typeof source !== "string" || source.length === 0) return null;
  try {
    const parsed = JSON.parse(source) as {
      repo?: unknown;
      path?: unknown;
      primary_branch?: unknown;
    };
    const repo = typeof parsed.repo === "string" ? parsed.repo : "";
    const path = typeof parsed.path === "string" ? parsed.path : "";
    const primaryBranch =
      typeof parsed.primary_branch === "string" ? parsed.primary_branch : "main";
    // A Project with neither a repo nor a path is not startable.
    if (repo.length === 0 && path.length === 0) return null;
    return { repo, path, primaryBranch };
  } catch {
    return null;
  }
}

/**
 * Read every `.jsonld` entity of one kind across every brain domain (read-only).
 *
 * WP-003 / ADR-020: soft-deleted entities (`sys_status ∈ {deleted, purged,
 * archived}`) are filtered out here via the shared `isActiveStatus` predicate,
 * so a removed Project no longer resolves a repo. A legacy entity with no
 * `sys_status` is active (absence ≠ deleted). Any future reader of these
 * entities MUST apply the same filter.
 */
async function readEntitiesOfKind(
  instancesDir: string,
  kind: string,
): Promise<Array<Record<string, unknown>>> {
  const out: Array<Record<string, unknown>> = [];
  for (const domain of await listDirs(instancesDir)) {
    const kindDir = join(instancesDir, domain, kind);
    for (const file of await listEntityFiles(kindDir)) {
      const parsed = await readJsonldEntity(join(kindDir, file));
      if (parsed !== null && isActiveStatus(parsed)) out.push(parsed);
    }
  }
  return out;
}
