# Routing Rubric — the authored routing layer

> The inventory, route-set, and invocations are DERIVED by `sulis-route` from
> skill + agent frontmatter. This file holds only what can't be derived:
> which skills are deliberately not routing targets, and extra trigger
> keywords where a skill's own description isn't sharp enough.
>
> This is the single place a human edits to change routing behaviour. It is
> read by `_route_rubric.parse()` using the existing `_wpxlib` Markdown-table
> helpers (no new table parser). See TDD §8, ADR-003, ADR-004.

## Exclusions

Skills here are intentionally absent from the closed route-set. The coverage
gate treats anything NOT here and NOT in the route-set as an orphan (build
failure). Every exclusion needs a reason — a blank-reason row is a defect, not
a valid exclusion (ADR-004, closed-world: silence is never consent).

The names below are frontmatter `name:` values, reconciled against the live
tree (TDD §7.4 seed). Reconciliation note: the §7.4 seed labelled the
ARCHITECTURAL-INTENT reference agent as "sulis"; in the live tree that marker
sits on the agent whose frontmatter `name` is `orchestrator` (`sulis` is the
active founder-facing concierge and is a legitimate route). The exclusion is
therefore authored as `orchestrator`, matching the agent that carries the
"NOT ACTIVELY INVOKED" marker.

| Skill | Reason |
|---|---|
| requirements-templates | template; consumed by requirements-analyst, not a route |
| requirements-validation | meta; validates requirements artifacts, not founder-facing intent |
| index-specifications | meta; rebuilds an index, not founder-facing intent |
| consolidate-into-sulis | maintenance; invoked by maintainers, not founder intent |
| backfill-gates | maintenance backfill; not founder intent |
| backfill-code-review | maintenance backfill; not founder intent |
| jargon | maintenance/lint; not founder intent |
| orchestrator | agent marked ARCHITECTURAL-INTENT REFERENCE — NOT ACTIVELY INVOKED; reference spec, not a route |

## Trigger keywords

Extra match keywords for routes whose prose description isn't sharp enough for
rules matching. Additive only — a route with no row here still matches on its
description (the auto-discovery baseline). Each cell is a comma-separated list
of phrases; phrases may contain spaces.

| Route | Trigger keywords |
|---|---|
| check-security | secrets, vulnerability, leak, exposed, CVE, injection |
| dashboard | what am I working on, in flight, overview, status of everything |
