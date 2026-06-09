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
// treated as ACTIVE — absence ≠ deleted. This is the one deliberate exception
// (legacy rows minted before sys_status was stamped); every sanctioned emitter
// now writes `sys_status: "active"` on emission.
//
// HARDENING (allow-list, not deny-list): a PRESENT `sys_status` is shown ONLY
// when it is the explicit active sentinel. Any other present value — a known
// removed status (deleted/purged/archived) OR an unrecognised/typo'd one — is
// hidden. A deny-list would let a crafted or misspelled status sail through as
// "active"; the allow-list closes that. This matches the Python read helper
// (`list-entities.py`, `sys_status == "active"`) and `settingsActiveSort.ts`, so
// all three active-status definitions agree by construction.
//
// ADR-020 consequence: ANY future reader of `dna:product` / `dna:project`
// entities added later must apply this same filter, or soft-deleted entities
// will leak back into that read path (e.g. the per-change Brain view, which now
// also filters through this predicate).

/** The single `sys_status` value that means "active" — the only present status
 *  shown on a read path (allow-list). */
const ACTIVE_STATUS = "active";

/**
 * True when a raw brain entity should be shown on a read path — i.e. it is not
 * soft-deleted. An entity with no `sys_status` (legacy) is active; an entity
 * with a present `sys_status` is active ONLY when it equals the active sentinel
 * (allow-list) — any other present value is hidden.
 */
export function isActiveStatus(entity: Record<string, unknown>): boolean {
  const status = entity.sys_status;
  if (typeof status !== "string") return true; // legacy / absent ⇒ active
  return status === ACTIVE_STATUS; // allow-list: only explicit "active" is shown
}
