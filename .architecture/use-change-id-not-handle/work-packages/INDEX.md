# Work Packages — use-change-id-not-handle

> change_id `01KTV4SS9N8BP0XN8GCQAXT6PC` · `fix` · kind: backend.
> WP-001..005 `done` (example-based safe-resolution). WP-006..008 `pending`
> (property-based testing layer — Phase 1 pure-core + Phase 2 stateful).

## Set

| ID | Title | Primitive | Status | Depends On | Blocks | Delta | Sev |
|---|---|---|---|---|---|---|---|
| WP-001 | CLI `recreate --change-id` resolves the exact change; handle stays display | Fix | done | — | WP-003, WP-004, WP-005 | HD-001 | high |
| WP-002 | `nuke` resolves via the safe matcher; retire the dead head-prefix rung; readable name in candidates | Fix | done | — | WP-004 | HD-002 | medium |
| WP-003 | Cockpit drives recreate by `record.changeId`, not the handle (port + adapters + serving path + HD-004 test) | Fix | done | WP-001 | — | HD-001, HD-004 | high |
| WP-004 | 26-collision regression fixture: every change resolves to itself across all four verbs | Fix | done | WP-001, WP-002 | — | HD-003 | medium |
| WP-005 | DiD: recreate fallback worktree keyed by change_id (opportunistic) | Harden | done | WP-001 | — | HD-005 | low |
| WP-006 | Hypothesis strategies module + dev-dependency wiring (property-layer foundation) | Create | done | — | WP-007, WP-008 | — | low |
| WP-007 | Phase 1 — pure-core property tests (handle/match/resolve/refuse/path invariants, universal) | Test | done | WP-006 | — | — | low |
| WP-008 | Phase 2 — stateful model-based test (lifecycle never acts on wrong id; ambiguous always refuses) | Test | done | WP-006 | — | — | low |

## Dependency graph

```
WP-001 ─┬─→ WP-003 ──→ (cockpit unambiguous; Scenarios 1,2,3 closed)
        ├─→ WP-005   (opportunistic DiD)
        └─→ WP-004 ←─ WP-002
WP-002 ───→ (CLI consistency + mint/lookup mismatch; Scenarios 4,5,6 closed)
WP-004 ───→ (Scenario 7: proves 1–6 stay closed against the live state)

WP-006 ─┬─→ WP-007   (Phase 1: pure-core properties — universal complement to WP-004)
        └─→ WP-008   (Phase 2: stateful lifecycle model)
```

WP-006..008 are the property-based testing layer. They add no production
code — they prove the WP-001..005 safe-resolution invariants UNIVERSALLY
(generated inputs) rather than on the single fixed population WP-004 uses.
WP-006 is the foundation (strategies module + `hypothesis` dev-dependency);
WP-007 and WP-008 depend on it and are mutually independent.

## Execution order

- **Wave 1 (parallel):** WP-001, WP-002 — independent; one touches `recreate`,
  the other `nuke` + the shared resolver's dead rung. No file conflict (recreate
  body vs nuke body; both edit `sulis-change` but disjoint functions — sequence
  if the executor batches single-file edits).
- **Wave 2 (parallel after Wave 1):** WP-003 (needs WP-001), WP-005 (needs
  WP-001, opportunistic), WP-004 (needs WP-001 + WP-002).
- **Wave 3 (property layer — foundation):** WP-006 — strategies module +
  `hypothesis` dev-dep wiring. Independent of WP-001..005 *files* (it adds new
  test-only files + one `pyproject.toml`/`uv.lock` edit), but ordered after them
  because its properties characterise the behaviour those WPs built.
- **Wave 4 (parallel after WP-006):** WP-007 (Phase-1 pure-core properties) and
  WP-008 (Phase-2 stateful model). Disjoint file scopes —
  `test_change_identity_properties.py` vs `test_change_lifecycle_stateful.py`,
  each its own NEW file, the shared `_change_identity_strategies.py` owned by
  WP-006 and only *read* by both. No add/add conflict; safe to batch in parallel.

## Scenario → WP coverage

| Scenario | Closed by |
|---|---|
| 1 Colliding recreate resolves to self | WP-001 + WP-003 |
| 2 Tidied colliding rebuilds for itself | WP-001 + WP-003 |
| 3 Two colliding stay separate | WP-003 (+ WP-005 DiD) |
| 4 Destructive verbs never hit wrong change | WP-002 (nuke) + already-green (ship) |
| 5 Ambiguous handle disambiguates | WP-002 (readable candidate list) |
| 6 New-style handle resolves | WP-002 (retire dead rung) |
| 7 Regression vs live collision state | WP-004 |
| 1,3,4,5,6 proven universally (any collision structure) | WP-006 + WP-007 (per-call) ; WP-006 + WP-008 (per-sequence) |

> The property layer (WP-006..008) does not open new scenarios — it strengthens
> the *evidence* for the existing safety scenarios from "holds on one fixed
> 26-change population" (WP-004) to "holds for any generated population and any
> operation sequence". Per-call invariants in WP-007; sequence-level invariant in
> WP-008.

## Out of scope (recorded)

Relabelling the 26 colliding handles · repairing corrupted workspaces ·
terminal-WS `?changeId` hardening · changing the `CH-XXXXXX` format. (SPEC
Non-goals — not planned as WPs.)
