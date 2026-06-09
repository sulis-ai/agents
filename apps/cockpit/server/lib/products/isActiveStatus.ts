// WP-003 (ADR-020) — shared read-side soft-delete filter.
//
// Remove is a soft-delete: the entity's `.jsonld` file stays on disk with
// `sys_status` set to a removed value (ADR-020). For removal to be observable
// in the cockpit, every reader of these brain entities MUST skip the removed
// ones. This is the single source of that predicate — `readProducts` and
// `resolveProjectRepo` both filter through it (EP-03; the predicate lives once,
// no duplicated status list).
//
// Back-compat invariant: an entity with no `sys_status` field (legacy) is
// treated as ACTIVE — absence ≠ deleted. Only the explicit removed statuses
// hide an entity.
//
// ADR-020 consequence: ANY future reader of `dna:product` / `dna:project`
// entities added later must apply this same filter, or soft-deleted entities
// will leak back into that read path.

/** The `sys_status` values that mean "removed" — hidden from every read path. */
const REMOVED_STATUSES: ReadonlySet<string> = new Set([
  "deleted",
  "purged",
  "archived",
]);

/**
 * True when a raw brain entity should be shown on a read path — i.e. it is not
 * soft-deleted. An entity with no `sys_status` (legacy) is active; an entity
 * whose `sys_status` is one of the removed values is hidden.
 */
export function isActiveStatus(entity: Record<string, unknown>): boolean {
  const status = entity.sys_status;
  if (typeof status !== "string") return true; // legacy / absent ⇒ active
  return !REMOVED_STATUSES.has(status);
}
