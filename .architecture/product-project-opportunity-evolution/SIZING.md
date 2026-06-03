# SIZING — product-project-opportunity-evolution

> Computed by `/sulis:draft-architecture` (SEA blueprint pass) 2026-06-03.
> Source: `.changes/feat-product-project-opportunity-evolution.SPEC.md` +
> recon-verified code state. Subsequent SEA skills read this rather than recomputing.

## Tier: **L** (confirmed at the M/L boundary)

| Axis | Value | Tier signal |
|---|---|---|
| sFPC (simplified function point count) | **17** | M (11–30) |
| ASR (architecturally-significant requirements) | **13** | M (6–15) |
| Distinct subsystems touched | **4** (PROV grammar · evolve mechanism · Platform store · discovery/mint reconcile) | pushes to L |

Both numeric axes land mid-M. Tier is taken to **L** because the change spans four
distinct concerns with a hard breaking-migration dependency chain between them, and
touches the brain ontology grammar (a cross-cutting contract), not one component.
This is the "take the higher tier when the change crosses multiple bounded contexts"
rule from `right-sizing.md`.

### sFPC breakdown

| Element | Count | Items |
|---|---|---|
| ILF (living/persistent entity types) | 6 | Product, Opportunity, Project, LifecycleRun, Step (referenced), PROV-Activity binding |
| EIF (outbound integration) | 0 | none new — the cross-repo home REUSES the existing file adapter pointed at the central `~/.sulis/instances/{tenant_id}/` Tenant home; the SQLite backend (#30) is deferred to a later change (ADR-005) |
| EI (mutating ops) | 7 | evolve-close-window, evolve-open-window, PROV-edge-write, LifecycleRun v2 emit, v1→v2 instance migration, Project mint reconcile, central-Tenant-home write (existing adapter, relocated `base_dir`) |
| EO (deriving ops) | 2 | as-of-time window query, cross-repo Tenant read |
| EQ (retrieving ops) | 2 | read-current-version, find latest-open-window |
| **sFPC** | **17** | |

### ASR breakdown

| Class | Count | Items |
|---|---|---|
| NFR-derived | 7 | lockstep migration atomicity (no half-migrated state), graceful degradation preserved, bitemporal window invariants, W3C PROV-O grammar conformance, cross-repo read consistency, central-home write durability (existing file adapter atomic-write), deterministic ULID stability across migration |
| Integration | 0 | none new — the cross-repo home REUSES the existing file adapter at the central Tenant home; SQLite backend deferred to a later change (ADR-005) |
| MUC/policy | 3 | append-only protection for event entities, evolve-not-applied-to-events guard, path-safety preserved on Project reconcile |
| Hard data constraint | 3 | BREAKING LifecycleRun schema migration, deterministic ULID derivation, valid-window non-overlap invariant |
| **ASR** | **13** | |

## Per-pillar addressable scope

The codebase is **already hexagonal**. This materially shrinks the addressable scope —
several pillar concerns are *covered* and only need a one-line reference, not a section.

| Pillar | Coverage | Why | Addressable work |
|---|---|---|---|
| **Form** | Partial (high existing coverage) | `EntityRepository` port + `LocalFileEntityAdapter` (relocatable `base_dir`) already exist; the cross-repo Tenant home convention (`~/.sulis/instances/{tenant_id}/`) is already documented in `_tenant_emission.py`. The read seam (`_brain_query.iter_entities`) is also already a port-shaped function. | New: the evolve helper's place in the layering; the PROV grammar's schema shape; wiring the emit `base_dir` to the central Tenant home (reuse, no new adapter); the Project ownership-boundary move. |
| **Armor** | Partial | Graceful-degradation discipline (`_brain_emit_helper`), atomic-write + path-safety (`minter.py`), reject-on-invalid validation all exist and are reused. | New: migration atomicity (no half-migrated state), evolve window-invariant enforcement, central-home write durability (existing atomic-write), append-only guard for event entities. |
| **Proof** | Partial | Contract-test discipline exists (the port has tests; the file adapter is covered). Drift-detector parity infrastructure exists. | New: central-home read/write test (existing file adapter at the central Tenant home) + cross-repo Tenant read; evolve close/open-window characterisation test; PROV-emission test; the v1→v2 instance-migration test. |

## Circuit breakers

None triggered at design time. The TDD references the existing port/adapter/query
seams rather than restating them (the hexagonal architecture is not re-derived).

## Notes

- No `.context/{project}/INDEX.md` exists for this worktree — Respect-Don't-Restate
  applies via the in-repo design docs and the existing `.architecture/*` siblings
  (discover-project, release-train-as-entities) instead, which are the authoritative
  prior art for the Path-A canonical-as-spec discipline this change continues.
- The change is large by founder decision (full arc, not a carved slice). Size is
  absorbed by decomposition (`/sulis:plan-work`, next pass), not by tier inflation.
