# Code Review: WP-008 — Tokenise the navigation-chrome straggler colours

> **Timestamp:** 2026-06-08T062459Z (ISO 8601 UTC)
> **Author:** executor (WP-008)
> **Branch:** feat/wp-008-sidebar-files-liveness → change/feat-dark-mode
> **Files changed:** 5 (4 CSS modules modified, 1 test added)
>
> **Outcome:** Ready to merge

---

## At a glance

This change finishes the dark-mode clean-up by replacing the last few hard-coded
colours in the sidebar, the files panel, and the little status dot with the
app's shared colour names, so they now switch correctly between light and dark.
There are no build errors, the change is tightly scoped to exactly the four
files it was meant to touch, and it ships with a test that fails if a raw colour
ever sneaks back in. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

There is one thing worth being **aware of** (not a problem): three spots now
render a slightly different shade in light mode than before, on purpose. The
sidebar's selected-item highlight moves from a one-off light blue to the app's
standard quiet-surface colour (the selected item still stands out via its blue
text and bold weight); and a files-panel toolbar button that was previously
falling back to a near-black background (a latent legibility quirk) now uses the
proper surface colour. Both are deliberate and documented in code comments. If
the founder's signed-off mockup expects the old blue selected-item background
specifically, that is the one place to double-check during the visual pass —
otherwise this is the intended result.

## How this pull request is shaped

**Size — clean.** Five files, a small, single-purpose change.

**Scope — clean.** One concern: tokenise colours in the navigation chrome. No
mixed feature/refactor, no migrations, no infrastructure, no dependency changes.

**Safety — clean.** No database, schema, secret, or infrastructure changes. This
is presentation-layer CSS plus one text-parsing test.

**Completeness — clean.** The change ships with its own test
(`no-raw-colours.sidebar-files-liveness.test.ts`), which both proves the
behaviour and guards against regression.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all `none`)
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low) + 1 awareness note
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — correct token-consumption direction |
| Security | 0 | 0 | none — no auth/injection/secret/network surface |
| Quality | 0 | 0 | none (1 awareness note: intentional light-mode shade change) |

### Build Verification (CR-01)

`npm run typecheck` (tsc -p server && tsc -p client) → 0 errors.
`npm run lint` (eslint --ext .ts,.tsx) → 0 errors.
Raw-colour scan over the four modules → 0 matches (`tool-outputs/raw-colour-scan.log`).
No PR-introduced errors. Build Verification section empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread: {refactor}; module_fan_out: 2 dirs → severity: none
Size (PH-02):        files_changed: 5; net lines ~ +40/-15 → severity: none
Safety (PH-03):      migrations: 0, schema_idl: 0, infra: 0, secrets: 0 → severity: none
Completeness (PH-04): new_source_without_test: 0 (test added) → severity: none
```

### Findings in the Changes

None.

**Awareness note (not a finding — no severity):** the tokenisation
intentionally changes the rendered light-mode value at three sites, per the WP
mandate "replace with the nearest existing token":

- `SidebarItem.module.css` `.item[data-active="true"]` — `#dbedff` (one-off light
  blue) → `var(--secondary)`. Active state remains distinct from `:hover`
  (`var(--muted)`) via `color: var(--primary)` + `font-weight: 600`, and via
  distinct dark-set surfaces (`--secondary` #2a2e36 vs `--muted` #20232a).
- `FilesPanel.module.css` `.copyPathButton/.diffToggle` — `var(--surface,
  var(--foreground))` → `var(--secondary)`. The retired `--surface` token never
  existed, so the prior render was `--foreground` (near-black button bg under
  inherited dark text — a latent legibility bug). Mapped to the nearest correct
  surface token.
- `FilesPanel.module.css` `.nodeFileActive` — `var(--selected, rgba(80,140,255,
  0.18))` → `var(--secondary)`.

All three are documented inline. Verified against the running visual contract
during the WP's prove/verify pass is the calling session's Step 8+ responsibility.

### Findings in the Neighbours

None. Neighbours considered: `Sidebar.tsx`, `SidebarItem.tsx`, `LivenessDot.tsx`,
`FileTree.tsx`, `FilePane.tsx`, `FileToolbar.tsx`, `CopyPathButton.tsx` — none
read raw colour literals; all consume `styles.*` from the modules under review.
The component logic is unchanged by this diff (CSS-only + new test).

### Watch List

- If the founder-signed dark-theme mockup specifies a primary-tinted (blue)
  selected-item background rather than a neutral one, a future WP that adds a
  `--selected` / `--primary-subtle` token to `tokens.css` (WP-006's domain)
  could restore the blue tint while keeping it themeable. Out of scope here
  (this WP references existing tokens only; tokens.css edits belong to WP-006).
  No delta — theoretical, no failing characterisation test.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this project.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` → 0 errors; `npm run lint` → 0 errors; raw-colour grep → 0 matches. Base (change/feat-dark-mode) is green; head introduces no errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: ~55 lines, 5 files** (≤200 lines AND ≤5 files — carve-out satisfied).
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end (each <160 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** Awareness note cites file + selector + before/after value. No findings requiring deltas.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low. 1 awareness note (no severity).
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked dependency-direction, singletons, imports — CSS consumes tokens, correct direction). Security: nothing surfaced (no auth/injection/secret/network/PII surface in CSS + a fs-read test; primitives SEC-01..07 N/A). Quality: 0 findings + JSX-ident scan N/A (no JSX in the .ts test) + dead-surface none + contract-drift none + test-coverage present (characterisation test added with 3 self-guard checks) + CR-10 perf N/A (no loops/DB/RPC/filesystem-in-loop).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none ({refactor}, 2 dirs). PH-02 Size: none (5 files, ~55 lines). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (test included). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** git working tree vs `change/feat-dark-mode` (WP-008 change set, uncommitted at review time per Step 6.5 ordering).
- **Neighbour expansion:** git grep for `styles.` consumers of the four modules.
- **Neighbour cap:** 7 of 7 considered, 0 excluded.
- **Scanners run:** tsc, eslint, raw-colour grep. Gitleaks/Semgrep/Trivy not run — no security-relevant surface (CSS + fs-read test); recorded as deliberate scope, not a gap.
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02) for a 5-file/~55-line diff.
