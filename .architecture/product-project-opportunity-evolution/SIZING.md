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
| EI (mutating ops) | 7 | evolve-close-window, evolve-open-window, conditional wasGeneratedBy prov_constraints-edge-write (Product/Opportunity only), LifecycleRun v2.1.0 re-vendor+emit (one atomic op), v1→v2 instance migration, Project mint reconcile (windows only, no prov), central-Tenant-home write (existing adapter, relocated `base_dir`) |
| EO (deriving ops) | 2 | as-of-time window query, cross-repo Tenant read |
| EQ (retrieving ops) | 2 | read-current-version, find latest-open-window |
| **sFPC** | **17** | |

### ASR breakdown

| Class | Count | Items |
|---|---|---|
| NFR-derived | 7 | lockstep re-vendor+emitter atomicity (no half-migrated state — schema + emitter in one WP), graceful degradation preserved, bitemporal window invariants, PROV-O `prov_constraints` convention conformance (reuse not new grammar; wasGeneratedBy on prov:Entity types only), cross-repo read consistency, central-home write durability (existing file adapter atomic-write), deterministic ULID stability across migration |
| Integration | 0 | none new — the cross-repo home REUSES the existing file adapter at the central Tenant home; SQLite backend deferred to a later change (ADR-005) |
| MUC/policy | 3 | append-only protection for event entities, evolve-not-applied-to-events guard, path-safety preserved on Project reconcile |
| Hard data constraint | 3 | BREAKING LifecycleRun schema migration (surgical re-vendor of canonical v2.1.0 — step_name→step), deterministic ULID derivation, valid-window non-overlap invariant |
| **ASR** | **13** | |

## Per-pillar addressable scope

The codebase is **already hexagonal**. This materially shrinks the addressable scope —
several pillar concerns are *covered* and only need a one-line reference, not a section.

| Pillar | Coverage | Why | Addressable work |
|---|---|---|---|
| **Form** | Partial (high existing coverage) | `EntityRepository` port + `LocalFileEntityAdapter` (relocatable `base_dir`) already exist; the cross-repo Tenant home convention (`~/.sulis/instances/{tenant_id}/`) is already documented in `_tenant_emission.py`. The read seam (`_brain_query.iter_entities`) is also already a port-shaped function. **PROV is NOT greenfield** — `wasGeneratedBy`/`used` already in the PD `_predicate_map`, the edge already wired on 5 entities as `prov_constraints`. | New: the evolve helper's place in the layering; re-vendoring the already-minted canonical LifecycleRun v2.1.0; consuming the upstream-minted `wasGeneratedBy` edge on Product/Opportunity (reuse of the `prov_constraints` convention, no new grammar authored here); wiring the emit `base_dir` to the central Tenant home (reuse, no new adapter); the Project ownership-boundary move. |
| **Armor** | Partial | Graceful-degradation discipline (`_brain_emit_helper`), atomic-write + path-safety (`minter.py`), reject-on-invalid validation all exist and are reused. | New: migration atomicity (no half-migrated state), evolve window-invariant enforcement, central-home write durability (existing atomic-write), append-only guard for event entities. |
| **Proof** | Partial | Contract-test discipline exists (the port has tests; the file adapter is covered). Drift-detector parity infrastructure exists. | New: central-home read/write test (existing file adapter at the central Tenant home) + cross-repo Tenant read; evolve close/open-window characterisation test; `wasGeneratedBy` prov-edge-emission test (Product/Opportunity only; a paired assertion that Project's evolve writes NO prov edge); the re-vendor + v1→v2 instance-migration test. |

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
- **2026-06-03 rework against brain-governance review.** Tier (L), sFPC (17), and
  ASR (13) are **unchanged** — the corrections re-shape *how* four ops are built,
  not *how many* there are. Net WP count moved 15 → 14 (the two schema-authoring
  WPs collapsed into one atomic re-vendor+emitter WP; the prov-edge WP narrowed
  to Product+Opportunity and gained an explicit upstream-mint gate). The
  provenance work is now convention-reuse (`prov_constraints`) rather than
  greenfield grammar, and the LifecycleRun migration is a surgical re-vendor of
  the already-minted canonical v2.1.0 rather than an authored bump. No tier
  change results; the corrections reduce risk (drift-from-canonical eliminated),
  they do not change the functional surface.
