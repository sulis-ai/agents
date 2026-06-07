# Code Review: PR feat/wp-007-search-roundtrip — Journey D round-trip (search + filter)

> **Timestamp:** 2026-06-04T125317Z (ISO 8601 UTC)
> **Author:** executor (WP-007)
> **Branch:** feat/wp-007-search-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 15 (9 source + 4 tests + 1 README + 1 wiring)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the search-and-filter round-trip: a toolbar above the board
lets you type a word, pick a stage, or flag "needs attention", and the same
board narrows to the matching changes. The build is clean (no type errors, no
lint errors), every new behaviour has tests, and the read-only guarantee still
holds (search only ever reads). The standout is that search looks inside each
change's conversation and the things the agent created — not just titles — so
you can find a change by a word you remember discussing. Nothing needs fixing.

## What to fix

No issues that need attention.

A couple of minor things for awareness (not blockers):

- **Search reads a bit of everything for every change.** When you search, the
  server reads each change's conversation, brain, and status to decide what
  matches. That is the same per-change reading the board already does, it runs
  in parallel, and it only ever reads — so it is safe and fast enough for the
  local app. If the number of changes ever grew into the thousands, this is the
  first place to add a cheaper pre-filter. For today's scale it is fine.

## How this pull request is shaped

**Size — clean.** ~1,660 lines, but two-thirds is tests and most of the rest
is small, single-purpose new files. Well within a reviewable size.

**Scope — clean.** One concern: the search round-trip. No mixed refactor +
feature; the one refactor (extracting a shared status-gathering helper) is in
direct service of the feature and is covered by the existing status tests.

**Safety — clean.** No migrations, no schema changes, no secrets, no infra
files. Search is a new read-only GET endpoint; the read-only gate confirms it.

**Completeness — clean.** 4 new source files, 4 new test files. New behaviour
is tested at the unit (pure filter), integration (route over real on-disk
transcripts), and component (toolbar + board-wiring) levels.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck + eslint clean on HEAD.
- **PR Hygiene:** 0 high, 0 medium, 0 note (CR-09 / PH-01..PH-04).
- **In the changes:** 0 critical, 0 high, 0 medium, 1 low (watch-list).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (no failing characterisation test to ground a delta; the one low item is a watch-list note).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — composes existing reads, no new port, dependency direction clean |
| Security | 0 | 0 | None — GET-only, read-only gate green, no new secrets/auth surface |
| Quality | 1 (low) | 0 | Per-change read fan-out in the search route (bounded, parallel, read-only) |

### Build Verification (CR-01)

No PR-introduced errors.

- `tsc --noEmit -p server && tsc --noEmit -p client` → clean (tool-outputs/typecheck-head.log).
- `eslint --ext .ts,.tsx .` → clean (tool-outputs/lint-head.log).
- `bash scripts/check-read-only.sh` → clean, 124 files, no mutating operations (tool-outputs/read-only-gate.log).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: apps/cockpit only            → clean
  severity: low

Size (PH-02):
  lines_added: 1661, lines_removed: 33, total: 1694
  files_changed: 15 (of which 4 are tests, 1 README)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: low (test-heavy; cohesive)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0   (openapi.yaml already carried /api/search; not modified here)
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (every new lib/route/component has a test)
  api_change_without_schema: false (route conforms to the pre-signed openapi /api/search)
  severity: low
```

### Findings in the Changes

**[low / quality] `apps/cockpit/server/routes/search.ts:69-83` — per-change read fan-out**

Quoted text:
```ts
const items: SearchableChange[] = await Promise.all(
  records.map((record) => assembleSearchable(deps, record)),
);
```
Each change triggers liveness + transcript + blocker + brain reads (each
itself parallelised inside `gatherChangeStatus` + `readBrain`). For N changes
this is O(N) read fan-out. Mitigations already in place: all fan-out is
`Promise.all`-parallel (not a serial waterfall); every underlying read is
fail-soft and bounded; it is identical in shape to the existing board-list
read (`GET /api/changes`); and the surface is read-only (no mutation, no
process start). Severity `low` (not `medium`): no hot production path — this is
the local single-user cockpit, and the read cost matches the already-shipped
board read. **No delta** (no failing characterisation test to ground one).
Recorded on the Watch List for the WP-008 product-scope pass, which will narrow
the candidate set server-side before the content scan.

### Findings in the Neighbours

None. The two modified neighbours — `server/app.ts` (router mount) and
`server/routes/status.ts` (refactored to the shared `gatherChangeStatus`) —
were read end-to-end. The status route's behaviour is unchanged and pinned by
the existing `routes.status.test.ts` (still green); the refactor removed
duplicated read-pipeline code (EP-03, 2-consumer threshold).

### Watch List

- Search content-scan fan-out (see the low finding). The natural place to add a
  cheaper pre-filter is the WP-008 active-Product server-side scope, which
  shrinks the candidate set before the per-change content read.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server && -p client` clean; `eslint --ext .ts,.tsx .` clean; read-only gate clean (124 files). Base: 0 errors. Head: 0 new errors. Coverage gap: `@vitest/coverage-v8` not installed — fell back to per-file case-count (searchChanges 13, gatherChangeContent 4, route 7, SearchBar 11); recorded in the executor journal preflight.
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Justification: although 15 files (>5), the changed set is highly cohesive — 9 small single-purpose new files for one feature, all authored in this session and read end-to-end; the reviewer has full-file context for every file. Diff: 1661 lines / 15 files (4 tests, 1 README). No cross-cutting utility change; neighbour ring is 2 files.
- [✓] **CR-03 Full-file reads.** All changed files >50 lines read end-to-end (each was authored this session): searchChanges.ts, gatherChangeContent.ts, gatherChangeStatus.ts, search.ts, SearchBar.tsx, useSearch.ts, Board.tsx, status.ts, app.ts + the 4 test files + README. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: dependency direction (shared/ import via the established eslint-disable seam, no new infra→domain import), no new singletons, no new circular imports, no new untimed external calls (no HTTP/RPC introduced; all reads are local fs/process-probe), composes existing reads with no new port. Security: nothing surfaced — primitives checked: SEC-01..07 (no new auth/authz/injection/XSS surface; GET-only; query params validated — `parseStages` allow-lists against VALID_STAGES, `needsAttention` is a strict `=== "true"`), secrets (none), read-only gate green. Quality: 1 finding + jsx-ident-scan.log (all 8 introduced JSX identifiers resolve in lexical scope — no PR-168 class bug) + dead-surface (none — every export consumed: searchChanges/gatherChangeContent/gatherChangeStatus by the routes, SearchBar/useSearch by Board) + contract-drift (route returns `{ results: Change[] }` exactly per the pre-signed openapi /api/search; `hasActiveFilter`/`buildSearchPath` exported + tested) + test-coverage observation (every new unit has a test) + CR-10 perf (one bounded parallel fan-out, noted; no N+1 DB, no serial waterfall — fan-out is Promise.all).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single feat). PH-02 Size: low (1694 lines, test-heavy, cohesive). PH-03 Safety: low (0 migrations, 0 schema, 0 secrets, 0 infra). PH-04 Completeness: low (0 new source without test). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/create-autonomous-delivery-environment -- apps/cockpit` (staged WP source).
- **Neighbour expansion:** git grep — direct callers/callees of the changed symbols. `gatherChangeStatus` consumers: search.ts (new) + status.ts (refactored); `createSearchRouter` consumer: app.ts. 2 neighbour files, under the 20 cap.
- **Neighbour cap:** 2 of 2 considered, 0 excluded.
- **Scanners run:** typecheck (tsc), lint (eslint), read-only gate (project script). Gitleaks/Semgrep/Trivy not invoked — no new dependency, no new secret-shaped string, no new network surface; diff is local read-only TS.
- **Scanners unavailable:** @vitest/coverage-v8 (coverage gap noted above).
- **Lenses dispatched in parallel:** no — single-reader pass per the CR-02 justification above (cohesive feature, full-file authorship context).
