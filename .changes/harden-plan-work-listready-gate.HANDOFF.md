# Handoff — harden-plan-work-listready-gate (CH-01KTMJ) — task #99

> Seed for a fresh, scoped session, written from the originating session while the
> investigation was fresh. Read this before `/sulis:recon` → `/sulis:specify`. Small,
> well-bounded harden change. Parallel track to #98 (touches plan-work, NOT the scenario
> runner) — no collision.

## The problem (a recurring failure-class, past the build-now threshold)

The to-do list (`INDEX.md`) that plan-work/decompose emits can be in a shape the BUILDER
can't read. The builder (run-all / wpx-train) reads ready WPs via `wpx-index list-ready`.
When the INDEX is non-canonical, list-ready returns 0 → the builder thinks there's
nothing to build → the break surfaces MID-BUILD, not at creation.

Recurrence cluster (GitHub ISSUES, not task IDs):
- #60 [CLOSED] original — non-canonical header (`| WP |` not `| ID |`)
- #218 [OPEN] #60 RECURRED (`| WP |`/`| Kind |` not `| ID |`/`| Status |`)
- #222 [OPEN] status-value variant — statuses `ready`/`blocked` instead of `pending` → ready-set empty
- #233 [OPEN] non-canonical header again → run-all/train read 0 WPs
- #97 [OPEN, on the watchlist] meta-diagnosis: header lint can't catch a *missing* table; needs a list-ready round-trip gate.
4 distinct recurrences in ~10 days; it bit CH-01KTMA's (#98) own decompose. Watchlist
escalation rule = 2 failures → stop logging lessons, BUILD the gate. We are at 4 → overdue.

## Why the existing gate is insufficient (don't just "fix the lint")

plan-work's Definition-of-Done ALREADY runs `wpx-index lint` (SKILL.md Step 9.5;
non-zero exit = decompose not done). But lint validates the header SHAPE *if a table is
present* — it cannot catch (a) a table that isn't there at all, and it has been letting
(b) the recurring header/status variants through. It checks the shape, not whether the
real builder can actually parse the INDEX.

## The fix (this is the whole methodology program's thesis, one level down)

Make plan-work's DoD **drive the real consumer**, not lint the shape: run
`wpx-index list-ready` (the EXACT call run-all/wpx-train make) and assert it returns the
EXPECTED WP set (≥1 when WPs were authored; ideally == the count of `pending` WPs in the
INDEX). **0 returned while WPs exist = decompose NOT done.** This is observed-or-blocked
applied to the INDEX artifact itself, and it catches ALL three variants at once — missing
table, bad header, wrong status — because each manifests as list-ready returning 0.

**Recommended shape (evaluate at design, but this is the lean path):** wire the
round-trip INTO the existing `wpx-index lint` (lint additionally runs the list-ready
parse and fails non-zero if the authored WPs don't round-trip). Then plan-work's EXISTING
Step 9.5 wiring ("lint non-zero = not done") enforces it for free — no new gate to wire,
maximal enforcement, minimal surface. Consider whether a distinct `wpx-index verify` /
`round-trip` subcommand is cleaner than overloading `lint`; lean toward extending lint
unless there's a reason to separate.

## Test-first (MUST — this is the point of the change)

Author failing tests FIRST that pin each recurrence variant, then make them pass:
1. A missing WP table entirely → gate FAILS (today's lint passes — that's the bug).
2. A non-canonical header (`| WP |`/`| Kind |`) → gate FAILS (#218/#233).
3. All WP statuses non-`pending` (`ready`/`blocked`) → gate FAILS (#222).
4. A canonical INDEX with ≥1 `pending` WP → gate PASSES (no false-positive).
Tests likely live near the existing wpx-index tests (`plugins/sulis/scripts/tests/unit/`
— grep `test_wpx_index*`, `list-ready`, `lint`). Reuse existing fixtures.

## Files in play
- `plugins/sulis/scripts/wpx-index` — the `list-ready` + `lint` commands (the round-trip).
- `plugins/sulis/skills/plan-work/SKILL.md` — Step 9.5 / Definition of Done (the gate wiring).
- `plugins/sulis/scripts/_wpxlib.py` — `parse_index_md` / `resolve_wp_columns` (the parser list-ready uses; the column-resolver work from task #40 lives here).

## On ship (watchlist hygiene)
When this lands: comment the build on watchlist #97 (the structural fix shipped → it can
graduate after clean executions), and the recurrence issues #218/#222/#233 can close.

## Suggested next step
`/sulis:recon` (confirm current lint/list-ready behaviour + where the DoD wiring lives),
then `/sulis:specify`. This is engineering-architect-light — a focused harden; it may be
small enough to specify + design + build in one or two WPs.
