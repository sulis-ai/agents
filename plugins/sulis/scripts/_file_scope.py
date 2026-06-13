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

**One source, two consumers (ADR-004 / SC-E5).** The same canonical
``AllowedRoots`` value feeds BOTH the L2 file-tools scope check (this module's
``within_allowed_scope``) AND the L3 OS-sandbox config: ``sandbox_write_roots``
emits the rw roots as sandbox ``allowWrite`` path strings, reading the one
``AllowedRoots.writable_roots`` accessor the scope check also uses — so the two
layers cannot drift. The *resolved* brain dir (via ``brain_base_dir`` — #127,
never a hardcoded ``~/.sulis``) joins the rw roots **only when it is outside the
worktree** (a relocated brain); narrowest-root throughout (the specific resolved
subtree, never all of ``~/.sulis/``, which holds other changes' state).

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

from _brain_location import brain_base_dir
from _change_state import change_dir, change_worktree_dir, changes_base

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

    ``tools_cache_dir``, ``creds_dir`` and ``brain_dir`` are optional: a
    deployment (or a default-brain layout) that has not populated one
    contributes no allowlist entry for it (a None root is never a match —
    fail-closed). ``creds_dir`` permits ``read`` only; ``brain_dir`` — the
    *resolved* brain dir, set ONLY when the brain lives outside the worktree
    (a relocated brain; the default in-worktree brain is already covered by
    ``worktree``) — is shared rw and permits all four operations.

    The rw roots (``write``/``move``/``remove``) are the SINGLE SOURCE the
    sandbox config consumes via :func:`sandbox_write_roots`; both that emit and
    this scope check derive from :meth:`writable_roots`, so they cannot drift
    (ADR-004 single-source-of-truth, SC-E5).
    """

    worktree: Path
    git_common_dir: Path
    change_state_dir: Path
    tools_cache_dir: Path | None
    creds_dir: Path | None
    brain_dir: Path | None = None

    def writable_roots(self) -> "list[Path]":
        """The roots that permit mutation (``write``/``move``/``remove``).

        This is the ONE rw root-set. ``permitted_for`` for a mutating op and
        :func:`sandbox_write_roots` both read it — the file-tools scope check
        and the sandbox ``allowWrite`` emit can therefore never drift.
        ``creds_dir`` is excluded (read-only — never mutated via a scoped
        file-tool). ``None`` roots contribute nothing (fail-closed).
        """
        roots: list[Path] = [self.worktree, self.git_common_dir, self.change_state_dir]
        if self.tools_cache_dir is not None:
            roots.append(self.tools_cache_dir)
        if self.brain_dir is not None:
            roots.append(self.brain_dir)
        return roots

    def permitted_for(self, operation: str) -> "list[Path]":
        """The allowlist roots that permit ``operation`` (already-validated).

        Mutating ops (``write``/``move``/``remove``) get :meth:`writable_roots`.
        ``read`` gets the same set plus ``creds_dir`` (read-only secret). None
        roots contribute nothing.
        """
        roots = self.writable_roots()
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
    worktree = change_worktree_dir(change_id).resolve()
    return AllowedRoots(
        worktree=worktree,
        git_common_dir=_git_common_dir(Path(repo_root)),
        change_state_dir=change_dir(change_id).resolve(),
        tools_cache_dir=tools_cache_dir.resolve() if tools_cache_dir is not None else None,
        creds_dir=creds_dir.resolve() if creds_dir is not None else None,
        brain_dir=_resolve_brain_root(Path(repo_root), worktree),
    )


def _resolve_brain_root(repo_root: Path, worktree: Path) -> "Path | None":
    """The canonical brain dir as a shared-rw root, or ``None``.

    Resolves via ``brain_base_dir`` (the single #127 resolver — NEVER hardcode
    ``~/.sulis``). Returns the resolved brain subtree ONLY when it is *outside*
    the worktree (a relocated brain — e.g. ``~/.sulis/brain``); the default
    in-worktree brain (``<repo>/.brain/instances``) is already covered by the
    worktree root, so it adds no extra entry. Narrowest-root: the specific
    resolved subtree, never all of ``~/.sulis/`` (which holds OTHER changes'
    state — that would reopen the #130 cross-change risk). Fail-closed: an
    unresolvable brain path contributes no root.
    """
    brain = canonical(brain_base_dir(repo_root))
    if brain is None:
        return None
    if _is_within(brain, worktree):
        return None
    # Reject a too-broad brain: one that IS or CONTAINS the per-change state
    # tree would let a write reach sibling changes (the #130 cross-change risk
    # the narrowest-root rule exists to prevent). brain_base_dir faithfully
    # returns whatever is configured, so this guard ENFORCES narrowest-root
    # rather than merely documenting it. Fail-closed.
    changes_root = canonical(changes_base())
    if changes_root is not None and _is_within(changes_root, brain):
        return None
    return brain


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


# ─── the sandbox-config emit (the SECOND consumer of the SAME rw root-set) ───


def _sandbox_path_string(root: Path) -> str:
    """One canonical rw root → a sandbox ``allowWrite`` path string.

    The sandbox ``allowWrite`` grammar (per the Claude Code sandboxing docs)
    accepts ``/abs``, ``~/`` and ``./`` prefixes — NOT the ``//abs`` *permission*
    syntax. We emit an absolute path, collapsed to ``~/…`` when it lives under
    the user's home (the docs' tilde form), else the plain ``/abs`` form. The
    root is already ``.resolve()``-d (canonical) by ``resolve_allowed_roots``.
    """
    root = root.resolve()
    home = Path.home().resolve()
    if root == home or _is_within(root, home):
        rel = root.relative_to(home)
        # "~" for home itself; "~/<rel>" otherwise.
        return "~" if str(rel) == "." else f"~/{rel.as_posix()}"
    return root.as_posix()


def sandbox_write_roots(roots: AllowedRoots) -> "list[str]":
    """Emit the rw roots as sandbox ``allowWrite`` path strings (ADR-004).

    The ONE adapter from the canonical :class:`AllowedRoots` to the sandbox
    config shape (WP-004's recipe pastes this into
    ``sandbox.filesystem.allowWrite``). It reads :meth:`AllowedRoots.writable_roots`
    — the SAME set the file-tools scope check uses for a mutating op — so the L2
    decision layer and the L3 sandbox config are structurally one source of
    truth and cannot drift (SC-E5). Order is deterministic and dedup-stable.

    Redundancy note (ADR-004): the sandbox auto-allows a linked worktree's
    shared ``.git``, so emitting ``git_common_dir`` here is partly redundant
    *under the sandbox* — but the L2 file-tools check still needs that root, and
    emitting it keeps both consumers reading one set. We keep it (and document
    the redundancy) rather than special-casing it out, which would reintroduce a
    second, divergent list.
    """
    seen: dict[str, None] = {}
    for root in roots.writable_roots():
        seen.setdefault(_sandbox_path_string(root), None)
    return list(seen)
