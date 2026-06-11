# Work Packages — use-change-id-not-handle

> change_id `01KTV4SS9N8BP0XN8GCQAXT6PC` · `fix` · kind: backend · all `pending`.

## Set

| ID | Title | Primitive | Status | Depends On | Blocks | Delta | Sev |
|---|---|---|---|---|---|---|---|
| WP-001 | CLI `recreate --change-id` resolves the exact change; handle stays display | Fix | done | — | WP-003, WP-004, WP-005 | HD-001 | high |
| WP-002 | `nuke` resolves via the safe matcher; retire the dead head-prefix rung; readable name in candidates | Fix | done | — | WP-004 | HD-002 | medium |
| WP-003 | Cockpit drives recreate by `record.changeId`, not the handle (port + adapters + serving path + HD-004 test) | Fix | pending | WP-001 | — | HD-001, HD-004 | high |
| WP-004 | 26-collision regression fixture: every change resolves to itself across all four verbs | Fix | pending | WP-001, WP-002 | — | HD-003 | medium |
| WP-005 | DiD: recreate fallback worktree keyed by change_id (opportunistic) | Harden | pending | WP-001 | — | HD-005 | low |

## Dependency graph

```
WP-001 ─┬─→ WP-003 ──→ (cockpit unambiguous; Scenarios 1,2,3 closed)
        ├─→ WP-005   (opportunistic DiD)
        └─→ WP-004 ←─ WP-002
WP-002 ───→ (CLI consistency + mint/lookup mismatch; Scenarios 4,5,6 closed)
WP-004 ───→ (Scenario 7: proves 1–6 stay closed against the live state)
```

## Execution order

- **Wave 1 (parallel):** WP-001, WP-002 — independent; one touches `recreate`,
  the other `nuke` + the shared resolver's dead rung. No file conflict (recreate
  body vs nuke body; both edit `sulis-change` but disjoint functions — sequence
  if the executor batches single-file edits).
- **Wave 2 (parallel after Wave 1):** WP-003 (needs WP-001), WP-005 (needs
  WP-001, opportunistic), WP-004 (needs WP-001 + WP-002).

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

## Out of scope (recorded)

Relabelling the 26 colliding handles · repairing corrupted workspaces ·
terminal-WS `?changeId` hardening · changing the `CH-XXXXXX` format. (SPEC
Non-goals — not planned as WPs.)
