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
