# Work Package Index — harden-plan-work-listready-gate

> **Change:** CH-01KTMJ · harden · plan-work's decompose gate drives the real
> consumer (the WP tracker), not a header proxy.
> **Source of record:** `.changes/harden-plan-work-listready-gate.SPEC.md`

## Orchestrator Config

max_parallel: 1

## Status Summary

| Status | Count |
|---|---|
| pending | 1 |
| in_progress | 0 |
| done | 0 |
| blocked | 0 |

## Primitive Distribution

| Primitive | Group | Count |
|---|---|---|
| harden | REINFORCE | 1 |

## Adapter Distribution

| Adapter | Count |
|---|---|
| backend | 1 |

## Dependency Graph

```mermaid
graph TD
    WP-001["WP-001 · list-ready round-trip gate"]
```

## WP table

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | Fold a list-ready round-trip into wpx-index lint so the decompose gate drives the real consumer | harden | pending | — | — |

## Recommended Order

1. **WP-001** — single atomic WP; no dependencies. Test-first (Red proves the
   #60/#218/#222/#233 failure class against today's gate; Green folds the
   round-trip into `cmd_lint`; Blue updates the Step 9.5 note and dogfoods the
   gate).
