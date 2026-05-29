# ADR-003 — Per-change resolution is generic; nothing is hard-wired to a specific change

> Status: accepted · 2026-05-29 · change: cockpit-contract-preview

## Decision

Every path the feature touches — locating a change's data contract(s), locating
its visual contract, resolving where the rendered artifacts live, surfacing the
cockpit links — derives **entirely from the change's own record** (`change.json`
via the `ChangeStoreReader` port: `worktreePath`, `changeId`, `branch`,
`shipped_sha`). No change handle, slug, or path is ever embedded in code.

- The renderer **discovers** the data contract(s) inside a given worktree by
  convention-based search, recognising formats in precedence order (ADR-005):
  ServiceSpec JSON-LD first (e.g. `**/*service*spec*.json`, `**/*.servicespec.json`,
  plus a JSON-LD `@type: "ServiceSpec"` content sniff), then OpenAPI
  (`**/openapi*.y?ml`, `**/*.openapi.json`, `**/openapi.json`, `**/swagger.json`),
  not by a fixed filename for one change.
- The cockpit endpoints take `:id` and resolve the worktree via the existing
  `requireChange` + `resolveWorktreeRoot` helpers — the same generic path the
  tree/file/diff endpoints already use.
- Release acceptance includes the founder's explicit anti-hard-wiring check:
  open the cockpit, walk *every* in-flight change, confirm each surfaces its
  *own* data + UI contracts.

## Why

- **Founder decision 3 (binding).** The founder explicitly asked for this; it
  is the trust property of the whole feature.
- **The cockpit data layer is already generic.** `/api/changes` and
  `/api/changes/:id` list/open changes through the `ChangeStoreReader` port with
  no per-change special-casing. Building the new surfaces the same way is reuse
  (EP-03), not new work.

## Rejected alternatives

- **A lookup table mapping change → spec path.** Rejected: hard-wiring; rots the
  moment a change is added; precisely what the founder forbade.

## Consequence

The renderer must handle "spec not found" and "more than one spec" without
assuming a single canonical file (see ADR-002's degradation path). The
acceptance walk-every-change check is a release gate, not a smoke test on one
change.
