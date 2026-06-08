---
# Identity (WP-01)
id: WP-008
title: "Journey K round-trip: pick another Product in the switcher → the board re-scopes to it"
kind: full-round-trip
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: vertical-slice
slice_kind: round-trip
journey: "K — Switch the active Product; the board re-scopes"

atomic_branch: yes
estimate: 10h
blast_radius: medium     # introduces the full server-side scope roll-up + the scope-selection verb
primitive: EXPAND-Create
group: expand
visual_contract: WP-002

observed_acceptance:
  scenario: "PENDING-MINT:K"   # author scenario K (sulis-author-scenario) then backfill dna:scenario:<ULID>
  observable_result: "With more than one Product, the founder opens the product switcher on the board, picks a different Product, and the board (and its search / stage / needs-attention filters) re-scopes to show only that Product's changes — no other Product's change ever appears."
  how_observed: "Run the real cockpit app with TWO seeded Products, each with changes. OBSERVE the board shows only the active Product's changes. Open the switcher, pick the other Product. OBSERVE the board re-scopes to the second Product's changes and the first Product's changes disappear. Apply a search/filter; OBSERVE it stays within the now-active Product. Confirm the switch performed no write/mint/session-start."
  not_sufficient: "Green CI / from-graph run alone do NOT satisfy the DoD. Only picking a Product in the running app and watching the board re-scope does."
  human_hops: "None — fully observable locally with two seeded Products."

acceptance_criteria:
  - "DATA/ROUTE: GET /api/products returns the Tenant's Products with the active one marked (ProductList; activeProductId null when none selected) — read-only (FR-38, ADR-009); POST /api/products/active {productId} sets+echoes the active Product, 404 unknown, writes NOTHING to store/brain, mints nothing, starts/signals no session — a SCOPE selection only (FR-38). lib/products/productScope.ts computes the change→Project→Product roll-up server-side so GET /api/changes + GET /api/search return ONLY the active Product's changes (FR-37) — this REPLACES the trivial single-Product scope the board slice (WP-003) shipped"
  - "GATE: read-only gate classifies POST /api/products/active as a SCOPE-SELECTION verb — neither a forbidden mutation nor conflated with the sanctioned chat write (ADR-003+ADR-009); the ?product= query-param variant needs NO gate change (recorded if the builder picks it)"
  - "DATA: active-Product scope is view/session state, NOT a new persistent store (NFR-DATA-01); single-Product Tenant is the trivial case (one Product, shown active)"
  - "UI: the product switcher lists the Tenant's Products, marks active, and on select re-scopes the board AND the per-product views (search, stage, needs-attention) to the chosen Product (FR-38, UC-11); the select performs ZERO writes/mints/session-starts (FR-38 read-only); the client trusts the seam's scoped list (server-side roll-up), never filtering cross-Product data itself; consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
  - "OBSERVED ROUND-TRIP: with two Products seeded and the app running, picking another Product in the switcher re-scopes the board to it (scenario-K observable result), confirmed by driving the app"
test_plan:
  unit:
    - "apps/cockpit/server/tests/productScope.test.ts (NEW) — change→Project→Product roll-up; two Products seeded, scope returns only the active set; single-Product trivial case"
  integration:
    - "apps/cockpit/server/tests/routes.products.test.ts (NEW) — supertest: GET list marks active; POST sets+echoes; 404 unknown; GET /api/changes + /api/search honour active-Product scope server-side"
    - "apps/cockpit/server/tests/read-only-inventory.test.ts (EXTEND) — POST /api/products/active is the scope-selection verb; writes/mints/starts none"
    - "apps/cockpit/client/src/tests/ProductSwitcher.test.tsx (NEW) — lists Products, marks active, re-scopes on select; single-Product trivial case; select performs no write/mint/start"
  observed:
    - "MANUAL/DRIVEN (the gate): run server+client with two Products, pick the other in the switcher, OBSERVE the board re-scope per observed_acceptance.how_observed"
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0"
    - "axe-core a11y on the product switcher green"
    - "branch-ci green"
    - "OBSERVED round-trip recorded — not just CI"
verification_gates: [unit, integration, component, visual_diff, a11y, observed_roundtrip]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.products.test.ts"

derived_from:
  - finding: "Re-slice vertical: Journey K (product switch). Folds prior horizontal WP-018 (products route + full server-side scope + gate classification) + WP-024 (ProductSwitcher UI) into ONE observable round-trip. This slice promotes the trivial single-Product scope from WP-003 to the full roll-up. ADR-009; FR-37, FR-38, UC-11."
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-009-board-is-product-scoped-with-server-side-rollup.md
    severity_at_discovery: n/a
generated_by:
  activity: re-slice-vertical/2026-06-04
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-003, WP-006, WP-007]
# data contract + visual contract + the board it re-scopes (WP-003) + the brain/thread (WP-006) and search (WP-007) views the switch must also re-scope

child_wps: []
kinds: null

locked_decisions:
  - "ONE Product per onboarding conversation (multi-product setup deferred) — founder-locked; this slice is multi-product VIEW scope, not multi-product setup"

security_constraints:
  - "POST /api/products/active is scope-selection only: no store/brain write, no mint, no session start/signal (FR-38)"
  - "Server-side roll-up keeps the seam the single source of truth for scope; no cross-Product data leaks to the client (NFR-ARCH-01, ADR-009)"

verifies_scenario: "PENDING-MINT:K"   # Product-switch (UC-11) — author + backfill the dna:scenario ULID

rollback: |
  New productScope lib + products route + gate scope-selection classification +
  ProductSwitcher component + useProducts hook + tests. Remove the switcher + the
  mount; revert the gate edit (the gate returns to its prior state; the ?product=
  variant is the zero-gate-change fallback); GET /api/changes + /api/search revert
  to the trivial single-Product scope from WP-003. Revert the commit.
---

# Journey K round-trip: switch the active Product → the board re-scopes

## The round-trip this slice delivers

**Pick another Product in the switcher → (action: select it) → OBSERVE: the board
(and its filters) re-scope to that Product's changes.** The products route +
server-side scope and the switcher UI that drives it ship together. This is the
first slice where multi-Product *view scope* becomes real — the board slice
(WP-003) shipped only the trivial single-Product case; this slice promotes it to
the full `change → Project → Product` roll-up.

## What changes (the whole round-trip, one branch)

- **Route + scope (server):** `lib/products/productScope.ts` (the roll-up — the
  single source of truth for active-Product scope); `routes/products.ts`
  (`GET /` ProductList + `POST /active` scope selection); `routes/changes.ts` +
  `routes/search.ts` take the active Product as server-side scope (composing
  `productScope`) — replacing WP-003's trivial scope; the read-only gate gains a
  **scope-selection** classification for `POST /api/products/active` (ADR-009),
  or the `?product=` query-param variant with no gate change (builder's choice,
  recorded on landing).
- **UI (client):** `components/ProductSwitcher.tsx` (lists Products, marks active,
  re-scopes on select); `api/useProducts.ts`. The board shell (WP-003) hosts the
  switcher and re-fetches the scoped change list on switch.

## The observed-acceptance gate (MUST)

DoD = the **observed round-trip**: run the real app with **two** seeded Products,
pick the other in the switcher, and **watch** the board re-scope — the first
Product's changes disappear, only the second's remain, and search/filters stay
within the active Product. Capture the driven-app evidence. Author scenario K and
run it from-graph on top of the human observation.

**Human/third-party hops:** none — fully observable locally with two Products.

## Scenario K (PENDING-MINT)

Author scenario K (`sulis-author-scenario` in the specify step) and backfill its
`dna:scenario:<ULID>` into `observed_acceptance.scenario` and `verifies_scenario`
here.

## Rollback

Remove the switcher + route + gate classification; `/api/changes` + `/api/search`
revert to the trivial single-Product scope. Revert the commit.
