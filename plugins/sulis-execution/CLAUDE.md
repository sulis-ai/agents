# Sulis Execution

The Work Package Executor — autonomous per-WP atomic implementation
via Red-Green-Blue test-driven cycle, direct merge to dev, deploy,
smoke-test, mark done.

## Purpose

The marketplace produces Work Packages (`sea:decompose`) and verifies
them (`sea:verify`) but had no agent that actually implemented them.
The Work Package Executor closes that gap. Each WP is an atomic
operation: nothing is "done" until it's live in dev and healthy.

## Entry points

```bash
# Single WP (power-user / debugging)
/sulis-execution:run-wp WP-NNN

# Whole INDEX (the orchestrator walks it)
/sulis-execution:run-all

# Read-only status
/sulis-execution:status

# Retry a blocked WP after the external blocker is resolved
/sulis-execution:retry WP-NNN
```

## What's in this plugin

- **`agents/executor.md`** — the per-WP atomic-lifecycle agent.
- **`agents/orchestrator.md`** — walks the WP INDEX, dispatches the
  executor. (Ships in v0.4; see version history.)
- **`skills/run-wp/SKILL.md`** — `/sulis-execution:run-wp WP-NNN`.
- **`skills/run-all/SKILL.md`** — `/sulis-execution:run-all`.
- **`skills/status/SKILL.md`** — `/sulis-execution:status`.
- **`skills/retry/SKILL.md`** — `/sulis-execution:retry WP-NNN`.
- **`references/lifecycle.md`** — the 10-step lifecycle in detail.
- **`references/primitive-scaffolds.md`** — per-primitive RGB scaffolds.
- **`references/self-heal-budget.md`** — failure-type → budget →
  escalation.

## Composition with marketplace standards

- **`git-workflow-standard.md`** (GIT-01..GIT-10) — every branch /
  commit / push / merge follows this.
- **`executor-loop-standard.md`** (EL-01..EL-08) — every failure-
  handling moment runs OODA + Five Whys + scope guard + budget per
  this.
- **`red-green-blue.md`** (RGB-01..RGB-03) — the load-bearing test
  cycle; Blue is non-negotiable.
- **`change-primitives.md`** — the executor branches on the WP's
  `primitive` field to apply the appropriate scaffold.
- **`engineering-principles.md`** (EP-02 / EP-03 / EP-07) — Quality
  Paramount, Reuse First, Boy-Scout-Scoped.
- **`convention-preference-standard.md`** (CP-01..CP-05) — every
  technical choice defaults to the established convention.
- **`audience-adapted-framing-standard.md`** (AAF-01..AAF-09) — applies
  to BLOCKER plain-English summaries (which the concierge surfaces).

## Versioning

- **v0.1.0** — worktree + RGB + lint + commit + push. Stops at branch
  pushed to remote. EXPAND-group primitives only (Reuse / Compose /
  Extend / Generate / Create).
- **v0.2.0** — adds CI poll + direct squash-merge to `dev` on CI
  green. No PR ceremony.
- **v0.3.0** — adds Sulis SDK deploy + health-check polling + smoke-
  test + mark `done` in INDEX. Full atomic lifecycle.
- **v0.4.0** — adds orchestrator agent + `run-all` + `retry` skills.
  Concierge Phase 5 dispatches the orchestrator via Agent tool.
- **v0.5.0** — adds REORGANISE / SUBSTITUTE / CONTRACT / REINFORCE
  primitive scaffolds (full 22-primitive coverage).

## Sibling plugins it pairs with

- **`sulis`** (concierge agent) — Phase 5 (Implement) spawns the
  orchestrator; translates BLOCKER plain-English summaries into founder
  updates. Previously `sulis-concierge`; absorbed at sulis v0.2.0.
- **`sea`** (`sea:decompose`) — produces the WPs the executor
  consumes; `sea:verify` confirms the executor's output is complete.
- **`sulis-platform-sdk`** — provides the deploy + health-check
  primitives the executor uses at lifecycle steps 8-10.
