"""Brownfield emission helper — call sites for substrate lifecycle events.

Substrate scripts (`sulis-change`, `wpx-pipeline`, `wpx-train`) reach a
moment in the lifecycle where an entity should appear in the brain (a
change starts, a change ships, a deploy succeeds). They call into here
rather than each importing the entity adapter + emitter directly. That
keeps the wiring discipline in one file: every brownfield emission point
shares the same defensive shape, the same error policy, the same logging.

Why a separate helper:

1. **Graceful degradation.** If `.brain/instances/` doesn't exist, the
   schemas aren't vendored, or `jsonschema` isn't installed (a fresh
   clone, a CI image without `uv sync`, the marketplace consumed by a
   downstream project that hasn't bootstrapped) — the substrate script
   MUST still work. Emission is a side-effect, never a precondition for
   the host operation.

2. **One discipline, many callers.** Every brownfield emission point is
   reached from inside a script that already has its own success path
   the founder cares about (`change start` succeeded, `deploy` succeeded).
   Wrapping each call site in defensive try/except duplicates intent.
   This module owns it once.

3. **Substrate-level naming.** Each function names the LIFECYCLE EVENT,
   not the entity type. `emit_change_started_event(...)` reads at the
   call site; `emit_lifecyclerun(step=<change-started Step ULID>, ...)`
   does not.

Every helper returns `dict | None`:
  - `dict` (entity payload) on successful emission
  - `None` on graceful degradation (anything went wrong: missing schemas,
    missing brain dir, validation failure, IO failure, missing
    dependencies)

The host script logs but does NOT fail when None comes back.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


# ─── Step resolution (name → canonical Step ULID) ───────────────────────
#
# A LifecycleRun's `step` ref points at a canonical Step (a prov:Plan). The
# three operational Steps are authored ONCE in
# `plugins/sulis/instances/lifecycle-steps/steps.jsonld` (WP-001) with
# deterministic ULIDs; these are the single source of truth, copied here —
# never re-minted (ADR-001/ADR-004). The per-run specificity that the old free
# `step_name` string carried is preserved in the run's `run_id`, NOT in a
# `step_label` (which does not exist in canonical v2).

_STEP_CHANGE_STARTED: Final[str] = "dna:step:01KT61X5ST01CHANGESTART00A"
_STEP_CHANGE_SHIPPED: Final[str] = "dna:step:01KT61X5ST02CHANGESH1PP00A"
_STEP_UNCLASSIFIED: Final[str] = "dna:step:01KT61X5ST03VNC1ASS1F1ED0A"

_NAME_TO_STEP_ULID: Final[dict[str, str]] = {
    "change-started": _STEP_CHANGE_STARTED,
    "change-shipped": _STEP_CHANGE_SHIPPED,
}


def _resolve_step(name: str) -> str:
    """Return the canonical Step ULID for a known lifecycle name.

    Unknown names resolve to the `unclassified-lifecycle-step` Step so every
    run points at a real Step ref rather than an inline-minted one. The
    original free `name`, where trace grouping is needed, is carried by the
    run's `run_id` field — not by a `step_label` (which does not exist).
    """
    return _NAME_TO_STEP_ULID.get(name, _STEP_UNCLASSIFIED)


def _brain_emit_enabled() -> bool:
    """Allow opting out via env var.

    Defaults to ON so the wiring fires by default for the marketplace's
    own use. Downstream consumers can set `SULIS_BRAIN_EMIT=0` to
    suppress — the host operation continues either way.
    """
    val = os.environ.get("SULIS_BRAIN_EMIT", "1").strip().lower()
    return val not in ("0", "false", "no", "off")


# ─── Project resolution (repo → for_project ref) ────────────────────────
#
# A change-start LifecycleRun records which Project (release-unit / repo) it ran
# in, via the optional `for_project` ref (ADR-007, v2.2.0+). The Project entity
# is minted to `<repo_root>/.sulis/projects/<slug>.jsonld` (the discover-project
# minter, WP-011/WP-014). We READ that bag here to resolve the ULID — there is
# no separate resolver helper to reuse (the minter only writes), so this is the
# minimal in-scope reader. `for_project` is OPTIONAL: a repo with no Project bag
# (a meta-run, a pre-discovery repo) resolves to None and the field is omitted —
# never an error (graceful degradation, ADR-007 §4).

_PROJECT_ID_RE: Final = re.compile(r"^dna:project:[0-9A-HJKMNP-TV-Z]{26}$")


def _resolve_project_ulid(repo_root: Path) -> str | None:
    """Resolve the active Project ULID for `repo_root`, or None.

    Reads `<repo_root>/.sulis/projects/*.jsonld` — the minter's output bags,
    each a `project-instances` doc carrying a `projects` array. Returns the
    `id` of the first `active` Project found (a single-Project repo is the
    common case). Any failure (no bag, malformed JSON, no valid ref) returns
    None so the emit degrades gracefully rather than failing.
    """
    projects_dir = Path(repo_root) / ".sulis" / "projects"
    if not projects_dir.is_dir():
        return None
    try:
        bags = sorted(projects_dir.glob("*.jsonld"))
    except OSError:
        return None
    for bag in bags:
        try:
            doc = json.loads(bag.read_text())
        except (OSError, ValueError):
            continue
        projects = doc.get("projects")
        if not isinstance(projects, list):
            continue
        for project in projects:
            if not isinstance(project, dict):
                continue
            if project.get("sys_status") not in (None, "active"):
                continue
            pid = project.get("id")
            if isinstance(pid, str) and _PROJECT_ID_RE.match(pid):
                return pid
    return None


def _brain_base_dir(repo_root: Path) -> Path:
    """Resolve the brain instances directory.

    `SULIS_BRAIN_BASE_DIR` overrides; otherwise `<repo_root>/.brain/instances`.
    """
    explicit = os.environ.get("SULIS_BRAIN_BASE_DIR", "").strip()
    if explicit:
        return Path(explicit).resolve()
    return Path(repo_root) / ".brain" / "instances"


def central_tenant_home(tenant_id: str) -> Path:
    """The central, cross-repo Platform home for one Tenant's living entities.

    Resolves the EXISTING convention ``~/.sulis/instances/{tenant_id}/`` —
    documented verbatim in ``_tenant_emission.py``'s module docstring and the
    "follow-up slice" it promised. This is the single cross-repo boundary: a
    Tenant whose Product/Opportunity history spans many repos has ONE home to
    read, keyed by the *deterministic* Tenant ULID (same Tenant name everywhere
    → same ``dna:tenant:<ulid>`` → same path on disk — that is what makes the
    namespace cross-repo).

    ADR-005 is a **reuse, not build** decision: pointing the living-entity emit
    ``base_dir`` here — ``LocalFileEntityAdapter(base_dir=central_tenant_home(...))``
    — IS the cross-repo Platform home. No new backend, no new adapter, no new
    query class; SQLite is deferred behind the same ``EntityRepository`` port.

    The ``~/.sulis`` root is resolved through ``_change_state.sulis_state_base()``
    — the ONE place that base is computed (honours ``SULIS_STATE_DIR`` for an
    isolated store, else ``~/.sulis``). Routing through it rather than
    hard-coding ``Path.home()`` keeps this home in lockstep with every other
    reader/writer of the local store and lets tests point at a tmp dir.

    Args:
        tenant_id: the EXISTING deterministic ``dna:tenant:<ulid>`` id (reused,
            not minted here — the recipe lives in ``_tenant_emission``). It is
            the home's namespace component, used verbatim.

    Returns:
        The ``{sulis_state_base()}/instances/{tenant_id}/`` path. Not created
        here — the file adapter creates the per-entity-type subtree on first
        write, exactly as it does for the repo-local tree.
    """
    from _change_state import sulis_state_base

    return sulis_state_base() / "instances" / tenant_id


def _try_adapter(repo_root: Path, domain: str) -> Any:
    """Return a `LocalFileEntityAdapter` or None if the brain isn't usable.

    Failure modes covered:
      - `jsonschema` not installed (downstream consumer hasn't run `uv sync`)
      - schemas not vendored at `plugins/sulis/brain/compiled/{domain}/`
      - `_entity_adapter_local` itself not importable for any reason

    Returning None signals "skip emission". The caller MUST NOT raise.
    """
    try:
        from _entity_adapter_local import LocalFileEntityAdapter
    except Exception:
        return None
    try:
        base_dir = _brain_base_dir(repo_root)
        return LocalFileEntityAdapter(base_dir=base_dir, domain=domain)
    except Exception:
        return None


def _safely(fn, *args, **kwargs) -> dict | None:
    """Call `fn(*args, **kwargs)`. Return its result, or None on ANY exception.

    Used to wrap the actual emit_* calls. If anything goes wrong inside —
    schema validation, IO, importing the emitter module — the host script
    sees a None and continues.
    """
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


# ─── Lifecycle event helpers ───────────────────────────────────────────


def emit_change_started_event(
    repo_root: Path,
    *,
    change_id: str,
    handle: str,
    slug: str,
    primitive: str,
) -> dict | None:
    """Emit a LifecycleRun marking `sulis-change start` completion.

    Call site: `sulis-change cmd_start`, after the branch + worktree +
    metadata are persisted. Best-effort.
    """
    if not _brain_emit_enabled():
        return None
    adapter = _try_adapter(repo_root, domain="product-development")
    if adapter is None:
        return None
    try:
        from _lifecyclerun_emission import emit_lifecyclerun
    except Exception:
        return None
    # Resolve the Project this run operated in (ADR-007). Optional — a repo with
    # no discovered Project omits the field; resolution never fails the emit.
    for_project = _resolve_project_ulid(repo_root)
    return _safely(
        emit_lifecyclerun,
        repo=adapter,
        step=_resolve_step("change-started"),
        run_id=f"change-started:{primitive}:{slug}",
        outcome="completed",
        at=datetime.now(timezone.utc).isoformat(),
        for_project=for_project,
    )


def emit_change_shipped_event(
    repo_root: Path,
    *,
    change_id: str,
    handle: str,
    slug: str,
    primitive: str,
    shipped_sha: str,
) -> dict | None:
    """Emit a LifecycleRun marking `sulis-change mark-shipped` completion.

    Call site: `sulis-change cmd_mark_shipped`, after the global record is
    flipped to stage='shipped'. Best-effort.
    """
    if not _brain_emit_enabled():
        return None
    adapter = _try_adapter(repo_root, domain="product-development")
    if adapter is None:
        return None
    try:
        from _lifecyclerun_emission import emit_lifecyclerun
    except Exception:
        return None
    return _safely(
        emit_lifecyclerun,
        repo=adapter,
        step=_resolve_step("change-shipped"),
        run_id=f"change-shipped:{primitive}:{slug}",
        outcome="completed",
        at=datetime.now(timezone.utc).isoformat(),
    )


def emit_lifecycle_step_event(
    repo_root: Path,
    *,
    step_name: str,
    outcome: str,
    at: str | None = None,
) -> dict | None:
    """Emit a LifecycleRun for any lifecycle step.

    The general-purpose helper. Use this for substrate seams that don't
    have a more specific helper (e.g. wpx-pipeline step completion,
    wpx-train per-WP shipped). The `step_name` should be a stable,
    human-readable string that uniquely names the event class
    (e.g. `"wpx-pipeline-success:WP-012"`).

    Under v2 the free `step_name` is resolved to a canonical Step ULID for
    the run's `step` ref (known names map to their Step; everything else
    falls back to the `unclassified-lifecycle-step` Step). The original
    `step_name` string is carried into `run_id` for trace grouping — it is
    not lost, and it does not go into a `step_label` (which does not exist).

    Outcome MUST be one of: completed / failed / in-progress / cancelled.
    """
    if not _brain_emit_enabled():
        return None
    adapter = _try_adapter(repo_root, domain="product-development")
    if adapter is None:
        return None
    try:
        from _lifecyclerun_emission import emit_lifecyclerun
    except Exception:
        return None
    return _safely(
        emit_lifecyclerun,
        repo=adapter,
        step=_resolve_step(step_name),
        run_id=step_name,
        outcome=outcome,
        at=at or datetime.now(timezone.utc).isoformat(),
    )


def emit_deployment_event(
    repo_root: Path,
    *,
    release_id: str,
    environment_id: str,
    outcome: str,
    at: str | None = None,
) -> dict | None:
    """Emit a Deployment for a successful (or failed) deploy step.

    Call site: `wpx-pipeline cmd_run` after the deploy poll resolves
    (success/failure/rolled-back/in-progress). Best-effort.

    Args:
        release_id: a valid `dna:release:<ulid>` ref. If the caller
            doesn't have a known Release entity, it should skip the call
            rather than synthesise a placeholder — Deployment without a
            valid Release ref is unhelpful noise.
        environment_id: a valid `dna:environment:<ulid>` ref.
    """
    if not _brain_emit_enabled():
        return None
    adapter = _try_adapter(repo_root, domain="product-development")
    if adapter is None:
        return None
    try:
        from _deployment_emission import emit_deployment
    except Exception:
        return None
    return _safely(
        emit_deployment,
        repo=adapter,
        of_release=release_id,
        to_environment=environment_id,
        outcome=outcome,
        at=at,
    )


def emit_release_event(
    repo_root: Path,
    *,
    version: str,
    component_ids: list[str],
    sbom_uri: str,
    changelog: str = "",
    shipped_at: str | None = None,
) -> dict | None:
    """Emit a Release entity at tag-cut time.

    Call site: a release-on-merge workflow step OR a manual release script,
    after `git tag` has been pushed. Best-effort.

    Args:
        version: SemVer string (e.g. `v0.34.0`).
        component_ids: at least one `dna:component:<ulid>` ref. If the
            caller doesn't yet know component IDs, skip rather than
            synthesise — Release without `comprises[]` is rejected.
        sbom_uri: URI to SPDX/CycloneDX (an SBOM file in the release
            artifacts, or a placeholder URI like `urn:sbom:none-yet`
            until the SBOM-build wiring lands).
    """
    if not _brain_emit_enabled():
        return None
    if not component_ids:
        # Schema requires minItems=1; skip cleanly rather than emit invalid.
        return None
    adapter = _try_adapter(repo_root, domain="product-development")
    if adapter is None:
        return None
    try:
        from _release_emission import emit_release
    except Exception:
        return None
    return _safely(
        emit_release,
        repo=adapter,
        version=version,
        comprises=component_ids,
        sbom=sbom_uri,
        changelog=changelog,
        shipped_at=shipped_at,
    )


# ─── Spec-ingestion helpers (for skills that produce SRD / TDD) ────────


def emit_requirements_from_srd(
    repo_root: Path,
    *,
    srd_path: Path,
) -> list[dict] | None:
    """Bulk-emit Requirement entities for every FR/NFR in an SRD.

    Call site: end of the SRD specify skill's flow, after `SRD.md` is
    written. Best-effort.

    Returns the list of emitted requirements (could be empty list if
    the SRD has no FR/NFR blocks), or None on graceful degradation.
    """
    if not _brain_emit_enabled():
        return None
    adapter = _try_adapter(repo_root, domain="product-development")
    if adapter is None:
        return None
    try:
        from _requirement_emission import emit_requirements_from_srd as _emit
    except Exception:
        return None
    return _safely(_emit, Path(srd_path), adapter)


def emit_design_from_tdd(
    repo_root: Path,
    *,
    tdd_path: Path,
) -> list[dict] | None:
    """Emit a Design entity for a TDD (with its requirement + decision refs).

    Call site: end of the SEA blueprint / design skill's flow, after
    `TDD.md` is written. Best-effort.
    """
    if not _brain_emit_enabled():
        return None
    adapter = _try_adapter(repo_root, domain="product-development")
    if adapter is None:
        return None
    try:
        from _design_emission import emit_design_from_tdd as _emit
    except Exception:
        return None
    return _safely(_emit, Path(tdd_path), adapter)


def emit_decisions_from_adrs(
    repo_root: Path,
    *,
    adr_dir: Path,
) -> list[dict] | None:
    """Bulk-emit Decision entities for every ADR file in `adr_dir`.

    Call site: end of the SEA blueprint skill, after ADR files are
    written. Best-effort. Returns the list of emitted decisions, or
    None on graceful degradation.
    """
    if not _brain_emit_enabled():
        return None
    adapter = _try_adapter(repo_root, domain="product-development")
    if adapter is None:
        return None
    try:
        from _decision_emission import emit_decision_from_adr
    except Exception:
        return None
    adr_path = Path(adr_dir)
    if not adr_path.exists():
        return None
    decisions: list[dict] = []
    for f in sorted(adr_path.glob("ADR-*.md")):
        d = _safely(emit_decision_from_adr, f, adapter)
        if d is not None:
            decisions.append(d)
    return decisions
