# ADR-004 — L2 extends `within_change_scope` to a multi-root allowlist resolver over canonical paths; the four file-tools share it

> **Status:** accepted
> **Date:** 2026-06-13
> **Change:** CH-E22SX6 · harden
> **Affects:** L2 file-tools (read/write/move/remove), the scope-resolver, SC-L2.1–2.4

## Context

#130's `within_change_scope` (`_worktree_safety.py`) already encodes the
exact safety invariant L2 needs: a path is in scope only if it resolves
(`Path.resolve()` — canonical, handles `..` traversal and symlink escape and
the `/tmp`→`/private/tmp` footgun) to strictly within the named change's dir,
fail-closed on a missing/invalid change-id. It is wired into
`git_worktree_remove` and `wpx-worktree remove`.

The SPEC says L2 **extends this exact pattern from `remove` to the full
read/write/move surface** (Non-Negotiable: reuse it, don't fork it). But two
things differ from the `remove` case:

1. **Multiple allowed roots, not one.** A working agent legitimately reads/
   writes the worktree **and** the git-common-dir (shared `.git`), the
   change-state dir, the tools/cache dir, and the creds it needs — SPEC §L2.
   `within_change_scope` allows exactly one root (`change_dir(cid)`) and
   *excludes the cwd*; that exclusion is right for `remove` (don't delete the
   floor you stand on) but wrong for read/write (you absolutely read the cwd).
2. **Per-operation policy.** `read` may be allowed on a slightly wider set
   than `write`/`move`/`remove` (e.g. read creds, never write them).

## Decision

**Add a `within_allowed_scope(target, change_id, *, operation, roots=None)`
resolver in a new `_file_scope.py` that REUSES `within_change_scope`'s
canonical-resolution + fail-closed core, generalised to a multi-root
allowlist; the four file-tools all call it.**

1. **Reuse, don't fork.** The canonical `Path.resolve()` step, the
   `_is_within` containment check, the ULID validation, and the fail-closed
   default are imported/lifted from `_worktree_safety`, not re-implemented.
   Where the shape genuinely generalises (one root → many roots), the shared
   helper is extracted so `within_change_scope` becomes the single-root,
   exclude-cwd special case of the same primitive (REORGANISE-Extract,
   characterisation-test-first against `test_worktree_safety.py`).

2. **The allowlist source (canonical paths, computed once):**

   | Root | Source | read | write/move/remove |
   |---|---|---|---|
   | worktree | `change_worktree_dir(cid)` | ✓ | ✓ |
   | git-common-dir | `git rev-parse --git-common-dir` resolved | ✓ | ✓ (git internals) |
   | change-state dir | `change_dir(cid)` | ✓ | ✓ |
   | tools / cache | configured tools/cache dir | ✓ | ✓ |
   | creds | configured creds path | ✓ | ✗ (read-only) |

   **Every root is `.resolve()`-d at allowlist construction**, so the
   `/tmp`→`/private/tmp` footgun (and any symlinked root) is canonicalised
   on *both* sides of the containment check — the SPEC's "canonical paths
   everywhere" constraint.

3. **Fail-closed.** Unknown operation, missing change-id, unresolvable path,
   path outside every allowed root → refuse with a clear reason. The default
   is deny.

4. **The four tools are thin.** `read` / `write` / `move` / `remove` each
   resolve scope first (`move` checks **both** source and destination), then
   perform the op. The decision is in `_file_scope`; the I/O is in the tool.

## Alternatives considered

- **Fork `within_change_scope` into four near-copies (rejected).** Four
  copies of the invariant drift; the #130 incident is exactly what a drifted
  copy reintroduces. CP-01 + Non-Negotiable #2: extract the shared primitive.
- **A single allow-all-under-worktree check (rejected).** Misses the
  legitimate multi-root reality (git-common-dir, creds) — would break normal
  work (SC-L2.1) by refusing reads the agent genuinely needs.
- **Per-tool bespoke path checks (rejected).** Scatters the safety invariant
  across four call sites; a fix to one (e.g. a new traversal case) misses the
  others. One resolver, four callers.

## Consequences

- SC-L2.1 (in-scope ops succeed) is proven across all four tools + the
  multi-root allowlist. SC-L2.2/2.3 (out-of-scope read/write/move/remove
  refused, incl. the `~/.ssh` and sibling-worktree cases) and SC-L2.4
  (traversal/symlink) reuse `test_worktree_safety.py`'s case set, extended to
  the new operations and roots.
- The cross-worktree-deletion incident (#130) is now structurally refused on
  `write`/`move`/`remove` too, not just `remove` — the SPEC's SC-L2.3 replay.
- `within_change_scope`'s existing callers (`git_worktree_remove`,
  `wpx-worktree`) are unchanged: it remains the single-root exclude-cwd
  special case, now expressed via the shared primitive. The characterisation
  test guarantees no regression.
- SC-L2.5 (subprocess bypass) is explicitly **out of this resolver's reach** —
  a `bash -c 'cat …'` never calls `within_allowed_scope`. ADR-001's honesty
  applies: L2 is a guardrail over the *tools*, not a wall over the *process*;
  that is L3.
