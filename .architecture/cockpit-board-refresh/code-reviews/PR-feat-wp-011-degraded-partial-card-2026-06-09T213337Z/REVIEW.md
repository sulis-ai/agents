# Code Review: feat/wp-011-degraded-partial-card — Degraded / partial change card

> **Timestamp:** 2026-06-09T213337Z (ISO 8601 UTC)
> **Author:** executor (WP-011)
> **Branch:** feat/wp-011-degraded-partial-card → change/feat-cockpit-board-refresh
> **Files changed:** 4 (2 source, 2 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the "degraded card" state to the board: when a change's record
is partly unreadable, its card still shows up, still opens, and falls back to
the same calm "no signal yet" marks used everywhere else — plus a quiet line
that says "Some details couldn't be read." The build is clean, the changes are
tightly scoped to the one card component, and they come with thorough tests
(including accessibility checks in both light and dark mode). Nothing needs
fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: 4 files, all inside the one card component
and its tests.

**Scope — clean.** A single concern (the degraded card state). One `feat`.

**Safety — clean.** No database changes, no infrastructure, no secrets, no new
network calls. This is a render-only change.

**Completeness — clean.** Every new behaviour is covered by a new test. Two new
test files (behaviour + accessibility) accompany the one source change.

---

## Technical detail

> Internal taxonomy (CR-NN, PH-NN, lens IDs) below for engineers and downstream
> agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
source files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — render-only, no new import direction / external call |
| Security | 0 | 0 | None — fixed-string notice, React-escaped text, no innerHTML |
| Quality | 0 | 0 | None — typed, linted, fully tested |

### Build Verification (CR-01)

`npx tsc --noEmit -p client` → exit 0 (HEAD). `npx eslint --ext .ts,.tsx` on the
three changed code files → exit 0. Base already green. No PR-introduced errors.
Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):  commit_type_spread {feat}; module_fan_out 1 dir   → severity none
Size  (PH-02):  ~396 lines, 4 files                                → severity none
Safety(PH-03):  migrations 0, schemas 0, infra 0, secrets 0        → severity none
Complete(PH-04):new_source_without_test 0, new_tests 2             → severity none
```

### Findings in the Changes

None.

Notes on the high-risk surfaces specific to this WP (all clear):

- **NFR-SEC-03 / FR-32 (no content echo).** The degraded notice renders the
  exported constant `DEGRADED_NOTICE = "Some details couldn't be read"`. JSX
  identifier scan (`tool-outputs/jsx-ident-scan.log`) shows only
  `{DEGRADED_NOTICE}`, `{intentText}`, `{slugText}`, `${ariaIntent}` — all
  declared in lexical scope; none interpolates a record `reason`/transcript
  into the notice. A dedicated test seeds a `<script>`+secret into the field
  reasons and asserts the notice equals the fixed string and no `<script>`
  element is injected (React escapes all rendered text; no
  `dangerouslySetInnerHTML`).
- **BR-26 (board-unaffected).** A multi-card test renders two healthy + one
  degraded card and asserts all three render and exactly one notice appears —
  the bad record never drops a sibling.
- **EP-03 (reuse).** The unknown reads reuse WP-005's `LivenessProbe`
  (unknown `?` probe) and `ChangeHealthBadge` ("Not assessed yet"); no second
  unknown implementation was added.
- **WPF-06/07 (a11y + tokens).** jest-axe passes light + dark; the notice
  carries `role="status"` so it is announced (not colour-/placement-alone);
  CSS is tokens-only (`--border`, `--border-muted`, `--text-secondary`,
  `--muted-foreground`).
- **CR-10 performance.** No loops, N+1, RPC, or filesystem access introduced —
  `isDegraded()` is a pure render-time predicate.

### Findings in the Neighbours

None. The change is additive to `ChangeCard`; existing card-family tests
(redesign / axe / terminal) + board + token-discipline suites stay green
(96/96 across the touched suites).

### Watch List

None.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p client` (exit 0); `npx eslint` on changed files (exit 0). Base green, head green. No coverage gap.
- [✓] **CR-02 Dispatch shape.** Diff is 2 source files (ChangeCard.tsx ~90 changed lines + ChangeCard.module.css 31 lines) + 2 test files. Source surface is within the single-reader carve-out; both source files read end-to-end. Single-reader pass justified by the effective source diff size (one component, ~120 source lines).
- [✓] **CR-03 Full-file reads.** ChangeCard.tsx and ChangeCard.module.css read end-to-end; both new test files read end-to-end.
- [✓] **CR-04 Evidence discipline.** No findings; surfaces-clear notes cite the specific tests/tool-outputs that establish each clearance.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every level.
- [✓] **CR-06 Verdict computed.** `PASS`. No auto-downgrade triggers fired (Build Verification empty; no unread >50-line file; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (render-only; no new import direction, singleton, external call, or contract). Security: nothing surfaced (no innerHTML, fixed-string notice, React-escaped text, no new secret/auth/injection surface; scanners not separately run — no new dependency or network surface to scan). Quality: build-verification clean, JSX identifier scan clean, no dead surface, no contract drift, tests present for all new behaviour, CR-10 perf no matches.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope none; PH-02 Size none; PH-03 Safety none; PH-04 Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** staged working tree vs `change/feat-cockpit-board-refresh`.
- **Neighbour expansion:** consumers of `ChangeCard` (Board / StageColumn) re-run green; no neighbour findings.
- **Scanners run:** tsc, eslint, vitest (incl. jest-axe). Gitleaks/Trivy/Semgrep not run — no new dependency, secret, or network surface in a render-only client diff.
- **Lenses dispatched in parallel:** no — single-reader pass per the effective source diff size (CR-02 carve-out).
