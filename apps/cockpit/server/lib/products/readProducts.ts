// WP-008 — readProducts: the Tenant's Products + the change→Project→Product
// roll-up index (FR-38, ADR-009).
//
// Sources the Tenant's Products from the brain's `dna:product` entities and
// (when given the change set) builds the `change → Project → Product` roll-up
// a board/search read scopes with. The roll-up keys on a change's worktree
// path falling under a Project's `source.path`; a Project carries
// `belongs_to_product_ref` (→ its Product).
//
// HONEST single-Product reality: the real brain has no Product entities
// minted yet, so when none are found readProducts synthesises ONE implicit
// Product (the single-Product Tenant trivial case) — the board still renders
// a switcher showing that one Product, marked active, and every change is in
// scope (productScope's trivial branch).
//
// Pure read over the on-disk brain — no process start, no write (the same
// seam discipline as readBrain; the read-only gate proves no mutation here).
// Fail-soft: a malformed entity file is skipped, an absent brain yields the
// implicit single Product.

import { join } from "node:path";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { Product, ProductList } from "../../../shared/api-types";
import type { ChangeStoreRecord } from "../../ports/ChangeStoreReader";
import { listDirs, listEntityFiles, readJsonldEntity } from "../brainFs";
import { isActiveStatus } from "./isActiveStatus";
import type { ProductRollup } from "./productScope";

/** The brain layout the Tenant's entities live under (mirrors readBrain). */
const BRAIN_INSTANCES = [".brain", "instances"];

/** The id of the synthesised single implicit Product (the trivial Tenant). */
export const IMPLICIT_PRODUCT_ID = "dna:product:implicit-single";
/** The display name of the implicit single Product. */
export const IMPLICIT_PRODUCT_NAME = "Your product";

export interface ReadProductsOptions {
  /** ~/.sulis (or a test override). */
  sulisStateDir: string;
  /**
   * The Product the client asked to scope to (the `?product=` value). When
   * unknown or absent, the first Product is marked active. Never produces a
   * null active id when at least one Product exists.
   */
  activeProductId?: string | null;
  /**
   * The change set, when the caller needs the `change → Product` roll-up
   * (the board/search reads). Omit for the product-list-only read
   * (`GET /api/products`), where `changeToProduct` stays empty.
   */
  changes?: readonly ChangeStoreRecord[];
}

export interface ReadProductsResult {
  list: ProductList;
  rollup: ProductRollup;
}

/** One Project's owning-Product + the filesystem root its changes live under. */
interface ProjectRecord {
  productId: string;
  sourcePath: string;
}

/**
 * Read the Tenant's Products and (optionally) build the change→Product
 * roll-up. See the file header for the single-Product honest fallback.
 */
export async function readProducts(
  opts: ReadProductsOptions,
): Promise<ReadProductsResult> {
  const instancesDir = join(opts.sulisStateDir, ...BRAIN_INSTANCES);

  const rawProducts = await readEntitiesOfKind(instancesDir, "product");
  const products = rawProducts
    .map(toProduct)
    .filter((p): p is Product => p !== null);

  // HONEST single-Product fallback: no minted Products ⇒ one implicit Product.
  if (products.length === 0) {
    const implicit: Product = {
      productId: IMPLICIT_PRODUCT_ID,
      name: IMPLICIT_PRODUCT_NAME,
      active: true,
    };
    return {
      list: { products: [implicit], activeProductId: IMPLICIT_PRODUCT_ID },
      rollup: { productIds: [IMPLICIT_PRODUCT_ID], changeToProduct: new Map() },
    };
  }

  // Resolve the active Product: honour the request when it names a real
  // Product, else default to the first. Never null when a Product exists.
  const productIds = products.map((p) => p.productId);
  const requested = opts.activeProductId ?? null;
  const activeProductId =
    requested !== null && productIds.includes(requested)
      ? requested
      : (productIds[0] ?? null);

  const list: ProductList = {
    products: products.map((p) => ({
      ...p,
      active: p.productId === activeProductId,
    })),
    activeProductId,
  };

  // Build the roll-up only when the caller supplied the change set.
  const changeToProduct = new Map<string, string>();
  if (opts.changes && opts.changes.length > 0) {
    const projects = await readProjects(instancesDir);
    for (const change of opts.changes) {
      const productId = rollUpChange(change, projects);
      if (productId !== null) changeToProduct.set(change.changeId, productId);
    }
  }

  return { list, rollup: { productIds, changeToProduct } };
}

/**
 * Roll one change up to its Product via the Project whose `source.path` is a
 * prefix of the change's worktree path (`change → Project → Product`). The
 * longest matching prefix wins (nested project roots). Returns null when no
 * Project claims the change — in the multi-Product case it is then left out
 * of any specific Product's scope (productScope's filter).
 */
function rollUpChange(
  change: ChangeStoreRecord,
  projects: ProjectRecord[],
): string | null {
  let best: ProjectRecord | null = null;
  for (const project of projects) {
    if (isUnder(change.worktreePath, project.sourcePath)) {
      if (best === null || project.sourcePath.length > best.sourcePath.length) {
        best = project;
      }
    }
  }
  return best?.productId ?? null;
}

/** True when `path` is the same as, or nested under, `root`. */
function isUnder(path: string, root: string): boolean {
  if (root.length === 0) return false;
  if (path === root) return true;
  const withSep = root.endsWith("/") ? root : `${root}/`;
  return path.startsWith(withSep);
}

/** Parse the Tenant's Project entities into productId + source-path records. */
async function readProjects(instancesDir: string): Promise<ProjectRecord[]> {
  const raw = await readEntitiesOfKind(instancesDir, "project");
  const out: ProjectRecord[] = [];
  for (const entity of raw) {
    const ref = entity.belongs_to_product_ref;
    const sourcePath = parseSourcePath(entity.source);
    if (typeof ref !== "string" || ref.length === 0 || sourcePath === null) {
      continue;
    }
    // `belongs_to_product_ref` is the bare ULID (per the schema); the Product
    // id is the full `dna:product:<ulid>`. Normalise to the full id.
    const productId = ref.startsWith("dna:product:") ? ref : `dna:product:${ref}`;
    out.push({ productId, sourcePath });
  }
  return out;
}

/** Project.source is a JSON-encoded `{repo, path, primary_branch}` string. */
function parseSourcePath(source: unknown): string | null {
  if (typeof source !== "string" || source.length === 0) return null;
  try {
    const parsed = JSON.parse(source) as { path?: unknown };
    return typeof parsed.path === "string" && parsed.path.length > 0
      ? parsed.path
      : null;
  } catch {
    return null;
  }
}

/**
 * Read every `.jsonld` entity of one kind across all brain domains. The same
 * kind may live under more than one domain folder (product-development,
 * foundation, …); we scan them all. Fail-soft: an absent brain returns [], a
 * malformed file is skipped.
 *
 * WP-003 / ADR-020: soft-deleted entities (`sys_status ∈ {deleted, purged,
 * archived}`) are filtered out here via the shared `isActiveStatus` predicate,
 * so a removed entity disappears from the cockpit. A legacy entity with no
 * `sys_status` is active (absence ≠ deleted). Any future reader of these
 * entities MUST apply the same filter.
 */
async function readEntitiesOfKind(
  instancesDir: string,
  kind: string,
): Promise<Array<Record<string, unknown>>> {
  const out: Array<Record<string, unknown>> = [];
  const domains = await listDirs(instancesDir);
  for (const domain of domains) {
    const kindDir = join(instancesDir, domain, kind);
    const files = await listEntityFiles(kindDir);
    for (const file of files) {
      const parsed = await readJsonldEntity(join(kindDir, file));
      if (parsed !== null && isActiveStatus(parsed)) out.push(parsed);
    }
  }
  return out;
}

function toProduct(entity: Record<string, unknown>): Product | null {
  const id = typeof entity.id === "string" ? entity.id : null;
  const name = typeof entity.name === "string" ? entity.name : null;
  if (id === null || !id.startsWith("dna:product:")) return null;
  return { productId: id, name: name ?? id };
}

