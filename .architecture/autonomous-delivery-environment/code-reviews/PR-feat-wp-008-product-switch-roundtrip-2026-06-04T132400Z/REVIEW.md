# Code Review: PR feat/wp-008-product-switch-roundtrip — Journey K: switch the active Product → the board re-scopes

> **Timestamp:** 2026-06-04T132400Z (ISO 8601 UTC)
> **Author:** executor (WP-008)
> **Branch:** feat/wp-008-product-switch-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 28 (13 modified, 15 new; net +162 / −154 — the deletions are the superseded single-Product scope lib + its test)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds the multi-product switcher and promotes the board's
change list from the old "one implicit product" scope to a real
`change → Project → Product` roll-up computed on the server. It is clean: no
build errors, the read-only guarantee still holds (the gate scans 131 files
and finds nothing that writes), and every new piece has tests. The whole app
stays GET-only — the builder chose the `?product=` query-param approach, so
the one-write-path rule (chat only) is untouched.

The single most useful thing to know: against the real brain (which has no
products defined yet) the switcher correctly shows one implicit product and
the board shows all changes — and with two products seeded it lists both and
re-scopes when you pick the other. Both paths were exercised live.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** ~160 lines of real new logic (plus tests and the removal of
the now-dead single-Product helper). Well within a comfortable review size.

**Scope — clean.** Single concern: the product switcher + its server-side
scope. One feature, one branch.

**Safety — clean.** No database migrations, no schema/contract files, no
secrets, no infrastructure changes. The new endpoint is read-only and the
read-only gate proves it.

**Completeness — clean.** Six new test files cover the new behaviour: the
pure roll-up, the product reader (including the single-product fallback), the
products route + scoped board/search, the switcher component, the products
hook, and the board re-scope round-trip.

## Things to take away

Nothing to add — the pull request is well-shaped and the honest
single-product reality is handled correctly and documented.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `npm run typecheck` exit 0, `eslint` exit 0 on HEAD.
- **PR Hygiene:** 0 findings (PH-01 scope low, PH-02 size low, PH-03 safety none, PH-04 completeness none).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`tool-outputs/typecheck-head.log` (exit 0) and `tool-outputs/eslint-head.log`
(exit 0). The mechanical baseline also ran as Step 6 of the executor
lifecycle: typecheck pass, eslint pass, read-only gate clean (131 files),
full suite 585 passed. No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: apps/cockpit only            → clean
  severity: low

Size (PH-02):
  lines_added: 162, lines_removed: 154 (deletions = superseded scope lib+test)
  files_changed: 28 (15 new, 13 modified; ~160 lines real new logic)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: low

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (6 new test files cover the new behaviour)
  api_change_without_schema: false (GET /api/products + ?product= are documented in the SIGNED openapi.yaml; api-types already carried Product/ProductList from WP-001)
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The diff touches `routes/changes.ts`, `routes/search.ts`, `app.ts`,
`lib/readBrain.ts`, `client/pages/Board.tsx`, `client/components/Sidebar.tsx`
and their hooks; all callers/callees were reviewed. The `readBrain` refactor
(extracting `brainFs.ts`) is behaviour-preserving and pinned by the existing
`readBrain.test.ts` + `routes.brain.test.ts` (both green).

### Notable design points reviewed (no finding)

- **CR-10 (performance).** `readProducts.rollUpChange` is an O(changes ×
  projects) nested loop, but the only filesystem read (`readProjects`) runs
  ONCE before the loop; the per-change body is pure in-memory prefix
  matching, and `projects` ≈ number of products (small). No N+1 IO.
  `listScopedChanges` adds one shallow brain-directory scan per board fetch
  (same cost class as the existing brain route's per-request read; fail-soft;
  local read-only cockpit). Benign.
- **Read-only gate (ADR-003/009).** The builder took the `?product=`
  query-param variant — the seam stays all-GET, no `POST /api/products/active`,
  so no scope-selection gate classification was needed. The gate (shell +
  vitest inventory) passes unchanged; `routes/products.ts` registers only
  `router.get`.
- **Honest single-product reality.** The real brain has no `dna:product`
  entities; `readProducts` synthesises one implicit Product (active) and the
  roll-up index stays empty → productScope's trivial branch returns all
  changes. Verified live (94 changes, scoped == unscoped). Two-product
  switching verified live against a seeded brain.

### Watch List

- When a second Product is genuinely minted in the brain, the
  `change → Project → Product` roll-up keys on the change's worktree path
  falling under a Project's `source.path`. Changes whose Project cannot be
  resolved are left out of any specific Product's scope (correct — no leak),
  but this depends on Projects carrying a `source.path` that roots their
  changes' worktrees. No action now; noted for the calling session driving
  the two-product observed gate.

### Cross-Reference

- No prior `.security/{project}/viability-report-*.md` to cite.
- No existing hardening deltas to cite or duplicate.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (tsc server+client) exit 0; `eslint --ext .ts,.tsx .` exit 0 on HEAD. Base is green (the executor baselined the suite at 560 before any change). Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Diff is ~160 lines of real new logic in one cohesive feature confined to `apps/cockpit/`; the 15 new files are the products lib + 6 test files. Justified by bounded size + zero cross-module fan-out.
- [✓] **CR-03 Full-file reads.** All changed/new files >50 lines read end-to-end (productScope, readProducts, ProductSwitcher, _product-scope, the route + hook + component edits, README). Unread: none.
- [✓] **CR-04 Evidence discipline.** No findings; the design points reviewed cite file + line ranges.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings at any severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked: new domain→infra imports none; new singletons none; the activeProduct React context is request-scoped UI state, not a server singleton; no new external calls/timeouts/secrets). Security: nothing surfaced (checked SEC access-control — products route + ?product= are read-only scope selection, no mutation, no session start; no injection — query value is used only for Map lookup + string equality; no secrets; SC no new deps). Quality: jsx-ident-scan `{productList}`/`{setActiveProductId}` both resolve in Sidebar scope; no dead surface; no contract drift (Product/ProductList match the openapi + api-types); tests present for all new behaviour; CR-10 no anti-pattern matches (see design points).
- [✓] **CR-09 PR Hygiene applied.** PH-01 scope low (single `feat`), PH-02 size low (~160 lines), PH-03 safety none (0 migrations/schemas/secrets/infra), PH-04 completeness none (6 new tests). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/create-autonomous-delivery-environment` (working tree; pre-commit review per Step 6.5).
- **Neighbour expansion:** git grep over the touched route/hook/component symbols within `apps/cockpit/`.
- **Neighbour cap:** not reached.
- **Scanners run:** tsc, eslint, the cockpit read-only inventory gate (shell + vitest).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (bounded diff, one feature).
