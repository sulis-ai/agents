# ADR-004 — Reach a shipped change's contracts by recreating its worktree via `sulis-change recreate`

> Status: accepted · 2026-05-29 · change: cockpit-contract-preview

## Decision

When a change is shipped, its worktree is removed (the #56 tidy step) but its
branch + record (with the pinned `shipped_sha`) are kept. To render contracts
for a tidied change, the feature **recreates the worktree on demand** by
invoking the already-shipped `sulis-change recreate` command (resolved by
`--handle`), then renders against the re-materialised worktree, transparently
to the founder.

`recreate` already does the right thing: attaches to the branch if it still
exists, else checks out detached at `shipped_sha`; and is idempotent ("worktree
already exists" → no-op success).

## Why

- **Reuse (EP-03, CP-01 internal prior art).** `sulis-change recreate` is
  shipped and exactly fits. Re-implementing worktree materialisation would
  duplicate `cmd_recreate`.
- **The cockpit stays read-only.** Recreate is a separate, explicitly-invoked
  step (a `spawn` of the existing CLI with a timeout), not request-path
  generation. It is gated on the founder reaching for a shipped change's
  contract — not done speculatively for every list render.

## Rejected alternatives

- **Render at ship time and cache the HTML forever.** Rejected for the on-demand
  path: a shipped change may never be re-inspected, and caching every render
  bloats state; also the founder asked for transparent recreate, which keeps
  the source-of-truth property (render against the actual shipped tree).
  (Design-time rendering still happens for in-flight changes — see TDD §timing.)
- **Keep all worktrees forever.** Rejected: contradicts the #56 lifecycle work
  that this change composes with.

## Consequence

The renderer/serving path must distinguish three states for a change:
(a) worktree present → render directly; (b) worktree absent but recreatable
(branch or `shipped_sha`) → recreate then render; (c) absent and not
recreatable (legacy, predates `shipped_sha`) → degrade with a plain note. The
recreate call follows the cockpit's spawn-not-exec + timeout discipline.
