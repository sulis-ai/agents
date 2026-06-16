# Code Review: ProductControl — shared product chip + searchable popover

> **Branch:** wp/feat-cockpit-product-experience/wp-002-product-control-primitive → change/feat-cockpit-product-experience
> **Files changed:** 4 (all new)
>
> **Outcome:** Ready to merge

---

## At a glance

This adds one shared building block — the "product" control that shows up as a small chip you click to open a searchable menu — built once so it can be dropped into three places later. The build is clean (no type or lint errors), it's faithful to the signed design, and it comes with a thorough set of tests including automated accessibility checks in both light and dark themes. There is nothing that needs fixing before merge. One small accessibility nuance was raised and checked; it turned out to match what the existing product switcher already does and passes the accessibility checker, so no change was needed.

## What to fix

No issues that need attention.

## How this pull request is shaped

Well-shaped: a single new component plus its stylesheet and two test files, all doing one job. New code arrives with tests (35 of them, including accessibility), so the next person to touch this has a safety net. No database changes, no infrastructure changes, no secrets.

---

## Technical detail

> Internal taxonomy below for engineers + downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck=0, eslint=0, prettier clean.
- **PR Hygiene:** 0 high, 0 medium, 1 note (size: 1569 lines but all-new + single-concern + ~706 lines are tests).
- **In the changes:** 1 finding (0 critical, 0 high, 1 medium, 0 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one medium was dispositioned as not-a-defect; no delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced — presentation-only confirmed (no api/ import, no network), monogram() reused not re-implemented |
| Security | 0 | 0 | nothing surfaced — no dangerouslySetInnerHTML, no secrets, no injection, zero network (test-enforced) |
| Quality | 1 (medium, dispositioned) | 0 | role="separator" inside role="menu" |

### Build Verification (CR-01)

No PR-introduced errors. `pnpm typecheck` exit 0; `eslint` (tsx) exit 0; `prettier --check` clean; vitest 35/35 green; full client suite 667/667 green.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):     commit_type_spread {feat}; module_fan_out 1 dir → severity none
Size (PH-02):      +1569 / -0, 4 files; generated 0; lock 0 → severity low (single new component + tests)
Safety (PH-03):    migrations 0; schemas 0; infra 0; secrets 0 → severity none
Completeness (PH-04): new_source_without_test 0 (2 src + 2 test files) → severity none
```

### Findings in the Changes

#### `apps/cockpit/client/src/components/ProductControl.tsx` (separator rows) — medium (quality) — DISPOSITIONED: not-a-defect

**Quality lens raised:** `<div className={styles.pmsep} role="separator" />` inside the `role="menu"` element may be a WAI-ARIA strictness concern; suggested `<hr aria-hidden="true">`.

**Disposition (executor):** Not a defect.
1. Per WAI-ARIA, `separator` IS a permitted owned element of the `menu` role (menu > group | menuitem* | separator).
2. The existing, axe-clean `ProductSwitcher.tsx` (lines 154, 186) uses the identical `<div className={styles.pmsep} role="separator" />` pattern. CP-01 (default to the established convention) dictates consistency with it.
3. The component's own jest-axe tests pass in both light and dark themes with the separator present (ProductControl.axe.test.tsx) — the accessibility checker confirms no violation.

No code change made; no Hardening Delta drafted. Recorded as an addressed-by-documented-convention finding.

### Findings in the Neighbours

None.

### Watch List

None.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `pnpm typecheck` (exit 0), `eslint` tsx (exit 0), prettier --check (clean), vitest (35/35). 0 PR-introduced errors. JSX identifier scan: all braces-wrapped tokens resolve in lexical scope.
- [✓] **CR-02 Parallel dispatch used.** Diff 1569 lines / 4 files (above carve-out) → three lenses dispatched concurrently as sub-agents.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end by the relevant lens(es).
- [✓] **CR-04 Evidence discipline.** The single finding cites file + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 1 medium (dispositioned), 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives listed. Quality: all of dead-surface (clean) / contract-drift (clean) / test-coverage (comprehensive) / CR-10 performance (clean) / style (excellent) / a11y sanity (1 medium, dispositioned).
- [✓] **CR-09 PR Hygiene applied.** Scope none; Size low; Safety none; Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff change/feat-cockpit-product-experience...HEAD (4 new files).
- **Neighbour expansion:** ProductSwitcher.tsx (monogram source + separator convention) considered; no neighbour findings.
- **Scanners run:** tsc, eslint, prettier, vitest, jest-axe (in-suite).
- **Lenses dispatched in parallel:** yes (3 sub-agents).
