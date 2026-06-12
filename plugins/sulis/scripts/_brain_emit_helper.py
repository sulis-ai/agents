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
   call site; `emit_lifecyclerun(step_name=f"change-started:{slug}", ...)`
   does not.

Every helper returns `dict | None`:
  - `dict` (entity payload) on successful emission
  - `None` on graceful degradation (anything went wrong: missing schemas,
    missing brain dir, validation failure, IO failure, missing
    dependencies)

The host script logs but does NOT fail when None comes back.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _brain_emit_enabled() -> bool:
    """Allow opting out via env var.

    Defaults to ON so the wiring fires by default for the marketplace's
    own use. Downstream consumers can set `SULIS_BRAIN_EMIT=0` to
    suppress — the host operation continues either way.
    """
    val = os.environ.get("SULIS_BRAIN_EMIT", "1").strip().lower()
    return val not in ("0", "false", "no", "off")


def _brain_base_dir(repo_root: Path) -> Path:
    """Resolve the brain instances directory.

    `SULIS_BRAIN_BASE_DIR` overrides; otherwise `<repo_root>/.brain/instances`.
    """
    explicit = os.environ.get("SULIS_BRAIN_BASE_DIR", "").strip()
    if explicit:
        return Path(explicit).resolve()
    return Path(repo_root) / ".brain" / "instances"


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
        adapter = LocalFileEntityAdapter(base_dir=base_dir, domain=domain)
    except Exception:
        return None
    # #67 slice 3b — when a change is active (SULIS_CHANGE_ID), wrap the adapter
    # so every entity this emits is stamped with the change that produced/revised
    # it. No active change → the plain adapter, unchanged. Best-effort: a
    # stamping-import failure degrades to the unwrapped adapter (emission works).
    try:
        from _provenance_stamp import stamping_repo
        return stamping_repo(adapter)
    except Exception:
        return adapter


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
    return _safely(
        emit_lifecyclerun,
        repo=adapter,
        step_name=f"change-started:{primitive}:{slug}",
        outcome="completed",
        at=datetime.now(timezone.utc).isoformat(),
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
        step_name=f"change-shipped:{primitive}:{slug}",
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
        step_name=step_name,
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
