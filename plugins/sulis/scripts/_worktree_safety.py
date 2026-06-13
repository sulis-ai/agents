"""within_change_scope — makes cross-change worktree removal structurally
impossible (#130).

The incident: a cleanup found worktrees by a WP-number glob (`git worktree list
| grep wp-006`) in the SHARED repo, where WP numbers aren't unique across
changes — so it removed worktrees belonging to OTHER in-flight changes. Root
cause: the glob discards the only unique key — the change-id in the path.

The guard: a removal MUST name the change it owns, and the target MUST resolve
to within that change's scoped dir (`{changes_base}/{change_id}/`). Everything
else is refused:
  - a DIFFERENT change's dir (the incident)
  - the main repo, /tmp, anywhere outside the change scope
  - a `..` path-traversal or a symlink that escapes the scope (resolve() first)
  - a removal with NO / an invalid change scope → fail-closed
  - the directory you're currently standing in (or an ancestor of it)

The change-id in the path is the unique key; a name/number glob throws it away.
"""

from __future__ import annotations

from pathlib import Path

from _change_state import change_dir

# REUSE — not fork — the L2 scope-resolver's safety core (ADR-004).
# `within_change_scope` is the SINGLE-ROOT, exclude-cwd, exclude-base special
# case of the same canonical-resolution + fail-closed containment primitive that
# the multi-root `within_allowed_scope` is built on. One copy of the #130
# invariant: a fix to the containment check (a new traversal/symlink case)
# lands in `_file_scope.resolve_within_roots` and both resolvers inherit it.
from _file_scope import (
    _is_within,
    canonical,
    is_valid_change_id,
    resolve_within_roots,
)


def within_change_scope(target, change_id, *, cwd=None) -> "tuple[bool, str]":
    """(ok, reason). True ONLY when `target` resolves to strictly within change
    `change_id`'s scoped dir and isn't the change dir itself, the cwd, or an
    ancestor of the cwd. Fail-closed on a missing/invalid change_id. See module
    docstring for the threat model.

    This is the single-root (`change_dir(cid)`), exclude-cwd, exclude-base
    special case of `_file_scope.within_allowed_scope` — expressed via the same
    shared `resolve_within_roots` core so the #130 invariant lives in one place.
    """
    cid = str(change_id or "").strip()
    if not is_valid_change_id(cid):
        return False, ("no valid change scope — refusing removal. A removal must "
                       "name the change it owns; never enumerate-and-match by name.")
    base = change_dir(cid).resolve()
    # Shared containment decision (canonical resolve + fail-closed) over the
    # single allowed root.
    ok, _reason = resolve_within_roots(target, cid, [base])
    resolved = canonical(target)
    # Refuse anything outside the root OR the root itself: removing the whole
    # change dir via a worktree-remove is not a worktree op (strictly-within).
    if not ok or resolved is None or resolved == base:
        return False, (f"refusing: {resolved if resolved is not None else target} "
                       f"is outside change {cid}'s scope ({base}) — "
                       f"cross-change / out-of-scope removal blocked.")
    # Exclude the cwd / an ancestor of it: don't delete the floor you stand on.
    if cwd is not None:
        cwdr = Path(cwd).resolve()
        if resolved == cwdr or _is_within(cwdr, resolved):
            return False, f"refusing: {resolved} is the current directory (or an ancestor)."
    return True, "within change scope"
