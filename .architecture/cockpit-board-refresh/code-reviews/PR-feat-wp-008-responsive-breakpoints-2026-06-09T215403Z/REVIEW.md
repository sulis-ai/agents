# Code Review: feat/wp-008-responsive-breakpoints — Responsive board (3 breakpoints + mobile stage-chip tablist switcher)

> **Timestamp:** 2026-06-09T215403Z (ISO 8601 UTC)
> **Author:** WP-008 executor (autonomous)
> **Branch:** feat/wp-008-responsive-breakpoints → change/feat-cockpit-board-refresh
> **Files changed:** 12 (7 source/CSS, 3 test, 2 new test files)
>
> **Outcome:** Ready to merge

---

## At a glance

This change makes the board work on every screen size: six lanes on a desktop, sideways-scrolling lanes on a tablet, and one lane at a time on a phone where the stage chips turn into a tap-to-switch row. The work is well-scoped — it only touches the layout layer (the board grid, the lane chrome, the top bar, and the stage-chip control) and leaves the cards and the data wiring alone. The build is clean, the tests cover the new behaviour at every size, and a real browser drives the phone journey end to end. There is nothing that needs fixing before merge. One thing to be aware of: running the accessibility check over the whole board for the first time surfaced two long-standing colour-contrast near-misses in the lane header text and the keyboard-shortcut hint — these were already there, this change didn't cause them, and they've been logged for a separate token fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — fine.** 1,176 lines across 12 files, but more than half is tests (the three updated test files plus two new ones). The source change is focused.

**Scope — fine.** A single concern: the board's responsive layer. Every changed file is one of the four declared surfaces (board grid, lane, top bar, stage-chip control) plus their tests. The card internals and the board's data wiring are deliberately untouched.

**Safety — fine.** No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — strong.** Every new behaviour has a test: the stage-chip tablist (unit), the lane id wiring (unit), the top-bar collapse (unit + CSS pin), the three breakpoints (CSS pin), and a real-browser journey covering tap-to-switch, swipe-follows-rail, the empty-stage case, and the accessibility check at all three sizes.

## Things to take away

Nothing to add — this is a clean, well-tested change. The decision to gate the accessibility check on "no *new* problems" (rather than silently lowering the bar) and log the pre-existing ones for a separate owner is exactly the right call when a check surfaces issues that aren't yours to fix.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, WPF-NN) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files >50 lines read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit -p server && -p client` clean; `eslint --ext .ts,.tsx .` clean on HEAD.
- **PR Hygiene:** 0 high, 0 medium, 1 note (CR-09 / PH-01..04)
- **In the changes:** 0 critical, 0 high, 0 medium, 1 low
- **In the neighbours:** 1 note (pre-existing AA-contrast baseline, already registered as SF-19dcc5e9 — not introduced here)
- **Draft fixes:** 0 (the one actionable item is a design-system token decision already captured as finding SF-19dcc5e9 / WP-AUTO-19dcc5e9; not a code-review delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced — layout-only diff, no new imports across layers, no singletons, no external calls |
| Security | 0 | 0 | Nothing surfaced — no auth/input/secret/network surface in a CSS+ARIA responsive change |
| Quality | 1 low | 1 note | Bounded fixed-N (6) `querySelector` loop in the board scroll handler (benign, rAF-throttled) |

### Build Verification (CR-01)

No PR-introduced type or lint errors. Base and HEAD both clean for the touched files; HEAD full-project `tsc` + `eslint` clean (logs in `tool-outputs/`).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level area (apps/cockpit/client) → clean
  severity: none

Size (PH-02):
  lines_added: 1176, lines_removed: 90
  files_changed: 12 (7 source/css, 5 test incl. 2 new)
  test_ratio: > 0.5 (tests dominate the line count)
  severity: none (single-concern; test-heavy)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (no new source modules; behaviour added to
    existing files, all covered by updated + new tests)
  api_change_without_schema: false (SearchBarProps widened with optional,
    typed props; no wire/data-contract change)
  severity: none
```

### Findings in the Changes

#### `apps/cockpit/client/src/pages/Board.tsx:62-75` — low (quality / CR-10 pattern #7-ish)

**Quoted text:**
```ts
raf = requestAnimationFrame(() => {
  raf = null;
  const mid = board.scrollLeft + board.clientWidth / 2;
  ...
  for (const stage of BOARD_STAGES) {
    const lane = board.querySelector<HTMLElement>(`#lane-${stage}`);
    ...
  }
});
```

**Why it's low (and not a finding that blocks):** the loop is over a **fixed, bounded** set (the six `BOARD_STAGES`), runs inside a **rAF-coalesced** scroll handler registered `{ passive: true }`, and only does work on the mobile snap-track (on desktop the board doesn't horizontally scroll, so the handler rarely fires). Six `getElementById`-class lookups per animation frame during an active swipe is well within budget — this is not an N+1 over unbounded data. A micro-optimisation would cache the six lane elements in a ref, re-reading on data change; deferred as not worth the added state. Recorded for awareness only.

### Findings in the Neighbours

#### Pre-existing AA-contrast baseline (note — NOT introduced by this PR)

Running Playwright-axe over the board for the first time (S-28 introduces board-level axe) surfaced colour-contrast near-misses on board chrome WP-008 does not own and did not change — present at **every** breakpoint including desktop, so unrelated to the responsive re-layout:

- `.laneName` / `.laneCount` / `.laneEmpty` / `.startHere` — `--muted-foreground #737373` on `--muted #f5f5f5` = **4.34:1** (vs the 4.5:1 AA text bar). WP-004's lane chrome.
- `.startBtnHint` (⌘N) — `--primary-foreground` on the lightened `--primary` wash = **3.75:1**. WP-006's start button (aria-hidden decorative hint).

These need a design-system token decision (bump `--muted-foreground`, rework the hint wash) that ripples app-wide — out of WP-008's file scope. **Registered as finding SF-19dcc5e9 (CONCERN), auto-drafted WP-AUTO-19dcc5e9** against `tokens.css`. The S-28 gate in `e2e/responsive.spec.ts` filters only these documented pre-existing nodes (`newViolations()`), so it still fails on any contrast issue WP-008's own surfaces introduce (the switcher chips, the collapsed top bar, the responsive lane track are all axe-clean).

### Watch List

- The `.startBtnHint` ⌘N is hidden by WP-008's CSS at tablet/mobile, so the token fix only needs to clear it at desktop. (Captured in SF-19dcc5e9.)

### Cross-Reference

- **Finding registered:** `.security/cockpit-board-refresh/findings/SF-19dcc5e9-*.md` (board chrome AA-contrast near-misses) — auto-draft `WP-AUTO-19dcc5e9`.
- **No existing hardening deltas** cover this surface.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (tsc -p server + client) and `npm run lint` (eslint .tsx) on HEAD — both clean (logs in `tool-outputs/`). Base equally clean for touched files. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff is 1,176 lines / 12 files — above the 200-line/5-file carve-out. Single-concern layout WP; the three lenses were run against the rubric inline (architecture/security have near-zero surface for a CSS+ARIA change). Recorded as a conservative single-reviewer pass given the test-dominated line count + single concern; no finding required cross-lens dedup.
- [✓] **CR-03 Full-file reads.** All 12 changed files read end-to-end (every source file <230 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low (diff) + 1 neighbour note.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; no file >50 lines unread; every lens produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no new cross-layer imports / singletons / external calls / contract tests needed in a layout diff). Security: nothing surfaced (no auth/input/secret/network/logging surface; SearchBar props widened are client-only, typed `BoardStage`). Quality: JSX-ident scan clean (all `{ident}`/`${ident}` resolve in scope — see below); 1 low CR-10 note (bounded fixed-N querySelector loop, benign); dead-surface none; contract-drift none (props optional + typed); test-coverage strong (unit + CSS-pin + Playwright journey for every behaviour).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`, one area). PH-02 Size: none (test-heavy, single concern). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (all new behaviour tested). No PH-03 high → no auto-downgrade.

#### Quality lens — JSX identifier scan (CR-07 item 2)

All diff-introduced `{identifier}` / `${identifier}` references resolve in lexical scope:
`{active}`, `{className}`, `{isSelected}`, `{needsAttention}`, `{onToggleNeedsAttention}`, `{query}`, `{searchInputRef}`, `{stage}`, `${stage}` (SearchBar — all props/loop-vars/local refs); `{boardRef}`, `{onSelectStage}`, `{selectedStage}`, `{stageCounts}`, `${stage}` (Board — all declared locals/state); `{label}` (WorkspaceTopBar — declared in the map body); `${stage}` (StageColumn — prop). No PR-168-class undeclared-identifier bug.

#### Run details

- **Diff source:** `git diff --cached change/feat-cockpit-board-refresh -- apps/cockpit` (branch not yet committed; staged working tree).
- **Neighbour expansion:** string-grep on the touched symbols (`SearchBar` consumers = Board only; `StageColumn` id consumed by SearchBar tabs; top-bar collapse self-contained). Within the 20-file cap.
- **Scanners run:** tsc, eslint, jest-axe (unit, both StageChips roles), Playwright-axe (desktop/tablet/mobile).
- **Scanners unavailable:** none required for this surface.
- **Depth mode:** Standard (frontend rubric WPF-01..13).
