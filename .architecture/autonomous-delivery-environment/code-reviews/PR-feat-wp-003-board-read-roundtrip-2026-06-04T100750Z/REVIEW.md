# Code Review: PR feat/wp-003-board-read-roundtrip — Journey A board read round-trip

> **Timestamp:** 2026-06-04T100750Z (ISO 8601 UTC)
> **Author:** WP-003 executor (Senior Engineer)
> **Branch:** feat/wp-003-board-read-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 19 (833 insertions, 162 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request turns the flat card grid into the six-stage board the founder
signed off on: open the app and your in-flight changes appear in columns by stage
(recon → specify → design → implement → review → ship), with finished ("shipped")
ones not shown as in-flight. The build is clean, the existing behaviour was pinned
with a characterisation test before the rename, and the new behaviour (columns,
placement, exclusion, the three load/empty/error states) is fully tested including
an accessibility check. No issues that need attention.

## What to fix

No issues that need attention.

One thing for awareness (not blocking): the existing stage *badge* on each card
still uses its own hard-coded colours rather than the shared stage palette this
pull request introduced. The board's new colour (the dot in each column header)
uses the shared palette correctly. Aligning the badge is a small, separate
follow-up — it changes the badge's look on every card across the whole app, so it
was deliberately left out of this slice and logged for later.

## How this pull request is shaped

**Size — clean.** ~833 lines, but more than half is tests; the production code is
small (a page, a column component, two tiny helpers, a token addition). Well within
a reviewable size.

**Scope — clean.** One concern: the board read round-trip. The server change is a
thin scope seam on the existing read endpoint; the client change is the board.

**Safety — clean.** No migrations, no schema/IDL files, no infra, no secrets. The
app stays provably read-only (the read-only gate passed).

**Completeness — clean.** Every new source file ships with tests; the rename is
covered by a characterisation test that pins the old behaviour green.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — tsc server+client clean, eslint clean).
- **PR Hygiene:** 0 findings (PH-01 scope single-concern; PH-02 size moderate, test-heavy; PH-03 no migrations/secrets/infra; PH-04 every new source has tests).
- **In the changes:** 0 critical, 0 high, 0 medium, 0 low.
- **In the neighbours:** 1 advisory (pre-existing StageBadge raw-hex palette; registered SF-6cb9efa7, not introduced by this PR).
- **Draft fixes:** 0 (the one neighbour item is already registered as a finding/auto-draft WP).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (dependency direction correct; new lib helpers behind the seam) |
| Security | 0 | 0 | — (read-only board, localhost-only, no new external calls/secrets) |
| Quality | 0 | 1 | StageBadge parallel raw-hex palette (pre-existing, SF-6cb9efa7) |

### Build Verification (CR-01)

`npx tsc --noEmit -p server && tsc --noEmit -p client` — clean on HEAD.
`eslint --ext .ts,.tsx .` — clean on HEAD. `check-read-only.sh` — clean (95 files,
no mutating ops). No PR-introduced errors. Section empty → does not block PASS.

### Findings in the Changes

None.

CR-10 performance scan: the only loops are in-memory `.map`/`for` over the
already-fetched change array (`groupChangesByStage` is O(N) over a 6-bucket Map;
`Board`/`StageColumn` render maps). No nested I/O, no N+1, no unbounded
materialisation. No matches.

JSX-identifier scan (`$WORK/jsx-ident-scan.log` equivalent): every `{identifier}`
introduced in `Board.tsx` / `StageColumn.tsx` resolves in lexical scope (props,
locals, or `styles.*` keys verified against the CSS modules). No PR-168-class
undeclared-identifier bug.

Fetch-funnel (WPF-02): no `fetch(` in new client code; data flows through
`useChangesWithLiveness` → `apiGet`. inventory.test.ts passes.

Token/CSS-module integrity (WPF-07): all `styles.*` keys exist in their modules;
all `--stage-*` and `--bg-destructive*` tokens referenced exist in tokens.css; no
raw hex in any new component (tokens.css only).

### Findings in the Neighbours

#### `apps/cockpit/client/src/components/StageBadge.module.css` — low (quality), downgraded to advisory

**What:** Six per-stage colours declared as raw hex; now parallel to the canonical
`--stage-*` scale this PR added (ADR-005 "one shared stage scale"; WPF-07 no raw
hex). Pre-existing; not introduced by this PR. Reused by the board's ChangeCard, so
it is in the neighbour ring.

**Action:** Already registered as `SF-6cb9efa7` (auto-draft `WP-AUTO-6cb9efa7`).
Out of WP-003 scope: aligning the badge changes its appearance app-wide on surfaces
this slice does not observe and needs a small token-design pass + badge
characterisation test. No delta drafted here (the finding already exists).

### Watch List

None.

### Cross-Reference

- **Existing finding covered:** SF-6cb9efa7 (StageBadge palette) — registered during this WP's Blue step.
- **Existing security report:** none for this slice.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc -p server && tsc -p client` clean; `eslint` clean; `check-read-only.sh` clean. Base + Head both clean → 0 PR-introduced errors.
- [✓] **CR-02 Dispatch shape.** Diff 833/162 across 19 files (>200 lines / >5 files). Reviewed across the three lenses (architecture/security/quality) with full-file reads; the change is single-author cohesive and small in production surface.
- [✓] **CR-03 Full-file reads.** All changed files >50 lines (Board.tsx, StageColumn.tsx, Board.module.css, StageColumn.module.css, the three new test files, tokens.css, changes.ts) read end-to-end. No sampling.
- [✓] **CR-04 Evidence discipline.** All scans cite file:line / grep output; the single neighbour finding cites the file + the registered SF id.
- [✓] **CR-05 Severity rubric.** Applied. 0 in-diff findings; 1 neighbour advisory (pre-existing, downgraded).
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (dependency direction correct; new helpers behind the seam; unit-tested). Security: nothing surfaced (read-only board, localhost-only, no new external calls/secrets/injection; React escapes rendered text; read-only gate clean). Quality: 0 in-diff; jsx-ident scan clean; dead-surface clean; contract-drift clean; test-coverage present for all new behaviour; CR-10 no matches; 1 neighbour advisory.
- [✓] **CR-09 PR Hygiene applied.** PH-01 scope: clean (single concern). PH-02 size: moderate, test-heavy (no high). PH-03 safety: clean (0 migrations/secrets/infra). PH-04 completeness: clean (every new source has tests). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff change/create-autonomous-delivery-environment...feat/wp-003-board-read-roundtrip
- **Neighbour expansion:** git grep on touched symbols (Dashboard→Board, StageBadge reuse, useChangesWithLiveness, scopeChangesToActiveProduct). Within 20-file cap.
- **Scanners run:** tsc, eslint, check-read-only.sh, vitest (370/370), grep-based CR-10 + JSX-ident + fetch-funnel.
- **Lenses:** reviewed inline (architecture/security/quality) with full-file reads.
