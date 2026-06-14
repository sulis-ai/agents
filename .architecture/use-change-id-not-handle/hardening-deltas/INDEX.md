# Hardening Deltas — use-change-id-not-handle

> change_id `01KTV4SS9N8BP0XN8GCQAXT6PC` · all `status: proposed` (design only).

## By severity + dependency

| ID | Sev | Pillar | Gap (one line) | Scenarios | Depends on |
|---|---|---|---|---|---|
| HD-001 | high | form+armor | Add `recreate --change-id`; cockpit passes `record.changeId`, not the non-unique handle | 1,2,3 | — |
| HD-002 | medium | armor | Route `nuke` through the safe matcher; retire the dead head-prefix rung; readable name in candidate list | 4,5,6 | — |
| HD-003 | medium | proof | 26-collision fixture + cross-verb self-resolution (Python) | 7 | HD-001, HD-002 |
| HD-004 | medium | proof | Cockpit recreate carries change_id (behavioural test) | 1,2 | HD-001 |
| HD-005 | low | form | Key recreate fallback worktree by change_id (defence-in-depth) | 3 | — (opportunistic) |

## Dependency graph

```
HD-001 ─┬─→ HD-003 (regression needs recreate-by-id + nuke-via-matcher)
        └─→ HD-004 (cockpit-carries-id test asserts HD-001's wiring)
HD-002 ──→ HD-003
HD-005  (independent; opportunistic — bundle with HD-001 or defer)
```

## Suggested acceptance order

1. HD-001 — closes the primary leak (Scenarios 1–3).
2. HD-002 — closes the CLI consistency + mint/lookup mismatch (Scenarios 4–6).
3. HD-003 + HD-004 — prove it stays closed against the live collision state
   (Scenario 7) and pin the cockpit wiring.
4. HD-005 — opportunistic defence-in-depth; bundle if cheap, else defer.

## Out of scope (recorded, not deltas)

Relabelling the 26 colliding handles · repairing already-corrupted workspaces ·
terminal-WS `?changeId` hardening · changing the `CH-XXXXXX` format.
(All four are SPEC Non-goals.)
