"""WP-003 — tests for ``_brain_capture.bootstrap_backing_chain``.

Verifies the ADR-002 backing-chain bootstrap: resolve-or-emit the mandatory
Tenant → Product prefix, bottom-up, write-once. The load-bearing invariant
(ADR-002) is that the Tenant id is byte-identical to the CANONICAL consumer-
tenant deriver (``_discovery.tenant.Sha256CrockfordTenantDeriver``) — never
``_tenant_emission``'s divergent ad-hoc derivation — so capture's chain joins
the existing graph rather than forking a parallel identity.

No store mocks (MEA-09): tests run against a temp ``.brain/instances`` and the
real ``LocalFileEntityAdapter`` validating against the real vendored schemas
under ``plugins/sulis/brain/compiled/{foundation,product-development}/``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _brain_capture import BackingChain, bootstrap_backing_chain
from _discovery.tenant import Sha256CrockfordTenantDeriver
from _entity_adapter_local import LocalFileEntityAdapter


_REPO = "sulis-ai/agents"
_TENANT_ID_RE = re.compile(r"^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$")
_PRODUCT_ID_RE = re.compile(r"^dna:product:[0-9A-HJKMNP-TV-Z]{26}$")


@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    """A fresh temp ``.brain/instances`` directory (no entities yet)."""
    return tmp_path / ".brain" / "instances"


@pytest.fixture
def repo_foundation(base_dir: Path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(base_dir=base_dir, domain="foundation")


@pytest.fixture
def repo_pd(base_dir: Path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(base_dir=base_dir, domain="product-development")


def _instance_files(base_dir: Path) -> list[Path]:
    """Every ``.jsonld`` instance file under the temp store, sorted."""
    return sorted(base_dir.rglob("*.jsonld"))


def test_first_call_emits_whole_prefix(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
) -> None:
    """Fresh store → after the call a Tenant + a Product exist and
    ``Product.belongs_to_tenant`` resolves to the persisted Tenant."""
    chain = bootstrap_backing_chain(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
    )

    assert isinstance(chain, BackingChain)
    assert _TENANT_ID_RE.match(chain.tenant_id)
    assert _PRODUCT_ID_RE.match(chain.product_id)

    tenant = repo_foundation.find_by_id("tenant", chain.tenant_id)
    product = repo_pd.find_by_id("product", chain.product_id)
    assert tenant is not None, "Tenant was not persisted"
    assert product is not None, "Product was not persisted"

    # Chain whole on disk: the Product's parent ref points at the Tenant we
    # just persisted (not a divergent / dangling id).
    assert product["belongs_to_tenant"] == chain.tenant_id
    assert tenant["id"] == chain.tenant_id


def test_tenant_id_equals_canonical_deriver(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
) -> None:
    """The returned tenant id is byte-identical to the canonical deriver's
    output for the same repo shorthand (ADR-002 — no second algorithm)."""
    expected = Sha256CrockfordTenantDeriver().derive_consumer_tenant(_REPO)

    chain = bootstrap_backing_chain(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
    )

    assert chain.tenant_id == expected


def test_second_call_writes_nothing_new(
    base_dir: Path,
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
) -> None:
    """Write-once / idempotent (NFR-04): a second call finds both entities
    and writes nothing — same file set, unchanged mtimes."""
    first = bootstrap_backing_chain(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
    )
    files_after_first = _instance_files(base_dir)
    mtimes_after_first = {p: p.stat().st_mtime_ns for p in files_after_first}
    assert len(files_after_first) == 2  # exactly one Tenant + one Product

    second = bootstrap_backing_chain(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
    )

    # Same ids returned.
    assert second == first
    # No new files, and the existing files were not rewritten.
    files_after_second = _instance_files(base_dir)
    assert files_after_second == files_after_first
    mtimes_after_second = {p: p.stat().st_mtime_ns for p in files_after_second}
    assert mtimes_after_second == mtimes_after_first


def test_emitted_entities_validate(
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
) -> None:
    """Both emitted entities validate against their real vendored schemas via
    the real adapter (MEA-09 — no mock). ``save`` already validates, so a
    successful bootstrap means they validated; re-assert explicitly via
    ``validate`` to pin the contract."""
    chain = bootstrap_backing_chain(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
    )

    tenant = repo_foundation.find_by_id("tenant", chain.tenant_id)
    product = repo_pd.find_by_id("product", chain.product_id)
    assert tenant is not None
    assert product is not None

    # Re-validate the persisted instances against the real schemas — raises
    # EntityValidationError if anything drifted.
    repo_foundation.validate("tenant", tenant)
    repo_pd.validate("product", product)


def test_bottom_up_order_leaves_valid_prefix(
    base_dir: Path,
    repo_foundation: LocalFileEntityAdapter,
    repo_pd: LocalFileEntityAdapter,
) -> None:
    """Bottom-up emit order (Tenant before Product) means a crash after the
    Tenant write still leaves a valid prefix; the subsequent Product emit then
    resolves its ``belongs_to_tenant`` ref against the already-persisted
    Tenant (ADR-002 Armor: no orphan Product)."""
    # Simulate a partial bootstrap: only the Tenant exists on disk (as if the
    # process died after the first, bottom-most write).
    canonical_tenant = Sha256CrockfordTenantDeriver().derive_consumer_tenant(_REPO)
    repo_foundation.save(
        "tenant",
        {
            "id": canonical_tenant,
            "name": "Sulis AI",
            "kind": "company",
            "state": "active",
            "sys_status": "active",
        },
    )
    # The Tenant alone is a valid prefix.
    assert repo_foundation.find_by_id("tenant", canonical_tenant) is not None
    assert repo_pd.find_by_id("product", "dna:product:" + "0" * 26) is None

    # Re-run: Tenant is reused (not re-derived to a different id), Product emit
    # resolves its ref to the persisted Tenant.
    chain = bootstrap_backing_chain(
        repo_foundation=repo_foundation,
        repo_pd=repo_pd,
        repo_org_slash_name=_REPO,
    )

    assert chain.tenant_id == canonical_tenant
    product = repo_pd.find_by_id("product", chain.product_id)
    assert product is not None
    assert product["belongs_to_tenant"] == canonical_tenant
    # Still exactly one Tenant (no duplicate, divergent identity).
    tenant_files = sorted((base_dir / "foundation" / "tenant").glob("*.jsonld"))
    assert len(tenant_files) == 1
