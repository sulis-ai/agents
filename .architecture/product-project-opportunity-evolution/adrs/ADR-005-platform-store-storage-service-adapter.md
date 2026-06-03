---
id: ADR-005
title: Platform store is the EXISTING file adapter pointed at the central `~/.sulis/instances/{tenant_id}/` Tenant home (reuse, not build); SQLite deferred to a later change behind the same port
status: accepted
date: 2026-06-03
deciders: [iain]
---

## Context

Scope item 5 + the SPEC LADDER ("the flat-file query swaps for a real backend
there"): Product and Opportunity are **Tenant-scoped / cross-repo** entities.
Today they emit to the *repo-local*
`.brain/instances/{domain}/{entity_type}/{ulid}.jsonld` tree via
`LocalFileEntityAdapter`, read back by the flat-file walk in
`_brain_query.iter_entities`. That home is per-repo: a Tenant whose Product
spans five repos has its Product version-history scattered across five
`.brain/instances` trees with no single place to read "the Product as the
Tenant sees it across all its repos."

**Check-before-building (CLAUDE.md non-negotiable #2) changed the answer.** The
first draft of this ADR proposed *building* a new SQLite-backed
`StorageServiceAdapter`. Searching for existing prior art before building
surfaced that the cross-repo home already exists as a documented convention —
so the correct move is **reuse**, not build:

- **The central Tenant-namespaced home is already specified.**
  `plugins/sulis/scripts/_tenant_emission.py` (module docstring, lines 1–25)
  documents it verbatim: *"The marketplace's local entity store is namespaced
  by Tenant ID (`~/.sulis/instances/{tenant_id}/...`), which a follow-up slice
  will wire after this emitter is live."* **This change is that follow-up
  slice.** The cross-repo namespace works because the Tenant ULID is a
  *deterministic* Crockford-base32 ULID derived from the sha256 of the Tenant
  name — *"Same name everywhere produces the same Tenant ID — this is what
  makes the cross-repo namespace work (every repo with `.sulis/tenant.yaml`
  naming the same tenant resolves to one identity)."* The single cross-repo
  Tenant boundary is therefore already a real, addressable path on disk; it
  does not need inventing.

- **The existing file adapter already writes there with no new code.**
  `LocalFileEntityAdapter` (`_entity_adapter_local.py`) writes
  `{base_dir}/{domain}/{entity_type}/{ulid}.jsonld` with `base_dir` as a
  **constructor argument** — fully relocatable, the caller is not expected to
  pre-create the subtree. Pointing that `base_dir` at
  `~/.sulis/instances/{tenant_id}/` **IS** the cross-repo Platform home. No new
  backend, no new adapter class, no new query adapter — the same write adapter
  and the same `_brain_query` flat-file walk, relocated.

- **The hexagonal seam already anticipates a future swap.** The
  `LocalFileEntityAdapter` docstring names a future `StorageServiceAdapter` that
  *"implements the same `EntityRepository` port; nothing else changes — the
  schemas, the validation, the call sites, all stay identical."* That swap is
  real — but it belongs to a **later change**, not this one, and only when query
  scale demands it.

The question with a real consequence is therefore *not* "what backend do we
build" — it is: **where does the central home live, and what is deferred?**

## Decision

**The cross-repo Platform home is the EXISTING `LocalFileEntityAdapter` pointed
at the EXISTING `~/.sulis/instances/{tenant_id}/` Tenant-namespaced convention.
Reuse, not build. SQLite (#30) is explicitly deferred to a later change as a
drop-in adapter behind the same `EntityRepository` port.**

This change *wires the follow-up slice* the `_tenant_emission.py` docstring
already promised: it points the living-entity emitters' `base_dir` at the
central Tenant-namespaced home and proves a cross-repo Tenant read against it.
Nothing above the port changes; nothing new is built at the storage layer.

### Where the store lives

| Concern | Decision |
|---|---|
| Backend | The existing flat-file `LocalFileEntityAdapter` — no new backend. |
| Location | The existing convention `~/.sulis/instances/{tenant_id}/` (one subtree per Tenant — the cross-repo boundary is the Tenant, established by the deterministic Tenant ULID). |
| Tenant ULID | The existing deterministic sha256-of-name derivation in `_tenant_emission.py` — same name → same ID → one cross-repo identity. Reused as-is. |
| Schema / validation | Unchanged: the same vendored compiled schema (`plugins/sulis/brain/compiled/{domain}/{entity_type}.schema.json`), the same reject-on-invalid `save`. |
| Read path | The existing `_brain_query.iter_entities` flat-file walk, now able to walk the central Tenant home; the cross-repo Tenant read is a walk of one Tenant's subtree across the entities written there. |

The repo-local `.brain/instances` tree and the central
`~/.sulis/instances/{tenant_id}/` home are the **same** `LocalFileEntityAdapter`
behind the **same** `EntityRepository` port, distinguished only by which
`base_dir` the caller passes. They are siblings selected by configuration, not
two adapters.

### What is deferred (and why the later swap stays cheap)

SQLite (#30) is **deferred to a later change**. When query scale demands a real
backend — concurrent multi-writer access, indexed cross-repo Tenant reads that
the flat-file walk can no longer serve at acceptable latency — a
`StorageServiceAdapter` that `implements EntityRepository` (an EXPAND-Create
adapter, exactly as the `_entity_adapter_local.py` docstring anticipates) is a
**drop-in swap behind the same port**. The swap stays cheap precisely because
the port is already the contract: `save` / `find_by_id` / `validate` and the
`_brain_query` read-seam signatures do not move, so no call site above the port
changes when the backend changes. This is the SPEC LADDER's "the flat-file
query swaps for a real backend there" — *there*, not here.

## Options Considered

- **Build a new SQLite `StorageServiceAdapter` now (rejected — check-before-
  building).** This was the first draft. Searching for prior art surfaced an
  already-documented central Tenant home (`_tenant_emission.py`) and an
  already-relocatable file adapter (`base_dir` constructor arg) that together
  *are* the cross-repo home with zero new code. Building a SQLite backend now
  would add a second storage idiom, its own query adapter, and its own
  durability/transactionality surface before any query-scale need exists —
  the position that requires defence, not the default. Deferred to a later
  change behind the same port.

- **Extend the file adapter to walk multiple repos (rejected).** Would push
  cross-repo knowledge into the adapter and re-derive an index by walking N repo
  trees per query. Unnecessary: the central `~/.sulis/instances/{tenant_id}/`
  home is already a *single* Tenant-scoped subtree — pointing `base_dir` there
  gives one home to read, not N trees to merge.

- **Postgres / a hosted DB now (rejected — premature).** Heavier ops, a network
  dependency, a server to run, for a store whose only current reader is a local
  cross-repo Tenant walk. Deferred — and when a backend *is* needed, SQLite (the
  SPEC's #30) is the boring convention ahead of Postgres.

## Consequences

- **No new module.** No `_entity_adapter_sqlite.py`, no SQLite query adapter, no
  `entities` table, no WAL/transaction surface in this change. The store adapter
  and SQLite query adapter that earlier drafts listed are **removed** from this
  change's scope.
- **The addressable work is relocation + a cross-repo read proof.** Point the
  living-entity emit `base_dir` at `~/.sulis/instances/{tenant_id}/` (resolved
  from the deterministic Tenant ULID), and prove a cross-repo Tenant read: every
  current (open-window) Product/Opportunity for one Tenant, read from the central
  home, across repos.
- **Proof (this is build-order piece 5):** a **central-home read/write test
  against the existing file adapter** — write living-entity versions to a temp
  `~/.sulis/instances/{tenant_id}/`-shaped base_dir via `LocalFileEntityAdapter`,
  read them back cross-repo for one Tenant via the existing `_brain_query` walk.
  No new-adapter contract test (there is no new adapter); the existing port
  contract test already covers `LocalFileEntityAdapter`.
- **Deferred (later change), not lost:** the SQLite backend (#30) as a drop-in
  `StorageServiceAdapter` behind the same `EntityRepository` port, taken up when
  query scale demands it. The deferral is cheap because the port is the contract
  and no call site moves on the swap.
- Build-order dependency: piece 5 depends on the evolve helper (ADR-003, piece
  3) — the central home stores the *windows* the evolve cycle produces, so the
  window contract must exist first.
- No call site above the port moves. Emitters that called `repo.save(...)` /
  `evolve_entity(repo=...)` work unchanged when `repo` is the file adapter
  pointed at the central home — and will work unchanged again when a SQLite
  adapter replaces it later. The convergence the seam docstrings promised holds
  in both directions.

> **Wiring status (reconciliation note, added post-Stage-4 review).** For
> **Product** and **Opportunity**, the central-home `base_dir` is
> *wired-but-not-yet-defaulted*: the relocatable seam is proven end-to-end by
> `test_central_tenant_home.py` (write to a central-home-shaped `base_dir`, read
> back cross-repo), but the production emit CLIs (`sulis-emit-product`,
> `sulis-emit-opportunity`) still **default `base_dir` to the repo-local
> `.brain/instances`**, and nothing in the lifecycle invokes them yet — so in
> production today the central home is reached **only by the minter** (the
> **Project** entity, via `_discovery/minter`'s canonical brain-store save,
> ADR-006). Flipping the Product/Opportunity CLI default to the central home is
> a follow-on slice; this ADR establishes the seam and the cross-repo read
> proof, not the CLI default. The Decision wording above ("points the
> living-entity emitters' `base_dir` at the central home") describes the seam
> that is now reusable, not a defaulted production code path for
> Product/Opportunity.
