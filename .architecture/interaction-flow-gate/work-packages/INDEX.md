# Work Packages — interaction-flow-gate (CH-01KT9H)

> change_id: 01KT9HJMZC4731H0TAVW1E5QCD · primitive: gate · Tier S
> Mirrors `#45 / UXD-14` visual-contract done-gate. Phase 1: mechanism + spike.

## Config

```yaml
max_parallel: 2
```

## Work packages

| ID | Title | Primitive | Status | Depends On | Blocks | Token | TDD § |
|---|---|---|---|---|---|---|---|
| WP-001 | Interaction-flow gate predicate + recognition (`_wpxlib.py`) | create | done | — | WP-002, WP-004 | ~6k/~3k | §2,§4 |
| WP-002 | Enforce interaction gate at flip-to-done (`wpx-index`) | extend | done | WP-001 | WP-004 | ~7k/~3k | §2,§4 |
| WP-003 | Document interaction contract's home in decomposition (SHOULD) | document | done | — | — | ~5k/~2k | §5 |
| WP-004 | Clinics-scheme spike — block → exercise-over-stubs → release | create | pending | WP-002 | — | ~9k/~5k | §3,§4 |

## Status Summary

| Status | Count |
|---|---|
| pending | 1 |
| in_progress | 0 |
| done | 3 |
| blocked | 0 |

## Dependency graph

```
WP-001 (predicate) ──► WP-002 (enforcement) ──► WP-004 (clinics spike)
                                                      ▲
WP-003 (docs, SHOULD) ───────────────────────────────┘  (independent; no code dep)
```

## Sequence

- **Can start now (no deps):** WP-001, WP-003 (run in parallel).
- **After WP-001:** WP-002.
- **After WP-002:** WP-004 (the spike needs the live enforcer to demonstrate the block).

The gate predicate + enforcement (WP-001 → WP-002) deliberately land **before**
the spike (WP-004) that depends on them — the spike drives the real gate, so
the gate must exist first.

## Notes

- Every WP is test-first (EP-02); each characterises both the block path and
  the release path.
- WP-003 is documentation-only at SHOULD strength (ADR-002). It does not gate
  any code and carries no runtime dependency.
- Phase 2 (the MUST flip — interaction contract mandatory for all
  founder-facing work) is **out of scope** and tracked in the change task
  backlog.
