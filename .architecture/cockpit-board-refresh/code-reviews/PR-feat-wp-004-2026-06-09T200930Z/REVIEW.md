# Code Review: feat/wp-004-full-height-lanes — Full-height lanes (sticky header, internal scroll, empty-lane note)

> **Timestamp:** 2026-06-09T200930Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-004)
> **Branch:** feat/wp-004-full-height-lanes → change/feat-cockpit-board-refresh
> **Files changed:** 4 (3 modified, 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change reshapes each board column into a full-height lane: the lane header
stays pinned while the cards underneath scroll on their own, and an empty stage
keeps its place with a quiet "Nothing here yet" note rather than collapsing. The
Recon lane (where new changes begin) gets a small "Start here" button. The build
is clean, the work is tightly scoped to the three files it was meant to touch,
and it ships with a new test file that pins the new behaviour — including an
accessibility check in both light and dark themes. Nothing needs attention
before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 4 files, ~240 lines including the new test. Small and easy to
review.

**Scope — clean.** Single concern (a layout refactor), confined to the stage
column component, its stylesheet, and the board page stylesheet — exactly the
files the work was scoped to.

**Safety — clean.** No database changes, no schema changes, no infrastructure
files, no secrets. This is presentation-layer only — it changes how the board
looks and scrolls, not what data it reads.

**Completeness — clean.** A new test file accompanies the change and covers the
new behaviour (sticky header, internal-scroll list, the empty-lane note, the
Recon-only "Start here" button), plus an automated accessibility check.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers
> and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck exit 0, lint exit 0.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (presentational component; no imports/calls/state added) |
| Security | 0 | 0 | — (no input handling, no secrets, no dependency change) |
| Quality | 0 | 0 | — (full test coverage incl. jest-axe light+dark) |

### Build Verification (CR-01)

No PR-introduced errors. `npm run typecheck` (tsc server+client) exit 0;
`npm run lint` (eslint --ext .ts,.tsx) exit 0. Raw logs in `tool-outputs/`.
(Note: a root-relative `tsc -p apps/cockpit/client` invocation emits TS5058
"path does not exist" — an invocation artifact, not a code error; the
project's own typecheck script run from the app dir is the authoritative
green floor.)

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type: {refactor}; module_fan_out: 1 dir → none
Size (PH-02):        +188 / -52; files: 4 → none (within smallest band)
Safety (PH-03):      migrations: 0; schemas: 0; infra: 0; secrets: 0 → none
Completeness (PH-04): new_source_without_test: 0; new_tests: 1 → none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The change renames the StageColumn CSS-module class set
(`col*` → `lane*`); the only consumer of `styles.*` is StageColumn.tsx itself
(CSS-module-scoped, no string class references elsewhere). `Board.tsx` consumes
`<StageColumn>` by component, not by class — unaffected. The no-raw-colours
characterisation test that parses `Board.module.css` still targets `.errorBox`/
`.errorMessage` (untouched) and passes.

### Watch List

None.

### Cross-Reference

- No prior `.security/cockpit-board-refresh/` viability report to cite.
- No existing hardening deltas covered.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (tsc server+client) exit 0; `npm run lint` exit 0; JSX identifier scan over StageColumn.tsx + test (`{name}`, `${stage}` — both in lexical scope). Base & head both green. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: ~240 lines, 4 files** (≤200 source lines + ≤5 files; the new test file is the bulk of the line count). Below the parallel-dispatch threshold.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end (StageColumn.tsx 110 lines, StageColumn.module.css 197 lines, Board.module.css 105 lines, StageColumn.test.tsx 232 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens "nothing surfaced" entries recorded with checks run.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 none).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: domain→infra import direction (none), module singletons (none), circular imports (none), external calls/timeouts/breakers (none — pure presentational), contract-test presence (StageColumn.test.tsx pins behaviour). Security: nothing surfaced — primitives checked SEC-01..07 (no input handling, no auth surface, no injection vector, no secret; `Link to="/start"` is a static internal route), SC-01..04 (no dependency change). Quality: nothing surfaced — (1) build verification clean; (2) jsx-ident-scan.log: `{name}`/`${stage}` in scope; (3) no dead surface (Link, BoardStage, every style class referenced); (4) no contract drift (props unchanged: stage, changes); (5) test coverage present (18 cases incl. jest-axe light+dark on populated+empty lane); (6) style clean; (7) CR-10 perf — single bounded `changes.map()` render, no per-iter I/O, no anti-pattern.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single refactor concern, 1 dir). PH-02 Size: none (+188/-52, 4 files). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: none (new test accompanies new behaviour). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-board-refresh` (working tree, WP not yet committed at review time).
- **Neighbour expansion:** git grep for `styles.col`/`styles.lane` string consumers — none outside StageColumn.tsx (CSS-module-scoped). Board.tsx consumes by component, not class.
- **Neighbour cap:** not reached (0 of ≤20).
- **Scanners run:** typecheck (tsc), lint (eslint), jsx-ident-scan.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked — no diff signal warranting them (no secrets pattern, no dependency change, no Dockerfile/infra). Recorded as scoped-out, not a coverage gap.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (diff within size limit).
