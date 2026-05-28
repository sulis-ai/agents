# Work Packages — harden-preflight-dev-drift-check

> **Change:** CH-01KSQB · harden · Closes #52
> **Base:** dev · **Branch:** change/harden-preflight-dev-drift-check
> **Source:** lesson #52 + hardening-deltas HD-001..HD-004

## Orchestrator Config
max_parallel: 2

## Dependency graph

```
Track A (pre-flight dev-clean):
  WP-001 (helper) ──> WP-003 (CLI + run-all Step 0 gate)

Track B (unprotected-repo warning):
  WP-002 (free-plan distinction) ──┐
                                   ├──> WP-004 (protection-status + warnings)
  WP-003 (wpx-preflight CLI) ──────┘
```

WP-001 and WP-002 are independent → first parallel batch (max_parallel: 2).
WP-003 depends on WP-001. WP-004 depends on WP-002 AND WP-003 (it adds a
subcommand to the CLI WP-003 creates, and consumes WP-002's predicate).

## WP table

> All WPs are `kind: backend` (carried in each WP file's frontmatter). The
> table header below uses the canonical `| ID | Title | Primitive | ... |`
> signature the wpx-index / parse_index_md tooling requires.

| ID | Title | Primitive | Status | Depends On | Blocks | File scope |
|---|---|---|---|---|---|---|
| WP-001 | Non-polling pre-flight CI-conclusion helper in `_wpxlib` | Create | done | — | WP-003 | `_wpxlib.py`, `tests/unit/test_wpxlib_preflight_ci.py` |
| WP-002 | Distinguish free-plan 403 from genuine missing protection | Refactor | done | — | WP-004 | `wpx-arrival-check`, `tests/unit/test_wpx_arrival_check.py` |
| WP-003 | `wpx-preflight dev-clean` + run-all Step 0 hard blocker | Create | done | WP-001 | WP-004 | `wpx-preflight`, `tests/unit/test_wpx_preflight.py`, `skills/run-all/SKILL.md` |
| WP-004 | `wpx-preflight protection-status` + one-time warnings | Create | done | WP-002, WP-003 | — | `wpx-preflight`, `tests/unit/test_wpx_preflight.py`, `skills/run-all/SKILL.md`, `skills/change/SKILL.md` |

## Suggested execution order

1. **Batch 1 (parallel):** WP-001 + WP-002 — independent helper-level work, no
   file overlap (`_wpxlib.py` + new test vs `wpx-arrival-check` + its test).
2. **WP-003** — after WP-001 merges (imports `_preflight_ci_conclusion`).
3. **WP-004** — after WP-002 AND WP-003 merge (adds to `wpx-preflight`; consumes
   the free-plan predicate; Blue extracts the shared predicate to `_wpxlib.py`).

WP-003 and WP-004 both touch `wpx-preflight` and `run-all/SKILL.md`, so they must
NOT run in the same batch (file-scope overlap) — the `dependsOn` edge serialises
them anyway.

## Notes

- **All four are test-first** (CLAUDE.md non-negotiable #1): failing test → code
  → refactor. WP-002 additionally carries a characterisation test (REORGANISE /
  Refactor — CLAUDE.md #3).
- **No CONTRACT_FIRST seam.** No producer/consumer cross-kind boundary here —
  every WP is `kind: backend` Python-script work. (`wpx-preflight`'s JSON envelope
  is consumed by a skill body, not by a separately-shipped consumer WP, so there
  is no contract WP to ship first.)
- **Reuse over rebuild:** WP-001 reuses `_gh_check_runs`/`GHClient`; WP-003 reuses
  the `wpx-arrival-check` JSON-envelope shape; WP-004 reuses WP-002's predicate
  (extracted to `_wpxlib.py` in WP-004's Blue — the second-caller extract-now rule).
- **No train change.** None of these WPs touch `wpx-train`'s merge gate
  (spec non-goal #1 — it already pauses on red).
