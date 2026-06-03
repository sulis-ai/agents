---
id: ADR-006
title: Project home reconciliation — brain store is canonical; `.sulis/projects/<slug>.jsonld` becomes a human-facing mirror; Project provenance is NOT applicable (prov:Plan)
status: accepted
date: 2026-06-03
revised: 2026-06-03 — ADDED the explicit "Project provenance: NOT applicable" decision (Project is prov:Plan; wasGeneratedBy is a type violation; lineage = bitemporal + supersedes; run→Project link deferred to LifecycleRun.for_project ON THE RUN). Home-reconciliation decision unchanged.
deciders: [iain]
---

## Context

Scope item 6 + the recon-verified inconsistency: `/sulis:discover-project` mints
a Project entity to `.sulis/projects/<slug>.jsonld` via
`_discovery/minter.py:write_project_entity`, **not** through the
`EntityRepository` port into the brain store. Every other living entity
(Product, Opportunity, LifecycleRun, …) goes through the port; Project is the
one that writes its own divergent path. Recon: *"Project is minted to
`.sulis/projects/<slug>.jsonld` by `/sulis:discover-project` (minter.py:93), NOT
`.brain/instances` — the real inconsistency to reconcile."*

This matters now because this change turns Project into a **living** entity
(scope item 4 — Project evolves like Product/Opportunity). A living entity needs
its history-bearing windows in the same store the evolve helper (ADR-003) and
the query seam read — i.e. behind the port. A Project stranded in
`.sulis/projects/` cannot be evolved by `evolve_entity(repo=...)`, cannot be
read by the cross-repo Tenant query (ADR-005), and is invisible to the
bitemporal as-of-time read.

Recon-verified facts that constrain the answer:

- **`minter.py` carries hard-won discipline** the reconciliation MUST preserve:
  atomic write (`_atomic_write` — tmp + `os.fsync` + `os.replace`), path-safety
  (`_assert_path_safety` — `.resolve()` + `is_relative_to(<repo_root>/.sulis/projects)`
  blocking symlink/`..` traversal), pre-existence refusal (`_assert_not_exists`,
  MUC-003), stale-tmp sweep (MUC-002), SIGINT handler. These are not incidental;
  they are the Mint-phase contract.
- **Project's multi-repo anchor role is load-bearing and must survive**:
  `belongs_to_product_ref` (a plain string ref — ontology v0.7 resolution is a
  NON-GOAL), `depends_on` / `consumed_by` (the inter-repo dependency edges),
  `source` (repo + path), `belongs_to_tenant`. The Project schema's own
  description names the monorepo / multi-repo / shared-library scenarios these
  fields enable.
- **`.sulis/projects/<slug>.jsonld` is the human-facing, git-tracked artifact**
  a consumer sees in their repo. Removing it entirely would hide the Project
  from the human who minted it and break the `/sulis:release-train` binding that
  resolves the Project by source path.

The question with a real consequence: *how does Project land in the canonical
brain home (so it can be a living, queryable, cross-repo entity) without losing
the minter's safety discipline or the human-facing repo artifact?*

## Decision

**The brain store (behind the `EntityRepository` port) becomes the canonical
home for the Project entity. `.sulis/projects/<slug>.jsonld` is retained as a
human-readable mirror — written from the same validated entity, in the same
atomic, path-safe step, never as a second source of truth.**

So the Mint phase writes **once, to the canonical store, then mirrors**:

```
discover-project Mint
        │
        ▼
  compose Project entity (confirmed values + multi-repo anchor fields)
        │
        ▼
  repo.save("project", entity)          ◀── CANONICAL: the EntityRepository port
        │  (validate → persist; reject-on-invalid; same discipline as every
        │   other entity; the configured adapter — file or SQLite per ADR-005)
        ▼
  write_project_mirror(.sulis/projects/<slug>.jsonld, entity)   ◀── human mirror
           (atomic + path-safe, derived from the SAME entity dict)
```

### `discover-project` / `minter.py` changes

`write_project_entity(target_path, entity, ...)` is refactored so its two
responsibilities separate cleanly:

1. **Canonical write** — a new call through the `EntityRepository` port:
   `repo.save("project", entity)`. The port's adapter (file adapter for repo-
   local; SQLite `StorageServiceAdapter` for the Tenant store, ADR-005) decides
   *where* the canonical bytes land. Validation (reject-on-invalid) now happens
   at the port, against the vendored compiled `project.schema.json` — the same
   schema source every other entity uses. This is the reconciliation: Project
   stops being special.
2. **Human mirror** — the existing atomic-write + path-safety machinery is
   **kept**, repurposed as `write_project_mirror(...)`. It still does
   `_assert_path_safety` (the `.sulis/projects/` boundary), `_atomic_write`
   (tmp + fsync + `os.replace`), `_assert_not_exists` (MUC-003), the stale-tmp
   sweep, and the SIGINT handler — verbatim discipline, now writing the *mirror*
   rather than the *canonical*. No safety code is deleted; it moves to guard the
   mirror.

The ordering is **canonical-first, mirror-second**: if the canonical port write
fails validation, no mirror is written (and the founder sees the plain-English
schema error) — the mirror can never show a Project the store rejected. If the
mirror write fails after a successful canonical save, that is a best-effort
degradation (logged, host operation continues) consistent with the brain's
graceful-degradation discipline — the canonical truth is already safe.

### Multi-repo anchor role preserved (NON-GOAL respected)

The reconciliation moves *where* the bytes live; it changes **nothing** about
the Project's shape:

- `belongs_to_product_ref` **stays a plain string** ref. Ontology v0.7 cross-
  artifact resolution is an explicit NON-GOAL (ARCH.yaml + SPEC). The
  reconciliation does not resolve it, validate it as a live ref, or touch it.
- `depends_on` / `consumed_by` inter-repo edges are carried verbatim into the
  canonical entity. They are the multi-repo orchestration signal; they ride
  through `repo.save` unchanged.
- `source`, `belongs_to_tenant`, `release_workflow_ref` (including the valid
  cross-tenant reference to the marketplace's release-train Workflow) — all
  unchanged. The cross-tenant-refs-allowed semantics from discover-project's
  Verify phase stay as they are.

### Project becomes living (the evolve tie-in)

Because Project now goes through the port, applying evolve to it (scope item 4)
is the *same* `evolve_entity(repo=..., entity_type="project", ...)` call used
for Product and Opportunity — **for the bitemporal window mechanics only**. A
re-discovery (`--update` — the per-field diff flow) becomes an **evolve**: close
the prior Project window, open a new one with the changed fields. The mirror is
re-rendered from the new current window.

> **Correction.** An earlier draft of this subsection said the Project evolve
> would "write `was_generated_by`". **It does not** — Project carries no
> provenance edge (next section). For Project, `evolve_entity` is called with
> `generated_by=None`: it closes the prior window and opens a new one with the
> bitemporal fields, and writes **no** `wasGeneratedBy` triple. The allowlist in
> the evolve helper (ADR-003) admits Project as a *living* entity (it gets
> windows); the *provenance* write is conditional on the caller supplying a
> `generated_by`, which the Project emitter never does.

### Project provenance: NOT applicable (Project is `prov:Plan`)

**Project carries no `wasGeneratedBy` provenance edge — not now, not at v0.7,
not ever. This is a settled brain-governance verdict, recorded here so the
decomposition does not re-introduce it.**

The reasoning, cited against the canonical:

1. **`wasGeneratedBy` is a type violation on a Plan.** Project is
   `is_a: prov:Plan` (`foundation.entities.jsonld:251`). In PROV-O,
   `prov:wasGeneratedBy` is an **Entity → Activity** edge — it asserts "this
   *produced thing* came out of that activity." A `prov:Plan` is a *recipe* /
   guide, not a produced thing: an Activity **uses** a Plan (via
   `prov:Association`), it never **generates** one. The obstacle is the semantics
   of the edge against the type, not a grammar or cross-artifact limitation, so
   no variant (string-ref-now, wait-for-v0.7, foundation-Activity-target)
   rescues it. (Product and Opportunity are both `prov:Entity` — the edge is
   clean on them; see ADR-002.)

2. **Project's lineage is ALREADY complete without a prov edge.** Project loses
   nothing by carrying no `wasGeneratedBy`:
   - **Bitemporal window** — `valid_from` / `valid_to` (inherited since v0.5.1):
     the *when-was-this-version-true* axis is already there, and this change
     turns it on for Project via the evolve helper.
   - **State enum** — Project's `state` already records lifecycle position.
   - **Supersedes chain** — Project's existing `deprecated_for → project (0..1)`
     edge (`foundation.entities.jsonld:251`) already threads version-to-version
     succession.

   Run-provenance (*which Activity produced this version*) is simply **not
   applicable to a Plan** — a recipe is authored, not generated.

3. **The run→Project link lives ON THE RUN, never on Project.** The legitimate
   "which runs touched this Project?" question is the separately-deferred
   **`LifecycleRun.for_project`** edge (L13 n=2, v0.7+), which lives **on the
   LifecycleRun**, pointing *at* the Project. It requires **no Project edit, now
   or later**, and is **out of scope** for this change. (And "which run shipped
   which version?" is already answered on **Release**, a `prov:Entity` that
   already carries `wasGeneratedBy → lifecyclerun`, `_step_name: "release"`.)

**Net for the decomposition:** Project's "apply evolve" WP covers **bitemporal
windows + supersedes only** — close-window / open-window with `generated_by=None`.
Project is **excluded from the provenance-edge WP** (which touches Product +
Opportunity only). No Project schema edit, no Project `wasGeneratedBy` write, no
v0.7 watchlist item.

## Options Considered

- **Keep Project in `.sulis/projects/` only; teach evolve/query to read that
  path (rejected).** Re-introduces the special case for every consumer (evolve,
  the cross-repo Tenant query, as-of-time read) instead of removing it once at
  the Mint seam. The inconsistency the SPEC names would persist, just pushed
  downstream into more readers.
- **Delete `.sulis/projects/<slug>.jsonld` entirely; brain store is the only
  home (rejected).** Hides the Project from the human who minted it (no git-
  tracked artifact in their repo) and breaks `/sulis:release-train`'s source-path
  binding to it. The mirror is cheap and serves a real human/tooling reader; the
  canonical/mirror split is the boring, correct shape.
- **Mirror as a separate later step / separate command (rejected).** Splits the
  atomic Mint into two operations with a window where canonical and mirror
  disagree. Writing both in the one Mint step (canonical-first, mirror-second,
  derived from the same entity dict) keeps them consistent by construction.
- **Two sources of truth, reconciled by a sync job (rejected — band-aid).** A
  sync job between `.sulis/projects/` and the brain store is exactly the
  half-consistent state the SPEC's reconciliation forbids. One canonical writer
  (the port), one derived mirror.
- **Give Project a `wasGeneratedBy` edge so its versions trace to a run
  (rejected — PROV-O type violation).** Project is `prov:Plan`; `wasGeneratedBy`
  is an Entity→Activity edge. The brain-governance review settled this: Project's
  lineage is complete via bitemporal + `state` + `deprecated_for`, and the
  run↔Project association is the deferred `LifecycleRun.for_project` edge *on the
  run*. Treating Project like Product/Opportunity for provenance would put an
  Entity→Activity edge on a recipe. See the "Project provenance: NOT applicable"
  section above.

## Consequences

- This is build-order piece 6 — it depends on the evolve mechanism (piece 3,
  ADR-003) and the store (piece 5, ADR-005): Project lands in the *reconciled*
  home, which is whichever adapter the port is configured with.
- `_discovery/minter.py` is refactored: `write_project_entity` gains a canonical
  `repo.save` path; the existing atomic/path-safe machinery is preserved as
  `write_project_mirror`. Because this is a structural change to an existing
  module (extracting + re-pointing functions), it carries a **characterisation
  test first** (REORGANISE MUST, EP-07): capture minter's current atomic-write +
  path-safety + MUC-003 + stale-tmp behaviour, confirm green, refactor, confirm
  still green — then add the canonical-write behaviour.
- The `discover-project` SKILL Mint-phase prose updates: Mint now says "write to
  the brain store (canonical) and mirror to `.sulis/projects/<slug>.jsonld`."
  The drift-detector annotations (`canonical:step:…`) stay; the canonical
  Workflow's Mint Step description is updated to match (Path-A discipline — skill
  conforms to canonical).
- A migration consideration for already-minted Projects: any existing
  `.sulis/projects/*.jsonld` in a consuming repo is back-filled into the
  canonical store on next discover/evolve touch (the same lazy-for-consumers /
  eager-for-our-own posture ADR-004 takes for LifecycleRun instances). The
  marketplace's own Projects (authored in `release-train/projects.jsonld` per
  release-train-as-entities ADR-004) are already canonical and are unaffected —
  this ADR reconciles the *consumer-minted* path only.
