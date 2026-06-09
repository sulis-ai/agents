# Code Review: WP-003 — Apply the dark-mode token changes to `tokens.css`

> **Timestamp:** 2026-06-09T200653Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-003)
> **Branch:** feat/wp-003-dark-mode-token-changes → change/feat-cockpit-board-refresh
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adjusts the dark-mode colour values so a card reads as a raised
surface above its lane, and sharpens the "waiting on you" amber. It also
darkens one light-mode warning colour so a small icon clears the contrast bar.
Nothing else changes. There are no build errors, the changes are tightly
scoped to the two files they should touch, and the new colours are proven by a
test that checks the page → lane → card brightness ordering. Ready to merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

This is a small, single-purpose change: 2 files, about 147 lines, no database
migrations, no new dependencies, no configuration changes. The colour values
all live in one place (the design-token file the whole app reads from), and the
test that proves them was extended rather than duplicated. Well-shaped.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; both
changed files read end-to-end; all three lenses produced output. No
auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (token-value-only; no import/direction/resilience surface) |
| Security | 0 | 0 | — (no auth/injection/secrets/dependency surface) |
| Quality | 0 | 0 | — (typecheck+lint clean; behaviour covered by the diff's test) |

### Build Verification (CR-01)

`npm run typecheck` (tsc -p server && tsc -p client) → exit 0, no errors.
`npx eslint client/src/tests/tokens.dark.test.ts` → exit 0, no errors.
(`tokens.css` is not linted by eslint — CSS is outside the `.ts/.tsx` config;
its values are gated by `tokens.dark.test.ts` instead.) No PR-introduced
errors. Section empty → does not block PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (apps/cockpit/client/src)
  severity: none

Size (PH-02):
  lines_added: 133, lines_removed: 14, total: 147
  files_changed: 2
  generated_ratio: 0, lock_file_ratio: 0
  severity: none (within the smallest band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (modify-only; existing test extended)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring: component CSS files that consume `var(--warning)` /
`var(--card)` etc. were checked for raw-hex introduction (`git diff` over
`*.module.css` / `*.tsx`) — none added; every surface still rides the token
(WPF-07 honoured). The three `*.module.css` files that mention `#b45309` carry
it only in migration-provenance COMMENTS ("was #b45309 … -> --warning"), not as
live declarations.

### Watch List

None.

### Cross-Reference

- No prior `.security/` report for this change.
- No existing hardening-deltas relevant to this diff.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (exit 0);
  `npx eslint <changed .ts>` (exit 0). Head: 0 new errors. Coverage gap:
  `tokens.css` not eslint-eligible (CSS) — gated by the token test instead.
- [✓] **CR-02 Single-reader pass justified by diff size: 147 lines, 2 files**
  (within the ≤200-line AND ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files (`tokens.css`,
  `tokens.dark.test.ts`) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; baseline logs in
  `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks run:
  import direction, singletons, external-call resilience, new ports — none
  present in a token-value diff). Security: nothing surfaced (primitives
  checked: SEC access-control/injection/secrets, SC dependency — no surface;
  no lock-file change). Quality: typecheck+lint clean; no JSX (no tsx/jsx in
  diff); no dead surface; no contract drift (token set unchanged — values
  only); test-coverage: the new behaviour (elevation values + page<lane<card
  ordering, S-31) is asserted by the diff's own test; CR-10 perf: no
  loop/DB/RPC/FS anti-pattern (the one new `for...of` iterates an 8-entry
  literal record, no I/O in body).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none
  (147 lines / 2 files). PH-03 Safety: none (0 migrations/schema/secrets/infra).
  PH-04 Completeness: none (modify-only; existing test extended). No PH-03 high
  → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-board-refresh`
- **Neighbour expansion:** `git grep` / `git diff` over component CSS + TSX for
  raw-hex introduction; 0 neighbours with findings.
- **Neighbour cap:** not reached.
- **Scanners run:** tsc, eslint. (Gitleaks/Semgrep/Trivy not invoked — no
  secret/dependency/IaC surface in a colour-value diff; recorded as a scoped
  coverage decision, not a silent skip.)
- **Lenses dispatched:** single-reader (carve-out), all three lenses scored.
