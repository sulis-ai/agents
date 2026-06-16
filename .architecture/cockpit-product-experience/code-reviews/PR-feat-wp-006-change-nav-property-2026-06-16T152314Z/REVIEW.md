# Code Review: WP-006 — Change-nav product property (replace raw select with ProductControl)

> **Timestamp:** 2026-06-16T152314Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/feat-cockpit-product-experience/wp-006-change-nav-property → change/feat-cockpit-product-experience
> **Files changed:** 8 (source only; spurious pnpm-lock.yaml artifacts removed pre-review)
>
> **Outcome:** Ready to merge

---

## At a glance

This change swaps the change nav's raw drop-down for the shared product chip + searchable popover, and moves it up to sit with the change's name and stage as an identity property. There are no build errors, the old drop-down and its leftover styling are fully removed, and the work ships with sixteen tests (behaviour + accessibility, both light and dark themes). Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: one new component, one nav edit, two style files, and the removal of the old picker. The large line count is almost entirely the two new test files; the production code is roughly 130 lines.

**Scope — clean.** Single concern: replace the product picker. The deletion of the old picker and its leftover stylesheet block travel with the replacement, which is the right grouping.

**Safety — clean.** No migrations, no schema changes, no infrastructure, no secrets. No new network surface — it reuses the existing assign write and the already-merged un-assign hook.

**Completeness — clean.** New behaviour ships with tests: the assign and un-assign journeys, the chip swap, the saving/saved feedback, the no-products case, and an accessibility audit in both themes.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high findings in the diff; Build Verification empty; all changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `pnpm typecheck` + `pnpm lint` both exit 0 on HEAD; base (merged change branch) also clean.
- **PR Hygiene:** 0 high, 0 medium findings (CR-09 / PH-01..PH-04).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Empty. `pnpm typecheck` (server + client `tsc --noEmit`) exit 0; `pnpm lint` (eslint `.ts/.tsx`) exit 0. Captured in the WP journal Step 6.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern: replace picker)
  module_fan_out: 1 (apps/cockpit/client)      → clean
  severity: none

Size (PH-02):
  source files: 8 (2 are new test files; 2 are deletions; 2 CSS)
  production LOC: ~130 (ChangeProductProperty 114 new + ChangeNav +16)
  generated_ratio: 0 (pnpm-lock.yaml artifacts removed — npm-workspaces repo)
  severity: none

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (ChangeProductProperty.tsx covered by
    ChangeNavProduct.test.tsx + .axe.test.tsx)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

#### Architecture lens

Nothing surfaced. Checks run: dependency direction (the placement imports only `../api/*` hooks + `./ProductControl` — presentation injects data at the edge per ADR-002, no domain→infra leak); no new singletons / `getInstance`; no new network surface (reuses existing `useAssignChangeProduct` + the merged `useClearChangeProduct`, both funneling through the hardened single-write adapter); no circular imports (ChangeNav → ChangeProductProperty → ProductControl is acyclic); presentation primitive still never calls the network itself.

#### Security lens

Nothing surfaced. Primitives checked: SEC-01..07. No new auth/authz surface; no injection vector (the `changeId` is passed to the existing hooks which `encodeURIComponent` it before the fetch); no secrets in the diff; no SSRF/XSS (no `dangerouslySetInnerHTML`, no URL construction from user input); no new dependency. The write path inherits the existing path-confinement + ULID validation at the adapter (TDD §Armor).

#### Quality lens

1. **Build Verification follow-up:** none (baseline clean).
2. **JSX identifier scan:** all introduced `{…}`/`${…}` refs resolve in lexical scope — `styles.cnProduct`, `styles.sectionLabel` (CSS module import); `rows`, `selectedId`, `saveState`, `triggerLabel`, `onSetUpNew` (locals/props on the ProductControl call); `assignedName` (local). Scan log at `tool-outputs/jsx-ident-scan.log`. No PR-168-class undeclared-identifier bug.
3. **Dead surface:** none. Every prop on `ChangeProductProperty` (`changeId`, `currentProductId`, `onSetUpNew`) is consumed. The `onSetUpNew` prop is optional and forwarded to the primitive (wired by a later WP / placement); not dead.
4. **Contract drift:** none. The placement maps `currentProductId` → `selectedId: string | null` exactly as ProductControl's prop contract requires; rows carry `glyph: "monogram"` per the assign-mode shape.
5. **Test-coverage observation:** new behaviour fully covered — 10 behaviour tests (assigned/unassigned trigger, assign-commit-PUT, chip-swap + Saved, Saving…, remove-DELETE, return-to-Add, no-products, ChangeNav no-`<select>`, Product label) + 6 axe tests (both themes × assigned/unassigned/menu-open).
6. **Style / readability:** clean. `SAVED_LINGER_MS` is a named constant; the saveState effect has a cleanup; comments explain the identity-placement rationale.
7. **CR-10 performance procedural checks:** no anti-pattern matches. The single `list.map` builds product rows (bounded by the tenant's product count, typically single digits) — pure transform, no N+1 / nested call / unbounded materialisation. Log: no loops with side-effecting calls.

### Watch List

None.

### Cross-Reference

- No prior `.security/cockpit-product-experience/viability-report-*.md` to cite.
- No existing hardening deltas in scope.
- No neighbour-ring pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `pnpm typecheck` + `pnpm lint`, both exit 0 on HEAD (Step 6); base (merged change branch) clean. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size:** 8 source files, ~130 lines production code (rest is tests). Within the ≤200-line / ≤5-source-file spirit (the two extra files are test + deletion). Parallel dispatch not required.
- [✓] **CR-03 Full-file reads.** ChangeProductProperty.tsx (114 lines), ChangeNav.tsx (full), both test files, both CSS edits — all read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings; all lens checks cite the concrete code paths inspected.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all three lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives listed. Quality: all 7 outputs produced (jsx-ident-scan + dead-surface + contract-drift + test-coverage + CR-10).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single concern). PH-02 Size: none (~130 production LOC). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (new source covered by tests). PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/feat-cockpit-product-experience -- apps/cockpit` (working tree staged; spurious pnpm-lock.yaml removed — repo uses npm workspaces, the lockfiles were an artifact of running `pnpm install` in the worktree and are NOT part of the WP).
- **Neighbour expansion:** git grep — ProductPicker had a single consumer (ChangeNav, edited in-diff); ChangeProductProperty's neighbours are ProductControl (unchanged, exhaustively tested) + the assign/clear hooks (unchanged, merged WP-002/WP-004).
- **Neighbour cap:** not reached (3 neighbours considered).
- **Scanners run:** typecheck + eslint (mechanical baseline); JSX identifier scan; CR-10 regex scan.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (diff size).
