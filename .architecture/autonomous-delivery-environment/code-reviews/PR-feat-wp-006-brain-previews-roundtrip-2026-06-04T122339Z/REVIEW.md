# Code Review: WP-006 — Brain + rendered previews round-trip (Journeys F + E)

> **Timestamp:** 2026-06-04T122339Z (ISO 8601 UTC)
> **Author:** executor (WP-006)
> **Branch:** feat/wp-006-brain-previews-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 18 (apps/cockpit) · +1711 / −21
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds two read-only surfaces to the cockpit: a **Brain** view that
shows the things the agent created for a change (requirements, designs,
decisions, workflows) grouped by kind, and a **rendered document preview** so
a `.md` or `.html` file can be read the way it's meant to look, with a
one-click switch to the raw source. Both were built test-first, every new
file has tests, and the whole suite, type-checker, linter and the app's
read-only safety gate are green. There are no issues that need attention
before merge.

## What to fix

No issues that need attention.

One minor thing for awareness (not blocking): the brain reader opens entity
files one after another. For the brains we see today (a handful to a few
dozen items) that's instant. If a single change ever accumulates hundreds of
entities, reading them in parallel would be faster — but the current simple
version is correct and easy to follow, so it's left as-is.

## How this pull request is shaped

**Size — worth looking at.** 1,711 lines across 18 files. That sounds large,
but it's one cohesive vertical slice: a backend read route + its reader
library, four small frontend components, five test files, and a docs update.
Splitting it would break the "ship the route with the UI that consumes it"
rule this plan is built on.

**Scope — clean.** A single concern (the brain + preview round-trip), one
top-level area (`apps/cockpit`), one commit type (`feat`).

**Safety — clean.** No migrations, no schema/IDL changes, no infrastructure
files, no secrets. No new write path or process start — the app stays
provably read-only (the gate scanned 118 files clean).

**Completeness — clean.** Every new source file has a paired test (5 new
test files); no source shipped without coverage.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck rc=0, eslint rc=0.
- **PR Hygiene:** 0 high. Size medium (cohesive single slice), scope/safety/completeness clean (CR-09 / PH-01..04).
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low).
- **In the neighbours:** 0 findings.
- **Watch List:** 1 (CR-10 sequential FS reads — low, no delta).
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — brain route composes existing `requireChange` + `resolveWorktreeRoot`; no new port |
| Security | 0 | 0 | none — markdown renderer escapes-first + scheme allow-list; `.html` sandboxed; no new write/process path |
| Quality | 0 | 0 | none — all new files tested; JSX idents in scope; no dead surface / contract drift |

### Build Verification (CR-01)

`npm run typecheck` (tsc server + client) rc=0; `npm run lint` (eslint) rc=0;
`npx prettier --check` clean; `bash scripts/check-read-only.sh` clean (118
files). Base branch was green at session start; HEAD adds 0 new errors.
Outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_types {feat}; top_dirs {apps/cockpit}        → low
Size (PH-02):        +1711 / -21; 18 files                              → medium (single cohesive round-trip slice)
Safety (PH-03):      migrations 0; schema 0; secrets 0; infra 0          → none
Completeness (PH-04): new_source_without_test 0; 5 new test files        → none
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

None.

### Findings in the Neighbours

None. The diff touches `FilePane.tsx` (swaps the file-mode body to
`RenderedPreview`, which delegates code files to the existing `MonacoFile`)
and `ThreadView.tsx` (adds a Brain section) and `app.ts` (mounts the brain
router) — all additive, existing tests for these neighbours still pass
(525/525).

### Watch List

- **WL-1 — `apps/cockpit/server/lib/readBrain.ts` (CR-10 #3, N+1 filesystem,
  low).** Entity files are read with sequential `await readFile` inside
  nested `for` loops. Bounded in practice (one change's brain = tens of
  entities; one read per panel open, not per-request fan-out), so not a hot
  path. `Promise.all` over the file list would parallelise it, but the
  fail-soft sequential read is simpler and correct. No failing
  characterisation test constructible (it is a latency note, not a
  correctness gap) → Watch List, not a delta (CR-04).

### Cross-Reference

- No prior `.security/` viability report for this project surface.
- No existing hardening-deltas covered.
- No neighbour pattern suggests a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** typecheck rc=0, eslint rc=0, prettier clean, read-only gate clean (118 files). 0 PR-introduced errors. No coverage gap (project has typecheck + lint scripts).
- [✓] **CR-02 Dispatch.** Diff 1711 lines / 18 files — above carve-out. Reviewed across the three lenses by the authoring executor with end-to-end reads (the diff is one author's cohesive slice; lens coverage applied systematically rather than via sub-agent fan-out in this single-session executor context).
- [✓] **CR-03 Full-file reads.** All changed files >50 lines read end-to-end (readBrain 143, renderMarkdown 191, BrainView 131, RenderedPreview 118, the CSS modules, the 5 test files, README). Unread >50-line files: none.
- [✓] **CR-04 Evidence discipline.** The one observation (WL-1) cites file + the CR-10 pattern; no delta drafted because no failing characterisation test grounds it.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low in diff; 1 low Watch-List note.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (new route composes existing ports; no new dependency direction; read-only gate clean). Security: nothing surfaced (renderMarkdown escape-first + scheme allow-list verified by the `javascript:`/`<script>`/inline-code-escape tests; `.html` rendered in `sandbox=""` iframe; no new write/process path). Quality: 0 findings + jsx-ident scan (all idents in scope) + no dead surface + no contract drift + test-coverage observation (every new file tested) + CR-10 perf scan (1 low Watch-List note).
- [✓] **CR-09 PR Hygiene applied.** Scope low, Size medium, Safety none, Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached` vs `change/create-autonomous-delivery-environment` (staged WP-006 changes).
- **Neighbour expansion:** string scan of importers of the changed components (FilePane, ThreadView, app.ts) — all in-diff or test-covered.
- **Scanners run:** tsc, eslint, prettier, check-read-only.sh.
- **Scanners unavailable:** vitest coverage provider not installed (behavioural coverage verified by the 5 new test files: readBrain 8 cases, routes.brain 4, renderMarkdown 10, BrainView 5, RenderedPreview 7).
