// WP-002 — Shared "active, sorted by name" read helper (TDD §2.3; ADR-020).
//
// `readTree` must return ACTIVE entities only, each level sorted by name
// (TDD §5.3). That filter-then-sort appears at two levels inside any adapter
// (products at the top, projects under each product) and again — identically —
// inside the real adapter (WP-005). Per EP-03 / the Non-Negotiables, the
// moment a pattern has two consumers we extract the shared primitive; this is
// that primitive, lifted here so the real `SpineSettingsAdapter` reuses it
// rather than re-deriving the soft-delete-filter + name-sort and risking drift
// from the contract.
//
// It is intentionally generic over `{ name; status }`-shaped rows so both the
// fake's in-memory rows and the real adapter's brain-entity rows flow through
// the same code. The `status` field mirrors the brain schema's `sys_status`
// (ADR-020): "active" survives, everything else (deleted / archived / purged)
// is filtered out — an allow-list, not a deny-list, so an unknown future
// status is hidden by default rather than leaking into the cockpit.

/** The lifecycle field every settings entity carries (mirrors `sys_status`). */
export type HasStatus = { status: string };

/** Any row the helper can sort — it needs only a `name`. */
export type HasName = { name: string };

/** Stable, case-sensitive name comparator. Extracted so `readTree`'s product
 *  level and project level (and WP-005's real adapter) share ONE ordering. */
export function byName(a: HasName, b: HasName): number {
  return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
}

/** True iff the entity is active (allow-list, not deny-list — ADR-020). */
export function isActive(entity: HasStatus): boolean {
  return entity.status === "active";
}

/**
 * The one read primitive `readTree` uses at every level and WP-005 reuses:
 * keep only active rows, then sort by name. Returns a new array; the input is
 * never mutated.
 */
export function activeSortedByName<T extends HasStatus & HasName>(
  rows: Iterable<T>,
): T[] {
  return [...rows].filter(isActive).sort(byName);
}
