---
id: WP-003
title: Create bootstrap_backing_chain (Tenant + Product, reuse-first)
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-003
dependsOn: []
blocks: [WP-004, WP-005]
estimated_token_cost:
  input: 9k
  output: 4k
tdd_section: Form — Two-domain construction; ADR-002 backing-chain bootstrap
adrs: [ADR-002]
primitive: create
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_bootstrap_backing_chain.py::test_second_call_writes_nothing_new
---

## Context

Advances FR-04 (backing-chain bootstrap) and ADR-002. Creates the new
`_brain_capture.py` module's first responsibility: lay down the mandatory
**Tenant → Product** prefix the schema chain requires, reuse-first and
write-once. This wires the currently-orphaned `sulis-emit-product`
(via `_product_emission`) into a live caller (FR-04) and uses the canonical
consumer-tenant deriver for the Tenant identity (ADR-002 — extends external
`discover-project/ADR-002`), **not** `_tenant_emission`'s divergent ad-hoc
derivation. EXPAND-Create: a new helper that consumes ports the domain owns
(`EntityRepository`, the canonical `TenantDeriver`) — adapter-style, not a
wrapper.

Reuse mandate (CP-01..05): the tenant id comes from
`_discovery.tenant.Sha256CrockfordTenantDeriver.derive_consumer_tenant(...)`
reused unchanged; Product emission reuses `_product_emission`'s compose/save.
No new ULID algorithm is written here — reusing the canonical one is the
whole point of ADR-002 (a third derivation would silently fork the graph).

## Contract

```python
# plugins/sulis/scripts/_brain_capture.py  (new module — this WP creates the bootstrap helper only)

from dataclasses import dataclass

@dataclass(frozen=True)
class BackingChain:
    tenant_id: str   # dna:tenant:<ulid> — canonical-deriver output
    product_id: str  # dna:product:<ulid> — derived from the bootstrapped product name

def bootstrap_backing_chain(
    *,
    repo_foundation: EntityRepository,        # LocalFileEntityAdapter(base_dir, "foundation")
    repo_pd: EntityRepository,                # LocalFileEntityAdapter(base_dir, "product-development")
    repo_org_slash_name: str,                 # e.g. "sulis-ai/agents" from .sulis/repo-contract.yml
    product_name: str = "Sulis Agents Marketplace",
) -> BackingChain:
    """Resolve-or-emit the Tenant + Product prefix, bottom-up.

    1. tenant_id = Sha256CrockfordTenantDeriver().derive_consumer_tenant(repo_org_slash_name)
    2. If no Tenant with tenant_id on disk (find_by_id) → emit it (foundation domain).
    3. product_id derived deterministically (reuse _product_emission's id recipe);
       Product.belongs_to_tenant = tenant_id (explicit ref → product emitter precedence-1 branch).
    4. If no Product with product_id on disk → emit it (product-development domain).
    5. Return BackingChain. Second call: both found → zero new writes (NFR-04).
    """
```

Contract invariants:
- **Tenant identity == canonical deriver output** — byte-identical to what `/sulis:discover-project` would mint for the same repo shorthand (ADR-002). No `_tenant_emission` ad-hoc derivation.
- **Reuse-first, write-once** — second call finds both entities and writes nothing new (idempotent, NFR-04).
- **Bottom-up emit order** — Tenant before Product, so `Product.belongs_to_tenant` resolves to an already-persisted parent (ADR-002 Armor: a crash leaves a valid prefix).
- **Two-domain construction** — Tenant persists via the `foundation` adapter; Product via `product-development` (TDD two-domain detail).
- **Explicit `belongs_to_tenant`** is passed to the product emit so the precedence-1 (explicit ref) branch fires, bypassing the yaml-walk.
- Chain refs whole on disk: `Product.belongs_to_tenant` resolves to the persisted Tenant.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/unit/test_bootstrap_backing_chain.py::test_first_call_emits_whole_prefix` — fresh temp `.brain/instances`; after call, a Tenant + a Product exist; `Product.belongs_to_tenant` resolves.
- [ ] `tests/unit/test_bootstrap_backing_chain.py::test_tenant_id_equals_canonical_deriver` — returned `tenant_id` == `Sha256CrockfordTenantDeriver().derive_consumer_tenant(repo_org_slash_name)`.
- [ ] `tests/unit/test_bootstrap_backing_chain.py::test_second_call_writes_nothing_new` — call twice; instance file count + mtimes unchanged on the second call (write-once, NFR-04).
- [ ] `tests/unit/test_bootstrap_backing_chain.py::test_emitted_entities_validate` — Tenant + Product validate against their real vendored schemas via the real `LocalFileEntityAdapter` (no mock, MEA-09).
- [ ] `tests/unit/test_bootstrap_backing_chain.py::test_bottom_up_order_leaves_valid_prefix` — emitting only the Tenant (simulated partial) still validates; Product emit then resolves its ref.

### Green — Implementation makes tests pass
- [ ] All Red tests pass against a temp `.brain/instances` with the real vendored schemas.
- [ ] `Sha256CrockfordTenantDeriver` reused unchanged; no second tenant-ULID algorithm.
- [ ] `_product_emission`'s id recipe + save reused (orphaned emitter now has a live caller).
- [ ] Boring code: explicit two-adapter construction, no implicit domain inference.

### Blue — Refactor complete
- [ ] `resolve-or-emit` for Tenant and for Product share a single private helper if the shape is identical (`_resolve_or_emit(repo, entity_id, compose_fn)`).
- [ ] No new behaviour in Blue.
- [ ] All tests green after refactor.

## Sequence
- **dependsOn:** — (creates the new `_brain_capture.py` module; reuses existing modules unchanged)
- **blocks:** WP-004 (orchestrator calls bootstrap), WP-005 (`roadmap_add` is added to the `_brain_capture.py` this WP creates)
- **Parallelisable with:** WP-001, WP-002, WP-007

## Estimated Token Cost
- **Input:** ~9k (this WP + `_product_emission` head + `_discovery/tenant` + adapter)
- **Output:** ~4k (the helper + BackingChain + test file)
- **Total:** ~13k

## Notes
- At the merge SHA `.brain/instances/foundation/` is absent, so the first real run *will* mint the Tenant via the canonical deriver — this is correct (ADR-002 "Adopted: reuse-first, else mint via the canonical deriver").
- `repo_org_slash_name` is read from `.sulis/repo-contract.yml` by the orchestrator (WP-004) and passed in — keep this helper pure of git/file discovery so it stays unit-testable.
