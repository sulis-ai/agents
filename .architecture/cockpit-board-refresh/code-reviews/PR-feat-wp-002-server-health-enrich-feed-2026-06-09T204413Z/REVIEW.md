# Code Review: WP-002 — Server: derive health + enrich the board feed

> **Timestamp:** 2026-06-09T204413Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-002)
> **Branch:** feat/wp-002-server-health-enrich-feed → change/feat-cockpit-board-refresh
> **Files changed:** 21 (1866 insertions, 47 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the server side of the board's change-health signal: each row in the
board list now carries whether the change is waiting on you, a cheap on-track / off-track /
"not enough signal yet" health read, and a last-activity time — all from one read, no
extra network calls. The work is well-scoped (server only), fully tested (9 new test
files, 1347 tests green), and built around one load-bearing rule: a single broken or
missing change folder can never crash the board — it just shows an honest "unknown" and
the other cards render fine. No issues that need attention.

## What to fix

No issues that need attention.

One small thing for awareness (not blocking): when you *search* the board, the code reads
each surviving change's folder twice — once to score the search match, once to shape the
result row. It's harmless (the reads are cheap and bounded to the changes on screen), and
the technical design document already says folder-read tuning is a separate future task,
so it's left as-is here. Noted below for a later pass.

## How this pull request is shaped

**Size — worth looking at.** 1,866 lines across 21 files. Most of that is tests (9 test
files) and explanatory comments, not logic — the four new building blocks are small and
pure. Single concern (the feed enrichment), single `feat:` scope.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files,
no secrets. Every new read is read-only and proven (by a dedicated test suite) to never
crash the board.

**Completeness — clean.** Five new source files, nine new test files. Every new behaviour
has a test, including the failure paths (gone folder, garbage data, hundreds of changes).

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, WPB-NN, lens IDs) for engineers and
> downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every changed
file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). Server `tsc --noEmit -p server`
  exit 0; `eslint` on all changed files exit 0.
- **PR Hygiene:** size medium (1866/21); scope/safety/completeness low. No PH-03 high.
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single low finding is a deferred-by-ADR optimisation → Watch List,
  no delta per CR-04: no failing characterisation test to anchor it).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture (WPB-01..12) | 0 | 0 | Dependency direction holds; pure libs import only types; reads behind the route layer (WPB-01). |
| Security | 0 | 0 | No secrets; worktree reads contained via safeJoin + realpath (MUC-4); reasons fixed-set (FR-32). |
| Quality | 1 (low) | 0 | Search route double-reads survivor context (bounded; ADR-002-deferred). |

### Build Verification (CR-01)

Nothing surfaced. Server typecheck exit 0, eslint exit 0 on all changed files
(`tool-outputs/typecheck-server-head.log`, `tool-outputs/eslint-head.log`). The full
combined `npm run typecheck` (server + client) and `npm run lint` were green at Step 6;
the one client-side error (`StageColumn.test.tsx` fixture missing WP-001-widened fields)
was pre-existing on the base branch and completed mechanically in this PR.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread: {feat}; module_fan_out: 1 (apps/cockpit) → low
Size (PH-02):        +1866 / -47; files 21; generated_ratio ~0 → medium (1001+ band, but test/comment-heavy)
Safety (PH-03):      migrations 0; schema/idl 0; infra 0; secrets 0 → low
Completeness (PH-04): new_source 5; new_tests 9; new_source_without_test 0 → low
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

#### `apps/cockpit/server/routes/search.ts:74,86` — low (quality)

**What:** `assembleSearchable` calls `gatherChangeStatus(deps, record)` (for content +
attention) for every record; then the survivor-shaping loop calls
`gatherChangeEnrichment(deps, record)` — which itself calls `gatherChangeStatus` again —
for every *surviving* record. Survivors are thus read twice.

**Quoted text:**
```ts
const items = await Promise.all(records.map((record) => assembleSearchable(deps, record)));
const survivors = searchChanges(items, { q, stage, needsAttention });
const results = await Promise.all(
  survivors.map(async (record) => {
    const { liveness, enrichment } = await gatherChangeEnrichment(deps, record); // re-reads
    return toWireChange(record, liveness, enrichment);
  }),
);
```

**Why it matters:** Wasted best-effort filesystem reads for the searched (filtered) subset
only — not the full board. Bounded by the on-screen survivor count; reads are idempotent.
The board feed itself (`changes.ts`, the WP's load-bearing path) does a single gather per
record — no double-read there.

**Why not fixed here:** Threading the already-gathered context through `searchChanges`
would expand the search route's surface beyond WP-002's enrichment concern, and ADR-002
explicitly defers per-record fan-out tuning to a separate optimisation WP. EP-07 (scope
your improvements) → Watch List, not an in-WP fix.

### Findings in the Neighbours

Nothing surfaced. The `toWireChange` signature change rippled to three call sites (list,
detail, search) — all updated in lockstep; the characterisation test pins the preserved
field mapping; 854 server tests green confirm no neighbour regression.

### Watch List

- **Search survivor double-read** (above) — bounded, ADR-002-deferred. No failing
  characterisation test to anchor a delta (CR-04) → no Hardening Delta.
- **CR-10 bounded fan-out** — `changes.ts:52` and `search.ts:86` are `.map(async)` over
  records with per-record filesystem reads. NOT an N+1 anti-pattern: this is the single
  bounded `Promise.all` ADR-002/MUC-2 sanctions (board-sized set, no per-card HTTP, no
  second poll), proven bounded at N=400 by `changes.scale.test.ts` (S-25). Benign per the
  CR-10 context-read carve-out.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p server` (exit 0); `npx eslint`
  on 9 changed source files (exit 0). Base: green. Head: green. No PR-introduced errors.
- [✓] **CR-02 Dispatch shape.** Diff 1866 lines / 21 files — above carve-out; reviewed as a
  backend WP against WPB-01..12 across the three lenses (single-session, full-file reads).
- [✓] **CR-03 Full-file reads.** All changed source files (each new lib + the 4 modified
  routes + helper) read end-to-end during authoring and review.
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line + quoted text. No
  delta drafted (no failing characterisation test to anchor — Watch List instead).
- [✓] **CR-05 Severity rubric.** 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (dependency direction holds,
  reads behind route layer, never-throw discipline). Security: nothing surfaced (no secrets;
  safeJoin+realpath containment MUC-4; fixed-set reasons FR-32; readTestsState fixed-relpath
  no-traversal). Quality: 1 low (search double-read) + test-coverage (9 new test files cover
  every new behaviour incl. failure paths) + CR-10 (bounded fan-out, benign).
- [✓] **CR-09 PR Hygiene applied.** Scope low, Size medium, Safety low, Completeness low.
  No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --staged` vs `change/feat-cockpit-board-refresh`.
- **Neighbour expansion:** `toWireChange` call sites (grep) — list/detail/search, all in diff.
- **Scanners run:** tsc, eslint (project mechanical floor). No external SAST (not configured).
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed; manual secret grep clean.
