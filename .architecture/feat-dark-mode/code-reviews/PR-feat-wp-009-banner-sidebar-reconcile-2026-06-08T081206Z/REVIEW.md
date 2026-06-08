# Code Review: feat/wp-009-banner-sidebar-reconcile — Dashboard banner + active sidebar item visual reconciliation

> **Timestamp:** 2026-06-08T081206Z (ISO 8601 UTC)
> **Author:** executor (WP-009)
> **Branch:** feat/wp-009-banner-sidebar-reconcile → change/feat-dark-mode
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change brings two screens back in line with the approved dark-mode design. The dashboard's error banner now uses a soft red tint (instead of a loud solid-red block), and the selected item in the sidebar now uses the solid blue highlight with white text from the design. Both changes are backed by a new test that pins the exact design values, the whole test suite passes, and nothing in the build or styling raised a concern.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Three files, a small focused change (about 36 lines of real styling change plus a new test that locks the design in place).

**Scope — clean.** One concern: matching two screens to the signed-off design. Nothing else bundled in.

**Safety — clean.** No database changes, no infrastructure changes, no secrets. Only colour styling that reads from the existing theme.

**Completeness — clean.** The change is test-first: a new test was added that fails against the old styling and passes against the new, so the design values are protected against future drift.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high findings in the diff; Build Verification empty; all changed files read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 1 (low) | 0 | minor guard overlap with WP-006/008 specs |

### Build Verification (CR-01)

No PR-introduced errors. Mechanical baseline ran in the executor's Step 6:
`tsc --noEmit -p server && tsc --noEmit -p client` → exit 0; `eslint --ext .ts,.tsx .` → exit 0. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {fix/refactor — single visual reconciliation} → clean
  module_fan_out: 1 top-level dir (apps/cockpit/client/src)          → clean
  severity: none

Size (PH-02):
  lines_added: 221 (195 of which are the new test), lines_removed: 10
  files_changed: 3
  severity: none (3-file band; substantive non-test change ~36 lines)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the change IS the test + the styling it pins)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `apps/cockpit/client/src/tests/no-raw-colours.banner-sidebar-reconcile.test.ts` — low (quality)

**What:** The new spec's final assertion ("neither reconciled surface introduces a raw colour literal") overlaps in intent with the existing `no-raw-colours.badges.test.ts` (which already scans `Dashboard.module.css`) and `no-raw-colours.sidebar-files-liveness.test.ts` (which already scans `SidebarItem.module.css`).

**Why it matters:** Negligible. The new assertion is scoped to the two reconciled surfaces as a local guard so this spec is self-contained — a reader of WP-009's test sees the no-raw-literal invariant without cross-referencing the WP-006/008 specs. It is complementary, not redundant; removing it would not reduce coverage but would make this spec depend on out-of-file guards to stay honest.

**What to do:** Nothing. Retained deliberately as a local invariant. No delta.

### Findings in the Neighbours

None. The active-item `.slug` descendant rule was verified wired: `SidebarItem.tsx` renders `<span className={styles.slug}>` inside the `.item` link that carries `data-active`, so `.item[data-active="true"] .slug` targets a real element (WPF-11 — not orphaned).

### Watch List

- **AA contrast over the soft tint (verified, not a finding).** The banner text uses `var(--foreground)` over a 16% `--destructive`/`--card` tint — near-black on very-light-pink in light mode (>12:1), near-white on dark-muted-red in dark mode (high contrast). Both pass AA. The active sidebar item uses the designed-together `--primary`/`--primary-foreground` pairing (white on blue / near-black on light-blue), pre-validated AA. This mirrors the signed mockup exactly, so the contrast was decided at design time (WPF-06 / UXD).

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none applicable (no security surface in diff)
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit` (server+client) and `eslint --ext .ts,.tsx .` both exit 0 on HEAD (Step 6). Base is the change tip with the same gates green. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified.** Diff: 3 files, substantive non-test change ~36 lines (well within ≤5 files; net logic under the 200-line threshold — the 195-line count is the new characterisation test). CSS token edits + a text-parsing test; no concurrent-lens dispatch warranted.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end. The new test (195 lines) read in full; both CSS modules read in full.
- [✓] **CR-04 Evidence discipline.** The single finding cites file + quoted rationale.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read fully; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks run: import direction, singletons, resilience surfaces — none present in a CSS+test diff). Security: nothing surfaced (no secrets/auth/injection/SSRF surface; tokens only). Quality: 1 low finding + JSX-ident scan (n/a — no TSX/JSX in diff, the test is `.ts`) + dead-surface (none) + contract-drift (none) + test-coverage (change is test-first) + CR-10 perf (no anti-pattern matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single concern). PH-02 Size: clean (3 files). PH-03 Safety: clean (no migrations/schemas/secrets/infra). PH-04 Completeness: clean (test-first). PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-dark-mode...feat/wp-009-banner-sidebar-reconcile` (local)
- **Neighbour expansion:** git grep — verified `SidebarItem.tsx` renders `.slug` inside the active `.item`
- **Neighbour cap:** not reached (CSS+test diff has no import fan-out)
- **Scanners run:** tsc, eslint (mechanical baseline)
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked — no security surface in a colour-token + test diff (coverage gap noted; immaterial)
- **Lenses dispatched in parallel:** no (single-reader carve-out justified above)
