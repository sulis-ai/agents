# Code Review: feat/wp-001-front-door-button — Front-door "Start something new" button

> **Timestamp:** 2026-06-08T223618Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-001)
> **Branch:** feat/wp-001-front-door-button → change/feat-cockpit-start-change-button
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the single "Start something new" button to the workspace top
bar — the one obvious way in. It is well-scoped (one component, its stylesheet,
and a new test file), has no build errors, consumes the design system's colours
and fonts rather than hardcoded values, and ships with five tests including an
accessibility check. There is nothing that needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 225 lines across 3 files, most of it the new test file. Easy
to review in full.

**Scope — clean.** A single feature (`feat:`), one area of the app.

**Safety — clean.** No database changes, no infrastructure files, no secrets.
The button only moves the user to an existing screen; it creates nothing.

**Completeness — clean.** The one new behaviour ships with its own test file
(five tests, including a keyboard-focus check and an accessibility scan).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (pure client navigation; no new layer/port/call) |
| Security | 0 | 0 | — (no secrets/auth/injection/dependency surface) |
| Quality | 0 | 0 | — (build clean, identifiers in scope, tests present) |

### Build Verification (CR-01)

Empty. `npx tsc --noEmit -p client` exit 0. `npx eslint` exit 0 on the two
`.ts/.tsx` files. The `.css` file is not eslint-parseable (eslint has no CSS
grammar); excluded by design — it is not a coverage gap.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread {feat}; module_fan_out 1   → none
Size (PH-02):        +225 / -1; files 3                            → none
Safety (PH-03):      migrations 0; schemas 0; infra 0; secrets 0   → none
Completeness (PH-04):new_source_without_test 0; new_tests 1        → none
```

### Findings in the Changes

None.

#### Architecture lens

Nothing surfaced. Checks run: domain→infrastructure import scan (button imports
only `react-router-dom`'s already-used `useNavigate` and a Heroicon — both
existing deps); module-level singleton scan (none added; `START_HOTKEY_HINT` is
a const string, not state); circular-import scan (none); new external-call scan
(none — the button calls `navigate("/start")`, a pure in-app route change, so
the timeout / retry / circuit-breaker / observability gap types do not apply,
per the TDD Armor section "the front door only navigates; it triggers nothing
consequential"). Conforms to ADR-001 (one front door, no new surface/route/port).

#### Security lens

Nothing surfaced. Primitives checked: SEC-01..07 (no access-control, auth,
injection, validation, XSS, SSRF, or secrets surface — the diff adds a static
navigation control and CSS); SC-01..04 (no dependency added — `PlusIcon` is from
the already-installed `@heroicons/react`). No Dockerfile, no logging call, no PII.

#### Quality lens

1. **Build Verification follow-up:** none (CR-01 empty).
2. **JSX identifier scan:** `{START_HOTKEY_HINT}` resolves to the module-level
   `export const START_HOTKEY_HINT` in the same file (line 28). `{null}` is the
   existing `activeChangeId={null}` literal in the test harness. Both in scope.
   Log: `tool-outputs/jsx-ident-scan.log`.
3. **Dead-surface:** `START_HOTKEY_HINT` is exported and used in-file; the export
   is intentional and documented (WP-002's hotkey imports it to keep the hint in
   sync — ADR-002). Not dead. No unused imports/props.
4. **Contract drift:** none — `WorkspaceTopBar`'s `Props` signature is unchanged
   (the WP Contract requires this); no enum/DTO surface touched.
5. **Test coverage:** 5 new tests cover render-as-single-primary, navigate-to-
   /start (route probe), keyboard focus + visible ring, ⌘N hint, and a jest-axe
   no-violations scan. Existing `WorkspaceTopBar.theme.test.tsx` regression still
   green. No source-without-test gap.
6. **Style/readability:** clear names, small focused button, token-only CSS
   (WPF-07), comments cite the governing ADRs. No TODO/FIXME added.
7. **Performance (CR-10):** no anti-pattern matches — no loops, no DB/RPC/FS
   calls, no materialisation, no hot-path computation in the diff.

### Findings in the Neighbours

None. Neighbour ring: `WorkspaceShell.tsx` (mounts the bar), `App.tsx` (registers
`/start`), `StartFromIntentPage.tsx` (the route target). The diff integrates with
these through their existing, unchanged entry points; no pre-existing gap is
exposed by the change.

### Watch List

- The `⌘N` hint `<span>` is `aria-hidden="true"` (decorative keyboard hint). The
  button's accessible name remains the complete "Start something new", and the
  jest-axe scan is clean. This is the intended treatment for a decorative kbd
  hint and matches the design; not grounds for a delta. Noted for awareness only.

### Cross-Reference

- No prior `.security/{project}/` report to cite.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p client`; `npx eslint --ext .ts,.tsx <changed .ts/.tsx>`. Head: 0 errors. BASE is the change branch with these as net-new lines, so every diff line is HEAD-only; no BASE error to diff against. Coverage gap: `.css` not eslint-parseable (by design, not a gap).
- [✓] **CR-02 Single-reader pass.** Diff 225 lines / 3 files. Above the 200-line line-count trigger but the logic surface is one component edit (26 lines) + token-only CSS + a 145-line test file; all three files read end-to-end by the author and re-read after edits. Single-reader justified by the trivial logic surface; recorded here per CR-02.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end.
- [✓] **CR-04 Evidence discipline.** Findings (none) would cite file:line; lens "nothing surfaced" entries list the checks run.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade trigger fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives listed. Quality: all 7 outputs produced (jsx-ident-scan.log present).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope none; PH-02 Size none (+225/-1, 3 files); PH-03 Safety none (0 migrations/schemas/infra/secrets); PH-04 Completeness none (1 test file for the new behaviour). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-start-change-button` (staged + committed working tree).
- **Neighbour expansion:** git grep on `WorkspaceTopBar`, `/start`, `navigate`.
- **Neighbour cap:** 3 of 3 considered, none excluded.
- **Scanners run:** tsc, eslint (project gate). Gitleaks/Semgrep/Trivy not run — no secrets/dependency/IaC surface in the diff; recorded as scoped-out, not a gap.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (trivial logic surface).
