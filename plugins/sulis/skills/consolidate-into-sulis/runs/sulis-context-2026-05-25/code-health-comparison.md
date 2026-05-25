# Code-health comparison — baseline vs final

**Baseline:** `plugins/sulis/skills/consolidate-into-sulis/runs/sulis-context-2026-05-25/code-health-baseline.json`
**Final:** `plugins/sulis/skills/consolidate-into-sulis/runs/sulis-context-2026-05-25/code-health-final.json`

## Verdict

**REGRESSION** — 1 NEW finding(s) introduced. Investigate and fix forward.

## Counts

- NEW (introduced by consolidation): **1**
- PRE-EXISTING (also in baseline): **8**
- RESOLVED (in baseline, gone in final): **1**

## NEW findings (consolidation-attributed)

Investigate each. Classify as **regression-grade** (fix forward in Commit 6)
or **pre-existing in disguise** (document, don't gate). See
`references/code-health-gating.md` for the rubric.

- `plugins/sulis/.claude-plugin/plugin.json` — `?` [concern]

## RESOLVED findings (improvement from consolidation)

- `plugins/sulis/.claude-plugin/plugin.json` — `?` [concern]

## PRE-EXISTING findings (carried over)

8 pre-existing finding(s) carried over from baseline.
These are unrelated to the consolidation; not gating.

