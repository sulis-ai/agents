"""L2 scope-resolver — the per-change file-access allowlist, canonical and
fail-closed (ADR-004).

This module GENERALISES #130's ``within_change_scope`` (``_worktree_safety``)
from one root (exclude-cwd, for ``remove``) to a **multi-root allowlist** with
**per-operation** policy, REUSING — not forking — its safety core:

  * the canonical ``Path.resolve()`` step (handles ``..`` traversal, symlink
    escape, and the ``/tmp``->``/private/tmp`` footgun — applied on BOTH sides
    of the containment check),
  * the ``_is_within`` containment check,
  * ULID validation of the change-id,
  * the fail-closed default (deny unless a matching root permits the op).

The four file-tools (read / write / move / remove — WP-005) all call
``within_allowed_scope``, so the #130 invariant is enforced in ONE place, not
in four drifting copies — the incident's drifted-copy root cause cannot recur.

**Canonical paths everywhere.** Every allowlist root is ``.resolve()``-d at
construction (``resolve_allowed_roots``) AND defensively re-resolved inside the
containment check; the target is ``.resolve()``-d before comparison. So a path
handed in as ``/tmp/x`` (which the OS resolves to ``/private/tmp/x``) is matched
against a root by its real path, never its surface spelling.

**Per-operation policy.** ``read`` may be permitted on a wider set than
``write``/``move``/``remove``: the credentials root permits ``read`` only, never
mutation (Rule of Two — read a secret, never write one back out).

**Fail-closed.** An invalid change-id, an unknown operation, an unresolvable
target, or a target outside every permitted root → refuse with a clear reason.
The default is deny.

**Honest limit (SC-L2.5).** This resolver is a guardrail over the *tools*, not
a wall over the *process*. A raw subprocess (``bash -c 'cat <out-of-scope>'``)
never calls ``within_allowed_scope`` and is therefore NOT confined by it; that
is L3's job (the per-OS sandbox — ADR-001/004). Do not mistake this decision
layer for OS-level egress denial.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from _change_state import change_dir, change_worktree_dir

# Operations the resolver knows about. The credentials root permits only the
# first; every other populated root permits all four.
_OPERATIONS: frozenset[str] = frozenset({"read", "write", "move", "remove"})
_MUTATING: frozenset[str] = frozenset({"write", "move", "remove"})

_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


# ─── the shared safety core (reused by within_change_scope, #130) ───────────


def _is_within(child: Path, parent: Path) -> bool:
    """True iff ``child`` is at or under ``parent``. Both should already be
    canonical (``.resolve()``-d) — the single containment primitive."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def is_valid_change_id(change_id) -> bool:
    """True iff ``change_id`` is a syntactically valid ULID. The change-id in
    the path is the unique key; a name/number glob throws it away (#130)."""
    return bool(_ULID_RE.match(str(change_id or "").strip()))


def canonical(target) -> Path | None:
    """``Path(target).resolve()`` or ``None`` if the path cannot be resolved.

    Fail-closed: an unresolvable target (exotic FS error, a path-like that
    raises on ``__fspath__``) yields ``None`` so the caller refuses."""
    try:
        return Path(target).resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def resolve_within_roots(
    target,
    change_id,
    permitted_roots: "list[Path]",
) -> "tuple[bool, str]":
    """The shared containment decision both resolvers are thin over.

    ``(ok, reason)``. ``ok`` iff ``change_id`` is a valid ULID, ``target``
    resolves, and the resolved target is strictly within at least one of
    ``permitted_roots`` (each re-canonicalised defensively). Fail-closed on
    every other path. This is the ONE copy of the #130 invariant.
    """
    if not is_valid_change_id(change_id):
        return False, (
            "no valid change scope — refusing. An operation must name the "
            "change it owns; never enumerate-and-match by name."
        )
    resolved = canonical(target)
    if resolved is None:
        return False, f"cannot resolve target path {target!r} — refusing fail-closed."
    for root in permitted_roots:
        canon_root = canonical(root)
        if canon_root is not None and _is_within(resolved, canon_root):
            return True, "within allowed scope"
    return False, (
        f"refusing: {resolved} is outside change {str(change_id).strip()}'s "
        f"allowed scope — out-of-scope / cross-change access blocked."
    )


# ─── the multi-root allowlist ───────────────────────────────────────────────


@dataclass(frozen=True)
class AllowedRoots:
    """Canonical (``.resolve()``-d) per-change allowlist roots + per-op policy.

    ``tools_cache_dir`` and ``creds_dir`` are optional: a deployment that has
    not configured them contributes no allowlist entry for them (a None root is
    never a match — fail-closed). ``creds_dir`` permits ``read`` only.
    """

    worktree: Path
    git_common_dir: Path
    change_state_dir: Path
    tools_cache_dir: Path | None
    creds_dir: Path | None

    def permitted_for(self, operation: str) -> "list[Path]":
        """The allowlist roots that permit ``operation`` (already-validated).

        Every populated root permits all operations EXCEPT ``creds_dir``, which
        permits ``read`` only. None roots contribute nothing.
        """
        roots: list[Path] = [self.worktree, self.git_common_dir, self.change_state_dir]
        if self.tools_cache_dir is not None:
            roots.append(self.tools_cache_dir)
        if self.creds_dir is not None and operation == "read":
            roots.append(self.creds_dir)
        return roots


def _git_common_dir(repo_root: Path) -> Path:
    """Canonical git-common-dir (the shared ``.git``) for ``repo_root``.

    Uses ``git rev-parse --git-common-dir`` (portable; resolves the shared
    object store even from inside a worktree). Falls back to ``repo_root/.git``
    if git is unavailable or the call fails — fail-closed-friendly: the fallback
    is still a real in-repo path, never a wider scope.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return (repo_root / ".git").resolve()
    if not out:
        return (repo_root / ".git").resolve()
    candidate = Path(out)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def resolve_allowed_roots(
    change_id: str,
    *,
    repo_root: Path,
    tools_cache_dir: "Path | None" = None,
    creds_dir: "Path | None" = None,
) -> AllowedRoots:
    """Build the canonical allowlist (ADR-004 table). Every root ``.resolve()``-d.

    ``worktree`` / ``change_state_dir`` come from ``_change_state`` (the single
    source of per-change paths); ``git_common_dir`` is resolved from
    ``repo_root`` via ``git rev-parse --git-common-dir``. ``tools_cache_dir`` and
    ``creds_dir`` are passed through when a deployment has configured them
    (WP-005 wires the config); ``None`` when unconfigured — they then contribute
    no allowlist entry.

    Fail-closed on an invalid change-id (the path's unique key — #130).
    """
    if not is_valid_change_id(change_id):
        raise ValueError(
            f"invalid change_id {change_id!r}: a scope must name the change it "
            f"owns (a valid ULID)."
        )
    return AllowedRoots(
        worktree=change_worktree_dir(change_id).resolve(),
        git_common_dir=_git_common_dir(Path(repo_root)),
        change_state_dir=change_dir(change_id).resolve(),
        tools_cache_dir=tools_cache_dir.resolve() if tools_cache_dir is not None else None,
        creds_dir=creds_dir.resolve() if creds_dir is not None else None,
    )


def within_allowed_scope(
    target,
    change_id,
    *,
    operation: str,
    roots: "AllowedRoots | None" = None,
    repo_root: "Path | None" = None,
) -> "tuple[bool, str]":
    """``(ok, reason)``. ``operation`` ∈ {"read","write","move","remove"}.

    ``True`` iff ``target.resolve()`` is within an allowed root permitted for
    that operation. ``creds_dir`` permits ``read`` only. Fail-closed on an
    invalid change_id, an unknown operation, an unresolvable path, or no
    matching root.

    Pass ``roots`` to reuse a pre-built allowlist; otherwise ``repo_root`` is
    required and the allowlist is built on the fly via ``resolve_allowed_roots``.
    """
    if operation not in _OPERATIONS:
        return False, (
            f"unknown operation {operation!r} — refusing fail-closed "
            f"(known: {sorted(_OPERATIONS)})."
        )
    if not is_valid_change_id(change_id):
        return False, (
            "no valid change scope — refusing. An operation must name the "
            "change it owns; never enumerate-and-match by name."
        )
    if roots is None:
        if repo_root is None:
            return False, "no allowlist and no repo_root to build one — refusing fail-closed."
        try:
            roots = resolve_allowed_roots(change_id, repo_root=Path(repo_root))
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            return False, f"cannot build allowlist for change {change_id}: {exc}"
    ok, reason = resolve_within_roots(target, change_id, roots.permitted_for(operation))
    if not ok and operation in _MUTATING and roots.creds_dir is not None:
        # Distinguish the read-only-creds refusal from a plain out-of-scope one:
        # if the ONLY reason this mutation was refused is that the target lives
        # under the credentials root (which permits read only), say so.
        resolved = canonical(target)
        if resolved is not None and _is_within(resolved, roots.creds_dir):
            return False, (
                f"refusing {operation}: {resolved} is under the credentials "
                f"root, which permits read only — credentials are never "
                f"written/moved/removed via a scoped file-tool."
            )
    return ok, reason
