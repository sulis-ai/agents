"""Brain-capture orchestration helpers.

This module owns the capture-side composition that turns a founder's idea into
a rooted entry in the Brain graph. It has three public responsibilities:

* ``bootstrap_backing_chain`` (WP-003 / FR-04 / ADR-002) — laying down the
  mandatory **Tenant → Product** prefix the schema chain requires, reuse-first
  and write-once (described in detail below).
* ``roadmap_add`` (WP-005 / ADR-001 / FR-05) — the Roadmap-label sidecar
  writer (a sidecar file, not an entity field, because the schemas are
  ``unevaluatedProperties: false``).
* ``capture_idea`` (WP-004 / ADR-003 / ADR-004 / ADR-005 / FR-01-03) — the
  **orchestrator**, and the gate that makes "no orphan requirements" real in
  code. It is **one function, two depths** (``why_intensity`` =
  ``quick`` | ``full``) so the why-first invariant lives in exactly one place:

    * **quick** — the orchestrator roots the idea itself: bootstrap the chain,
      emit a thin ``hypothesis`` Opportunity from the founder's one-line why,
      then (when a ``what`` is given) a draft Requirement sourced from that
      real Opportunity id.
    * **full** — the opportunity-analyst has already emitted/matured an
      Opportunity (ADR-004 — the two compose *through the store*, by id, not
      via a function call); capture reads it back by id, confirms it resolves
      and its ``for_product`` chain is whole, then emits the Requirement
      sourced from it.

  The load-bearing invariant across both depths: the Requirement is the
  **last** write and only fires after its ``source`` resolves to a real
  Opportunity. ``quick`` with a blank ``why`` raises ``CaptureError`` and emits
  **nothing** (FR-02). A ``full`` id that doesn't resolve (or whose chain is
  broken) raises ``CaptureError`` and emits **no orphan Requirement** (NFR-01).
  A brain-unavailable / mis-validating store degrades to ``CaptureError`` too,
  never an uncaught crash — mirroring ``_brain_emit_helper``'s defensive
  discipline.

``bootstrap_backing_chain`` (WP-003 / FR-04 / ADR-002) lays down the mandatory
**Tenant → Product** prefix the schema chain requires, reuse-first and
write-once.

Why the prefix is load-bearing (ADR-002): a captured idea's chain is
``Requirement.source → Opportunity.for_product → Product.belongs_to_tenant``,
and each ref is *required*. A captured idea is invalid until its whole chain
exists on disk. So the chain is emitted **bottom-up** (Tenant first) — each ref
resolves to an already-persisted parent, and a crash mid-bootstrap leaves a
valid prefix rather than an orphan.

The tenant-identity trap (ADR-002): there are two divergent tenant-ULID
derivations in the tree. ``_tenant_emission`` seeds on the display name with a
reversed-chunk encoder; ``_discovery.tenant.Sha256CrockfordTenantDeriver`` (the
canonical consumer-tenant recipe, external ``discover-project`` ADR-002) seeds
on the repo shorthand with an MSB-first encoder + first-char clamp. They
produce *different* ids for the same conceptual tenant. This module reuses the
**canonical** deriver UNCHANGED, so capture's chain joins the graph that
``/sulis:discover-project`` and every other entity-emitting path can see —
rather than silently forking a third identity.

Reuse map:
  - Tenant id        → ``Sha256CrockfordTenantDeriver.derive_consumer_tenant``
                        (canonical recipe, reused unchanged).
  - Product compose  → ``_product_emission.compose_product_from_yaml`` (the
                        orphaned ``sulis-emit-product`` emitter now has a live
                        caller; its deterministic id recipe is reused).
  - Persistence      → the ``EntityRepository`` port. Tenant persists via the
                        ``foundation``-domain adapter; Product via
                        ``product-development`` — two-domain construction
                        mirroring the per-emitter ``--domain`` defaults.

This helper is PURE of git / file discovery: ``repo_org_slash_name`` is passed
in (the orchestrator, WP-004, reads it from ``.sulis/repo-contract.yml``), so
the bootstrap stays unit-testable against a temp ``.brain/instances``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import yaml

from _brain_labels import ROADMAP_LABEL, roadmap_sidecar_path
from _discovery.tenant import Sha256CrockfordTenantDeriver
from _entity_repository import EntityRepository
from _opportunity_emission import compose_opportunity_from_idea
from _product_emission import compose_product_from_yaml
from _requirement_emission import compose_requirement_from_idea


# The single Product this single-repo slice owns (ADR-002: derived
# deterministically from the repo, not asked of the founder per capture —
# NFR-03 single-repo, AAF-01 step-1-silent). A future multi-product slice
# would lift this to a parameter; today it is a boring constant.
_DEFAULT_PRODUCT_NAME = "Sulis Agents Marketplace"

# The bootstrapped Tenant's ``kind`` — the marketplace is a company. The Tenant
# schema requires ``kind`` (enum); ``company`` is the boring, correct value.
_TENANT_KIND = "company"
_TENANT_DISPLAY_NAME = "Sulis AI"


@dataclass(frozen=True)
class BackingChain:
    """The resolved Tenant + Product prefix every captured idea roots in.

    ``tenant_id``  — ``dna:tenant:<ulid>``, the canonical-deriver output.
    ``product_id`` — ``dna:product:<ulid>``, derived deterministically from the
    bootstrapped product name + tenant ref (``_product_emission``'s recipe).
    """

    tenant_id: str
    product_id: str


def _resolve_or_emit(
    repo: EntityRepository,
    entity_type: str,
    entity_id: str,
    compose: Callable[[], dict],
) -> None:
    """Write-once resolve-or-emit for one entity tier.

    If an instance with ``entity_id`` is already on disk, do nothing (the
    second-capture idempotence path — NFR-04). Otherwise compose the entity
    via ``compose`` and persist it through the port. ``compose`` is only
    invoked on the emit path, so neither tier composes work it then throws away.
    """
    if repo.find_by_id(entity_type, entity_id) is not None:
        return
    repo.save(entity_type, compose())


def bootstrap_backing_chain(
    *,
    repo_foundation: EntityRepository,
    repo_pd: EntityRepository,
    repo_org_slash_name: str,
    product_name: str = _DEFAULT_PRODUCT_NAME,
) -> BackingChain:
    """Resolve-or-emit the Tenant + Product prefix, bottom-up, write-once.

    1. ``tenant_id`` = canonical deriver output for ``repo_org_slash_name``.
    2. If no Tenant with that id exists (``find_by_id``) → emit it via the
       ``foundation`` adapter. The Tenant goes first so the Product's
       ``belongs_to_tenant`` resolves to an already-persisted parent.
    3. ``product_id`` derived via ``_product_emission``'s recipe, with an
       explicit ``belongs_to_tenant`` = ``tenant_id`` so the product emitter's
       precedence-1 (explicit-ref) branch fires — bypassing the sibling-yaml
       walk.
    4. If no Product with that id exists → emit it via the
       ``product-development`` adapter.
    5. Return the resolved chain. A second call re-derives the same ids, finds
       both present, and writes nothing new (NFR-04).

    Args:
        repo_foundation: ``EntityRepository`` for the ``foundation`` domain
            (where the Tenant lives).
        repo_pd: ``EntityRepository`` for the ``product-development`` domain
            (where the Product — and downstream Opportunity / Requirement —
            live).
        repo_org_slash_name: the repo's GitHub-shorthand (e.g.
            ``"sulis-ai/agents"``), passed in by the caller — this helper does
            no git / file discovery itself.
        product_name: the bootstrapped Product's display name. Defaults to the
            single-repo marketplace product; a constant, not a question.

    Returns:
        The resolved :class:`BackingChain`.
    """
    # ── Tenant (foundation) — bottom of the chain, emitted first ──────────
    tenant_id = Sha256CrockfordTenantDeriver().derive_consumer_tenant(
        repo_org_slash_name
    )
    _resolve_or_emit(
        repo_foundation,
        "tenant",
        tenant_id,
        lambda: {
            "id": tenant_id,
            "name": _TENANT_DISPLAY_NAME,
            "kind": _TENANT_KIND,
            "state": "active",
            "sys_status": "active",
        },
    )

    # ── Product (product-development) — refs the now-persisted Tenant ─────
    # Reuse _product_emission's compose: feed it a product-yaml shape with an
    # EXPLICIT belongs_to_tenant so its precedence-1 branch fires (no sibling
    # yaml-walk). This also reuses its deterministic id recipe, so the
    # product_id is stable across calls — the idempotence guarantee.
    product = _compose_bootstrap_product(product_name, tenant_id)
    product_id = product["id"]
    _resolve_or_emit(repo_pd, "product", product_id, lambda: product)

    return BackingChain(tenant_id=tenant_id, product_id=product_id)


def _compose_bootstrap_product(product_name: str, tenant_id: str) -> dict:
    """Compose the bootstrapped Product via ``_product_emission``'s recipe.

    Builds the minimal product-yaml shape the emitter expects, with an explicit
    ``belongs_to_tenant`` (the canonical tenant id) so the emitter's
    precedence-1 explicit-ref branch resolves the parent directly. Reusing
    ``compose_product_from_yaml`` keeps the Product id recipe in lockstep with
    the standalone ``sulis-emit-product`` path (single derivation, no fork).
    """
    yaml_text = yaml.safe_dump({"name": product_name, "belongs_to_tenant": tenant_id})
    products = compose_product_from_yaml(yaml_text, source_path="<bootstrap>")
    if not products:  # pragma: no cover - defensive: name is always present
        raise ValueError(
            f"bootstrap product compose produced nothing for name={product_name!r}"
        )
    return products[0]


# ─── Roadmap sidecar — the writer (ADR-001 / FR-05) ──────────────────────
# The Roadmap flag is a per-repo sidecar label file, NOT a field on the
# entity: the vendored schemas are ``unevaluatedProperties: false``, so a
# ``roadmap`` property would fail validation at the adapter boundary
# (ADR-001). The on-disk shape (filename, label, layout) is defined once in
# ``_brain_labels`` and shared with the reader (``_brain_query``).


def roadmap_add(base_dir: Path, member_ids: list[str]) -> None:
    """Add entity ids to the Roadmap sidecar's ``members`` (set semantics).

    Appends ``member_ids`` to ``<base_dir>/labels/roadmap.jsonld`` —
    deduplicating (set semantics) and writing the members sorted, so the
    file is diff-friendly and deterministic (ADR-001). The file and its
    parent directory are created on first call.

    Idempotent (NFR-04): re-adding an already-present id is a no-op. Tolerant
    of corruption (ADR-001 "Armor" row): if the existing sidecar is malformed
    (not valid JSON, or the wrong shape), it is rewritten cleanly rather than
    failing — the sidecar is marketplace-local convention, not a vendored
    entity, so the latest write is authoritative.

    Args:
        base_dir: the ``.brain/`` root. The sidecar lives at
            ``base_dir / "labels" / "roadmap.jsonld"``.
        member_ids: entity ids (``dna:<type>:<ulid>``) to mark Roadmap.
    """
    sidecar = roadmap_sidecar_path(base_dir)

    existing: set[str] = set()
    if sidecar.exists():
        try:
            data = json.loads(sidecar.read_text())
            members = data.get("members", []) if isinstance(data, dict) else []
            if isinstance(members, list):
                existing = {m for m in members if isinstance(m, str)}
        except (json.JSONDecodeError, OSError):
            # Malformed sidecar — rewrite cleanly (ADR-001 tolerant write).
            existing = set()

    merged = sorted(existing | set(member_ids))

    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(
        json.dumps({"label": ROADMAP_LABEL, "members": merged}, indent=2) + "\n"
    )


# ─── capture_idea — the orchestrator (ADR-003 / ADR-004 / ADR-005) ───────


class CaptureError(Exception):
    """Capture could not produce a rooted, orphan-free result.

    Raised by :func:`capture_idea` for the three refusal / degradation cases —
    all of which leave the store in a valid state (no orphan emitted):

    * **Why-first gate (FR-02):** ``quick`` intensity with a blank ``why`` —
      an idea cannot be captured as a bare requirement with no why. Nothing is
      written, not even the backing chain.
    * **No-orphan gate (NFR-01):** ``full`` intensity where the supplied
      ``opportunity_id`` doesn't resolve, or resolves to an Opportunity whose
      ``for_product`` chain isn't whole on disk. The Requirement is refused so
      it can never dangle.
    * **Store degradation (NFR-01):** the brain store is unavailable or a
      write fails validation. Rather than crash the host operation, capture
      surfaces a plain-English ``CaptureError`` (mirroring
      ``_brain_emit_helper``'s defensive discipline) — the CLI (WP-006)
      translates it to ``{"ok": false, "error": ...}``.

    The message is the founder-readable surface; the CLI renders it verbatim.
    """


# A well-formed Opportunity reference. The ``full`` path validates the
# supplied id's *shape* before touching the store, so a malformed id fails
# fast with a clear message rather than a confusing find-miss.
_OPPORTUNITY_REF_RE = re.compile(r"^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}$")


def _store(action: str, fn: Callable[[], object]) -> object:
    """Run a store operation, converting ANY failure to ``CaptureError``.

    The orchestrator receives its repositories as injected ports, so the
    brain-unavailable / validation-failure surface is the exception any
    ``save`` / ``find_by_id`` call may raise (a missing vendored schema, an
    invalid entity, an IO error). Wrapping each store touch here gives capture
    the same graceful-degradation contract ``_brain_emit_helper`` gives the
    substrate seams (NFR-01): the host never sees a raw traceback, only a
    plain-English ``CaptureError`` naming which step failed.
    """
    try:
        return fn()
    except CaptureError:
        raise
    except Exception as exc:  # noqa: BLE001 — deliberate degradation boundary
        raise CaptureError(
            f"capture could not {action}: the brain store is unavailable or "
            f"rejected the write ({exc})"
        ) from exc


def capture_idea(
    *,
    repo_foundation: EntityRepository,
    repo_pd: EntityRepository,
    repo_org_slash_name: str,
    roadmap_base_dir: Path,
    why_intensity: Literal["quick", "full"],
    why: str = "",
    what: str | None = None,
    seed: str,
    opportunity_id: str | None = None,
    roadmap: bool = False,
) -> dict:
    """Root an idea in an Opportunity and emit an orphan-free draft Requirement.

    The capture orchestrator (ADR-003 — one function, two depths). Both depths
    produce the same shape (a backing chain + an Opportunity + an optional
    Requirement); the only difference is **who fills the Opportunity** —
    ``quick`` populates it thinly from the founder's one-line ``why``; ``full``
    reads back an Opportunity the analyst already matured (ADR-004, by id).

    The Requirement is always the **last** write and only fires after its
    ``source`` resolves to a real Opportunity (ADR-002 / ADR-003): no orphan
    Requirement can ever land.

    Args:
        repo_foundation: ``EntityRepository`` for the ``foundation`` domain
            (the Tenant).
        repo_pd: ``EntityRepository`` for the ``product-development`` domain
            (Product / Opportunity / Requirement).
        repo_org_slash_name: the repo's GitHub-shorthand (e.g.
            ``"sulis-ai/agents"``), passed through to the backing-chain
            bootstrap — this function does no git / file discovery itself.
        roadmap_base_dir: the ``.brain/`` root (parent of ``instances``) — the
            Roadmap sidecar lives under it. Passed in so the orchestrator stays
            pure of discovery, mirroring ``bootstrap_backing_chain``.
        why_intensity: ``"quick"`` (orchestrator roots the why) or ``"full"``
            (analyst already rooted it; read the id back — ADR-004).
        why: the one-line why (``quick`` path). Blank ``why`` on ``quick`` is
            the FR-02 rejection.
        what: the requirement statement. ``None`` ⇒ the Opportunity stands
            alone as a ``hypothesis`` and no Requirement is emitted (FR-03 tail
            clause); ``requirement_id`` is ``None``.
        seed: a stable seed → deterministic ids (NFR-04). Same seed ⇒ same
            opportunity / requirement ids ⇒ overwrite-in-place, no duplicate.
        opportunity_id: the id the analyst already emitted (``full`` path,
            ADR-004). Required when ``why_intensity == "full"``.
        roadmap: when ``True``, mark the emitted ids on the Roadmap sidecar
            (FR-05) with idempotent set semantics (WP-005 ``roadmap_add``).

    Returns:
        A result dict the CLI envelope (WP-006) consumes::

            {"opportunity_id": str,
             "requirement_id": str | None,
             "roadmap": bool,
             "chain": {"tenant_id": str, "product_id": str},
             "bootstrapped": bool}

    Raises:
        CaptureError: on the why-first gate (FR-02), the no-orphan gate
            (NFR-01), or store degradation. See :class:`CaptureError`. In every
            case the store is left valid — no orphan Requirement is written.
    """
    # ── Why-first gate (FR-02) — fires BEFORE any write, even the chain. ──
    if why_intensity == "quick" and not why.strip():
        raise CaptureError("an idea needs a why before it can be captured")

    # ── Backing chain (ADR-002) — shared by both depths, bottom-up. ──────
    chain = _store(
        "bootstrap the backing chain",
        lambda: bootstrap_backing_chain(
            repo_foundation=repo_foundation,
            repo_pd=repo_pd,
            repo_org_slash_name=repo_org_slash_name,
        ),
    )
    assert isinstance(chain, BackingChain)  # noqa: S101 — _store return narrowing

    # ── Opportunity acquisition — THE single point of divergence (ADR-003).
    if why_intensity == "quick":
        resolved_opportunity_id = _acquire_quick_opportunity(
            repo_pd=repo_pd, why=why, product_id=chain.product_id, seed=seed
        )
    else:
        resolved_opportunity_id = _acquire_full_opportunity(
            repo_pd=repo_pd, opportunity_id=opportunity_id
        )

    # ── Shared tail: emit the Requirement (last write, real source). ─────
    requirement_id = _emit_requirement_if_what(
        repo_pd=repo_pd,
        what=what,
        source=resolved_opportunity_id,
        seed=seed,
    )

    # ── Roadmap label (FR-05) — idempotent set semantics (WP-005). ───────
    if roadmap:
        members = [resolved_opportunity_id]
        if requirement_id is not None:
            members.append(requirement_id)
        _store(
            "mark the idea on the roadmap",
            lambda: roadmap_add(roadmap_base_dir, members),
        )

    return {
        "opportunity_id": resolved_opportunity_id,
        "requirement_id": requirement_id,
        "roadmap": roadmap,
        "chain": {"tenant_id": chain.tenant_id, "product_id": chain.product_id},
        "bootstrapped": True,
    }


def _acquire_quick_opportunity(
    *,
    repo_pd: EntityRepository,
    why: str,
    product_id: str,
    seed: str,
) -> str:
    """``quick`` depth: the orchestrator roots the why itself.

    Compose a thin ``hypothesis`` Opportunity from the founder's one-line why
    (the ``job_statement`` is flattened to a single line inside
    ``compose_opportunity_from_idea``, mirroring ``_opportunity_emission``),
    persist it, and return its id. Idempotent on ``seed`` (NFR-04).
    """
    opportunity = compose_opportunity_from_idea(
        job_statement=why,
        for_product=product_id,
        seed=seed,
        state="hypothesis",
    )
    _store(
        "emit the opportunity",
        lambda: repo_pd.save("opportunity", opportunity),
    )
    return opportunity["id"]


def _acquire_full_opportunity(
    *,
    repo_pd: EntityRepository,
    opportunity_id: str | None,
) -> str:
    """``full`` depth: read back the Opportunity the analyst already emitted.

    The no-orphan gate (NFR-01 / ADR-004). The supplied id must (a) be a
    well-formed Opportunity ref, (b) resolve to an Opportunity on disk, and
    (c) have a whole ``for_product`` chain (its Product resolves too). Any
    miss raises ``CaptureError`` so the Requirement is never emitted against a
    dangling source.
    """
    if opportunity_id is None or not _OPPORTUNITY_REF_RE.match(opportunity_id):
        raise CaptureError(
            "the full why-rooting path needs the opportunity id the analyst "
            f"emitted (a 'dna:opportunity:<ulid>' reference); got "
            f"{opportunity_id!r}"
        )

    opportunity = _store(
        "read the analyst's opportunity",
        lambda: repo_pd.find_by_id("opportunity", opportunity_id),
    )
    if opportunity is None:
        raise CaptureError(
            f"the opportunity {opportunity_id} could not be found — the "
            "analyst hasn't emitted it yet, or it was removed. No requirement "
            "was captured (it would dangle)."
        )

    # Chain-whole: the Opportunity's parent Product must resolve on disk too,
    # or the Requirement we'd source from it would sit atop a broken chain.
    for_product = opportunity.get("for_product")
    product = _store(
        "resolve the opportunity's product",
        lambda: (
            repo_pd.find_by_id("product", for_product)
            if isinstance(for_product, str)
            else None
        ),
    )
    if product is None:
        raise CaptureError(
            f"the opportunity {opportunity_id} points at a product "
            f"({for_product!r}) that isn't on disk — its backing chain is "
            "incomplete. No requirement was captured (it would dangle)."
        )

    return opportunity_id


def _emit_requirement_if_what(
    *,
    repo_pd: EntityRepository,
    what: str | None,
    source: str,
    seed: str,
) -> str | None:
    """Emit the draft Requirement — the LAST write — when a ``what`` is given.

    ``what is None`` ⇒ the Opportunity stands alone as a hypothesis (FR-03
    tail clause); returns ``None``. Otherwise compose the Requirement against
    the **real** ``source`` Opportunity id (``compose_requirement_from_idea``
    refuses a non-Opportunity source — the code-level no-orphan gate),
    persist it, and return its id. Idempotent on ``seed`` (NFR-04).
    """
    if what is None:
        return None

    requirement = compose_requirement_from_idea(
        statement=what,
        source=source,
        seed=seed,
    )
    _store(
        "emit the requirement",
        lambda: repo_pd.save("requirement", requirement),
    )
    return requirement["id"]
