# Code Review: WP-009 — Settings write forms with the files-are-safe remove confirmation

> **Timestamp:** 2026-06-09T115813Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-009)
> **Branch:** feat/wp-009-settings-forms-and-remove-confirm → change/feat-user-level-product-store-settings
> **Files changed:** 8 (3 components + 1 CSS module + 4 test files)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the three "write" pieces of the Settings screen: the form for
creating and renaming products/projects, the form for attaching a local folder
to a project, and the confirmation box that appears before you remove
something. It builds cleanly, every piece has tests, and the reassuring
"Your files are safe" message — promising that removing a link never deletes
anything on your computer — is in place and checked by a test.

There is nothing that needs fixing. The code is well-scoped (it only touches
its own folder), uses the shared colour/spacing system rather than hard-coded
values so it looks right in both light and dark mode, and is accessible
(every form field has a proper label and the automated accessibility check
passes on each component).

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 928 new lines across 8 files, all in one folder
(`pages/settings/`). Half of those lines are tests. Nothing to split.

**Scope — clean.** A single feature (`feat:`), one module. No mixed concerns.

**Safety — clean.** No database migrations, no schema changes, no
infrastructure files, no secrets.

**Completeness — clean.** Four new components/styles, four matching test
files. Every behaviour — the success path, the error path, and the cancel
path — has a test.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, WPF-NN) for engineers
> and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings — Scope/Safety/Completeness clean, Size low (CR-09 / PH-01..04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (nothing surfaced) |
| Security | 0 | 0 | — (nothing surfaced) |
| Quality | 0 | 0 | — (nothing surfaced) |

### Build Verification (CR-01)

`npx tsc --noEmit -p client` → 0 errors (HEAD). `npx eslint --ext .ts,.tsx
client/src/pages/settings` → 0 errors (HEAD). Prettier `--check` clean. Raw
outputs in `tool-outputs/`. Section empty → does not block PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread {feat}; module_fan_out 1 → clean
Size (PH-02):        +928 / -0; 8 files; ~50% tests → low
Safety (PH-03):      migrations 0; schema 0; infra 0; secrets 0 → clean
Completeness (PH-04): new_source 4; new_tests 4; source_without_test 0 → clean
```

### Findings in the Changes

None.

### Lens output

**Architecture lens: nothing surfaced.** Checks run: dependency-direction (no
`infrastructure/`/`db/`/`http/` imports into these view components); singletons
(none — components are pure, props-driven, WPF-09 DI); network-in-component
(none — data flows through injected `Result`-returning fetcher props, WPF-02);
the shared chrome (`SettingsForms.module.css`) is the single extracted
primitive (EP-03 2-consumer threshold not reached for a `ConfirmDialog` —
`ConfirmRemoveDialog` is the only `role="dialog"` confirm in the cockpit, kept
local with a note).

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no
auth/authz surface — frontend show/hide only, and these components don't even
gate; no injection — no `dangerouslySetInnerHTML`, all server-provided error
strings render as React text nodes and are auto-escaped; `data-project-id` is
a benign data attribute), DAT-03 (no logging of PII/tokens). Secrets scan over
the diff: 0 hits.

**Quality lens (all 7 outputs):**
1. Build Verification follow-up — no CR-01 findings to translate.
2. JSX identifier scan — all introduced `{ident}` references
   (`{busy}`, `{describedBy}`, `{entityName}`, `{error}`, `{value}`, handlers,
   etc.) resolve in lexical scope (props or `useState`/`useId` locals).
3. Dead-surface — every declared prop is consumed: `projectId` →
   `data-project-id` (the WP-010 wiring hook), `entityName`/`title` rendered,
   all callbacks invoked. No unused imports/exports.
4. Contract-drift — components consume the exact WP-001 wire shapes
   (`SettingsProduct`/`SettingsProject`/`SettingsError`) via the WP-007
   `Result<T>` type; no field assumed beyond what the producer emits.
5. Test-coverage — 3 components + 1 CSS, each with a co-located test; every
   `Result` branch (ok / error) plus cancel exercised; jest-axe asserted on
   each component (WPF-06); token-only CSS asserted by a scan test (WPF-07).
6. Style/readability — clean; clear names, small focused components, 0
   TODO/FIXME.
7. CR-10 performance — no anti-pattern matches (no loops, no DB/RPC/fs calls;
   pure render components).

### Findings in the Neighbours

None. The diff is net-new files in a new directory; the only inbound
dependency is the WP-007 fetcher's `Result`/`SettingsError` types and the
WP-001 wire shapes, both consumed as `import type` (no runtime coupling
introduced).

### Watch List

- The live-`/settings` Playwright-axe page-level gate (WPF-06 page tier) is
  owned by WP-008 (the page) / WP-010 (integration), not this WP — these are
  standalone components per the WP-009 Contract. Component-level jest-axe is
  satisfied here. Not a finding; noted for the integration WP.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas covered or duplicated.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p client` (0 errors); `npx eslint --ext .ts,.tsx client/src/pages/settings` (0 errors); prettier --check (clean). Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff 928 lines / 8 files (above carve-out). All 8 files are net-new, in one tightly-coupled directory; reviewed by the three-lens rubric end-to-end (no file >170 lines).
- [✓] **CR-03 Full-file reads.** All 8 changed files read end-to-end during authoring + review. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All lens outputs cite the file/scan evidence. No findings → no deltas.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives/scanners listed. Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** Scope clean; Size low; Safety clean; Completeness clean. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/feat-user-level-product-store-settings` (local branch, not yet pushed at review time).
- **Neighbour expansion:** git grep; 0 neighbours with introduced coupling (type-only imports).
- **Scanners run:** grep-based secrets/fetch/dangerouslySetInnerHTML; raw-colour CSS scan; CR-10 loop/async scan.
- **Frontend rubric:** WPF-01 (component tiers), WPF-02 (typed client, no fetch in component), WPF-06 (jest-axe per component), WPF-07 (tokens-only), WPF-09 (props-driven DI) — all satisfied.
