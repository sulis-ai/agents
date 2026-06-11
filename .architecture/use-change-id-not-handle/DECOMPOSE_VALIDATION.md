# Decompose Validation — use-change-id-not-handle

> change_id `01KTV4SS9N8BP0XN8GCQAXT6PC` · 5 WPs · 2026-06-11

## Rubric

| Check | Verdict | Evidence |
|---|---|---|
| **Atomic** — each WP implementable without reading another | PASS | Each WP carries its own Context + Contract + DoD. Cross-WP need is expressed only via `dependsOn` (real data deps: WP-003/004/005 need WP-001's `--change-id`; WP-004 needs WP-002's matcher routing). |
| **No bundling** — one logical change per WP | PASS | recreate (WP-001), nuke + dead-rung (WP-002), cockpit wiring (WP-003), regression (WP-004), worktree DiD (WP-005) are distinct logical changes. |
| **Red/Green/Blue present** | PASS | All 5 WPs have all three sub-checklists with named tests. REORGANISE WPs (WP-002, WP-005) carry a `characterisation_test` in Red (MUST). |
| **Change primitive named** | PASS | WP-001/002/003 SUBSTITUTE-Replace; WP-004 REINFORCE-Test; WP-005 REORGANISE-Refactor. Groups set. |
| **Ports&Adapters not Wrapper** | PASS | The `RecreateRunner` change is correcting an **owned** port's identity key (ADR-001 whose-interface test) → REORGANISE/SUBSTITUTE of an owned contract, not a wrapper over external code. No band-aid wrapper introduced. |
| **change_id frontmatter** | PASS | All 5 WPs carry `change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC` (WORK_PACKAGE_STANDARD v1.1+). |
| **kind + verification adapter** | PASS | All `kind: backend`; all `verification.adapter: backend` with a concrete `artifact` pytest/vitest nodeid (Shape 1). |
| **Dependency graph acyclic** | PASS | WP-001 → {003,004,005}; WP-002 → 004. No cycles. |
| **MEA-09 (no mocks in integration)** | PASS | Python uses a real temp-store + temp-worktree fixture; cockpit uses the `FakeRecreateRunner` in-memory adapter (real adapter shape), not an ad-hoc mock. |
| **Scenario coverage complete** | PASS | All 7 SPEC scenarios mapped to WPs (INDEX.md). Out-of-scope items recorded, not planned. |

## P-VER (verification design-time check)

| P-VER check | Verdict | Evidence |
|---|---|---|
| `## Verification Plan` literal heading present in TDD | PASS | TDD.md carries it. |
| Canonical citation present | PASS | `<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->` above the TDD's Verification Plan (and inherited from the SPEC, which also carries a passing plan). |
| Six subsections populated + concretised | PASS | TDD §Verification Plan 1–6: user-observable, environments, fresh-clone, per-integration strategy (2 `existing` integrations concretised to test seams + the `RecreateRunner` port + bounded-spawn resilience), per-kind adapter (backend → pytest + vitest nodeids), infra (none deferred). |
| Per-integration: artifact path + seam + resilience primitive named | PASS | CLI integration → `test_change_identity_resolution.py` + the `RecreateRunner` seam + bounded-spawn timeout/SIGKILL/typed-outcome. Cockpit integration → `recreate-on-demand.test.ts` + `FakeRecreateRunner` seam + mock contract (records `lastArg`, returns typed outcome, never spawns). |
| `existing` paths resolve at design time | PASS | Repo-grep confirmed every cited path/symbol: `cmd_recreate`, `_resolve_nuke_target`, `_select_change_id_refusing_conflict`, `ulid_handle`, `_changes_matching_handle`, `_scan_state_dir_by_prefix`, `RecreateRunner.ts`, `SulisChangeRecreator.ts`, `_recreate-on-demand.ts`, `recreate-on-demand.test.ts`, `test_sulis_change_safe_resolution.py`. No hallucinated infrastructure. |
| Per-WP `verification:` shape declared | PASS | All 5 WPs use Shape 1 (concrete): `adapter: backend` + `artifact: <nodeid>`. No Shape 2 deferrals, no Shape 3 trivial carveouts. |
| Contradictions with SPEC plan surfaced | PASS — none | The TDD concretion (test seam = `RecreateRunner` port; behavioural tests on real temp store / in-memory adapter) is consistent with the SPEC's plan (the SPEC named the same files + the behavioural-test + state-assertion + idempotency-check adapter). No load-bearing contradiction; no founder escalation needed. |

## Verdict: **PASS** — ready for execution (WPs left `pending` per the design-only brief).

---

# Amendment — property-based testing layer (WP-006..008)

> 2026-06-11 · 3 appended WPs · founder-approved fold-in (Phase 1 + Phase 2).
> WP-001..005 unchanged.

## Rubric

| Check | Verdict | Evidence |
|---|---|---|
| **Atomic** | PASS | WP-006 (strategies + dep wiring), WP-007 (pure-core properties), WP-008 (stateful model) each carry own Context + Contract + DoD. Cross-WP need is only `dependsOn: WP-006` (real data dep: both consume the strategies module). |
| **No bundling** | PASS | Foundation / Phase-1 / Phase-2 are three distinct logical changes — split rather than one "add property tests" WP, per the no-bundling rule. |
| **Red/Green/Blue present** | PASS | All three carry all three sub-checklists with named tests. WP-006/007/008 are EXPAND-Create / REINFORCE-Test — no REORGANISE, so no characterisation-test-before-refactor obligation (these ADD test-only code; they do not restructure production code). |
| **Change primitive named** | PASS | WP-006 EXPAND-Create (new strategies module + new dev-dep; an additive net-new artifact, not a wrap). WP-007/008 REINFORCE-Test. Groups set. |
| **Ports&Adapters not Wrapper** | PASS | No wrappers. WP-006 creates a new test-support module; it does not wrap internal code. The property tests call the existing pure functions directly. |
| **change_id frontmatter** | PASS | All three carry `change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC`. |
| **kind + verification adapter** | PASS | All `kind: backend`; all `verification.adapter: backend` + concrete `artifact` pytest nodeid (Shape 1). |
| **Dependency graph acyclic** | PASS | WP-006 → {WP-007, WP-008}; WP-007 and WP-008 independent. No cycle; no back-edge into the `done` WP-001..005. |
| **MEA-09 (no mocks in integration)** | PASS | No mocks. Phase 1 drives the real pure functions over generated inputs. Phase 2 uses an in-memory store MODEL (a real dict-backed adapter shape, the documented design decision), not an ad-hoc mock; refusal is observed by patching `emit_error`/`_emit_ambiguous_match` to raise — the same in-process technique the shipped example-based suite uses, not a substitute for the function under test. |
| **Distinct test files per WP** | PASS | WP-006 → `test_change_identity_strategies_selftest.py` (+ owns `_change_identity_strategies.py` via `fixtures_created:`). WP-007 → `test_change_identity_properties.py`. WP-008 → `test_change_lifecycle_stateful.py`. All three NEW + mutually disjoint and distinct from the WP-001..005 files (`test_change_identity_resolution.py`, `test_collision_regression.py`, etc.). No add/add conflict — the earlier parallel-batch failure mode is closed by the `fixtures_created:` ownership declaration the existing `validate_fixture_collisions` check reads. |
| **Canonical INDEX header preserved** | PASS | Appended to the existing table under `\| ID \| Title \| Primitive \| Status \| Depends On \| Blocks \| Delta \| Sev \|` — the run-all-parsed prefix is byte-identical; trailing `Delta`/`Sev` columns are the pre-existing extra columns (allowed). |

## P-VER (verification design-time check)

| P-VER check | Verdict | Evidence |
|---|---|---|
| `## Verification Plan` heading present in TDD | PASS | Unchanged; the property layer note was added INSIDE §5, heading untouched. |
| Canonical citation present | PASS | `<!-- VERIFICATION_QUESTIONS source: …v1.0.0 -->` left in place (grep count = 1); not duplicated, not moved. |
| Six subsections still populated + concretised | PASS | §5 now names the property-based method with concrete artifact paths for Phase 1, Phase 2, the shared strategies module, and the dep-wiring location; §6 updated (`hypothesis` dev-group, nothing external). |
| Per-WP `verification:` shape declared | PASS | All three Shape 1 (concrete): WP-006 `…test_change_identity_strategies_selftest.py::test_colliding_ulid_group_shares_handle`; WP-007 `…test_change_identity_properties.py::test_matching_handle_is_sound_and_complete`; WP-008 `…test_change_lifecycle_stateful.py::ChangeLifecycleStateMachine`. |
| Cited symbols/paths resolve at design time | PASS | Repo-grep confirmed `ulid_handle`, `validate_change_ulid`, `_CROCKFORD_BASE32`, `_changes_matching_handle`, `_select_change_id_refusing_conflict`, `change_worktree_path` all present; `pytest` declared in `pyproject.toml [dependency-groups].dev`; `hypothesis` is the one NEW dev-dep WP-006 adds (declared, not yet installed — correct for design-time). No hallucinated infrastructure. |
| Contradictions with SPEC plan surfaced | PASS — none | The property layer strengthens evidence for the SPEC's existing safety scenarios; it opens no new scenario and contradicts nothing in the SPEC or original TDD plan. |

## Verdict: **PASS** — WP-006..008 ready for execution, left `pending` (design-only brief).
