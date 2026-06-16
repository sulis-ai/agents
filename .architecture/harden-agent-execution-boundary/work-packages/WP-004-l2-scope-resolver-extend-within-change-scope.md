---
# Identity (WP-01)
id: WP-004
title: L2 scope-resolver — generalise within_change_scope to a multi-root allowlist
status: pending
change_id: 01KTZVX7RBE22SX6DNHA4Y6Y7B
kind: backend
source: harden
primitive: abstract
group: REORGANISE

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: medium

# Lifecycle (WP-07)
sequence_id: WP-004
dependsOn: []
blocks: [WP-005]

# Composite (WP-08)
child_wps: []
kinds: null

# REORGANISE compliance
characterisation_test: plugins/sulis/scripts/tests/unit/test_worktree_safety.py

estimated_token_cost:
  input: 9k
  output: 7k
tdd_section: §Form (_file_scope.py); §Armor L2 (fail-closed, canonical paths)
adrs: [ADR-004]
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_file_scope.py

rollback: |
  Delete _file_scope.py + test_file_scope.py and revert _worktree_safety.py to
  its pre-extract form. The existing test_worktree_safety.py is the safety net
  proving within_change_scope is behaviour-identical after revert. No consumer
  depends on _file_scope until WP-005.
---

# L2 scope-resolver

## Context

TDD §Form / §Armor L2. [ADR-004](../adrs/ADR-004-file-tool-scope-resolver-and-allowlist-source.md):
generalise #130's `within_change_scope` (`_worktree_safety.py`) from one root
(exclude-cwd) to a **multi-root allowlist** with **per-operation** policy —
**reusing**, not forking, its canonical-resolution + fail-closed core
(SPEC + Non-Negotiable #2). This is the primitive the four file-tools (WP-005)
share so the #130 invariant is enforced once, not in four drifting copies.

REORGANISE-Abstract over existing code → **characterisation test first**
(Non-Negotiable #3): `test_worktree_safety.py` is the pin. After the extract,
`within_change_scope` must remain the single-root exclude-cwd special case and
ALL its existing tests stay green; its callers (`git_worktree_remove`,
`wpx-worktree`) are byte-unchanged.

## Contract

### Files

```
plugins/sulis/scripts/_file_scope.py        (CREATE — the multi-root resolver + shared core)
plugins/sulis/scripts/_worktree_safety.py   (MODIFY — re-express via the shared core)
```

### Public surface (pin exactly)

```python
# _file_scope.py
@dataclass(frozen=True)
class AllowedRoots:
    """Canonical (.resolve()-d) per-change allowlist roots + per-op policy."""
    worktree: Path
    git_common_dir: Path
    change_state_dir: Path
    tools_cache_dir: Path | None
    creds_dir: Path | None        # read-only

def resolve_allowed_roots(change_id: str, *, repo_root: Path) -> AllowedRoots:
    """Build the canonical allowlist (ADR-004 table). Every root .resolve()-d."""

def within_allowed_scope(target, change_id, *, operation, roots=None,
                         repo_root=None) -> tuple[bool, str]:
    """(ok, reason). operation ∈ {"read","write","move","remove"}.
    True iff target.resolve() is within an allowed root permitted for that
    operation. creds_dir permits 'read' only. Fail-closed on invalid change_id,
    unknown operation, unresolvable path, or no matching root."""
```

### Reused (lifted into a shared core, not re-implemented)

| Symbol | From | Role |
|---|---|---|
| `_is_within`, the `Path.resolve()` canonical step, ULID validation, fail-closed default | `_worktree_safety` | the shared core both resolvers use; `within_change_scope` becomes the single-root exclude-cwd special case of it |
| `change_dir`, `change_worktree_dir`, `changes_base` | `_change_state` | allowlist-root sources |

## Definition of Done

> **Satisfies (scenario):** the resolver-decision half of **SC-L2.2**
> (out-of-scope read, incl. `/tmp`→`/private/tmp` canonical case),
> **SC-L2.3** (out-of-scope write/move/remove), **SC-L2.4** (traversal/symlink).
> The tool-level success/refusal end-to-end (SC-L2.1, and the I/O side of
> 2.2–2.4) lands in WP-005.

### Red
- [ ] Confirm `test_worktree_safety.py` is GREEN before any edit (the
  characterisation pin).
- [ ] `test_file_scope.py` written failing:
  - **SC-L2.1 (decision):** a path in the worktree / git-common-dir /
    change-state / tools-cache resolves `ok=True` for read+write+move+remove;
    a path in creds resolves `ok=True` for read, `ok=False` for write/move/remove.
  - **SC-L2.2:** `~/.ssh` and a sibling change's worktree resolve `ok=False`
    for read; **the `/tmp`→`/private/tmp` canonical case** resolves correctly
    (a target given as `/tmp/...` is canonicalised before the containment check).
  - **SC-L2.3:** the #130 sibling-worktree path resolves `ok=False` for
    write/move/remove (the cross-worktree-deletion replay at the decision layer).
  - **SC-L2.4:** a `..`-escape and a symlink pointing outside scope resolve
    `ok=False` (mirrors `test_worktree_safety.py`'s case set).
  - fail-closed: invalid change-id, unknown operation, unresolvable path → `ok=False`.
  - a hypothesis property: no path outside every allowed root is ever `ok=True`
    (the safety invariant, mirroring the worktree-safety property).

### Green
- [ ] `_file_scope.py` created; all Red pass.
- [ ] `_worktree_safety.py` modified to re-express `within_change_scope` via the
  shared core. **`test_worktree_safety.py` still entirely GREEN** (characterisation
  held — no regression for `git_worktree_remove`/`wpx-worktree`).

### Blue
- [ ] `_file_scope` docstring: states canonical-paths-everywhere (both sides
  `.resolve()`-d), the per-op creds-read-only rule, fail-closed default, and
  the honest limit (SC-L2.5: this resolver is never reached by a subprocess —
  that is L3, ADR-001/004).
- [ ] One copy of the containment invariant (the shared core); `within_change_scope`
  and `within_allowed_scope` are both thin over it — the #130 incident's
  drifted-copy root cause cannot recur.
- [ ] Stdlib + `_change_state` only; Python 3.11-safe; portable (no GNU-only
  assumptions; `git rev-parse --git-common-dir` is portable).

## Sequence
- **dependsOn:** none (head of the L2 track).
- **Parallelisable with:** the entire L1 track (WP-001..003) — disjoint files.

## Verification Plan
- **Adapter:** `backend`. **Shape:** concrete.
- **Artifact:** `plugins/sulis/scripts/tests/unit/test_file_scope.py`
  (+ unchanged `test_worktree_safety.py` as the characterisation pin).
- **Proves:** the multi-root, canonical, fail-closed scope decision for all
  four operations + the #130-invariant non-regression.
