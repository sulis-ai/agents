"""``_change_session`` — deterministic per-change Claude session identity and
transcript-resumability helpers (focus-resumes-prior-session).

**The design wrinkle and the decision.** ``/sulis:change focus`` should RESUME
the prior ``claude`` conversation for a change instead of always spawning a
fresh self-orienting session. To resume we must know WHICH conversation. Claude
offers two handles: ``--resume <id>`` against an id Claude *assigned*, and
``--session-id <uuid>`` to *pin* a known id at the first spawn. We take the
**pinned-id** route: derive a deterministic UUID from the change ULID, pin it at
first spawn (``claude --session-id <uuid>``), and on focus pass the SAME derived
id as ``--resume <uuid>``. This beats transcript-discovery (scrape
``~/.claude/projects`` for the most-recent ``*.jsonl``) on every axis:

- The id is a pure function of the change — no need to capture the id Claude
  assigned, no race recording it, no "most-recent transcript wins" heuristic.
- Resumability is a single deterministic file check: does
  ``~/.claude/projects/<mangled-worktree>/<derived-uuid>.jsonl`` exist and carry
  any content. That check reads only the **persisted transcript**, so it does
  NOT depend on the daemon still holding the session — a janitor-reaped
  (intentionally shut-down) session is still resumable via focus, which is the
  whole point.
- When no transcript exists yet (a change never opened, or a clean first run),
  resumability is False and the caller takes the unchanged fresh-spawn
  self-orient path (#93 default-pre-prompt behaviour preserved).

**Why the transcript path is what it is.** Claude persists each conversation as
``~/.claude/projects/<dir>/<session-id>.jsonl`` where ``<dir>`` is the absolute
cwd with every ``/`` and ``.`` replaced by ``-`` (verified against a real
``~/.claude/projects`` dir for a sulis change worktree). Because we pin the
session id, the transcript filename is exactly ``<derived-uuid>.jsonl`` — so the
resumability check is a direct stat, not a directory scan.

Stdlib only (NFR-5): ``re``, ``uuid``, ``pathlib``. No ``_session_manager`` /
daemon import — ADR-003 keeps the daemon-presence binding stdlib-self-contained;
this module is a sibling pure-helper, not part of that binding.
"""

from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _wpxlib import validate_change_ulid  # noqa: E402

# A fixed namespace UUID so ``change_session_id`` is a stable, deterministic
# function of the change ULID across processes and machines. Generated once
# (uuid4) and frozen here — NOT a well-known namespace, so the derived ids do
# not collide with any other uuid5 scheme that might reuse the same names.
_CHANGE_SESSION_NAMESPACE = uuid.UUID("6f3a1d2c-9b47-4e8a-b1c0-7d2e5f8a9c10")

# Claude's project-dir mangling: every "/" and "." in the absolute path becomes
# "-" (e.g. /Users/iain/.sulis/changes/<id>/worktree ->
# -Users-iain--sulis-changes-<id>-worktree). Verified against the real
# ~/.claude/projects layout.
_PROJECT_DIR_MANGLE_RE = re.compile(r"[/.]")


def change_session_id(change_id: str) -> str:
    """Return the deterministic Claude ``--session-id`` UUID for ``change_id``.

    A UUIDv5 over a frozen namespace and the change ULID, so it is:
      - a valid UUID (``claude --session-id`` requires one), and
      - a pure function of the change — the spawn-time pin and the focus-time
        ``--resume`` ref always agree without recording the raw uuid anywhere.

    Raises ``ValueError`` if ``change_id`` is not a valid change ULID (we refuse
    to mint a session id for a malformed change rather than silently mangle it).
    """
    ok, reason = validate_change_ulid(change_id)
    if not ok:
        raise ValueError(reason)
    return str(uuid.uuid5(_CHANGE_SESSION_NAMESPACE, change_id))


def claude_project_dir(worktree_path: str | Path) -> Path:
    """Return ``~/.claude/projects/<mangled-worktree>`` for ``worktree_path``.

    ``<mangled-worktree>`` is the resolved absolute path with every ``/`` and
    ``.`` replaced by ``-`` (Claude's own transcript-dir naming).
    """
    resolved = str(Path(worktree_path).resolve())
    mangled = _PROJECT_DIR_MANGLE_RE.sub("-", resolved)
    return Path.home() / ".claude" / "projects" / mangled


def transcript_path(change_id: str, worktree_path: str | Path) -> Path:
    """Return the path Claude persists this change's pinned conversation to:
    ``<claude_project_dir>/<change_session_id>.jsonl``.

    Because the session id is pinned (``change_session_id``), the transcript
    filename is deterministic — so resumability is a direct stat, not a scan.
    """
    sid = change_session_id(change_id)
    return claude_project_dir(worktree_path) / f"{sid}.jsonl"


def has_resumable_transcript(change_id: str, worktree_path: str | Path) -> bool:
    """True iff a non-empty prior transcript exists for this change's pinned
    conversation under ``~/.claude/projects``.

    Pure filesystem check on the **persisted transcript** only — it never
    consults the daemon or ``session.json``, so a session the janitor reaped
    (intentional shutdown) is still reported resumable as long as its transcript
    persists (Step 3). A missing or empty file → False, so the caller falls back
    to the fresh self-orienting spawn (the #93 default), never a broken resume.

    A malformed ``change_id`` (no valid pinned id) is treated as not-resumable
    rather than raising — focus should degrade to a fresh spawn, not crash.
    """
    try:
        tp = transcript_path(change_id, worktree_path)
    except ValueError:
        return False
    try:
        return tp.is_file() and tp.stat().st_size > 0
    except OSError:
        return False
