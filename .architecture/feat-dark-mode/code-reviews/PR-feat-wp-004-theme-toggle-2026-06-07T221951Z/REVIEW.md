# Code Review: feat/wp-004-theme-toggle — Add the ThemeToggle control to the Shell top bar

> **Timestamp:** 2026-06-07T221951Z (ISO 8601 UTC)
> **Author:** executor (WP-004)
> **Branch:** feat/wp-004-theme-toggle → change/feat-dark-mode
> **Files changed:** 10
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a light/dark theme toggle button to the top of the app, so
the theme can be switched from any screen. It is clean: the build passes with
no errors, the new button is fully covered by tests (including an automated
accessibility check), and every colour comes from the shared theme system
rather than being hardcoded. There is nothing that needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — looks good**

Small and single-purpose: one new button component, its styles, its tests,
and a minimal top-bar region in the app shell to hold it. The line count
looks larger than the real change only because the project's auto-formatter
tidied an existing documentation file that was already being edited.

**Scope — looks good**

One concern: adding the theme toggle. No unrelated changes rode along.

**Safety — looks good**

No database changes, no configuration or deployment files, no secrets. This
is a presentation-only change — it draws a button and flips a colour theme.

**Completeness — looks good**

Every new piece of behaviour has a test. The new button has six tests
covering how it looks, how it reads to a screen reader, and that it works
with both mouse and keyboard. A shared test helper was extracted so the
toggle, shell, and routing tests do not each copy the same setup code.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty;
every changed file >50 lines read end-to-end; all three lenses produced
output. No auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean/low)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — correct dependency direction (component → theme context) |
| Security | 0 | 0 | none — client-only presentation, no secrets/auth/network |
| Quality | 0 | 0 | none — tsc/eslint clean, full a11y + keyboard coverage |

### Build Verification (CR-01)

`npm run typecheck` (tsc -p server && -p client) and `npx eslint` on the
changed `.ts/.tsx` files both exit 0 on HEAD. Base (change/feat-dark-mode)
is also clean. No PR-introduced errors. Raw outputs in
`tool-outputs/typecheck-head.log`, `tool-outputs/eslint-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (apps/cockpit)             → clean
  severity: none

Size (PH-02):
  lines_added: 339, lines_removed: 37
  files_changed: 10
  note: README prettier reformat inflates insertions; net logic ~120 lines
  severity: low (within carve-out on logic; file count 10)

Safety (PH-03):
  migration_count: 0; schema_idl_count: 0; infra_files: 0; secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (ThemeToggle.tsx ships with ThemeToggle.test.tsx)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The neighbour ring (App.tsx — provider wiring; theme/ThemeProvider.tsx
— useTheme source; Sidebar.tsx — sibling shell chrome) was inspected; the
diff integrates with WP-003's `useTheme()` exactly as App.tsx already does in
production. No pre-existing gap exposed.

### Watch List

None.

### Cross-Reference

- No prior `.security/feat-dark-mode/` report exists.
- No existing hardening-deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (exit 0) + `npx eslint` on 7 changed .ts/.tsx files (exit 0). Base clean, head clean, delta empty. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff is 10 files but small and single-domain (frontend presentation). All three lenses run inline with full end-to-end reads of every changed file (each <130 lines; all authored in this session). Single-reader justified by domain homogeneity + small per-file size; recorded here.
- [✓] **CR-03 Full-file reads.** All 10 changed files read end-to-end (authored/edited in this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; tool outputs captured under tool-outputs/.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade trigger fired (Build Verification empty; no unread files; every lens produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no domain→infra import, no singleton, no untimed external call — N/A for client presentation per TDD §4). Security: nothing surfaced (no secrets/auth/injection/network; localStorage write is WP-003's, untouched). Quality: tsc/eslint clean; JSX-identifier scan (actionLabel/isDark/toggle all in lexical scope); no dead surface (ThemeToggle exported→consumed by Shell; stubMatchMedia exported→consumed by 4 tests); no contract drift; tests present + comprehensive (jest-axe + keyboard); CR-10 perf scan: 0 matches (no loops with DB/RPC/fs).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: low. PH-03 Safety: none. PH-04 Completeness: none. No auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/feat-dark-mode` (staged working tree; branch not yet committed at review time per Step 6.5 gate-before-commit).
- **Neighbour expansion:** git grep for `useTheme`, `ThemeProvider`, `ThemeToggle`, `Shell`, `AppRoutes` consumers. 3 neighbours (App.tsx, ThemeProvider.tsx, Sidebar.tsx); within cap.
- **Scanners run:** tsc, eslint. Gitleaks/Semgrep/Trivy not run — no secret/dependency/infra surface in the diff (no new deps, no Dockerfile, no config).
- **Lenses dispatched in parallel:** no — inline, justified by small single-domain diff (CR-02).
