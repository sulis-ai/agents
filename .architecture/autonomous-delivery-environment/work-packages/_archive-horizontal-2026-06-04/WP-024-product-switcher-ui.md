---
id: WP-024
title: "Product switcher: list Products, mark active, re-scope the board on select"
kind: frontend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: surfaces
parent_group: multi-product

atomic_branch: yes
estimate: 5h
blast_radius: low
primitive: EXPAND-Create
group: expand
visual_contract: WP-002
acceptance_criteria:
  - "The product switcher lists the Tenant's Products (GET /api/products), marks the active one, and on select re-scopes the board AND the per-product views (search, stage filter, needs-attention) to the chosen Product (FR-38, UC-11)"
  - "Selecting a Product calls POST /api/products/active (or sets ?product= per the builder's ADR-009 choice) — a SCOPE selection; it performs ZERO writes / mints / session-starts (FR-38 read-only)"
  - "The single-Product Tenant shows one Product, already active (trivial case); a board that's been re-scoped never shows another Product's change (FR-37, server-side roll-up — the client trusts the seam)"
  - "Consumes tokens.css only (no raw hex); matches the SIGNED visual contract (WP-002 — now covers the product switcher surface)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/client/src/tests/ProductSwitcher.test.tsx (NEW) — lists Products, marks active, re-scopes on select; single-Product trivial case; the select performs no write/mint/start (read-only client funnel)"
  verification:
    - "axe-core a11y on the product switcher green"
    - "branch-ci green"
verification_gates: [unit, component, visual_diff, a11y, perf_budget]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ProductSwitcher.test.tsx"

derived_from:
  - finding: "ADR-009 board is Product-scoped + switcher re-scopes per-product views; TDD §2.4 ProductSwitcher row + §5.1 multi-product rows; FR-37, FR-38, UC-11; visual contract covers the product switcher surface"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-009-board-is-product-scoped-with-server-side-rollup.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-002, WP-011, WP-017, WP-018]
# SIGNED visual contract (#45) + the board it re-scopes + Product types + the products route/scope

child_wps: []
kinds: null

# read-only posture (client side):
security_constraints:
  - "The switcher is a scope selection: it performs no write / mint / session-start; the client read-only funnel inventory still passes (FR-38)"
  - "Cross-Product isolation is a SEAM guarantee (server-side roll-up, ADR-009) — the client trusts the scoped list, never filters cross-Product data itself"

verifies_scenario: "PENDING-MINT:K"   # Product-switch (UC-11)

rollback: |
  New ProductSwitcher component + its query hook in the board shell. Remove the
  switcher; the board reverts to the single active Product (or all, per prior
  behaviour). Revert the commit. No other surface affected.
---

# Product switcher: list Products, mark active, re-scope the board on select

## Why

A Tenant may have many Products; the board shows one at a time (FR-37) and the
switcher re-scopes to another (FR-38, UC-11). This is the client half of
ADR-009: the **seam** owns scope (server-side roll-up), so the switcher's job
is to list Products, mark the active one, and tell the seam which Product is
active — then let the re-scoped board/search/filters follow. It writes nothing.

## What changes

- `apps/cockpit/client/src/components/ProductSwitcher.tsx` (NEW, EXPAND-Create) — lists Products (`GET /api/products`), marks active, on select calls `POST /api/products/active` (or sets `?product=` per the builder's ADR-009 choice) and re-scopes the board + per-product views.
- `apps/cockpit/client/src/api/useProducts.ts` (NEW) — query for the products list + the active-Product selection.
- The board shell (WP-011) hosts the switcher and re-fetches the scoped change list on switch.

## How

Consume WP-018's products route + scope. The switch is a scope selection — no
write/mint/start (the client read-only funnel still passes). Cross-Product
isolation is a seam guarantee (server-side roll-up); the client trusts the
scoped list rather than filtering cross-Product data itself. Consume
`tokens.css` only; match the signed visual contract (WP-002), which now covers
the product switcher surface.

## Tests

`ProductSwitcher.test.tsx` — lists/marks/re-scopes; single-Product trivial
case; the select performs no write/mint/start. axe-core on the switcher.

## Scenario linkage

Verifies scenario **K — "Switch the active Product; the board re-scopes"**
(UC-11). Author scenario K and backfill its `dna:scenario:<ULID>` (aggregated
in WP-027).

## Rollback

Remove the switcher + hook; revert. No other surface affected.
