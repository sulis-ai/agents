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

import re
from pathlib import Path

from _change_state import change_dir

_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def within_change_scope(target, change_id, *, cwd=None) -> "tuple[bool, str]":
    """(ok, reason). True ONLY when `target` resolves to strictly within change
    `change_id`'s scoped dir and isn't the cwd/an ancestor. Fail-closed on a
    missing/invalid change_id. See module docstring for the threat model."""
    cid = str(change_id or "").strip()
    if not _ULID_RE.match(cid):
        return False, ("no valid change scope — refusing removal. A removal must "
                       "name the change it owns; never enumerate-and-match by name.")
    base = change_dir(cid).resolve()
    try:
        resolved = Path(target).resolve()
    except (OSError, RuntimeError) as exc:  # pragma: no cover - exotic FS error
        return False, f"cannot resolve target path {target!r}: {exc}"
    if resolved == base or not _is_within(resolved, base):
        return False, (f"refusing: {resolved} is outside change {cid}'s scope "
                       f"({base}) — cross-change / out-of-scope removal blocked.")
    if cwd is not None:
        cwdr = Path(cwd).resolve()
        if resolved == cwdr or _is_within(cwdr, resolved):
            return False, f"refusing: {resolved} is the current directory (or an ancestor)."
    return True, "within change scope"
