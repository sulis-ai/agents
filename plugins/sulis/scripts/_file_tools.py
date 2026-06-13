"""L2 file-tools — the four scoped tools the agent calls (read/write/move/remove).

Each tool is THIN: it routes its path(s) through WP-004's
``within_allowed_scope`` (``_file_scope``) **before** touching the filesystem
and refuses any out-of-scope path **fail-closed**, returning the resolver's
reason verbatim. The scope decision lives in ONE place (``_file_scope``,
ADR-004); these tools own only the I/O. There is no per-tool bespoke path logic
— so the #130 cross-worktree-deletion invariant cannot drift across four copies.

  * ``read_file`` / ``write_file`` / ``remove_file`` check the single path for
    their operation.
  * ``move_file`` checks **both** endpoints — the source under ``move`` and the
    destination under ``write`` — and refuses if **either** is out of scope,
    leaving the filesystem **untouched** (no partial move).

Every tool returns a typed :class:`FileToolResult`: ``ok`` plus a human reason
on refusal, or the payload (read content) on a successful read.

Honest limit — L2 is a guardrail over the *tools*, not a wall over the *process*
====================================================================
L2 confines **honest mistakes**, not adversaries. A raw subprocess
(``bash -c 'cat <out-of-scope>'``) never calls ``within_allowed_scope`` and is
therefore NOT confined by these tools — by design (SC-L2.5). That bypass
SUCCEEDS, and that is the documented limit: there is no false sense of security
here. The wall that denies a raw subprocess reading outside scope is **L3 — the
OS sandbox (the deferred ``l3-os-egress-denial`` capability: Seatbelt on macOS,
seccomp / namespaces on Linux)**, not L2 (ADR-001 / ADR-005). Do not mistake
this decision layer for OS-level confinement.

Stdlib + ``_file_scope`` only; portable; Python 3.11-safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from _file_scope import within_allowed_scope


@dataclass(frozen=True)
class FileToolResult:
    """The typed outcome of a file-tool call.

    ``ok`` is True iff the scope check passed and the I/O succeeded. ``reason``
    carries the resolver's refusal reason (or an I/O-error message) when
    ``ok`` is False, and a short success note otherwise. ``payload`` carries
    the file content for a successful ``read_file`` and is ``None`` everywhere
    else (and on every refusal).
    """

    ok: bool
    reason: str
    payload: str | None = None


def _refuse(reason: str) -> FileToolResult:
    return FileToolResult(ok=False, reason=reason, payload=None)


def read_file(path, change_id, *, repo_root, roots=None) -> FileToolResult:
    """Read ``path`` iff it is within the change's read scope; else refuse.

    On success ``payload`` is the file's text content; on refusal or I/O error
    ``payload`` is ``None`` and ``reason`` explains why.
    """
    ok, reason = within_allowed_scope(
        path, change_id, operation="read", roots=roots, repo_root=repo_root
    )
    if not ok:
        return _refuse(reason)
    try:
        content = Path(path).read_text()
    except OSError as exc:
        return _refuse(f"read failed for in-scope path {path}: {exc}")
    return FileToolResult(ok=True, reason="read ok", payload=content)


def write_file(path, content, change_id, *, repo_root, roots=None) -> FileToolResult:
    """Write ``content`` to ``path`` iff it is within the change's write scope.

    Parent directories are created as needed. Refuses fail-closed (nothing is
    written) when the path is out of scope.
    """
    ok, reason = within_allowed_scope(
        path, change_id, operation="write", roots=roots, repo_root=repo_root
    )
    if not ok:
        return _refuse(reason)
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    except OSError as exc:
        return _refuse(f"write failed for in-scope path {path}: {exc}")
    return FileToolResult(ok=True, reason="write ok", payload=None)


def move_file(src, dst, change_id, *, repo_root, roots=None) -> FileToolResult:
    """Move ``src`` to ``dst`` iff BOTH endpoints are in scope.

    The source is checked under ``move`` and the destination under ``write``.
    If **either** check fails the filesystem is **never touched** — no partial
    move. The order is: check src, check dst, then (only then) perform the move.
    """
    ok_src, reason_src = within_allowed_scope(
        src, change_id, operation="move", roots=roots, repo_root=repo_root
    )
    if not ok_src:
        return _refuse(f"move source refused: {reason_src}")
    ok_dst, reason_dst = within_allowed_scope(
        dst, change_id, operation="write", roots=roots, repo_root=repo_root
    )
    if not ok_dst:
        return _refuse(f"move destination refused: {reason_dst}")
    try:
        dst_path = Path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        Path(src).replace(dst_path)
    except OSError as exc:
        return _refuse(f"move failed for in-scope endpoints {src} -> {dst}: {exc}")
    return FileToolResult(ok=True, reason="move ok", payload=None)


def remove_file(path, change_id, *, repo_root, roots=None) -> FileToolResult:
    """Remove ``path`` iff it is within the change's remove scope; else refuse.

    Refuses fail-closed (nothing is removed) when the path is out of scope —
    the #130 cross-worktree-deletion replay.
    """
    ok, reason = within_allowed_scope(
        path, change_id, operation="remove", roots=roots, repo_root=repo_root
    )
    if not ok:
        return _refuse(reason)
    try:
        Path(path).unlink()
    except OSError as exc:
        return _refuse(f"remove failed for in-scope path {path}: {exc}")
    return FileToolResult(ok=True, reason="remove ok", payload=None)
