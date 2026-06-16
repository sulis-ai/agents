# ADR-001 — The recreate seam is keyed by change_id, not the handle

> change_id `01KTV4SS9N8BP0XN8GCQAXT6PC` · status: accepted (design) · 2026-06-11

## Decision

The `RecreateRunner` port and the underlying `sulis-change recreate` CLI verb
are keyed by the full unique `change_id`. The port method becomes
`recreate(changeId: string)`; the CLI gains a `recreate --change-id <ULID>`
entry point; the cockpit serving path passes `record.changeId` (which it already
holds, having read the record by id). `--handle` and `--slug` remain on the CLI
for backward compatibility and for founder-typed resolution, going through the
ambiguity-refusing `_changes_matching_handle` matcher.

## Context

The 6-char `CH-XXXXXX` handle is a display label derived from the ULID; live data
has 26 handles each shared by 2–4 changes. The cockpit read the change record by
its unique id, then discarded that id and re-resolved by the non-unique handle
across the CLI subprocess seam — the structural cause of "session works on the
wrong change". The port's own identity key was the wrong (non-unique) value.

The whose-interface discriminator (Ports & Adapters vs Wrappers): `RecreateRunner`
is the **cockpit's own** port. Correcting its identity key is a REORGANISE of an
owned contract, not a wrapper over external code.

## Alternatives considered

- **Keep `recreate(handle)`, make the CLI always refuse on collision.**
  Rejected: a colliding-handle recreate would then *fail* (degrade to "couldn't
  reach this change") even though the cockpit knew exactly which change it meant.
  The id is in hand; refusing to use it is throwing away certainty.
- **Resolve the id→handle→id round-trip inside the cockpit before spawning.**
  Rejected: a pointless round-trip through a non-unique key; the CLI must accept
  the id directly so the unambiguous path is first-class, matching `nuke` and
  `mark-shipped` which already accept `--change-id`.
- **Add a brand-new `materialise-by-id` verb.** Rejected: `recreate` already
  owns worktree materialisation (#56) and is idempotent; a parallel verb would
  duplicate that logic. Extend the existing verb (CP-01 internal prior art).

## Consequences

- The cockpit recreate path is unambiguous by construction; Scenarios 1–3 close.
- `recreate`, `nuke`, `mark-shipped` all accept `--change-id` → a consistent
  unambiguous entry point across the act-on verbs.
- The handle remains in CLI JSON output and the change record as a display label;
  no founder is forced to type a long id (SPEC Constraint preserved).
