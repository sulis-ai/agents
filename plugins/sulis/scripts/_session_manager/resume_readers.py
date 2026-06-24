"""``_session_manager.resume_readers`` — the REAL Working Set + brain readers
the live resume path injects into the assembler (CH-GJ9KQR WP-009, GAP-2).

The WP-003 :class:`~_session_manager.context_payload.ContextPayloadAssembler`
takes two injected, side-effect-free readers and defaults them to empty lambdas
(``lambda _tid: ""`` / ``lambda _tid: []``). Until they are wired to real
sources, even a live-assembled payload carries an empty Working Set + empty
brain — only the message summary is real. This module supplies the two real
readers the manager's composition root (WPB-07) injects, so the assembled
payload carries the change's live reasoning state + relevant brain entities.

**Dependency direction (MEA-01 / WPB-01).** These readers own the filesystem
IO the assembler must not — they are pure functions of the bound change /
thread id (constructed as closures over the change's worktree ``repo_root``).
The assembler still touches no filesystem; the readers + the store adapter are
the only IO on the assemble path.

**Reuse, don't rebuild (EP-03).** The Working Set reader resolves the
conventional path through :func:`_working_set.working_set_path` (the same
``.changes/{stem}.WORKING-SET.md`` convention the rest of the change uses); the
brain reader reads the change worktree's ``.brain/instances`` directly (the
same on-disk JSON-LD instance store the brain CLIs read), starting simple per
the spec: the bound change's relevant entities by type + a recency bound.

**Isolation.** A reader is called on the live spawn/resume seam. Either reader
returns an EMPTY result on ANY failure (missing file, malformed yaml/json,
unreadable dir) rather than raising — the manager's wiring degrades to the
default brief, and a reader fault never crashes the spawn (WP-004 ADV-1
isolation, applied at the reader boundary too).

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import _working_set

_log = logging.getLogger("sulis.session_manager.resume_readers")

# Brain entity types folded into the resume payload, in priority order (the
# spec's "start simple": the change's Opportunity / Requirements / Decisions /
# Design / Scenarios). Kept as a tuple so a future widening is a one-line edit.
_RELEVANT_BRAIN_TYPES: tuple[str, ...] = (
    "opportunity",
    "requirement",
    "decision",
    "design",
    "scenario",
)

# A recency bound on the brain entities folded in (the spec's "+ recency") — a
# small, fixed cap so a large brain never bloats the payload before the
# assembler's token budget even runs. The assembler still enforces the hard
# token cap on top; this is the cheap pre-trim.
_BRAIN_RECENCY_CAP = 12


def _change_stem_for(repo_root: Path, change_id: str) -> str | None:
    """Resolve the change's ``{primitive}-{slug}`` stem from its ``.changes``
    yaml whose ``change_id`` matches ``change_id`` — the same stem the
    ``.changes/{stem}.WORKING-SET.md`` / ``.SPEC.md`` siblings share.

    Scans ``repo_root/.changes/*.yaml`` for the one binding this change id and
    builds the stem from its ``primitive`` + ``slug`` fields. Returns ``None``
    if no binding matches (a worktree that is not this change's, or no yaml) so
    the caller degrades rather than guesses. A minimal line-scan parser (no yaml
    dependency) — the three fields are flat top-level scalars."""
    changes_dir = repo_root / ".changes"
    if not changes_dir.is_dir():
        return None
    for yaml_path in sorted(changes_dir.glob("*.yaml")):
        fields = _scan_flat_yaml(yaml_path)
        if fields.get("change_id") != change_id:
            continue
        primitive = fields.get("primitive")
        slug = fields.get("slug")
        if primitive and slug:
            return f"{primitive}-{slug}"
    return None


def _scan_flat_yaml(path: Path) -> dict[str, str]:
    """Read the flat top-level ``key: "value"`` scalars from a change yaml — a
    dependency-free line scan (the change yaml is flat scalars, not nested), so
    the readers carry no yaml-library dependency. Quotes are stripped; anything
    that fails to read returns ``{}`` (isolation)."""
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            out[key] = value
    return out


def make_working_set_reader(repo_root: Path | str, change_id: str):
    """Return a ``WorkingSetReader`` (``Callable[[str], str]``) that reads the
    bound change's ``.changes/{stem}.WORKING-SET.md`` crystallisation text.

    A closure over the change worktree ``repo_root`` + the bound ``change_id``
    (the stem is resolved from the change yaml, reusing the conventional path
    via :func:`_working_set.working_set_path`). The thread-id arg is accepted
    for the ``WorkingSetReader`` signature (one thread per change, ADR-004 — the
    thread id IS the change id) but the binding is fixed at construction.

    Returns ``""`` on ANY failure (no stem resolvable, missing file, unreadable)
    so a reader fault degrades the brief rather than crashing the spawn."""
    root = Path(repo_root)

    def _read(_thread_id: str) -> str:
        try:
            stem = _change_stem_for(root, change_id)
            if stem is None:
                return ""
            ws_path = _working_set.working_set_path(root, stem)
            if not ws_path.is_file():
                return ""
            return ws_path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 — reader isolation (see module docstring)
            _log.warning(
                "working-set reader failed for change %s (degrading to empty)",
                change_id,
                exc_info=True,
            )
            return ""

    return _read


def make_brain_reader(repo_root: Path | str):
    """Return a ``BrainReader`` (``Callable[[str], Sequence[Any]]``) that selects
    the change worktree's relevant brain entities (the spec's "start simple":
    Opportunity / Requirements / Decisions / Design / Scenarios + recency).

    A closure over the change worktree ``repo_root``. Reads the on-disk
    ``.brain/instances/**/<type>/*.jsonld`` instance store directly (the same
    JSON-LD instances the brain CLIs read), folds the relevant types, bounds the
    set by recency (newest-by-mtime first, capped), and returns them as plain
    dicts (vendor-neutral — no provider/Claude structure). The thread-id arg is
    accepted for the signature but the binding is the worktree.

    Returns ``[]`` on ANY failure so a reader fault degrades the brief rather
    than crashing the spawn."""
    root = Path(repo_root)

    def _read(_thread_id: str) -> Sequence[Any]:
        try:
            return _select_brain_entities(root)
        except Exception:  # noqa: BLE001 — reader isolation (see module docstring)
            _log.warning(
                "brain reader failed for %s (degrading to empty)",
                root,
                exc_info=True,
            )
            return []

    return _read


def _select_brain_entities(repo_root: Path) -> list[dict[str, Any]]:
    """Gather the relevant brain entities under ``repo_root/.brain/instances``,
    newest-first, capped at :data:`_BRAIN_RECENCY_CAP`.

    Matches by the entity-type directory name (``.../<type>/*.jsonld``) against
    :data:`_RELEVANT_BRAIN_TYPES`, so an Opportunity / Requirement / Decision /
    Design / Scenario is folded and lower-signal types (steps, testruns) are
    skipped. A single malformed instance is skipped (not fatal)."""
    instances_dir = repo_root / ".brain" / "instances"
    if not instances_dir.is_dir():
        return []
    candidates: list[tuple[float, dict[str, Any]]] = []
    for jsonld in instances_dir.rglob("*.jsonld"):
        type_dir = jsonld.parent.name
        if type_dir not in _RELEVANT_BRAIN_TYPES:
            continue
        try:
            data = json.loads(jsonld.read_text(encoding="utf-8"))
            mtime = jsonld.stat().st_mtime
        except (OSError, ValueError):
            continue  # malformed / unreadable instance — skip, not fatal
        if isinstance(data, dict):
            candidates.append((mtime, data))
    # Recency: newest first, then cap.
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return [data for _mtime, data in candidates[:_BRAIN_RECENCY_CAP]]
