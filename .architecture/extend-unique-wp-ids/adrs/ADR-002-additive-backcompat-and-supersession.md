# ADR-002 — Strictly additive prefixing, one-release back-compat, supersede the parked effort

> **Change:** CH-5DMB1N · extend · `unique-wp-ids`
> **Status:** accepted
> **Date:** 2026-06-10

## Context

Changes already in flight carry bare `WP-NNN` ids in their **committed** INDEX
files. The parser must keep understanding them, or in-flight changes break
mid-run. Separately, a parked effort `canonicalise-cross-wp-ids` exists with the
same goal but no real design.

## Decision

**1. Strictly additive, one-release back-compat.** New ids are minted prefixed
(`{CH-HANDLE}-WP-NNN`); existing bare `WP-NNN` ids stay bare and remain
*understood* by the widened matcher (ADR-001). There is **no migration pass**
over in-flight INDEX files — nothing rewrites an existing committed id. Both
shapes are understood for exactly one release.

**2. The minting change's own WPs stay bare (chicken-and-egg).** This change's
Work Packages are minted as `WP-001`, `WP-002`, `WP-003` — the *current* bare
scheme — because the parser and `run-all` loop won't understand prefixed ids
until this very change ships. Prefixed minting switches on for the *next* change
created after this one merges. This is recorded in the INDEX and the WP files.

**3. Legacy-removal is a future change, not this one.** Dropping bare-id support
is a separate, tracked follow-up (already on the task list:
*"Drop legacy bare WP-NNN id back-compat (one release after CH-5DMB1N)"*) so the
deprecation is actioned, not forgotten — mirroring how #283 tracked its own
fallback-removal as a follow-up.

**4. Supersede `canonicalise-cross-wp-ids`.** That parked effort contains only a
stray executor journal (`.architecture/canonicalise-cross-wp-ids/work-packages/
.executor-WP-001.md`) — no spec, no TDD, no real WP. Its intent ("WP ids unique
across changes") is realised here, canonically, mirroring #283's branch scheme.
There is no salvageable design to fold in. It is **superseded**; the stub is
retired. No work is duplicated.

## Alternatives considered

- **Migrate all in-flight INDEX files to the prefixed shape now (rejected).** A
  migration pass over committed artifacts in active changes is a large blast
  radius for zero benefit — the widened matcher already understands the bare
  ids. It would also risk corrupting an in-flight change's INDEX mid-run.
  Strictly-additive is the boring, safe path; the bare ids age out naturally as
  their changes complete.
- **Mint this change's own WPs with the new prefix (rejected — would not run).**
  The tooling that executes these WPs doesn't understand prefixed ids until this
  change merges; prefixed WPs here would be invisible to `run-all`. The
  chicken-and-egg forces bare ids for exactly this one change.
- **Drop legacy support in the same change (rejected).** Removing bare-id
  support immediately would break every in-flight change carrying committed bare
  ids. The one-release window is the whole point; removal is a separate change
  once the in-flight bare ids have drained.
- **Resurrect and continue `canonicalise-cross-wp-ids` (rejected).** It has no
  design to continue. Re-homing the intent here and retiring the stub avoids two
  competing efforts for one outcome.

## Consequences

- In-flight changes keep running unmodified through this release.
- Exactly one source of new collisions is closed (new mints are unique) without
  touching any existing id.
- The deprecation has an owner and a trigger (the tracked follow-up task), so
  the back-compat window closes deliberately rather than lingering as rot.
- One canonical effort owns "unique WP ids"; the parked duplicate is retired.
