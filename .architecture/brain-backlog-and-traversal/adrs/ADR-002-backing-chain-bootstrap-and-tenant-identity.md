# ADR-002 — Backing-chain bootstrap reuses the ADR-002-canonical tenant identity

> Change: CH-01KT60 · Status: accepted · Pillar: Form
> Relates: FR-04 (backing-chain bootstrap), NFR-04 (idempotent), NFR-03 (single-repo)
> Extends: external `discover-project/adrs/ADR-002-consumer-tenant-ulid-derivation`

## Decision

The first capture in a repo lays down the mandatory backing chain
**Tenant → Product → Opportunity → Requirement** and reuses it on every
subsequent capture. Two sub-decisions:

1. **Tenant identity uses the canonical consumer-tenant deriver**
   (`_discovery/tenant.Sha256CrockfordTenantDeriver`), seeded on the repo's
   GitHub-shorthand (`sulis-ai/agents` from `.sulis/repo-contract.yml`) —
   **not** `_tenant_emission`'s ad-hoc `tenant-name:{display-name}`
   derivation. The bootstrapped Tenant resolves to the same id that
   `/sulis:discover-project` would mint, so capture's chain joins the
   existing graph rather than forking a parallel identity.

2. **Bootstrap is reuse-first, write-once.** The capture orchestrator
   resolves the chain top-down; for each tier it queries the store
   (via `find_by_id`) and emits only if absent. A second capture re-derives
   the same ids and finds them present — zero new tenant/product writes.

## Why

The SRD's FR-04 says "lays down a Tenant, a Product, and reuses them." The
schema chain makes the *order* and the *identity* load-bearing:

- `Requirement.source` (required) → `dna:opportunity:<ulid>`
- `Opportunity.for_product` (required) → `dna:product:<ulid>`
- `Product.belongs_to_tenant` (required) → `dna:tenant:<ulid>`

A captured idea is invalid until its whole chain exists. So capture must
emit **bottom-up at write time** (Tenant first, Requirement last) so each
ref resolves to an already-persisted parent — the adapter validates
`belongs_to_tenant`/`for_product`/`source` pattern-shape but the *graph*
is only whole if the parents are on disk.

**The tenant-identity fork is the real trap.** Schema inspection surfaced
**two divergent tenant-ULID derivations already in the tree**, both claiming
to be canonical:

| Source | Seed | Algorithm | First-char clamp |
|---|---|---|---|
| `_tenant_emission._deterministic_ulid_from` | `tenant-name:{display-name}` | `digest[:17] & (2^130-1)`, reversed 5-bit chunks | no |
| `_discovery/tenant` (external ADR-002) | `tenant-name:{org}/{repo}` | `digest[:17] >> 6`, MSB-first | yes |

These produce **different ULIDs for the same conceptual tenant.** If capture
naively called `sulis-emit-tenant` with a `.sulis/tenant.yaml`, it would mint
a *third* identity for this repo and the captured ideas would dangle off a
tenant that `discover-project`, `release-train`, and every other entity-
emitting path can't see. The graph would silently fragment.

The external `discover-project` ADR-002 already won this argument: its
deriver is "the ADR-002 recipe," it carries the first-char ULID-spec clamp,
and it grandfathers the marketplace's historical tenant
(`dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM`). Capture **extends** that decision
rather than competing with it. This is CP-01 priority 0: internal prior art
that's already locked.

## Alternatives considered

- **Call `sulis-emit-tenant --from-yaml` with a bootstrapped
  `.sulis/tenant.yaml` (rejected).** Uses the divergent `_tenant_emission`
  derivation → fork. Also requires writing a config file as a side effect of
  capture, which is surprising. Rejected: identity fork + side effect.

- **Reuse the grandfathered marketplace tenant id verbatim (rejected as a
  rule; honoured opportunistically).** Empirically (verified at design time)
  the three candidate derivations all diverge for `sulis-ai/agents`:
  canonical `dna:tenant:7Q5TE6ZK6XMDM63BHNKXCJ46FY`; naive-`_tenant_emission`
  `dna:tenant:EBMWDZ6DV8V8C6Q3B7TS48CZWM`; grandfathered
  `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM`. The grandfathered id is **not**
  reproducible by either deriver (external ADR-002's amendment is explicit:
  it "predates this recipe"), and at the merge SHA **no Tenant instance
  exists on disk** (`.brain/instances/foundation/` is absent) — so
  reuse-first finds nothing and the bootstrap *will mint*. Minting the
  canonical-deriver id (not the grandfathered literal, not the naive one)
  is correct because it is the identity `/sulis:discover-project` mints for
  new Projects — capture's chain then aligns with the path founders already
  run, rather than with a historical ad-hoc literal that doesn't generalise.
  Rejected: hard-coding the grandfathered literal. **Adopted:** reuse-first
  (prefer any on-disk Tenant), else mint via the canonical deriver.

- **Let the founder name the Product per capture (rejected — friction).**
  FR-01/NFR-02 want capture to be lightweight and jargon-free. Asking
  "which product?" on every idea exposes the entity model. The repo has
  exactly one Product in this single-repo slice (NFR-03); derive it
  deterministically from the repo (`Sulis Agents Marketplace`) and reuse.
  Rejected: unnecessary question (AAF-01 step-1-silent).

## Consequences

- A new shared helper — `_brain_capture.bootstrap_backing_chain(repo,
  repo_root)` — owns the resolve-or-emit logic for Tenant + Product. It
  wires the orphaned `sulis-emit-product` (via `_product_emission`) into a
  live caller (FR-04) and uses the canonical deriver for the Tenant.
- **Domain split is explicit:** Tenant is a `foundation`-domain entity;
  Product/Opportunity/Requirement are `product-development`. The
  orchestrator constructs two adapters (one per domain) — mirroring how
  `sulis-emit-tenant` defaults `--domain foundation` while the others
  default `product-development`.
- Product's `belongs_to_tenant` ref is set to the canonical tenant id
  directly (not resolved from a sibling yaml), bypassing
  `_product_emission._resolve_tenant_ref`'s yaml-walk. The orchestrator
  passes an explicit `belongs_to_tenant` so the product emitter's
  precedence-1 branch (explicit ref) fires.
- Re-running capture on the same idea is idempotent end-to-end (NFR-04):
  same chain ids, same opportunity/requirement ids (ADR-005 seed).
- Cross-repo Tenant/Product (Platform tier) stays out of scope (NFR-03);
  this ADR is single-repo and joins the local graph only.
