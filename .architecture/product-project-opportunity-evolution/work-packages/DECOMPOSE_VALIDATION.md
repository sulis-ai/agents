# Decompose Validation Report — product-project-opportunity-evolution

**Date:** 2026-06-03
**Rubric:** decompose-validation-rubric (8 phases + P-VER + P-PLAT)
**WP set:** 15 WPs
**Source TDD:** `../TDD.md`
**SIZING:** tier L (sFPC 17 / ASR 13; four bounded contexts + a hard migration chain)
**Change:** CH-01KT61 (`feat`, `founder_facing: false`)

## At a glance

The breakdown is mechanically valid after two graph-hygiene repairs and one
peer-collision repair made during validation (recorded below). All 15 WPs carry
the required sections (Context, Contract, Red-Green-Blue DoD, Sequence, Token
cost, dependsOn/blocks, ADRs, TDD §, `verification:`). The dependency graph is a
clean DAG with two roots (WP-001, WP-002) and a single terminal join (WP-015).
The critical path is 7 packages; peak safe parallelism is 3. Every cross-WP
identifier (Step ULIDs, PROV namespace, Tenant-home path + ULID recipe) is cited
to an authoritative upstream source — none invented inline. The two
REORGANISE-Refactor WPs each carry a `characterisation_test:` field and
`dependsOn` a REINFORCE-Test WP that pins the baseline first. No Wrap WPs.

## Verdict: **PASS**

All MUSTs pass. No SHOULD failures. Three defects found during validation were
**repaired in place** (they are recorded in §Repairs applied, not left as gaps).

---

## Summary

| Metric | Count |
|---|---|
| WPs validated | 15 |
| Total checks | 58 (across 8 phases + P-VER + P-PLAT) |
| PASS | 58 |
| FAIL (MUST) | 0 |
| FAIL-WITH-RATIONALE (SHOULD) | 0 |
| Defects repaired during validation | 3 (2 graph-hygiene, 1 peer-collision) |

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| 1 Inventory completeness | 15/15 | 0 | Every WP has all required sections + `verification:` |
| 2 Atomicity | 15/15 | 0 | No ` and ` conjunctions joining separable concepts; touch surfaces ≤ ceiling |
| 3 Module naming + clean code | 15/15 | 0 | All slugs kebab-case + descriptive; no jargon prefixes |
| 4 Dependency graph correctness | 15/15 | 0 | DAG acyclic; depth 7; 2 graph-hygiene repairs applied |
| 5 Performance + non-functional reqs | 15/15 | 0 | No external-API/handler WPs; in-process backend work; bounds N/A |
| 6 Peer-collision risk | 15/15 | 0 | 1 collision found + repaired (`_brain_query.py`/`_brain_emit_helper.py`) |
| 7 ServiceSpec compliance | n/a | n/a | No external service surface; Python package boundary only |
| **8 Cross-WP identifier canonicalisation** | **15/15** | **0** | **Every cross-WP identifier cites an authoritative upstream source** |
| **P-VER Verification concretion** | **15/15** | **0** | **Every WP ships Shape-1 concrete pytest nodeid; kind→adapter honoured** |
| **P-PLAT Platform fit** | **3/3** | **0** | **Backend-only; no cross-kind seam; founder_facing:false honoured** |

---

## Repairs applied during validation

The decomposition was structurally complete on arrival. Validation surfaced three
defects in the `dependsOn`/`blocks` graph; each was repaired in place and the
INDEX (table + Mermaid + waves) updated to match. None changed the WP set or the
critical path.

| # | Class | Defect | Repair |
|---|---|---|---|
| R1 | Graph hygiene | WP-001 `blocks` over-claimed WP-005 (WP-005 `dependsOn` WP-003/WP-004, reaches WP-001 only transitively) | Pruned WP-005 from WP-001 `blocks` (transitive-edge removal) |
| R2 | Graph hygiene | WP-012 `dependsOn` WP-009 but WP-009 `blocks` omitted WP-012 (asymmetry) | Added WP-012 to WP-009 `blocks` (WP-012 directly calls `evolve_entity`, so the edge is real and kept) |
| R3 | **Peer-collision (P6)** | WP-010 and WP-013 both modify `_brain_query.py`; WP-004 and WP-013 both modify `_brain_emit_helper.py`; all were same-wave-parallelisable | Added WP-004 + WP-010 to WP-013 `dependsOn` (serialises the shared-file writes). WP-013 moves from wave 4 to wave 5; peak parallelism 4 → 3; critical path unchanged (WP-013 off the critical path). |

After repairs: bidirectional `dependsOn`/`blocks` consistency holds for all 15
WPs; DAG acyclic; `wpx-index lint` returns `header: canonical`.

---

## Blocking gaps (MUST failures)

None.

## Recommended improvements (SHOULD failures)

None.

---

## Detailed findings per check

### P1 — Inventory completeness (MUST)

| WP | Context | Contract | DoD R/G/B | Sequence | Token | Deps | ADRs | TDD § | verification: |
|---|---|---|---|---|---|---|---|---|---|
| WP-001 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-002 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-003 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-004 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-005 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-006 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-007 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-008 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-009 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-010 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-011 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-012 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-013 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-014 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-015 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

INDEX.md lists all 15 WP files; carries the `## Dependency Graph` (Mermaid),
`## Primitive Distribution`, `## Kind Distribution`, `## Wrap Audit`, and
`## Recommended Implementation Order`. Every WP carries a `primitive:` from the
22-primitive catalogue. The two REORGANISE WPs (WP-012, WP-015) and their
characterisation-test partners (WP-011, WP-014) each carry the
`characterisation_test:` field.

**P1: PASS.**

### P2 — Atomicity (MUST)

| WP | Single responsibility | Production files touched | ` and ` conjunction? |
|---|---|---|---|
| WP-001 | Author 3 canonical Step instances (one file, one contract) | 1 | no |
| WP-002 | Bump lifecyclerun schema to 2.1.0 + vendor compiled | 2 (source + compiled) | no |
| WP-003 | `compose_lifecyclerun` → step + step_label | 1 | no |
| WP-004 | Resolve Step refs in the 3 emit-helper helpers | 1 | no |
| WP-005 | CLI `--step` (`--step-name` deprecated alias) | 1 | no |
| WP-006 | Build migration script + run on marketplace store | 1 created + 2 instances | no |
| WP-007 | Register lifecycle-steps in drift detector | 1 | no |
| WP-008 | Add `was_generated_by`/`used` to living schemas + @context | 6 (3 source + 3 vendored) | no |
| WP-009 | Build `_entity_evolve` (close/open window + guard + PROV write) | 1 created | "+" join, single concept ("the evolve primitive") |
| WP-010 | Add `read_as_of` to `_brain_query` | 1 | no |
| WP-011 | Characterisation test pinning emit baseline | 1 created (test) | no |
| WP-012 | Refactor 3 emitters to call `evolve_entity` | 3 | no |
| WP-013 | Point base_dir at central home + cross-repo read | 2 | no |
| WP-014 | Characterisation test pinning minter safety | 1 created (test) | no |
| WP-015 | Refactor minter to canonical+mirror + update Mint prose | 2 | no |

**Touch-surface counts:** every WP ≤ 6 production files; well under the MUST ≤ 15
ceiling. WP-008's 6 files are the additive PROV field on three living schemas,
each with its vendored compiled copy — a mutually-validating set (the on-disk
schema and its compiled copy are the same contract; splitting would produce a
schema that validates against a stale compiled copy mid-slice).

**Title-conjunction scan:** WP-009 carries "+" tokens; per check 2.06 the
forbidden token is the literal word " and " joining two separable concepts. No
title contains " and " as a separable conjunction. WP-009 describes one atomic
unit ("the evolve primitive — close/open-window + PROV-write + guard, all of
which are the single window-invariant guarantee").

**P2: PASS.**

### P3 — Module naming + clean code (MUST)

WP filename pattern `WP-NNN-{descriptive-slug}.md`: ✓ for all 15. Contract module
names are purpose names (`_entity_evolve`, `_lifecyclerun_emission`,
`_brain_emit_helper`, `_brain_query`, `migrate_lifecyclerun_v1_to_v2`,
`_discovery/minter`). No single-letter abbreviations (3.02 ✓); no jargon prefixes
(3.07 ✓); no `mgr`/`svc`/`auth_mgr` patterns (3.04 ✓); no standalone
`utils`/`helpers`/`common` (3.05 ✓). Test files follow `test_{subject}.py` and
sit under `tests/unit/` or `tests/characterisation/`.

**P3: PASS.**

### P4 — Dependency graph correctness (MUST)

**DAG (after repairs R1–R3):**

```
WP-001 → WP-003, WP-004, WP-006, WP-007        (canonical Steps the chain resolves)
WP-002 → WP-003, WP-006, WP-007, WP-008        (v2.1.0 schema the consumers validate against)
WP-003 → WP-004, WP-005, WP-006
WP-004 → WP-005, WP-013                          (WP-013: shared-file serialisation, _brain_emit_helper.py)
WP-008 → WP-009                                  (was_generated_by field must exist before the writer)
WP-009 → WP-010, WP-011, WP-012, WP-013          (the windows the read/test/refactor/home consume)
WP-010 → WP-013                                  (shared-file serialisation, _brain_query.py)
WP-011 → WP-012                                  (characterisation baseline before the refactor — EP-07)
WP-012 → WP-014
WP-013 → WP-014                                  (piece 3+4+5 join)
WP-014 → WP-015                                  (characterisation baseline before the refactor — EP-07)
```

- **4.01 No cycles** ✓ (topologically sortable; verified mechanically)
- **4.02 Every dependsOn target exists** ✓ (all 15 IDs resolve)
- **4.03 No WP > 5 direct deps** ✓ (max is 3: WP-006 `[WP-001,WP-002,WP-003]`, WP-013 `[WP-004,WP-009,WP-010]`)
- **4.04 Depth ≤ 8** ✓ (longest path 7: WP-002 → WP-008 → WP-009 → WP-011 → WP-012 → WP-014 → WP-015)
- **4.05 No orphans** ✓ (WP-002 has no deps but blocks 4 WPs; every node has ≥1 edge)
- **4.06 ≥ 1 parallel batch** ✓ (waves 3 and 4 each carry 3 WPs)
- **4.07 Topological order valid** ✓ (INDEX `## Recommended Implementation Order` respects all `dependsOn`)
- **4.08 Cross-kind seam contract WP** — **N/A.** Kind set is {contract, backend}. The check fires when ≥2 of {backend, frontend, async} are present; frontend and async are absent. The 3 `contract` WPs (WP-001, WP-002, WP-008) are the canonical-grammar head; every backend WP `dependsOn` a contract WP directly or transitively. Contract-first ordering holds.
- **4.09 No direct cross-kind edge** ✓ (all backend WPs route through contract WPs at the head; no frontend/async kinds exist to cross)

**Bidirectional `dependsOn`/`blocks` consistency:** verified across all 15 WP
frontmatters after repairs — every `A dependsOn B` has a matching `B blocks A` and
vice versa.

**P4: PASS** (2 graph-hygiene repairs R1, R2 applied; see §Repairs applied).

### P5 — Performance + non-functional requirements

No WP in this set authors an external-API call, a network handler, or a
user-request hot path. All work is in-process Python against temp directories
(the central Tenant home is a temp dir served by the existing file adapter — TDD
§Verification Plan §2). The non-functional guarantees that DO apply (migration
atomicity, window invariants, central-home write durability, append-only guard)
are Armor concerns enforced inside specific WPs and verified by their tests
(WP-006 migration reject-on-invalid; WP-009 window invariants + no-two-open-windows;
WP-013 atomic-write durability via the existing `_atomic_write`; WP-009 allowlist
guard). These are correctness invariants, not latency/throughput bounds, so the
`## Performance` section (5.01) is **not triggered** — there is no external call to
bound.

- **5.01 External-API/handler WPs declare performance** — N/A (no such WPs)
- **5.05 External-API WPs declare rate-limit + timeout** — N/A (no network seam; no credentials; no vendor)

**P5: PASS (no performance-bearing WPs; Armor invariants verified per-WP).**

### P6 — Peer-collision risk (MUST)

**Cross-WP file-touch scan** (every production file path in every WP Contract,
checked for create-uniqueness and same-wave modify-overlap):

| File | Created by | Modified by | Same-wave overlap? |
|---|---|---|---|
| `plugins/sulis/instances/lifecycle-steps/steps.jsonld` | WP-001 (sole) | — | none |
| `…/lifecyclerun.schema.json` (source + compiled) | — | WP-002 (sole) | none |
| `_lifecyclerun_emission.py` | — | WP-003 (sole) | none |
| `_brain_emit_helper.py` | — | WP-004, **WP-013** | **was wave-4 overlap → serialised (R3)** |
| `sulis-emit-lifecyclerun` (CLI) | — | WP-005 (sole) | none |
| `migrate_lifecyclerun_v1_to_v2.py` | WP-006 (sole) | — | none |
| `.brain/instances/*/lifecyclerun/*.jsonld` | — | WP-006 (sole) | none |
| `check-canonical-drift.py` | — | WP-007 (sole) | none |
| `product/opportunity/project.schema.json` (×3 source + ×3 compiled) | — | WP-008 (sole) | none |
| `_entity_evolve.py` | WP-009 (sole) | — | none |
| `_brain_query.py` | — | WP-010, **WP-013** | **was wave-4 overlap → serialised (R3)** |
| `tests/characterisation/test_living_entity_emit_baseline.py` | WP-011 (sole) | — | none |
| `_product_emission.py` / `_opportunity_emission.py` / project emit | — | WP-012 (sole) | none (WP-013 edits the adapter-construction in `_brain_emit_helper.py`, not the emitter modules) |
| `tests/characterisation/test_minter_reconcile_baseline.py` | WP-014 (sole) | — | none |
| `_discovery/minter.py` + `discover-project/SKILL.md` | — | WP-015 (sole) | none |

**The two collisions found** — both on shared modules `_brain_emit_helper.py`
(WP-004 ∥ WP-013) and `_brain_query.py` (WP-010 ∥ WP-013) — were the exact P6
anchor-case class (two same-wave WPs writing one file). **Repaired (R3):** WP-013
now `dependsOn` WP-004 and WP-010, serialising both shared-file writes. After the
repair, no two WPs modify any production file in the same wave.

- **6.01 No two WPs Create the same file** ✓ (every Create is sole-owned)
- **6.02 Same-level parallel Modify of same file** ✓ **after R3** (the two overlaps serialised)
- **6.03 Shared scaffolding created by foundation WP** ✓ (no new package `__init__.py`; all touched modules pre-exist)
- **6.04 Contract distinguishes create vs modify** ✓ (each WP Contract uses "files created" / "files modified")

**P6: PASS** (1 peer-collision repaired; see §Repairs applied R3).

### P7 — ServiceSpec compliance

**Not applicable.** This change ships no external service surface — no HTTP/RPC
endpoint, no queue consumer, no inter-process contract. The deliverables are
brain-grammar schemas, Python emitters/helpers, a migration script, and skill
prose, all exercised at the Python package boundary (TDD §Verification Plan §1).
ServiceSpec compliance applies only to WPs authoring an inter-process service
contract. Recorded N/A per ARCH.yaml (`founder_facing: false`; no service surface).

**P7: N/A (not triggered).**

### P8 — Cross-WP identifier canonicalisation (MUST)

The TDD pre-canonicalised every cross-WP identifier in its **§Canonical
Identifiers** section. This is the explicit P8 compliance pattern (the anchor-case
defence against the CH-01KSZ4 tenant-ULID divergence).

**Cross-WP shared identifiers extracted from WP Contracts:**

| Identifier (class) | Appears in WPs | Authoritative upstream source | Result |
|---|---|---|---|
| 3 lifecycle Step ULIDs (`dna:step:01KT61X5ST0{1,2,3}…`) | WP-001 (authors), WP-004 (name→ULID map), WP-005 (CLI resolves), WP-006 (migration maps), WP-007 (drift parity) | **TDD §Canonical Identifiers — Canonical lifecycle Step instances** (ULIDs grounded in ADR-001/ADR-004) | ✓ resolves |
| `step`/`step_label` schema fields + v2.1.0 `$id` | WP-002 (authors), WP-003 (emits), WP-006 (migrates) | **TDD §Canonical Identifiers — Schema versions** (ADR-004) | ✓ resolves |
| name→Step-ULID resolution map | WP-004 (implements), WP-005 (CLI reuses), WP-006 (migration reuses) | **TDD §Canonical Identifiers — name→Step-ULID map** (ADR-004 §Step-ref resolution) | ✓ resolves |
| PROV term URIs (`prov:wasGeneratedBy` / `prov:used`) + `@context` maps | WP-008 (authors), WP-009 (writes `was_generated_by`), WP-012 (wires the ref) | **ADR-002** (W3C PROV-O; `was_generated_by`→`prov:wasGeneratedBy`, `used`→`prov:used`) | ✓ resolves |
| Central-home path `~/.sulis/instances/{tenant_id}/` + deterministic Tenant-ULID recipe | WP-013 (wires + reads) | **`plugins/sulis/scripts/_tenant_emission.py`** (module docstring lines 5–7 + `_deterministic_ulid_from` + seed `"tenant-name:"`), cited verbatim in WP-013 `# canonical-source:` and **ADR-005** | ✓ resolves |

**Per-check results:**

- **8.01 MUST — Every cross-WP shared identifier resolves to an authoritative upstream source.** 13 of 15 WPs carry a `# canonical-source:` annotation. The 2 without (WP-011, WP-014) are characterisation-test WPs that pin *existing* code behaviour and reference no cross-WP minted identifier — correct absence. ✓
- **8.02 MUST — No ULID-shape literal invented inline.** The only literal ULIDs in any WP are the 3 Step ULIDs in WP-001 and WP-004, both transcribed byte-exact from TDD §Canonical Identifiers (WP-001 states "transcribes; it does not invent"; WP-004's map ULIDs are annotated `= WP-001's authored values`). No inline minting. ✓
- **8.03 MUST — No `dna:*:*` in ≥2 WP Contracts without upstream source.** Every cross-referenced `dna:step:*` traces to TDD §Canonical Identifiers; the Tenant ULID traces to `_tenant_emission.py`. ✓
- **8.04 SHOULD — Each upstream source documents its minting recipe.** Step ULIDs: mnemonic-stamped Crockford-base32, prefix `01KT61X5`, recipe in TDD §Canonical Identifiers preamble (verified 26-char, no I/L/O/U). Tenant ULID: `_deterministic_ulid_from("tenant-name:{name}")` sha256-of-name, recipe in `_tenant_emission.py` + ADR-005. ✓
- **8.05 SHOULD — Single-WP-scoped identifiers carry annotation or are scope-local.** No scope-local identifiers; all cross-WP identifiers carry the upstream-binding annotation. ✓
- **8.06 MAY — Composite WPs declare shared identifier set in parent.** No composite WPs. N/A.

**P8: PASS.** A parallel-dispatched executor cannot drift the Step ULIDs (single
source: TDD §Canonical Identifiers), the PROV namespace (single source: ADR-002),
or the Tenant-home path/recipe (single source: `_tenant_emission.py`, cited in
ADR-005 + WP-013). The CH-01KSZ4 divergence class is structurally prevented.

### P-VER — Verification concretion (MUST)

The TDD's `## Verification Plan` is authored design-time-first (no SRD plan
exists — Path-A change). The change `kind: backend` → per-kind adapter = **pytest
nodeids**. Every WP must ship a concrete `verification:` resolving to a pytest
nodeid (TDD §Per-WP verification frontmatter shape: every WP is Shape-1 concrete;
no Shape-2 deferred).

| WP | `verification.adapter` | `verification.artifact` (pytest nodeid) | Shape |
|---|---|---|---|
| WP-001 | backend | `tests/unit/test_lifecycle_steps_canonical.py::test_step_ulids_match_canonical` | 1 concrete |
| WP-002 | backend | `tests/unit/test_lifecyclerun_schema_v2.py::test_v2_requires_step_ref` | 1 concrete |
| WP-003 | backend | `tests/unit/test_lifecyclerun_emission_v2.py::test_compose_emits_step_ref` | 1 concrete |
| WP-004 | backend | `tests/unit/test_brain_emit_helper_step_resolution.py::test_change_started_resolves_to_canonical_step` | 1 concrete |
| WP-005 | backend | `tests/unit/test_emit_lifecyclerun_cli_v2.py::test_step_flag_resolves` | 1 concrete |
| WP-006 | backend | `tests/unit/test_lifecyclerun_migration.py::test_v1_fixture_migrates` | 1 concrete |
| WP-007 | backend | `tests/unit/test_check_canonical_drift_lifecycle_steps.py::test_conformance_exits_zero` | 1 concrete |
| WP-008 | backend | `tests/unit/test_prov_grammar_schemas.py::test_was_generated_by_on_living_schemas` | 1 concrete |
| WP-009 | backend | `tests/unit/test_entity_evolve.py::test_close_open_window` | 1 concrete |
| WP-010 | backend | `tests/unit/test_brain_query_as_of.py::test_returns_window_containing_as_of` | 1 concrete |
| WP-011 | backend | `tests/characterisation/test_living_entity_emit_baseline.py::test_current_save_behaviour_pinned` | 1 concrete |
| WP-012 | backend | `tests/unit/test_emitters_evolve.py::test_product_emit_opens_window` | 1 concrete |
| WP-013 | backend | `tests/unit/test_central_tenant_home.py::test_round_trip_central_home` | 1 concrete |
| WP-014 | backend | `tests/characterisation/test_minter_reconcile_baseline.py::test_current_minter_safety_pinned` | 1 concrete |
| WP-015 | backend | `tests/unit/test_minter_reconcile.py::test_canonical_save_then_mirror` | 1 concrete |

- **VER.01 MUST — Every WP carries a `verification:` field.** ✓ (15/15)
- **VER.02 MUST — The adapter matches the change `kind:`.** ✓ (all `backend` → pytest nodeids per the canonical kind→adapter table; no Vitest/Playwright/methodology fixtures)
- **VER.03 MUST — Concrete WPs name a resolvable test artifact (pytest nodeid).** ✓ (all 15 are Shape-1 `adapter + artifact`)
- **VER.04 — Deferred WPs name a canonical need identifier.** N/A (no Shape-2 deferred WPs — TDD §Verification Plan §6 deferred-need list is empty; every integration is verifiable at land time against a temp dir served by the existing file adapter)
- **VER.05 — Trivial carveout (Shape-3) WPs justify `na:true`.** N/A (no Shape-3 WPs; no comment-only or mechanical-rename WP was split out)
- **VER.06 — Per-integration strategy resolves at design time.** ✓ The TDD §4 strategy rows map to WP test files; each is in-process against a real temp-dir adapter (MEA-09 honoured — no mocks at the store seam). The existing port contract test covers the file adapter (no new-adapter contract test, because ADR-005 adds no new adapter).

**P-VER: PASS.** Every WP lands with a real test the moment it merges.

### P-PLAT — Platform fit (MUST)

- **PLAT.01 — Kind set matches the change shape.** ✓ {contract, backend}. `founder_facing: false` → no `frontend` kind, no visual contract, no `WP_FRONTEND_STANDARD`, no Playwright/axe surface. The brain grammar (v2.1.0 LifecycleRun schema + PROV vocabulary) is a **data contract** other code consumes → 3 `kind: contract` WPs (WP-001, WP-002, WP-008) sit at the head, and every consumer WP `dependsOn` a contract WP (CONTRACT_FIRST honoured).
- **PLAT.02 — No cross-kind seam mis-modelled.** ✓ No backend↔frontend or backend↔async seam exists; the contract→backend ordering is the only cross-kind relationship and it is correctly head-first.
- **PLAT.03 — WP standard matches kind.** ✓ All WPs score against `WP_BACKEND_STANDARD` (WPB-01..12) per the TDD WP-doctrine note; the 3 contract WPs additionally honour CONTRACT_FIRST (consumers depend on them).

**P-PLAT: PASS.**

---

## Methodology

The validating agent attests:

- [✓] **P1 Inventory completeness.** 15 WPs read end-to-end. Required sections + `verification:` found per WP. Gaps: none.
- [✓] **P2 Atomicity.** Titles scanned for ` and `; touch surfaces counted per Contract (max 6 production files, well under the ≤15 ceiling). No separable-concept conjunctions.
- [✓] **P3 Module naming.** Filenames + Contract module names scanned for jargon prefixes, single-letter abbreviations, generic terms. All kebab-case + purpose-named. No findings.
- [✓] **P4 Dependency graph.** DAG built mechanically from `dependsOn:` across 15 frontmatters. Cycles: 0. Orphans: 0. Depth: 7. Max direct deps: 3. Bidirectional `dependsOn`/`blocks` consistency verified. 2 graph-hygiene repairs (R1, R2) applied + INDEX updated.
- [✓] **P5 Performance + non-functional.** No external-API/handler/hot-path WP in the set; in-process backend work. Armor invariants (migration atomicity, window invariants, durability, append-only guard) verified per-WP rather than as latency bounds.
- [✓] **P6 Peer-collision risk.** Cross-WP file-touch scan. 1 collision class found (shared `_brain_emit_helper.py` + `_brain_query.py` between same-wave WPs) and repaired (R3 — WP-013 serialised after WP-004 + WP-010). 0 collisions remain. Every Create sole-owned.
- [—] **P7 ServiceSpec compliance.** N/A — no external service surface; Python package boundary only.
- [✓] **P8 Cross-WP identifier canonicalisation.** 5 distinct cross-WP identifier classes extracted. Step ULIDs → TDD §Canonical Identifiers; PROV namespace → ADR-002; Tenant-home path + ULID recipe → `_tenant_emission.py` (cited in ADR-005 + WP-013). 0 inline-minted identifiers.
- [✓] **P-VER Verification concretion.** 15/15 WPs ship Shape-1 concrete pytest nodeids; adapter matches `kind: backend`; no deferred/trivial carveouts; MEA-09 honoured (real temp-dir adapters, no store-seam mocks).
- [✓] **P-PLAT Platform fit.** {contract, backend} kind set; `founder_facing:false` honoured (no frontend/visual contract); CONTRACT_FIRST ordering (3 contract WPs at the head, all consumers depend on them).

**Tooling:** `wpx-index lint --project product-project-opportunity-evolution` →
`header: canonical` (exit 0). Bidirectional graph consistency + acyclicity +
critical-path verified via a mechanical topological pass over all 15 frontmatters.

---

## Version history

| Date | Result | Notes |
|---|---|---|
| 2026-06-03 | PASS | Initial decompose validation (8 phases + P-VER + P-PLAT). 3 defects repaired in place: R1/R2 graph hygiene, R3 peer-collision serialisation. |
