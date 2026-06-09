# Code Review: WP-009 — Card selected (route-derived) + interaction/focus states

> **Timestamp:** 2026-06-09T223438Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-009)
> **Branch:** feat/wp-009-card-selected-interaction → change/feat-cockpit-board-refresh
> **Files changed:** 4 source (+3 new test files)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds two card states to the board: a card is marked as the
currently-open one (when you have that change open in a tab), and the card
now has clear keyboard focus, hover, and pressed feedback. It is small and
tightly scoped — about 116 lines across four files, plus three new test
files covering the behaviour. The build is clean, every test passes (1481 of
1481), and there are no issues that need attention.

## What to fix

No issues that need attention.

The change reuses the patterns already in the codebase: the "which change is
open" check is read from the page address exactly the way the rest of the app
does it, and the selected-card marker mirrors the existing sidebar's
selected-row treatment. All the colours come from the shared design palette
(no hand-picked colours), and the selected marker is more than just a colour —
it has a thick inset edge bar so it is still distinguishable for someone who
cannot rely on colour. The accessibility checks pass in both light and dark.

## How this pull request is shaped

**Size — clean.** 116 lines across four files, one concern (the two card
states), with three dedicated test files. Easy to review thoroughly.

**Scope — clean.** A single feature (`feat`), all within the card + its lane
parent + the board page. No mixed refactor-and-feature.

**Safety — clean.** No database migrations, no schema changes, no
infrastructure files, no secrets.

**Completeness — clean.** Three new test files accompany the change, covering
the selected marker (S-32), keyboard focus and activation (S-33), and the
accessibility audit for the new states.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high/medium/low in the diff; Build Verification
empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (one-directional prop threading; correct dependency direction) |
| Security | 0 | 0 | — (no input interpolation, no network, no secrets) |
| Quality | 0 | 0 | — (typecheck + lint clean; tests present; no CR-10 anti-pattern) |

### Build Verification (CR-01)

`npm run typecheck` (`tsc --noEmit -p server && tsc --noEmit -p client`) — clean
on HEAD. `npm run lint` (`eslint --ext .ts,.tsx .`) — clean on HEAD. BASE
(`change/feat-cockpit-board-refresh`) was already green (prior WPs merged).
Delta: 0 PR-introduced errors. Build Verification section empty → no CR-06
auto-downgrade.

JSX identifier scan (`jsx-ident-scan.log`): the diff introduces references to
`{activeChangeId}` (StageColumn, Board) and the `selected` prop (ChangeCard).
Both resolve in lexical scope — `activeChangeId` destructured in `StageColumn`
(line 139) and defaulted in its props (line 209), declared in `Board`
(line 78); `selected` destructured + defaulted in `ChangeCard` (line 213). No
PR-168-class undeclared-identifier bug.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {feat}; module_fan_out: 1 (card + lane + board page) → severity none
Size (PH-02):         lines_added: 116, lines_removed: 6, files_changed: 4, test_files_added: 3 → severity none
Safety (PH-03):       migrations: 0, schema_idl: 0, infra: 0, secret_hits: 0 → severity none
Completeness (PH-04): new_source_without_test: 0 (3 test files added), api_change_without_schema: false → severity none
```

### Findings in the Changes

None.

Architecture lens: nothing surfaced. Checks run: new infra/db imports into
domain (none — card is a pure view component); module-level singletons (none);
circular imports (none — Board → StageColumn → ChangeCard is acyclic,
one-directional); cross-module reach-through (none); new HTTP/RPC/DB calls
(none — selection is read from the route via `useMatch`, no I/O);
secrets (none). The route-read reuses the established `WorkspaceShell`
`useMatch("/c/:changeId")` pattern (EP-03); the marker reuses `SidebarItem`'s
`data-active`/`aria-current` shape.

Security lens: nothing surfaced. Primitives checked: SEC-01..07 (no auth/authz
surface — view component), injection/XSS (none — `aria-current="true"` is a
fixed literal; `data-selected` is boolean-derived; no user content
interpolated by this diff — the pre-existing `aria-label` from `change.handle`/
`change.intent` is unchanged by WP-009), SSRF (none — no network), secrets
exposure (none). Scanners: not separately run for a frontend-only,
input-free, network-free diff; recorded as a scoped coverage note.

Quality lens (CR-07 — all seven outputs):
1. Build Verification follow-up: 0 errors to translate.
2. JSX identifier scan: clean (above).
3. Dead surface: none — both new props (`selected`, `activeChangeId`) are
   consumed; optional defaults preserve existing call sites unchanged.
4. Contract drift: none — no `Change` wire-type field added (selection is
   route-derived, asserted by the "no `selected` on feed/state" Blue grep).
5. Test coverage: strong — `ChangeCard.selected.test.tsx` (S-32: at-most-one,
   none on `/`, survives re-poll, additive over waiting/degraded, token-only
   non-colour marker), `ChangeCard.focus.test.tsx` (S-33: tab order,
   `:focus-visible` ring pinned, Enter navigates, inner button is a separate
   tab stop, Space not swallowed, no hover-only signal),
   `ChangeCard.selected.axe.test.tsx` (selected + focused, light + dark).
6. Style/readability: clean — names follow the codebase; CSS tokens-only.
7. CR-10 performance procedural checks: no anti-pattern matches. The per-card
   `change.changeId === activeChangeId` comparison is O(1), evaluated only for
   the *virtualised* (windowed) cards inside the existing `.map`, not a nested
   loop and not over all N cards — no N+1, no O(N²), no unbounded
   materialisation.

### Findings in the Neighbours

None. Neighbours examined: `WorkspaceShell.tsx` (source of the reused
`useMatch` pattern — unchanged), `SidebarItem.tsx`/`.module.css` (the reused
selection-marker pattern — unchanged), `Board.test.tsx`/`StageColumn.test.tsx`
(existing callers — still green after the optional-prop threading).

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable.
- **Existing security report:** none for this diff.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` + `npm run lint`
  on HEAD: 0 errors. BASE already green. Coverage gap: none. JSX identifier
  scan run.
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified by diff size:
  116 source lines, 4 source files — within the ≤200-line AND ≤5-file
  carve-out. (3 additive test files reviewed alongside.)
- [✓] **CR-03 Full-file reads.** All 4 changed source files read end-to-end
  (`ChangeCard.tsx`, `ChangeCard.module.css`, `StageColumn.tsx`, `Board.tsx`).
  Unread files: none.
- [✓] **CR-04 Evidence discipline.** All observations cite file:line.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + explicit
  nothing-surfaced. Security: 0 findings + primitives-checked note. Quality:
  0 findings + all seven outputs (build, jsx-scan, dead-surface,
  contract-drift, test-coverage, style, CR-10).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none
  (116 lines / 4 files). PH-03 Safety: none (0 migrations / 0 schema /
  0 secrets / 0 infra). PH-04 Completeness: none (3 test files added). PH-03
  high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-board-refresh` (working tree)
  + 3 untracked test files.
- **Neighbour expansion:** git grep (string-based caller scan).
- **Neighbour cap:** 4 of 4 considered, 0 excluded.
- **Scanners run:** typecheck (tsc), lint (eslint), full vitest suite
  (1481 tests). Security scanners (Gitleaks/Semgrep/Trivy) not separately run
  for an input-free, network-free, secret-free frontend diff — scoped coverage
  note.
- **Scanners unavailable:** n/a.
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02).
