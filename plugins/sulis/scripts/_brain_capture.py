"""Brain-capture orchestration helpers.

This module owns the capture-side composition that turns a founder's idea into
a rooted entry in the Brain graph. Its first responsibility (WP-003 / FR-04 /
ADR-002) is ``bootstrap_backing_chain`` — laying down the mandatory
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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from _brain_labels import ROADMAP_LABEL, roadmap_sidecar_path
from _discovery.tenant import Sha256CrockfordTenantDeriver
from _entity_repository import EntityRepository
from _product_emission import compose_product_from_yaml


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
    yaml_text = yaml.safe_dump(
        {"name": product_name, "belongs_to_tenant": tenant_id}
    )
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
