"""``_discovery.minter`` — Mint phase: canonical brain-store save + human mirror.

Implements the ``write-project-entity`` Step
(``dna:step:01KT1WDSST08WR1TEPR0JEC000``) per TDD §Form #9, #10 + §Armor
§Atomic write semantics + §Path-safety check, and the Mint-phase contract for
MUC-002 (cancel mid-flow) / MUC-003 (entity already exists) /
NFR-003 (deterministic re-run) / NFR-004 (path safety).

**Project home reconciliation (ADR-006).** The brain store (behind the
``EntityRepository`` port) is the **canonical** home for the Project entity;
``.sulis/projects/<slug>.jsonld`` is retained as a **human-readable mirror**.
``write_project_entity`` writes **canonical-first, mirror-second**:

1. **Canonical** — the inner Project is saved through the shared bitemporal
   helper ``evolve_entity`` (WP-009), pointed at the central Tenant home
   (WP-013, ``central_tenant_home``), with ``generated_by=None``. Project is
   ``prov:Plan`` (ADR-002/ADR-006): it becomes a *living* entity (bitemporal
   windows + the supersedes chain), but carries **no** ``wasGeneratedBy`` edge —
   an Entity→Activity edge on a recipe is a PROV-O type violation. Window logic
   is NOT re-implemented here; the helper owns it (EP-03). A re-discovery
   (``--update``) is therefore an *evolve* (close the prior window, open a new
   one), not a second fresh save.
2. **Mirror** — the existing atomic-write + path-safety machinery is kept,
   repurposed as ``write_project_mirror``. It still does ``_assert_path_safety``
   (the ``.sulis/projects/`` boundary), ``_atomic_write`` (tmp + fsync +
   ``os.replace``), ``_assert_not_exists`` (MUC-003), the stale-tmp sweep and the
   SIGINT handler — verbatim discipline, now guarding the *mirror*.

The ordering is load-bearing: a failed canonical write writes **no** mirror (the
founder never sees a Project the store rejected); a failed mirror after a good
canonical save is a **logged best-effort degradation** (the canonical truth is
already safe), consistent with the brain's graceful-degradation discipline. One
canonical writer, one derived mirror — no sync job, no dual source of truth.

The four mirror-side safety properties (atomic write, path safety, MUC-003
refuse-on-exists, partial-write cleanup) are pinned by the WP-014
characterisation baseline; this module is the REORGANISE-Refactor that ADDS the
canonical save while preserving every one of them verbatim (EP-07).
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
from pathlib import Path

from _entity_evolve import evolve_entity

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# Canonical brain-store save (ADR-006) — the inner Project as a living entity
# ---------------------------------------------------------------------------


_PROJECT_ID_PREFIX = "dna:project:"
# Project's compiled schema lives in the foundation domain (Project is a
# foundation entity — `prov:Plan`), not product-development.
_PROJECT_DOMAIN = "foundation"

# The field set the compiled foundation Project schema admits
# (`unevaluatedProperties: false`). The human mirror carries a RICHER bag — the
# discover-project Configuration-Vocabulary extras (`deploy_target`,
# `package_manager`, `language_primary`, …) and the `@context`/`projects`
# wrapper. The canonical save is the schema-conformant PROJECTION of the same
# entity (ADR-006 "derived from the same entity dict"): the mirror keeps the
# extras for the human; the canonical store holds the validated Project body.
_CANONICAL_PROJECT_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "name",
        "belongs_to_tenant",
        "type",
        "source",
        "version_files",
        "branch_policy",
        "belongs_to_product_ref",
        "depends_on",
        "consumed_by",
        "release_workflow_ref",
        "description",
        "state",
        "sys_status",
        "valid_from",
        "valid_to",
        "confidence",
        "deprecated_for",
        "archived_at",
    }
)

# Legacy → canonical value normalisation for `branch_policy`. The discover-project
# flow historically emitted the loose `"trunk-based"` label (never schema-
# validated while Project lived only in `.sulis/projects/`); the compiled schema's
# enum is `trunk`. Mapping it here lets a pre-reconcile or loosely-composed body
# canonicalise cleanly rather than the founder hitting a confusing enum error on
# a value that means exactly `trunk`.
_BRANCH_POLICY_ALIASES: dict[str, str] = {"trunk-based": "trunk"}


def _canonical_body(project: dict) -> dict:
    """Project the inner Project bag down to the schema-conformant canonical body.

    Keeps only the fields the compiled foundation Project schema admits (the
    mirror keeps the richer Configuration-Vocabulary extras), and normalises the
    legacy ``branch_policy`` label. Reject-on-invalid still applies at the port —
    this projection removes mirror-only *extras*, it does not paper over a
    genuinely missing required field.
    """
    body = {k: v for k, v in project.items() if k in _CANONICAL_PROJECT_FIELDS}
    bp = body.get("branch_policy")
    if isinstance(bp, str) and bp in _BRANCH_POLICY_ALIASES:
        body["branch_policy"] = _BRANCH_POLICY_ALIASES[bp]
    return body


def _canonical_projects(entity: dict) -> list[dict]:
    """The inner Project body/bodies to save canonically, extracted from
    ``entity``.

    ``entity`` may be the composed project-instances *bag*
    (``{"projects": [proj, ...]}`` — the production discover-project shape) or a
    bare inner Project body (``{"id": "dna:project:…", …}`` — the unit/emitter
    shape). Anything else (e.g. a non-Project dict) yields ``[]`` — there is no
    Project to canonicalise, so only the mirror is written.
    """
    projects = entity.get("projects")
    if isinstance(projects, list):
        return [p for p in projects if isinstance(p, dict)]
    pid = entity.get("id")
    if isinstance(pid, str) and pid.startswith(_PROJECT_ID_PREFIX):
        return [entity]
    return []


def _canonical_repo_for(project: dict):  # -> EntityRepository
    """Build the ``EntityRepository`` pointed at the Project's canonical home.

    The home is the central, cross-repo Tenant store (ADR-005,
    ``central_tenant_home(belongs_to_tenant)``) — the same home Product /
    Opportunity living entities evolve into. Reuses the existing
    ``LocalFileEntityAdapter`` over the foundation domain; no new persistence
    code (the ADR-005 reuse posture).
    """
    from _brain_emit_helper import central_tenant_home
    from _entity_adapter_local import LocalFileEntityAdapter

    tenant_id = project["belongs_to_tenant"]
    return LocalFileEntityAdapter(
        base_dir=central_tenant_home(tenant_id), domain=_PROJECT_DOMAIN
    )


def _save_canonical(entity: dict) -> None:
    """Save the inner Project(s) through the canonical ``EntityRepository`` port
    as a *living* entity (ADR-006).

    Each Project is evolved via the shared ``evolve_entity`` helper (WP-009) with
    ``generated_by=None`` — Project is ``prov:Plan``, so it gets bitemporal
    windows + the supersedes chain but NO ``wasGeneratedBy`` edge (ADR-002). A
    re-discovery of an existing Project closes the prior window and opens a new
    one (the living-entity contract); a byte-identical re-emit is a no-op.

    Raises on a canonical-write failure — by ADR-006 ordering the caller writes
    no mirror when this raises (the mirror can never show a Project the store
    rejected).
    """
    for project in _canonical_projects(entity):
        body = _canonical_body(project)
        evolve_entity(
            repo=_canonical_repo_for(body),
            entity_type="project",
            entity_id=body["id"],
            new_fields=body,
            generated_by=None,  # Project is prov:Plan — no wasGeneratedBy edge.
        )


# ---------------------------------------------------------------------------
# Public surface — canonical-first, mirror-second (ADR-006)
# ---------------------------------------------------------------------------


# canonical:step:01KT1WDSST08WR1TEPR0JEC000
def write_project_entity(
    target_path: Path,
    entity: dict,
    *,
    allow_overwrite: bool = False,
) -> None:
    """Reconcile the Project home: canonical brain-store save, then human mirror.

    Per ADR-006, ``canonical-first / mirror-second``:

      1. **Canonical** — save the inner Project(s) through the
         ``EntityRepository`` port at the central Tenant home, as a living entity
         (``evolve_entity``, ``generated_by=None``). A failure here raises and
         **no mirror is written** — the mirror can never show a Project the store
         rejected.
      2. **Mirror** — write ``.sulis/projects/<slug>.jsonld`` via
         ``write_project_mirror`` (atomic + path-safe). A mirror failure *after*
         a good canonical save is a **logged best-effort degradation** — it does
         not raise; the canonical truth is already safe.

    The path-safety, pre-existence (MUC-003) and atomic-write guarantees on the
    mirror are unchanged from the pre-reconcile behaviour — they live in
    ``write_project_mirror`` verbatim.

    Ordering of the three concerns:

      0. **Refusal gates first** (NFR-004 path-safety + MUC-003 refuse-on-exists,
         evaluated against the mirror target). A fresh re-mint over an existing
         human mirror — or a hostile path — refuses the WHOLE operation, writing
         neither the canonical save nor the mirror. These gates are outermost
         because a refused mint must not silently mutate the canonical store.
      1. **Canonical save** (``evolve_entity``). A failure here raises and writes
         no mirror.
      2. **Mirror write**. A failure here *after* the good canonical save is a
         logged best-effort degradation — it does not raise.
    """
    # 0 · Refusal gates (NFR-004 + MUC-003) — outermost; a refused mint touches
    # neither the canonical store nor the mirror.
    _assert_path_safety(target_path)
    _assert_not_exists(target_path, allow_overwrite=allow_overwrite)

    # 1 · Canonical first. Propagate failure — no mirror on a rejected save.
    _save_canonical(entity)

    # 2 · Human mirror. Best-effort: a failure after the good canonical save is
    # logged and swallowed (graceful degradation, ADR-006). The refusal gates
    # above already cleared path-safety + pre-existence; the mirror re-asserts
    # them verbatim (cheap, and keeps `write_project_mirror` correct standalone).
    try:
        write_project_mirror(target_path, entity, allow_overwrite=allow_overwrite)
    except Exception:  # noqa: BLE001 — graceful-degradation boundary
        logger.warning(
            "Project mirror write to %s failed after a successful canonical "
            "save; the canonical Project is safe in the brain store. "
            "(best-effort degradation, ADR-006)",
            target_path,
            exc_info=True,
        )


# canonical:step:01KT1WDSST08WR1TEPR0JEC000
def write_project_mirror(
    target_path: Path,
    entity: dict,
    *,
    allow_overwrite: bool = False,
) -> None:
    """Atomically write the human-readable Project mirror to ``target_path``.

    The mirror (``.sulis/projects/<slug>.jsonld``) is the git-tracked, human-
    facing artifact derived from the same validated entity dict the canonical
    save used (ADR-006). This is the minter's hard-won safety discipline,
    preserved verbatim from the pre-reconcile ``write_project_entity`` — only the
    name changed (it now guards the mirror, not the canonical home).

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
