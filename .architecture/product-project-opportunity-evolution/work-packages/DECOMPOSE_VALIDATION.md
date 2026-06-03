# Decompose Validation Report — product-project-opportunity-evolution

**Date:** 2026-06-03 (re-validated after brain-governance rework)
**Rubric:** decompose-validation-rubric (8 phases + P-VER + P-PLAT)
**WP set:** 13 WPs (re-cut from 15)
**Source TDD:** `../TDD.md`
**SIZING:** tier L (sFPC 17 / ASR 13 — unchanged by the rework)
**Change:** CH-01KT61 (`feat`, `founder_facing: false`)

## At a glance

The re-cut decomposition is mechanically valid. All 13 WPs carry the required
sections (Context, Contract, Red-Green-Blue DoD, Sequence, Token cost,
dependsOn/blocks, ADRs, TDD §, `verification:`). The dependency graph is a clean
DAG with a single root (WP-001) and four terminals (WP-005, WP-006, WP-007,
WP-015). The critical path is 8 packages; peak safe parallelism is 3. One WP
(WP-008) is legitimately `blocked` on an **external upstream artifact** (the
`wasGeneratedBy` mint) — this is a real, declared dependency, not a broken edge.
Every cross-WP identifier is cited to an authoritative upstream source. The two
REORGANISE-Refactor WPs each carry a `characterisation_test:` field and
`dependsOn` a REINFORCE-Test WP. No Wrap WPs.

## Verdict: **PASS**

All MUSTs pass. No SHOULD failures. The rework corrected four mechanics against
the brain canonical (recorded in §What the rework corrected) and collapsed three
WPs into one atomic re-vendor+emitter WP; the resulting graph re-validates clean.

---

## What the rework corrected (vs the prior 15-WP PASS)

| # | Correction | Validation impact |
|---|---|---|
| C1 | **LifecycleRun v2.1.0 is re-vendored from already-minted canonical, not authored** (DR-009 + DR-013). The old "author schema" WP-002 + the two emitter WPs (003, 004) collapse into **one atomic WP-002** (README + ADR-004 lockstep mandate). | WP count 15→13. P2 atomicity re-checked: the merged WP is one removal (the `step_name`→`step` swap), `composite_of` records the three absorbed moves. P6 peer-collision re-checked: `_brain_emit_helper.py` is now edited inside WP-002, removing one of the two prior collision pairs. |
| C2 | **`step_label` + `used`-on-LifecycleRun DROPPED** (not in canonical v2.1.0; DR-013 rejected payload-on-run). Per-run specificity → the existing `run_id`. | P8 identifier set reduced (no `step_label` field). P-VER nodeids updated (WP-002 now asserts `test_no_step_label_field` / `test_no_used_field`). |
| C3 | **PROV edge reuses the `prov_constraints` convention** (camelCase `wasGeneratedBy`, range, card), NOT a snake_case `was_generated_by` wire field. Applies to **Product + Opportunity only**; **Project dropped** (prov:Plan type violation). The grammar change is routed **upstream through the mint**. | WP-008 reshaped + narrowed; gains an **upstream-mint gate** (status `blocked`). P4 re-checked: the gate is an external dependency, declared in `upstream_dependsOn`, not a missing in-graph edge. |
| C4 | **Project provenance is NOT applicable** — Project gets bitemporal windows + supersedes via evolve, but **no `wasGeneratedBy`**. The evolve helper's prov-write is now **conditional** (`generated_by is not None`). | P-VER re-checked: WP-009 adds `test_project_evolve_writes_NO_prov_edge`; WP-012 adds `test_project_emit_evolves_WITHOUT_prov`. The two guards (living-allowlist vs prov-Entity) are orthogonal — verified per-WP. |

---

## Summary

| Metric | Count |
|---|---|
| WPs validated | 13 |
| Total checks | 54 (across 8 phases + P-VER + P-PLAT) |
| PASS | 54 |
| FAIL (MUST) | 0 |
| FAIL-WITH-RATIONALE (SHOULD) | 0 |
| Defects repaired during validation | 1 (WP-002 `blocks` back-edge — added WP-008 + WP-013 to restore bidirectional consistency after the merge) |

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| 1 Inventory completeness | 13/13 | 0 | Every WP has all required sections + `verification:` |
| 2 Atomicity | 13/13 | 0 | The 3→1 merge is one removal (`composite_of`); touch surfaces ≤ ceiling |
| 3 Module naming + clean code | 13/13 | 0 | All slugs kebab-case + descriptive; no jargon prefixes |
| 4 Dependency graph correctness | 13/13 | 0 | DAG acyclic; depth 8; 1 back-edge repair after the merge; WP-008 external gate declared |
| 5 Performance + non-functional reqs | 13/13 | 0 | No external-API/handler WPs; in-process backend work; bounds N/A |
| 6 Peer-collision risk | 13/13 | 0 | One prior collision pair removed by the merge; one remaining serialised (WP-013) |
| 7 ServiceSpec compliance | n/a | n/a | No external service surface; Python package boundary only |
| **8 Cross-WP identifier canonicalisation** | **13/13** | **0** | **Every cross-WP identifier cites an authoritative upstream source; `step_label` removed** |
| **P-VER Verification concretion** | **13/13** | **0** | **12 Shape-1 concrete; WP-008 is Shape-1 concrete but external-gated (the gate is an upstream-artifact prerequisite, not a deferred test)** |
| **P-PLAT Platform fit** | **3/3** | **0** | **Backend-only; no cross-kind seam; founder_facing:false honoured** |

---

## Repair applied during validation

| # | Class | Defect | Repair |
|---|---|---|---|
| R1 | Graph hygiene (post-merge) | After collapsing old WP-002/003/004 into the new WP-002, the new WP-002 `blocks` listed only `[WP-005, WP-006, WP-007]` but WP-008 and WP-013 now `dependsOn WP-002` (WP-008 for the re-vendored LifecycleRun ref shape; WP-013 for the `_brain_emit_helper.py` base_dir edit that follows WP-002's Step-resolution edit). | Added WP-008 + WP-013 to WP-002 `blocks`. Bidirectional `dependsOn`/`blocks` consistency restored; mechanical topological pass confirms acyclic (13 nodes sortable). |

After repair: every `A dependsOn B` has a matching `B blocks A`; DAG acyclic;
`wpx-index lint` returns `header: canonical` (exit 0).

---

## Blocking gaps (MUST failures)

None.

> **Note on WP-008's `blocked` status — this is NOT a gap.** WP-008 is blocked on
> a *declared external upstream artifact* (the `wasGeneratedBy` mint being
> accepted + recompiled + re-vendored), recorded in its `blocked_reason` +
> `upstream_dependsOn` frontmatter. A blocked-on-declared-upstream WP is a correct
> representation of a real prerequisite, not a graph defect. The pre-gate spine
> (WP-001, WP-002, WP-005, WP-006, WP-007) is fully landable while the mint is in
> review.

## Recommended improvements (SHOULD failures)

None.

---

## Detailed findings per check

### P1 — Inventory completeness (MUST)

| WP | Context | Contract | DoD R/G/B | Sequence | Token | Deps | ADRs | TDD § | verification: |
|---|---|---|---|---|---|---|---|---|---|
| WP-001 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-002 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-005 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-006 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-007 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-008 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ + upstream | ✓ | ✓ | ✓ |
| WP-009 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-010 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-011 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-012 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-013 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-014 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-015 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

INDEX.md lists all 13 WP files; carries `## Dependency Graph` (Mermaid),
`## Primitive Distribution`, `## Kind Distribution`, `## Wrap Audit`,
`## Upstream Dependency`, and `## Recommended Implementation Order`. Every WP
carries a `primitive:` from the 22-primitive catalogue. WP-002 carries
`composite_of` (the three absorbed moves). The two REORGANISE WPs (WP-012,
WP-015) and their characterisation-test partners (WP-011, WP-014) each carry the
`characterisation_test:` field.

**P1: PASS.**

### P2 — Atomicity (MUST)

| WP | Single responsibility | Production files touched | ` and ` conjunction? |
|---|---|---|---|
| WP-001 | Author 3 canonical Step instances (prov:Plan defs) | 1 | no |
| WP-002 | Re-vendor canonical lifecyclerun v2.1.0 + migrate emitter core — one atomic removal | 3 (vendored schema + 2 emitter modules) | "+" join, single removal (the breaking swap) |
| WP-005 | CLI `--step` (`--step-name` deprecated alias) | 1 | no |
| WP-006 | Build migration script + run on marketplace store | 1 created + 2 instances | no |
| WP-007 | Register lifecycle-steps in drift detector | 1 | no |
| WP-008 | Re-vendor the upstream-minted prov edge on Product + Opportunity | 2 (vendored compiled copies) | no |
| WP-009 | Build `_entity_evolve` (close/open window + guard + conditional PROV write) | 1 created | "+" join, single concept ("the evolve primitive") |
| WP-010 | Add `read_as_of` to `_brain_query` | 1 | no |
| WP-011 | Characterisation test pinning emit baseline | 1 created (test) | no |
| WP-012 | Refactor 3 emitters to call `evolve_entity` | 3 | no |
| WP-013 | Point base_dir at central home + cross-repo read | 2 | no |
| WP-014 | Characterisation test pinning minter safety | 1 created (test) | no |
| WP-015 | Refactor minter to canonical+mirror + update Mint prose | 2 | no |

**Touch-surface counts:** every WP ≤ 3 production files; well under the MUST ≤ 15
ceiling. WP-002's 3 files are the **lockstep-mandated** atomic set (the re-vendored
schema + the two emitter modules that must agree with it at the slice boundary —
splitting them re-opens the reject-on-invalid window ADR-004 forbids). WP-008's 2
files are the additive prov edge on two living schemas' vendored compiled copies —
a mutually-validating set.

**Title-conjunction scan:** WP-002 and WP-009 carry "+" tokens; per check 2.06 the
forbidden token is the literal word " and " joining two *separable* concepts.
WP-002 is one removal (the breaking `step_name`→`step` swap, mandated atomic);
WP-009 is one primitive (the window-invariant guarantee). No title contains
" and " as a separable conjunction.

**P2: PASS.**

### P3 — Module naming + clean code (MUST)

WP filename pattern `WP-NNN-{descriptive-slug}.md`: ✓ for all 13. Contract module
names are purpose names (`_entity_evolve`, `_lifecyclerun_emission`,
`_brain_emit_helper`, `_brain_query`, `migrate_lifecyclerun_v1_to_v2`,
`_discovery/minter`). No single-letter abbreviations (3.02 ✓); no jargon prefixes
(3.07 ✓); no `mgr`/`svc`/`auth_mgr` patterns (3.04 ✓); no standalone
`utils`/`helpers`/`common` (3.05 ✓). Test files follow `test_{subject}.py` under
`tests/unit/` or `tests/characterisation/`.

**P3: PASS.**

### P4 — Dependency graph correctness (MUST)

**DAG (after repair R1):**

```
WP-001 → WP-002, WP-006, WP-007                  (canonical Step defs the chain resolves)
WP-002 → WP-005, WP-006, WP-007, WP-008, WP-013  (re-vendored v2.1.0 schema + emitter core)
WP-008 → WP-009                                  (the wasGeneratedBy edge must exist before the writer)
WP-009 → WP-010, WP-011, WP-012, WP-013          (the windows the read/test/refactor/home consume)
WP-010 → WP-013                                  (shared-file serialisation, _brain_query.py)
WP-011 → WP-012                                  (characterisation baseline before refactor — EP-07)
WP-012 → WP-014
WP-013 → WP-014                                  (piece 3+4+5 join)
WP-014 → WP-015                                  (characterisation baseline before refactor — EP-07)
```

- **4.01 No cycles** ✓ (topologically sortable; 13 nodes; verified mechanically)
- **4.02 Every dependsOn target exists** ✓ (all 13 IDs resolve)
- **4.03 No WP > 5 direct deps** ✓ (max is 3: WP-013 `[WP-002,WP-009,WP-010]`)
- **4.04 Depth ≤ 8** ✓ (longest chain depth 8: WP-001 → WP-002 → WP-008 → WP-009 → WP-011 → WP-012 → WP-014 → WP-015)
- **4.05 No orphans** ✓ (WP-001 root blocks 3 WPs; every node has ≥1 edge)
- **4.06 ≥ 1 parallel batch** ✓ (wave 3 carries WP-005 + WP-006 + WP-007)
- **4.07 Topological order valid** ✓ (INDEX `## Recommended Implementation Order` respects all `dependsOn`)
- **4.08 Cross-kind seam contract WP** — **N/A.** Kind set {contract, backend}; frontend + async absent. The 3 `contract` WPs (WP-001, WP-002, WP-008) are the canonical-grammar head; every backend WP `dependsOn` a contract WP directly or transitively.
- **4.09 No direct cross-kind edge** ✓ (no frontend/async kinds exist to cross)
- **4.10 External/upstream dependency is declared, not a dangling edge** ✓ — WP-008's `upstream_dependsOn` (the mint) is recorded in frontmatter with `blocked_reason`; it is a prerequisite on an artifact outside this WP graph, correctly represented as `status: blocked` rather than a phantom in-graph node.

**Bidirectional `dependsOn`/`blocks` consistency:** verified across all 13 WP
frontmatters after repair R1 — every `A dependsOn B` has a matching `B blocks A`
and vice versa (mechanical pass, 0 asymmetries).

**P4: PASS** (1 back-edge repair R1 after the 3→1 merge; see §Repair applied).

### P5 — Performance + non-functional requirements

No WP authors an external-API call, a network handler, or a user-request hot
path. All work is in-process Python against temp directories (the central Tenant
home is a temp dir served by the existing file adapter). The non-functional
guarantees that apply (migration atomicity, window invariants, central-home write
durability, append-only guard, conditional-prov correctness) are Armor concerns
enforced inside specific WPs and verified by their tests (WP-006 reject-on-invalid;
WP-009 window invariants + no-two-open-windows + Project-no-prov; WP-013 atomic-write
durability). These are correctness invariants, not latency/throughput bounds.

- **5.01 External-API/handler WPs declare performance** — N/A (no such WPs)
- **5.05 External-API WPs declare rate-limit + timeout** — N/A (no network seam)

**P5: PASS (no performance-bearing WPs; Armor invariants verified per-WP).**

### P6 — Peer-collision risk (MUST)

**Cross-WP file-touch scan:**

| File | Created by | Modified by | Same-wave overlap? |
|---|---|---|---|
| `plugins/sulis/instances/lifecycle-steps/steps.jsonld` | WP-001 (sole) | — | none |
| `…/compiled/product-development/lifecyclerun.schema.json` | — | WP-002 (sole, re-vendor) | none |
| `_lifecyclerun_emission.py` | — | WP-002 (sole) | none |
| `_brain_emit_helper.py` | — | WP-002, **WP-013** | **serialised: WP-013 dependsOn WP-002** |
| `sulis-emit-lifecyclerun` (CLI) | — | WP-005 (sole) | none |
| `migrate_lifecyclerun_v1_to_v2.py` | WP-006 (sole) | — | none |
| `.brain/instances/*/lifecyclerun/*.jsonld` | — | WP-006 (sole) | none |
| `check-canonical-drift.py` | — | WP-007 (sole) | none |
| `compiled/.../product.schema.json` + `opportunity.schema.json` | — | WP-008 (sole) | none |
| `_entity_evolve.py` | WP-009 (sole) | — | none |
| `_brain_query.py` | — | WP-010, **WP-013** | **serialised: WP-013 dependsOn WP-010** |
| `tests/characterisation/test_living_entity_emit_baseline.py` | WP-011 (sole) | — | none |
| `_product/_opportunity/project emit modules` | — | WP-012 (sole) | none |
| `tests/characterisation/test_minter_reconcile_baseline.py` | WP-014 (sole) | — | none |
| `_discovery/minter.py` + `discover-project/SKILL.md` | — | WP-015 (sole) | none |

**The 3→1 merge removed one prior collision pair:** old WP-004's `_brain_emit_helper.py`
edit is now inside WP-002, so the WP-004∥WP-013 collision no longer exists — it is
now a clean WP-002→WP-013 ordering. The remaining shared-file relationships
(`_brain_emit_helper.py`: WP-002∥WP-013; `_brain_query.py`: WP-010∥WP-013) are
both serialised by WP-013's `dependsOn [WP-002, WP-009, WP-010]`.

- **6.01 No two WPs Create the same file** ✓ (every Create sole-owned)
- **6.02 Same-level parallel Modify of same file** ✓ (the two overlaps serialised via WP-013 deps)
- **6.03 Shared scaffolding created by foundation WP** ✓ (all touched modules pre-exist; no new `__init__.py`)
- **6.04 Contract distinguishes create vs modify** ✓

**P6: PASS** (one prior collision pair eliminated by the merge; one remaining
serialised).

### P7 — ServiceSpec compliance

**Not applicable.** No external service surface — no HTTP/RPC endpoint, no queue
consumer, no inter-process contract. Deliverables are brain-grammar schemas (re-
vendored), Python emitters/helpers, a migration script, and skill prose, all
exercised at the Python package boundary. Recorded N/A per ARCH.yaml
(`founder_facing: false`; no service surface).

**P7: N/A (not triggered).**

### P8 — Cross-WP identifier canonicalisation (MUST)

| Identifier (class) | Appears in WPs | Authoritative upstream source | Result |
|---|---|---|---|
| 3 lifecycle Step ULIDs (`dna:step:01KT61X5ST0{1,2,3}…`) | WP-001 (authors), WP-002 (name→ULID map + resolution), WP-005 (CLI resolves), WP-006 (migration maps), WP-007 (drift parity) | **TDD §Canonical Identifiers — Canonical lifecycle Step instances** (grounded in ADR-001/ADR-004) | ✓ resolves |
| `step` schema field + v2.1.0 `$id` (canonical) | WP-002 (re-vendors), WP-006 (re-validates) | **canonical compiled v2.1.0** (`.specifications/business-dna/compiled/schemas/product-development/lifecyclerun.schema.json`) cited in ADR-004; TDD §Canonical Identifiers — Schema versions | ✓ resolves |
| name→Step-ULID resolution map | WP-002 (implements `_resolve_step`), WP-005 (CLI reuses), WP-006 (migration reuses) | **TDD §Canonical Identifiers — name→Step-ULID map** (ADR-004 §Step-ref resolution) | ✓ resolves |
| PROV edge (`wasGeneratedBy` → `dna:entity:lifecyclerun`, card `0..1`, `prov_constraints`) | WP-008 (re-vendors), WP-009 (writes the edge for prov:Entity types), WP-012 (wires the ref) | **ADR-002** + the **PD `_predicate_map`** (`prov:wasGeneratedBy` already present) + the mint-request (the upstream decision) | ✓ resolves |
| Central-home path `~/.sulis/instances/{tenant_id}/` + deterministic Tenant-ULID recipe | WP-013 (wires + reads) | **`plugins/sulis/scripts/_tenant_emission.py`** (docstring + `_deterministic_ulid_from` + seed `"tenant-name:"`), cited verbatim in WP-013 + **ADR-005** | ✓ resolves |

> **`step_label` is gone from the identifier set** (it was a fabricated field; the
> rework dropped it). The per-run specificity it carried is now the canonical
> `run_id` field, sourced from DR-013 / the re-vendored schema — not a cross-WP
> minted identifier.

**Per-check results:**

- **8.01 MUST — Every cross-WP shared identifier resolves to an authoritative upstream source.** 11 of 13 WPs carry a `# canonical-source:` annotation. The 2 without (WP-011, WP-014) are characterisation-test WPs pinning *existing* behaviour, referencing no cross-WP minted identifier — correct absence. ✓
- **8.02 MUST — No ULID-shape literal invented inline.** The only literal ULIDs are the 3 Step ULIDs in WP-001 + WP-002's resolution map, transcribed byte-exact from TDD §Canonical Identifiers. No inline minting. ✓
- **8.03 MUST — No `dna:*:*` in ≥2 WP Contracts without upstream source.** Every cross-referenced `dna:step:*` traces to TDD §Canonical Identifiers; the prov edge target `dna:entity:lifecyclerun` traces to the `_predicate_map` + ADR-002; the Tenant ULID traces to `_tenant_emission.py`. ✓
- **8.04 SHOULD — Each upstream source documents its minting recipe.** Step ULIDs: Crockford-base32, prefix `01KT61X5`, recipe in TDD §Canonical Identifiers. Tenant ULID: `_deterministic_ulid_from("tenant-name:{name}")` sha256-of-name, recipe in `_tenant_emission.py` + ADR-005. The PROV edge: convention recipe in ADR-002 (reuse the five existing producers' `prov_constraints` shape). ✓
- **8.05 SHOULD — Single-WP-scoped identifiers carry annotation or are scope-local.** ✓
- **8.06 MAY — Composite WPs declare shared identifier set in parent.** WP-002 carries `composite_of`; its three absorbed moves share the Step-ULID set + the re-vendored schema `$id`, both cited to upstream. ✓

**P8: PASS.** A parallel-dispatched executor cannot drift the Step ULIDs (single
source: TDD §Canonical Identifiers), the re-vendored schema `$id` (single source:
canonical compiled v2.1.0), the PROV edge (single source: `_predicate_map` +
ADR-002 + the mint), or the Tenant-home path/recipe (single source:
`_tenant_emission.py`).

### P-VER — Verification concretion (MUST)

The TDD's `## Verification Plan` is authored design-time-first (Path-A change, no
SRD plan). `kind: backend` → per-kind adapter = **pytest nodeids**. Every WP ships
a concrete `verification:` resolving to a pytest nodeid.

| WP | `verification.adapter` | `verification.artifact` (pytest nodeid) | Shape |
|---|---|---|---|
| WP-001 | backend | `tests/unit/test_lifecycle_steps_canonical.py::test_step_ulids_match_canonical` | 1 concrete |
| WP-002 | backend | `tests/unit/test_lifecyclerun_schema_v2.py::test_revendored_schema_matches_canonical` | 1 concrete |
| WP-005 | backend | `tests/unit/test_emit_lifecyclerun_cli_v2.py::test_step_flag_resolves` | 1 concrete |
| WP-006 | backend | `tests/unit/test_lifecyclerun_migration.py::test_v1_fixture_migrates` | 1 concrete |
| WP-007 | backend | `tests/unit/test_check_canonical_drift_lifecycle_steps.py::test_conformance_exits_zero` | 1 concrete |
| WP-008 | backend | `tests/unit/test_prov_edge_schemas.py::test_was_generated_by_edge_on_product_and_opportunity` | 1 concrete (external-gated) |
| WP-009 | backend | `tests/unit/test_entity_evolve.py::test_close_open_window` | 1 concrete |
| WP-010 | backend | `tests/unit/test_brain_query_as_of.py::test_returns_window_containing_as_of` | 1 concrete |
| WP-011 | backend | `tests/characterisation/test_living_entity_emit_baseline.py::test_current_save_behaviour_pinned` | 1 concrete |
| WP-012 | backend | `tests/unit/test_emitters_evolve.py::test_product_emit_opens_window` | 1 concrete |
| WP-013 | backend | `tests/unit/test_central_tenant_home.py::test_round_trip_central_home` | 1 concrete |
| WP-014 | backend | `tests/characterisation/test_minter_reconcile_baseline.py::test_current_minter_safety_pinned` | 1 concrete |
| WP-015 | backend | `tests/unit/test_minter_reconcile.py::test_canonical_save_then_mirror` | 1 concrete |

- **VER.01 MUST — Every WP carries a `verification:` field.** ✓ (13/13)
- **VER.02 MUST — The adapter matches the change `kind:`.** ✓ (all `backend` → pytest nodeids)
- **VER.03 MUST — Concrete WPs name a resolvable test artifact.** ✓ (all 13 Shape-1 `adapter + artifact`)
- **VER.04 — Deferred WPs name a canonical need identifier.** N/A (no Shape-2 deferred WPs). **WP-008's external gate is NOT a Shape-2 deferral** — it ships a concrete test the moment it lands; the gate is an *upstream-artifact prerequisite* (the mint must be re-vendored first), recorded in `upstream_dependsOn`, not a deferred-to-follow-on test. The distinction matters: Shape-2 means "the test ships in a later change"; WP-008's test ships with WP-008, which simply cannot start until the mint clears.
- **VER.05 — Trivial carveout (Shape-3) WPs justify `na:true`.** N/A (no Shape-3 WPs).
- **VER.06 — Per-integration strategy resolves at design time.** ✓ Each WP test is in-process against a real temp-dir adapter (MEA-09 honoured — no mocks at the store seam). The existing port contract test covers the file adapter (ADR-005 adds no new adapter, so no new-adapter contract test). The new prov-edge test (WP-008) asserts against the re-vendored compiled schema, which exists the moment the upstream gate clears.

**P-VER: PASS.** Every WP lands with a real test the moment it merges; WP-008's
test lands with WP-008 once its upstream prerequisite is satisfied.

### P-PLAT — Platform fit (MUST)

- **PLAT.01 — Kind set matches the change shape.** ✓ {contract, backend}. `founder_facing: false` → no `frontend` kind, no visual contract. The brain grammar (re-vendored v2.1.0 LifecycleRun + the prov_constraints edge) is a **data contract** other code consumes → 3 `kind: contract` WPs (WP-001, WP-002, WP-008) at the head; every consumer WP `dependsOn` a contract WP (CONTRACT_FIRST honoured).
- **PLAT.02 — No cross-kind seam mis-modelled.** ✓ No backend↔frontend or backend↔async seam; the contract→backend ordering is the only cross-kind relationship and it is head-first.
- **PLAT.03 — WP standard matches kind.** ✓ All WPs score against `WP_BACKEND_STANDARD` (WPB-01..12); the 3 contract WPs additionally honour CONTRACT_FIRST.

**P-PLAT: PASS.**

---

## Methodology

The validating agent attests:

- [✓] **P1 Inventory completeness.** 13 WPs read end-to-end. Required sections + `verification:` found per WP. Gaps: none.
- [✓] **P2 Atomicity.** Titles scanned for ` and `; touch surfaces counted (max 3 production files). WP-002's 3-file set is the lockstep-mandated atomic removal; no separable-concept conjunctions.
- [✓] **P3 Module naming.** Filenames + Contract module names scanned. All kebab-case + purpose-named. No findings.
- [✓] **P4 Dependency graph.** DAG built mechanically from `dependsOn:` across 13 frontmatters. Cycles: 0. Orphans: 0. Depth: 8. Max direct deps: 3. Bidirectional consistency verified (0 asymmetries after R1). WP-008's external upstream gate declared, not a dangling edge.
- [✓] **P5 Performance + non-functional.** No external-API/handler/hot-path WP; in-process backend work. Armor invariants verified per-WP.
- [✓] **P6 Peer-collision risk.** Cross-WP file-touch scan. The 3→1 merge removed the prior WP-004∥WP-013 collision; the two remaining shared-file relationships are serialised via WP-013 deps. 0 collisions remain. Every Create sole-owned.
- [—] **P7 ServiceSpec compliance.** N/A — no external service surface; Python package boundary only.
- [✓] **P8 Cross-WP identifier canonicalisation.** 5 distinct cross-WP identifier classes extracted. Step ULIDs → TDD §Canonical Identifiers; re-vendored schema `$id` → canonical compiled v2.1.0; PROV edge → `_predicate_map` + ADR-002 + mint; Tenant-home path + ULID recipe → `_tenant_emission.py`. `step_label` removed from the set. 0 inline-minted identifiers.
- [✓] **P-VER Verification concretion.** 13/13 WPs ship Shape-1 concrete pytest nodeids; adapter matches `kind: backend`; WP-008 is concrete-but-external-gated (not Shape-2 deferred); MEA-09 honoured (real temp-dir adapters, no store-seam mocks).
- [✓] **P-PLAT Platform fit.** {contract, backend}; `founder_facing:false` honoured; CONTRACT_FIRST ordering (3 contract WPs at the head).

**Tooling:** `python3 plugins/sulis/scripts/wpx-index lint --project
product-project-opportunity-evolution` → `{"data":{"header":"canonical"},"ok":true}`
(exit 0). Bidirectional graph consistency + acyclicity + critical-path verified via
a mechanical topological pass over all 13 frontmatters (13 nodes sortable; 0
asymmetries; longest chain depth 8; single root WP-001).

---

## Version history

| Date | Result | Notes |
|---|---|---|
| 2026-06-03 | PASS | Initial decompose validation (15 WPs). 3 defects repaired: R1/R2 graph hygiene, R3 peer-collision. |
| 2026-06-03 | PASS | **Re-validated after brain-governance rework (15→13 WPs).** Corrections C1–C4: re-vendor canonical v2.1.0 (3→1 atomic WP-002); drop `step_label`/`used`; prov_constraints edge on Product+Opportunity only (Project excluded, prov:Plan); conditional prov-write. 1 back-edge repair (R1) after the merge. WP-008 external-mint gate declared. `wpx-index lint` → `header: canonical`. |
