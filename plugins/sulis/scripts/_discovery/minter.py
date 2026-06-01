"""``_discovery.minter`` — Mint phase atomic-write + path-safety + cancellation.

Implements the ``write-project-entity`` Step
(``dna:step:01KT1WDSST08WR1TEPR0JEC000``) per TDD §Armor §Atomic write
semantics + §Path-safety check, and the Mint-phase contract for
MUC-002 (cancel mid-flow) / MUC-003 (entity already exists) /
NFR-003 (deterministic re-run) / NFR-004 (path safety).

Five concerns ride together because they are properties of the single
atomic-write contract:

1. **Atomic write** — write-to-tmp + fsync + ``os.replace`` (rename).
2. **Path safety** — resolve target; assert
   ``is_relative_to(<repo_root>/.sulis/projects)`` before any I/O.
3. **Pre-existence check** — refuse to overwrite unless
   ``allow_overwrite=True`` (MUC-003).
4. **Stale-tmp sweep** — remove ``*.tmp`` files left by a cancelled
   previous run (MUC-002).
5. **Signal handler** — SIGINT sweeps the projects dir then re-raises
   so the operator gets a clean ``KeyboardInterrupt``.

The implementation calls the existing ``entity-emitter`` Tool's
JSON-serialisation contract — entities are written as
``json.dumps(entity, indent=2)``. No wrapping involved.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Typed errors
# ---------------------------------------------------------------------------


class PathOutsideAllowedDirectoryError(Exception):
    """Raised when the resolved target path is outside
    ``<consuming_repo_root>/.sulis/projects/``. NFR-004 violation —
    the skill MUST never write outside that location.
    """


class EntityAlreadyExistsError(Exception):
    """Raised when ``target_path`` already exists and
    ``allow_overwrite=False``. MUC-003 (entity already exists);
    the founder reruns with ``--update`` to enter the per-field diff
    flow (ADR-005).
    """


class MonorepoSlugCollisionError(Exception):
    """Raised when a derived slug collides with an existing sibling
    project entity in a monorepo (MUC-007). Detection logic lives in
    the composition root (WP-008); this module exposes the type so
    the skill prose can ``except`` on it.
    """


# ---------------------------------------------------------------------------
# Repo-root resolution
# ---------------------------------------------------------------------------


# canonical:step:01KT1WDSST08WR1TEPR0JEC000
def consuming_repo_root() -> Path:
    """Return the consuming repo's top-level directory.

    Implementation: ``git rev-parse --show-toplevel``. Patched in unit
    tests via ``monkeypatch.setattr(minter, "consuming_repo_root", ...)``.
    """
    out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(out.strip()).resolve()


# ---------------------------------------------------------------------------
# Private helpers — read like a recipe when composed by ``write_project_entity``
# ---------------------------------------------------------------------------


def _assert_path_safety(target_path: Path) -> None:
    """First-thing-in check: refuse to write outside the allowed dir.

    Per TDD §Armor §Path-safety check, this runs BEFORE mkdir, BEFORE
    tmp creation, BEFORE any I/O that touches the target. ``.resolve()``
    follows symlinks; ``is_relative_to`` after resolve catches both
    symlink-traversal and ``..``-traversal.
    """
    resolved = target_path.resolve()
    allowed_dir = (consuming_repo_root() / ".sulis" / "projects").resolve()
    if not resolved.is_relative_to(allowed_dir):
        raise PathOutsideAllowedDirectoryError(
            f"Refusing to write outside {allowed_dir}: {resolved}"
        )


def _assert_not_exists(target_path: Path, *, allow_overwrite: bool) -> None:
    """Refuse to overwrite an existing entity unless explicitly permitted
    (MUC-003)."""
    if target_path.exists() and not allow_overwrite:
        raise EntityAlreadyExistsError(
            f"Project entity already exists at {target_path}. "
            "Re-run with --update to enter the per-field diff flow."
        )


def _atomic_write(target_path: Path, payload: str) -> None:
    """Write payload to ``target_path.with_suffix('.jsonld.tmp')``, fsync,
    then ``os.replace`` onto ``target_path``.

    POSIX guarantees ``os.replace`` is atomic when source + destination
    are on the same filesystem. Same-filesystem is guaranteed here:
    both paths sit inside the same ``.sulis/projects/`` dir.

    Cancellation (SIGINT) between ``write_text`` and ``os.replace``
    leaves a ``.tmp`` file (no target file). The startup sweep and
    SIGINT handler remove it.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = target_path.with_suffix(".jsonld.tmp")
    tmp.write_text(payload)
    # fsync the tmp file BEFORE the rename so the renamed file's
    # data is durable when it becomes visible at the target path.
    with tmp.open("rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, target_path)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


# canonical:step:01KT1WDSST08WR1TEPR0JEC000
def write_project_entity(
    target_path: Path,
    entity: dict,
    *,
    allow_overwrite: bool = False,
) -> None:
    """Atomically write ``entity`` to ``target_path``.

    Order (matters and is enforced by tests):

      1. Path-safety check — refuses if target is not under
         ``<repo_root>/.sulis/projects/`` (TDD §Armor §Path-safety check).
      2. Pre-existence check — refuses if target exists and
         ``allow_overwrite=False`` (MUC-003).
      3. Atomic write — mkdir -p, tmp + fsync + rename
         (TDD §Armor §Atomic write semantics).

    Postconditions:
      - either the full entity is at ``target_path``, or ``target_path``
        is absent (atomic guarantee);
      - on success, no ``.tmp`` file remains in the parent dir.
    """
    _assert_path_safety(target_path)
    _assert_not_exists(target_path, allow_overwrite=allow_overwrite)
    _atomic_write(target_path, json.dumps(entity, indent=2))


# canonical:step:01KT1WDSST08WR1TEPR0JEC000
def stale_tmp_sweep(projects_dir: Path) -> int:
    """Remove any ``*.tmp`` files in ``projects_dir``. Returns the count
    removed.

    Invoked on session startup AND on SIGINT (TDD §Armor §Atomic write
    semantics; MUC-002 idempotent cancellation).
    """
    if not projects_dir.exists():
        return 0
    removed = 0
    for tmp_file in projects_dir.glob("*.tmp"):
        tmp_file.unlink()
        removed += 1
    return removed


# Registry keyed by resolved projects_dir to keep installation
# idempotent without module-level mutable state about "have we installed
# the handler" — each unique projects_dir registers once.
_INSTALLED_HANDLERS: dict[str, object] = {}


# canonical:step:01KT1WDSST08WR1TEPR0JEC000
def install_sigint_handler(projects_dir: Path) -> None:
    """Install a SIGINT handler that sweeps ``.tmp`` files in
    ``projects_dir`` before re-raising the signal.

    Idempotent per ``projects_dir``: calling twice for the same dir
    is a no-op on the second call.

    The handler re-raises SIGINT (default behaviour) so the operator
    sees a clean ``KeyboardInterrupt`` at the top of the stack, not
    a silent absorption — TDD §Armor §Atomic write semantics names
    this behaviour explicitly.
    """
    key = str(projects_dir.resolve())
    if key in _INSTALLED_HANDLERS:
        return

    def _handler(signum: int, frame: object) -> None:  # noqa: ARG001
        stale_tmp_sweep(projects_dir)
        # Restore default and re-raise so the operator gets a clean
        # KeyboardInterrupt at the top of the stack.
        signal.signal(signal.SIGINT, signal.default_int_handler)
        raise KeyboardInterrupt()

    handler = signal.signal(signal.SIGINT, _handler)
    _INSTALLED_HANDLERS[key] = handler
