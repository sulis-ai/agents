---
id: WP-018
title: "Products: GET /api/products + POST /api/products/active + server-side Product scope"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: reads
parent_group: multi-product

atomic_branch: yes
estimate: 6h
blast_radius: medium       # introduces the scope-selection verb; touches the read-only gate classification
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "GET /api/products returns the Tenant's Products with the active one marked (ProductList; activeProductId null when none selected) — read-only (FR-38, ADR-009)"
  - "POST /api/products/active {productId} sets the active Product and echoes it; 404 for an unknown productId; it writes NOTHING to the change store or brain, mints nothing, starts/signals no session — a SCOPE selection only (FR-38 read-only, ADR-009)"
  - "lib/products/productScope.ts computes the change→Project→Product roll-up server-side: GET /api/changes and GET /api/search scoped to the active Product return ONLY that Product's changes; no other Product's change appears (FR-37)"
  - "read-only gate (check-read-only.sh + read-only-inventory.test.ts) classifies POST /api/products/active as a SCOPE-SELECTION verb — neither a forbidden mutation nor conflated with the sanctioned chat write (ADR-003 + ADR-009); the ?product= query-param variant needs NO gate change (recorded if builder picks it)"
  - "Active-Product scope is view/session state, NOT a new persistent store (NFR-DATA-01); single-Product Tenant is the trivial case (one Product, shown active)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/productScope.test.ts (NEW) — change→Project→Product roll-up; two Products seeded, scope returns only the active set; single-Product trivial case"
  integration:
    - "apps/cockpit/server/tests/routes.products.test.ts (NEW) — supertest: GET list marks active; POST sets+echoes; 404 unknown; GET /api/changes + /api/search honour the active Product scope server-side"
    - "apps/cockpit/server/tests/read-only-inventory.test.ts (EXTEND) — POST /api/products/active is the scope-selection verb; writes/mints/starts none; reads start no process"
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0"
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.products.test.ts"

derived_from:
  - finding: "ADR-009 board is Product-scoped + server-side roll-up; TDD §2.4 productScope row + §5.1 multi-product rows; FR-37, FR-38, UC-11; openapi.yaml /api/products + /api/products/active"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-009-board-is-product-scoped-with-server-side-rollup.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-017]   # change shape (WP-001) + Product/ProductList types (WP-017)

child_wps: []
kinds: null

# read-only posture carried on the scope-selection verb:
security_constraints:
  - "POST /api/products/active is scope-selection only: no store/brain write, no mint, no session start/signal (FR-38, NFR-DISC-05 posture)"
  - "Server-side roll-up keeps the seam the single source of truth for scope; no cross-Product data leaks to the client (NFR-ARCH-01, ADR-009)"

verifies_scenario: "PENDING-MINT:K"   # Product-switch (UC-11) — author scenario K then backfill the dna:scenario ULID

rollback: |
  New productScope lib + products route + gate scope-selection classification
  + tests. Remove the mount, revert the gate edit (the gate returns to its
  prior all-mutations-forbidden state — POST /api/products/active would then be
  flagged, which is why the ?product= variant is the zero-gate-change fallback),
  revert the commit.
---

# Products: GET /api/products + POST /api/products/active + server-side Product scope

## Why

A Tenant may have many Products; the board must show **one** Product's
in-flight changes at a time (FR-37), with a switcher to re-scope (FR-38,
UC-11). ADR-009: the **seam** owns scope — the roll-up `change → Project →
Product` is computed server-side so a client never receives another Product's
changes (NFR-ARCH-01). This WP is the backend half: the products list, the
scope-selection verb, and the `productScope` lib the board/search reads
consume. It supersedes the single-implicit-product board within this change's
namespace.

## What changes

- `apps/cockpit/server/lib/products/productScope.ts` (NEW, EXPAND-Create) — `(changes, projects, products, activeProductId) → Change[]`; the change→Project→Product roll-up; the single source of truth for "active Product" scope.
- `apps/cockpit/server/routes/products.ts` (NEW, EXPAND-Create) — `GET /` (ProductList) + `POST /active` (scope selection). Mounted at `/api/products`.
- `apps/cockpit/server/routes/changes.ts` + `routes/search.ts` (MODIFY) — take the active Product as server-side scope (compose `productScope`); the contract for `/api/changes` and `/api/search` gains optional Product scope (server-side, FR-37).
- `apps/cockpit/scripts/check-read-only.sh` + `read-only-inventory.test.ts` (MODIFY) — recognise `POST /api/products/active` as a **scope-selection** verb (ADR-009): no side effect beyond view scope, distinct from forbidden mutations and from the one sanctioned chat write.

The `?product=` query-param variant (ADR-009) is the recorded fallback: if the
builder prefers stateless scope, every board/search read takes `?product=<id>`
and there is no `POST /api/products/active` and **no** gate change. The
roll-up is server-side either way. The builder picks one and records it in the
WP's `## How` on landing.

## How

`productScope` reads the existing change list + the Project/Product graph (no
new store). Active-Product selection is view/session scope — the read-side
equivalent of a query parameter (NFR-DATA-01), not a persistent store. The
gate gains a scope-selection classification rather than a write exception.

## Tests

- `productScope.test.ts` — seed two Products; the active scope returns only its changes; single-Product trivial case.
- `routes.products.test.ts` — list marks active; POST sets+echoes; 404 unknown; `/api/changes` + `/api/search` honour scope server-side.
- `read-only-inventory.test.ts` — the scope-selection verb writes/mints/starts nothing.

## Scenario linkage

Verifies scenario **K — "Switch the active Product; the board re-scopes"**
(UC-11). Scenario K is not yet minted; author it (`sulis-author-scenario`) and
backfill the `dna:scenario:<ULID>` here so `sulis-verify-acceptance
--scenario` runs it from-graph (aggregated in WP-027).

## Rollback

Remove the lib + route + gate classification + tests; revert. If the
`?product=` variant was taken, there is no gate edit to revert.
