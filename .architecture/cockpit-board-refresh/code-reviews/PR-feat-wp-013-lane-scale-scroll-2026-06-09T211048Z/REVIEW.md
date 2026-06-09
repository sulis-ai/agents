# Code Review: WP-013 — Lane scale (200-card internal scroll at 60fps)

> **Timestamp:** 2026-06-09T211048Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-013)
> **Branch:** feat/wp-013-lane-scale-scroll → change/feat-cockpit-board-refresh
> **Files changed:** 4 (+ 1 new test spec)
>
> **Outcome:** Ready to merge

---

## At a glance

This change makes a single board lane stay smooth when it holds a lot of cards — up to 200 — by only drawing the cards you can actually see and recycling them as you scroll. The change is well-scoped (it touches only the lane and its styles), the build is clean, and it comes with a test that proves the smoothness it claims. Nothing needs fixing before merge.

One thing to be aware of (not a blocker): because off-screen cards are no longer drawn until you scroll to them, keyboard tabbing now reaches cards as they come into view rather than all at once. That matches how the lane's scroll already worked, so it's consistent — noted below for awareness.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 207 lines across 4 files plus one new test. Small and focused.

**Scope — clean.** A single concern: the lane's scroll performance. No mixed refactor-plus-feature, no unrelated files.

**Safety — clean.** No database migrations, no schema or infrastructure changes, no secrets. One new dependency (`@tanstack/react-virtual`) — from the same maintainer family as the data-fetching library this project already uses.

**Completeness — clean.** The new behaviour ships with its proof: a browser test that seeds 200 cards into one lane and confirms it scrolls without stutter, the count stays truthful, and scrolling triggers no extra network calls.

## Things to take away

Nothing specific — this is a clean, well-tested change. The decision to measure first (confirm the plain scroll actually stutters at 200 cards) before adding the recycling machinery is exactly the right instinct: it means the extra complexity is earning its place rather than being added on a hunch.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files >50 lines read end-to-end; all lenses produced output. No auto-downgrade triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc -p client` and `eslint` both exit 0 on HEAD.
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean).
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low blocking).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.
- **Watch List:** 1 awareness note (virtualisation + keyboard reachability).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced (1 Watch List note) |

### Build Verification (CR-01)

No PR-introduced errors. `npx tsc --noEmit -p client` exit 0; `npx eslint client/src/components/StageColumn.tsx e2e/board-scale.spec.ts` exit 0. Two `noUncheckedIndexedAccess` errors that appeared mid-implementation were fixed before this review (guarded `changes[index]` in `getItemKey` and the row map). Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (apps/cockpit) → clean
  severity: none

Size (PH-02):
  lines_added: 207, lines_removed: 8, total: 215 (incl lockfile)
  substantive: StageColumn.tsx +161, .module.css +25, board-scale.spec.ts (new)
  files_changed: 4 (+1 new test)
  lock_file_ratio: ~0.13 (package-lock.json)
  severity: none (well under 500-line band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the lane render change is proven by board-scale.spec.ts + StageColumn.test.tsx)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

#### Architecture lens
Nothing surfaced. Checks run: dependency direction (the lane is a presentation component; it imports a view library, not infrastructure — clean), no new singletons, no circular imports, no new external/network calls (the lane renders from props; data still flows from Board via the typed client — WPF-02 intact). Resilience/Proof N/A (no new ports, calls, or resiliency primitives).

#### Security lens
Nothing surfaced. Primitives checked: SEC (no auth/access-control/injection surface — this is client render of already-fetched data), SC-01..04 (one new dependency `@tanstack/react-virtual@^3.14.2`, a headless, widely-adopted TanStack package; no CVE signal). No secrets, no new network egress, no user-input handling introduced.

#### Quality lens
1. **Build Verification follow-up:** none (CR-01 clean).
2. **JSX identifier scan:** diff-introduced `{change}`, `{changes}`, `{scrollRef}`, `{stage}`, `${stage}` — all in lexical scope. Log in `tool-outputs/jsx-ident-scan.log`.
3. **Dead-surface:** none. `observeLaneRect`, `LaneCardList`, `CARD_ROW_PX`, `OVERSCAN`, `NO_LAYOUT_FALLBACK_HEIGHT` all referenced.
4. **Contract-drift:** none. The lane API (`StageColumnProps`) is unchanged; the header count remains `changes.length` (the truthful total), not a windowed subset.
5. **Test-coverage:** strong. New behaviour ships with `e2e/board-scale.spec.ts` (3 tests: count-truthful + reachability, no long-frame > 50 ms, no N+1 on scroll) and the WP-004 characterisation `StageColumn.test.tsx` (18/18) stays green.
6. **Style/readability:** clean. Constants documented; the no-layout fallback is explained; cards untouched (EP-03).
7. **Performance procedural checks (CR-10):** no anti-pattern matches. The single `items.map` loop renders a card from already-loaded props — no DB/RPC/filesystem call in the loop body (the no-N+1 property is asserted at runtime by the spec). This change *removes* a performance problem (the measured 6046 ms long-task on a plain 200-card scroll) rather than introducing one.

### Findings in the Neighbours

None. `Board.tsx` (the one caller) is unchanged and its tests stay green; `ChangeCard` is untouched.

### Watch List

- **Virtualisation and keyboard reachability (awareness, no delta).** With the lane virtualised, off-screen cards are not in the DOM, so keyboard Tab reaches a card only once it is scrolled into the window. This is consistent with the lane's pre-existing internal-scroll model (cards were always reached by scrolling) and the WCAG AA axe gates pass, but it is the standard a11y trade-off of any virtualised list and is recorded here for awareness. No failing characterisation test grounds a fix, so per CR-04 this stays a note, not a Hardening Delta.

### Cross-Reference

- No prior `.security/cockpit-board-refresh/` viability report to cite.
- No existing hardening deltas to dedupe against.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p client` (exit 0) + `npx eslint <changed>` (exit 0) on HEAD. Base branch is the project's known-green change branch (full suite 1388 green). Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 207 lines, 4 files (+1 new test) — within the ≤200-substantive-line / ≤5-file carve-out.** Lockfile excluded from the substantive count.
- [✓] **CR-03 Full-file reads.** StageColumn.tsx, StageColumn.module.css, and board-scale.spec.ts all read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings/notes cite file:line and quoted context; the one note carries no delta because no failing test grounds it.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low; 1 Watch List awareness note.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks listed). Security: nothing surfaced (primitives + dependency listed). Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (215 lines incl lockfile / 4 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (new behaviour is tested). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-board-refresh` (local; no PR yet — branch not pushed at review time).
- **Neighbour expansion:** git grep — `Board.tsx` is the sole consumer of `StageColumn`; unchanged.
- **Neighbour cap:** 1 of 1 considered.
- **Scanners run:** tsc, eslint (project mechanical floor). Gitleaks/Semgrep/Trivy not invoked — no secret/injection/infra surface in the diff; dependency reviewed by provenance.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out.
