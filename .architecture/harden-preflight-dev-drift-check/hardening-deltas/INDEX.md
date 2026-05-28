# Hardening Deltas — harden-preflight-dev-drift-check

> **Change:** CH-01KSQB · harden · Closes #52
> **Source:** lesson #52 (incl. the 2026-05-28 corroboration + scope sharpening)
> **All deltas:** `status: proposed` (awaiting acceptance)

## Severity + dependency graph

Two near-independent tracks sharing only the orchestration skills. Helper-level
work (HD-001, HD-003) precedes orchestration wiring (HD-002, HD-004).

```
Track A (pre-flight dev-clean):     HD-001 ──blocks──> HD-002
Track B (unprotected-repo warning): HD-003 ──blocks──> HD-004
```

HD-001 and HD-003 have no inter-dependency and may be implemented in parallel.

| Order | Delta | Severity | Pillar | Primitive | Depends on | Surface |
|---|---|---|---|---|---|---|
| 1 | HD-001 | medium | Armor | Create | — | `_wpxlib.py` — non-polling `_preflight_ci_conclusion(verdict, failed_names)` |
| 2 | HD-003 | medium | Armor | Refactor | — | `wpx-arrival-check` — distinguish free-plan 403 from genuine missing protection |
| 3 | HD-002 | medium | Armor | Create | HD-001 | `wpx-preflight dev-clean` + run-all Step 0 hard blocker |
| 4 | HD-004 | medium | Armor | Create | HD-003 | `wpx-preflight protection-status` + one-time warning on run-all & ship |

## Acceptance notes

- **No critical / high findings.** The train merge path is already gated
  (spec non-goal #1, verified in `wpx-train:1377`); these deltas close
  operational visibility gaps, not active incidents.
- **All four are test-first** (CLAUDE.md non-negotiable #1). HD-003 is a
  REORGANISE (Refactor) and additionally carries a characterisation test pinning
  the preserved public-repo RC-02 semantics (CLAUDE.md #3).
- **Faithful CI reproduction** is concentrated in HD-001 (reads GitHub's recorded
  conclusion — build order inherited) and never re-runs CI locally.
- **Reuse over rebuild:** HD-001 reuses `_gh_check_runs`/`GHClient`; HD-002/004
  reuse the `wpx-arrival-check` JSON-envelope convention; HD-004 reuses HD-003's
  free-plan predicate (extracted to `_wpxlib.py` if both callers consume it).
