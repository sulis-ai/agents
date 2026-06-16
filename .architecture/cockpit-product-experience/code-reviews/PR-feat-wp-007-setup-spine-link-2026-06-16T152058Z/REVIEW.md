# Code Review: feat/wp-007-setup-spine-link — "Manage products" switcher foot action (verification)

> **Timestamp:** 2026-06-16T152058Z (ISO 8601 UTC)
> **Author:** executor (WP-007)
> **Branch:** wp/feat-cockpit-product-experience/wp-007-setup-spine-link → change/feat-cockpit-product-experience
> **Files changed:** 1
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds three small tests that prove the "Manage products" item at the
bottom of the product switcher menu works: it's there, you can reach it with the
keyboard, and clicking it triggers the jump to the Settings page. The feature
itself was already wired up in an earlier piece of work; this change is the
proof that it behaves as intended. No build errors, well-scoped, nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 60 lines added, one file. A focused, single-purpose change.

**Scope — clean.** One concern: test coverage for the "Manage products" menu item.

**Safety — clean.** No database changes, no schema changes, no secrets, no
infrastructure files.

**Completeness — clean.** This change is itself the test coverage for behaviour
that shipped earlier. No new product code, so no missing tests.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; the one
changed file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit` exit 0, `eslint` exit 0.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

None. typecheck exit 0; eslint exit 0 on HEAD. See `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type {test}, module_fan_out 1            → none
Size (PH-02):        lines +60 -0, files 1                          → none
Safety (PH-03):      migrations 0, schema 0, secrets 0, infra 0     → none
Completeness (PH-04): new_source_without_test 0 (test-only diff)    → none
```

### Findings in the Changes

None.

#### Quality lens (CR-07 — all outputs)

1. **Build Verification follow-up:** none (CR-01 clean).
2. **JSX / template identifier scan:** `tool-outputs/jsx-ident-scan.log` — the diff introduces no out-of-scope `{ }`/`${ }` identifiers; `getByTestId`, `within`, `menu`, `onManageProducts` all resolve in lexical scope.
3. **Dead-surface:** none — every added symbol is used within its test.
4. **Contract-drift:** none — tests assert against the existing `ProductControl`/`ProductSwitcher` `onManageProducts` prop contract (ADR-002).
5. **Test-coverage observation:** the diff *is* test coverage; it adds the named verification artifact (`ProductSwitcher.test.tsx :: manage products routes to settings`) for scenario "Reach product setup from the switcher". RED was proven by temporarily removing the prop forwarding (foot item absent → present/invoke tests failed for the right reason).
6. **Style / readability:** mirrors the file's established per-describe-block, inline-render convention (CP-01). Clean.
7. **Performance (CR-10):** no anti-pattern matches — no loops, DB/RPC/FS calls, or materialisation in a test file.

#### Architecture lens (WPF-01..13)

Nothing surfaced. Checks run: no new domain↔infrastructure imports (test file only); a11y assertion present (`role="menuitem"` + accessible name, WPF-06); no resilience surface (no network); no contract change.

#### Security lens

Nothing surfaced. Primitives checked: SEC-01..07 (no auth/injection/validation/secrets surface in a test file), SC-01..04 (no dependency change). No new logging, Dockerfile, or external call.

### Findings in the Neighbours

None. Neighbours (`ProductSwitcher.tsx`, `ProductControl.tsx`, `WorkspaceTopBar.tsx`, `Sidebar.tsx`) are unchanged by this diff and already carry the foot-action wiring + a11y from WP-002/WP-005.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this diff scope.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server && tsc --noEmit -p client` exit 0; `eslint --ext .ts,.tsx .` exit 0. Base clean, head clean. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 60 lines, 1 file** (within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** The one changed file (`ProductSwitcher.test.tsx`, the added block + surrounding context) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Zero findings; each lens emitted an explicit "nothing surfaced" with checks run.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; every lens produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks. Security: nothing surfaced + primitives. Quality: all 7 outputs produced (jsx-ident-scan.log included).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope none; PH-02 Size none (60 lines / 1 file); PH-03 Safety none (0 migrations / 0 schemas / 0 secrets / 0 infra); PH-04 Completeness none (test-only). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-product-experience -- apps/cockpit/` (working tree; not yet committed at review time).
- **Neighbour expansion:** git grep — neighbours unchanged, no expansion needed.
- **Neighbour cap:** not reached.
- **Scanners run:** typecheck (tsc), lint (eslint). Gitleaks/Semgrep/Trivy not run — no security-relevant surface in a test-only diff; recorded as scoped coverage decision.
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02).
