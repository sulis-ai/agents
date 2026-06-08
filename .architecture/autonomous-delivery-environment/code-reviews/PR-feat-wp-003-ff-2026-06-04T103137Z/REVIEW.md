# Code Review: WP-003 fix-forward — board render-defect fixes

> **Timestamp:** 2026-06-04 (ISO 8601 UTC, see folder name)
> **Author:** sulis:executor (fix-forward)
> **Branch:** feat/wp-003-board-read-roundtrip → change/create-autonomous-delivery-environment
> **Base:** c2a6da6 (the original WP-003 ship)
> **Files changed:** 5 (4 modified, 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This is a small, focused follow-up that fixes three things a real screenshot
of the running board caught — things the green unit tests didn't. The biggest
one: a change with a very long description used to dump its whole text into the
card and blow the card out of shape. Cards now stay a calm, fixed height. No
build errors, no new risk, and a new test pins the fix so it can't quietly
come back.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose — a presentational fix-forward (CSS plus one test).
49 lines added, 13 removed, across 5 files. No database changes, no
configuration, no new dependencies. Easy to review and safe to merge.

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty;
every changed file read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck + lint clean.
- **PR Hygiene:** 0 findings — single-concern, 49/-13 lines, 5 files, no migrations/schema/secrets/infra.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — no new imports, no domain→infra reach, no new calls |
| Security | 0 | 0 | none — presentational CSS/TSX only |
| Quality | 0 | 0 | none — clamp keeps full text in DOM + title + aria-label |

### Build Verification (CR-01)

`npm run typecheck` (tsc server + client) and `npm run lint` (eslint) both
exit 0 on HEAD. Raw logs in `tool-outputs/`. No PR-introduced errors.

### Findings in the Changes

None.

The changes:
- `ChangeCard.module.css` — `.intent` now clamps to 2 lines
  (`display:-webkit-box; -webkit-line-clamp:2; line-clamp:2; overflow:hidden`)
  so a long intent can no longer blow the card out; card radius/hover/handle
  aligned to the SIGNED visual contract tokens (`--radius-container`,
  `--input`, `--font-mono`, `--muted-foreground`). The handle ellipsises on
  one line (`flex:1; min-width:0`).
- `ChangeCard.tsx` — adds `title={change.intent}` so the full (clamped) text
  stays reachable; the card `aria-label` already carried the full intent.
- `StageColumn.module.css` — column gains the signed 2px top hairline
  (`border-top:2px solid var(--border)`), a `max-height:560px` so the list
  scrolls within the column (calm board, not a sprawl), and the column name
  drops to `--muted-foreground` (the quiet signed label treatment).
- `Board.module.css` — skeleton column mirrors the 2px top border so the
  layout doesn't jump when data replaces the skeleton.
- `ChangeCard.test.tsx` (NEW) — pins the clamp: long-intent text stays in the
  DOM + title + accessible name; the intent element carries the clamp class;
  the stylesheet actually clamps `.intent` (regression guard).

### Findings in the Neighbours

None. The diff touches only presentational files. `Board.tsx` /
`groupChangesByStage.ts` (which exclude `shipped` from the in-flight columns,
FR-15) are unchanged and remain covered by `Board.test.tsx` +
`groupChangesByStage.test.ts`.

### Watch List

- The real acceptance gate for this WP is OBSERVED: the calling session
  re-drives the running app and screenshots the board. Unit-green (373/373)
  is necessary, not sufficient. The fix was self-verified against the real
  `~/.sulis` store (94 changes = 83 shipped + 11 in-flight; the six in-flight
  columns total exactly 11, shipped never shown).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` + `npm run lint`; 0 errors on HEAD; logs in tool-outputs/. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size:** 62 lines incl. test, 5 files — within the ≤200-line / ≤5-file carve-out.
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end (none >50 lines except the new test, read whole).
- [✓] **CR-04 Evidence discipline.** No findings; n/a. No theoretical deltas drafted.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical/high/medium/low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no new imports/calls/singletons). Security: nothing surfaced (presentational only; no auth/data/injection/secret surface). Quality: jsx-ident scan clean, CR-10 perf no anti-patterns, raw-hex none (tokens.css only), a11y full-text preserved + jest-axe green, test-coverage: clamp newly pinned.
- [✓] **CR-09 PR Hygiene applied.** Scope: low (single concern). Size: low (49/-13, 5 files). Safety: none (0 migrations/schema/secrets/infra). Completeness: none (style-only behaviour change, clamp test added). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff HEAD` (working tree vs the original WP-003 ship c2a6da6).
- **Neighbour expansion:** git grep; presentational diff, no neighbours exposed.
- **Scanners run:** tsc, eslint, read-only gate (95 files clean).
- **Lenses:** single-reader (carve-out path).
