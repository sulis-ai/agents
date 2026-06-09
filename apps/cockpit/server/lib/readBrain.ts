// WP-006 — readBrain(worktreeRoot, changeId) (FR-06/07).
//
// Composes a read-only view of the entities the agent created for a change:
// it walks the change worktree's brain instances tree
//
//   <worktreeRoot>/.brain/instances/<domain>/<kind>/<ULID>.jsonld
//
// parses each `.jsonld` entity, GROUPS them by kind (the `<kind>` directory
// segment, which matches the entity id's `dna:<kind>:<ulid>` prefix), omits
// empty groups, and returns a BrainView. The same kind appearing under more
// than one domain folder collapses into ONE group.
//
// The empty case — no `.brain`, or a `.brain` with no entities — yields
// `{ changeId, groups: [] }` (FR-06). Each BrainEntity carries enough for
// the readable detail view (FR-07): a resolved title and the full parsed
// object as `detail`.
//
// Pure read over the on-disk brain — no process start, no write (the same
// seam discipline as the status/transcript reads; the read-only gate
// proves no mutation here).

import { join } from "node:path";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type {
  BrainEntity,
  BrainGroup,
  BrainView,
} from "../../shared/api-types";
import { listDirs, listEntityFiles, readJsonldEntity } from "./brainFs";
import { isActiveStatus } from "./products/isActiveStatus";

/** The conventional brain layout under a change worktree. */
const BRAIN_INSTANCES = [".brain", "instances"];

/**
 * Read + group the brain entities created for a change.
 *
 * Best-effort and fail-soft: an absent `.brain` returns the empty case; a
 * single malformed entity file is skipped rather than failing the whole
 * read (a partial brain is still useful to the founder). Never throws on a
 * legitimate "no entities" condition.
 */
export async function readBrain(
  worktreeRoot: string,
  changeId: string,
): Promise<BrainView> {
  const instancesDir = join(worktreeRoot, ...BRAIN_INSTANCES);

  // kind → entities, preserving first-seen order of kinds.
  const byKind = new Map<string, BrainEntity[]>();

  const domains = await listDirs(instancesDir);
  for (const domain of domains) {
    const domainDir = join(instancesDir, domain);
    const kinds = await listDirs(domainDir);
    for (const kind of kinds) {
      const kindDir = join(domainDir, kind);
      const files = await listEntityFiles(kindDir);
      for (const file of files) {
        const entity = await readEntity(join(kindDir, file), kind);
        if (entity === null) continue;
        const bucket = byKind.get(kind);
        if (bucket) bucket.push(entity);
        else byKind.set(kind, [entity]);
      }
    }
  }

  const groups: BrainGroup[] = [];
  for (const [kind, items] of byKind) {
    if (items.length > 0) groups.push({ kind, items });
  }

  return { changeId, groups };
}

/**
 * Parse one entity file into a BrainEntity. Returns null (skip) when the
 * file is missing or not valid JSON — a malformed file must not sink the
 * whole brain read. The raw parse + fail-soft is the shared brainFs
 * primitive; this adds the BrainEntity shaping (id + title + detail).
 */
async function readEntity(
  path: string,
  kind: string,
): Promise<BrainEntity | null> {
  const parsed = await readJsonldEntity(path);
  if (parsed === null) return null;

  // ADR-020 soft-delete invariant: a removed entity (sys_status not active)
  // must not surface in the cockpit — the Brain view is a cockpit surface, so
  // it filters through the same shared predicate as readProducts /
  // resolveProjectRepo. Without this, a soft-deleted product/project would
  // still appear here.
  if (!isActiveStatus(parsed)) return null;

  const id = typeof parsed.id === "string" ? parsed.id : `dna:${kind}:unknown`;
  return {
    id,
    kind,
    title: resolveTitle(parsed, id),
    detail: parsed,
  };
}

/**
 * A human title for the detail view (FR-07): prefer an explicit `title`,
 * then `name`, then a decision-like field, else fall back to the id (never
 * empty). The fallback chain keeps every entity legible regardless of which
 * fields its schema carries.
 */
function resolveTitle(entity: Record<string, unknown>, id: string): string {
  const candidates = [
    entity.title,
    entity.name,
    entity.decision,
    entity.intent,
  ];
  for (const c of candidates) {
    if (typeof c === "string" && c.trim().length > 0) return c.trim();
  }
  return id;
}
