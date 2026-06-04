# ADR-009 — The board is Product-scoped; the Project→Product roll-up is computed server-side

- **Status:** accepted
- **Date:** 2026-06-04
- **Change:** CH-01KT50 · autonomous-delivery-environment
- **Deciders:** SEA

## Context

A Tenant may have many Products. The board must show **one Product's**
in-flight changes at a time — the active Product — never all Products mixed
(FR-37). A **product switcher** re-scopes the board and the per-product views
(search, filters, needs-attention) to the chosen Product (FR-38, UC-11). This
**supersedes the single-implicit-product board** the original slice
described; FR-01/02/03/15 are now read "for the active Product".

A change rolls up to a Product via its Project (`change → Project → Product`).
Two design questions:

1. **Where is the roll-up computed** — client-side (fetch all changes, group
   in the browser) or server-side (the seam returns only the active Product's
   changes)?
2. **Where does "active Product" live** — purely client UI state, or a value
   the seam understands?

The original `GET /api/changes` returns *all* changes and the board groups
them into stage columns client-side. Naively extending that — fetch
everything, filter to the active Product in the browser — would push every
Product's changes across the seam to a client that must drop most of them.

## Decision

**The seam is Product-aware: the board's change list is scoped to an active
Product server-side, and the active Product is an explicit, read-only scope
the seam understands.**

- **Server-side roll-up (FR-37):** the board endpoint returns only the active
  Product's in-flight changes. The `change → Project → Product` roll-up is
  computed at the seam (the server already reads the graph), so a client never
  receives another Product's changes. This keeps the seam the single source of
  truth for scope (NFR-ARCH-01) and avoids leaking cross-Product data to the
  client.
- **Products list + active-Product selection (FR-38):** the seam exposes
  `GET /api/products` (the Tenant's Products, with the active one marked) and
  `POST /api/products/active` to set the active Product. Setting the active
  Product is a **scope selection, not a data mutation** — it changes *what the
  seam returns*, writes nothing to the change store or brain, mints nothing,
  and starts/signals no session (FR-38 is read-only). The active-Product
  selection is the one piece of UI scope state the seam tracks; it is **not** a
  new persistent store (NFR-DATA-01) — it is session/view scope, the read-side
  equivalent of a query parameter.
- **Per-product views follow the active Product:** search (FR-10), stage
  filter (FR-11), and needs-attention (FR-12) all operate within the active
  Product's change set — they take the active Product as scope, server-side,
  so a filter can never surface another Product's change.

`POST /api/products/active` uses a mutation verb for a read-only scope
selection — the same shape question the chat relay faced (ADR-001). Unlike the
chat relay, it is **not** a sanctioned *write* path: it performs no filesystem
write, no git mutation, no process start, no store/brain mutation. The
read-only gate (ADR-003) is extended to recognise it as a **scope-selection
verb** (no side effect beyond view scope), distinct from both the forbidden
mutations and the one sanctioned chat write. (A `GET`-with-query alternative is
noted below.)

## Alternatives considered

- **Client-side roll-up — fetch all changes, filter in the browser
  (rejected).** Pushes every Product's changes across the seam, leaks
  cross-Product data to the client, and makes FR-37's "no other Product's
  changes appear" a client-trust property rather than a seam guarantee. The
  seam owns scope.
- **Active Product as pure client state, seam stays Product-blind
  (rejected).** Same leak: the seam would still have to return all changes for
  the client to choose from. Making the seam Product-aware is what keeps the
  data boundary honest.
- **Encode active Product as a query parameter on every read
  (`?product=…`) instead of `POST /api/products/active` (viable
  alternative).** Avoids the scope-selection verb entirely and is arguably the
  more boring/RESTful shape. Recorded as the design-stage builder's choice: if
  the builder prefers stateless scope, every board/search read takes
  `?product=<id>` and there is no `POST /api/products/active`. Either way the
  roll-up is server-side and the selection writes no data. The contract
  documents both; the builder picks one and records it.

## Consequences

- The seam gains `GET /api/products` and `POST /api/products/active` (or the
  `?product=` query-param variant); `GET /api/changes` and `GET /api/search`
  gain Product scoping (server-side roll-up).
- The read-only gate (ADR-003) gains a **scope-selection** classification so
  `POST /api/products/active` is neither flagged as a forbidden mutation nor
  conflated with the one sanctioned chat write. If the builder takes the
  `?product=` variant, no gate change is needed at all (it stays all-GET).
- Verified entirely from seeded fixtures (FR-37/38, UC-11): seed two Products,
  assert the board shows only the active Product's changes, assert switching
  re-scopes board + per-product views, assert the switch performs zero
  writes/mints/session-starts. No live agent.
- This supersedes the single-implicit-product board within this change's own
  namespace; FR-01/02/03/15 are re-read "for the active Product".
