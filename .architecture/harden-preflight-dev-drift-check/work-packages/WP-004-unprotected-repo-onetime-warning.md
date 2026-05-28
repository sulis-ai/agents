---
id: WP-004
slug: unprotected-repo-onetime-warning
title: wpx-preflight protection-status + one-time unprotected-repo warning on run-all & ship
kind: backend
status: pending
primitive: Create
group: expand
source_delta: HD-004
dependsOn: [WP-002, WP-003]
blocks: []
estimated_token_cost: "input: ~16k / output: ~6k"
files:
  - plugins/sulis/scripts/wpx-preflight
  - plugins/sulis/scripts/tests/unit/test_wpx_preflight.py
  - plugins/sulis/skills/run-all/SKILL.md
  - plugins/sulis/skills/change/SKILL.md
  # Blue extract-now targets (CLAUDE.md #2 — second caller of the free-plan
  # predicate): the shared _is_freeplan_protection_403 + _FREEPLAN_403_MARKER
  # move to _wpxlib.py and both scripts import them. In-scope for this WP.
  - plugins/sulis/scripts/_wpxlib.py
  - plugins/sulis/scripts/wpx-arrival-check
---

## Context

Implements HD-004 — the awareness half of lesson #52. Adds a
`wpx-preflight protection-status` subcommand that surfaces WP-002's free-plan
distinction as a closed three-state enum, and wires a one-time, plain-English,
non-blocking warning into both `/sulis:run-all` (Step 0, alongside the dev-clean
gate) and `/sulis:change ship` (at the branch-ci wait).

`dependsOn: [WP-002, WP-003]` — WP-002 supplies the free-plan predicate; WP-003
supplies the `wpx-preflight` CLI this subcommand is added to.

## Contract

**`wpx-preflight protection-status` subcommand:**

```
wpx-preflight protection-status --repo <org/repo> --branch <branch=dev>
```

Always `ok:true` (informational, never a blocker):

```json
{"ok": true, "data": {"protection": "protected | unavailable-free-plan | unconfigured"}}
```

- `protected` — protection API returns 200.
- `unavailable-free-plan` — 403 with the "Upgrade to GitHub Pro…" marker
  (reuses WP-002's `_is_freeplan_protection_403`).
- `unconfigured` — `rc != 0` without the free-plan marker (capable but not set).

**run-all/SKILL.md MODIFIED** — in Step 0, after the dev-clean gate, call
`protection-status`. On `unavailable-free-plan`, emit the one-time warning
(founder-English), then proceed regardless.

**change/SKILL.md MODIFIED** — in the `ship` flow at step 4 (the `branch-ci`
wait), call `protection-status` for the base branch. On `unavailable-free-plan`,
emit the same warning once per ship, then proceed (PR + branch-ci wait + review
gate unchanged; warning never gates the merge).

"Warn once" = once per invocation (per run-all run / per ship). No persistence,
no silencing (spec decided-by-default).

## Definition of Done

### Red (failing tests first)

Add to `plugins/sulis/scripts/tests/unit/test_wpx_preflight.py`:

- `test_protection_status_freeplan_403_reports_unprotected` — free-plan 403 mock
  → `ok:true`, `data.protection == "unavailable-free-plan"`.
- `test_protection_status_protected_reports_protected` — 200 mock →
  `data.protection == "protected"`.
- `test_protection_status_genuine_missing_reports_unconfigured` — 404 mock (no
  marker) → `data.protection == "unconfigured"`.

### Green (make them pass)

- Add the `protection-status` subcommand consuming the free-plan predicate.
- All three tests pass; WP-003's `dev-clean` tests still pass.
- run-all/SKILL.md: Step 0 emits the one-time warning on `unavailable-free-plan`,
  proceeds regardless. No warning on `protected`/`unconfigured` for the warning
  surface (spec: public/protected emit no warning).
- change/SKILL.md: `ship` step 4 emits the same one-time warning, proceeds.

### Blue (refactor — the extract-now rule fires here)

- **Two callers now consume `_is_freeplan_protection_403`** (`wpx-arrival-check`
  from WP-002, `wpx-preflight` from this WP). Per CLAUDE.md non-negotiable #2,
  extract the shared predicate (+ `_FREEPLAN_403_MARKER`) to `_wpxlib.py` in
  THIS PR, and have both scripts import it. Do not defer.
- Warning copy in both skills MUST match WP-002's RC-02 warning wording (one
  voice). If they drift, unify on the `_wpxlib` home or a shared copy block.
- Confirm `protection-status` is always `ok:true` (never blocks) — assert this in
  the Green tests and keep it true after the refactor.

## Test strategy

Subprocess + `mock_gh` for the script subcommand. The two skill-body warnings are
markdown — reviewer-checked for: one-time-per-invocation, plain-English copy,
non-blocking (proceeds regardless), public/protected emit nothing. A
`/sulis:verify-architecture` pass drives both surfaces against a mocked free-plan
403 (run-all warns once; ship warns once; neither blocks).

## Honest note

Both surfaces are founder-facing. The warning copy MUST pass founder-English:
no `RC-02`, `403`, `gh api`, `wpx-preflight`. Plain: "branch protection isn't
available on your plan, so the automated checks can't block a manual merge — only
merges I route through Sulis are checked before landing."
