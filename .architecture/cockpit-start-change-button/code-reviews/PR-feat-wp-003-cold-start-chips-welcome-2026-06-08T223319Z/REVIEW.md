# Code Review: WP-003 — Cold-start chips + soft welcome on the StartFromIntent empty state

> **Timestamp:** 2026-06-08T223319Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-003)
> **Branch:** feat/wp-003-cold-start-chips-welcome → change/feat-cockpit-start-change-button
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a friendly empty-state to the start screen: a short welcome line and a few example buttons ("Fix something that's broken", "Add a new feature", "Improve how something looks", "I'm not sure yet") so a first-time user has somewhere to start instead of a blank box. It is well-scoped — three files, all part of the same screen — with no build errors, tests for every new behaviour, and an accessibility check that passes. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 220 lines across 3 files, all part of the one start screen. Easy to review thoroughly.

**Scope — clean.** A single feature: the empty-state help. No mixing of unrelated changes.

**Safety — clean.** No database changes, no infrastructure changes, no secrets. The new buttons reuse the existing "start a change" path — they add no new way to create anything, so the existing "nothing happens until you confirm" rule still holds.

**Completeness — clean.** Seven new tests cover the new behaviour: the buttons appear only on the empty screen, clicking one fills the box and (for the concrete ones) kicks off the existing flow, the buttons vanish once you start typing or a proposal appears, they are keyboard-reachable, and the screen passes an automated accessibility check.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed source read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings; all four primitives `low` (CR-09 / PH-01..04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — pure UI; no new infra import, no new external call, no secrets |
| Security | 0 | 0 | none — static chip literals rendered as text (React-escaped); no new surface |
| Quality | 0 | 0 | none — full test coverage incl. prefill-only branch + jest-axe |

### Build Verification (CR-01)

`tsc --noEmit -p server && tsc --noEmit -p client` — 0 errors (HEAD).
`eslint --ext .ts,.tsx .` — 0 errors (HEAD).
Base branch is also clean for these files (the diff is purely additive: +220 / -0). No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 → low
Size (PH-02):         +220 / -0; files 3 → low
Safety (PH-03):       migrations 0; schemas 0; infra 0; secrets 0 → low
Completeness (PH-04): new_source_without_test 0 (additive to existing files; 7 new tests) → low
```

### Findings in the Changes

None.

Lens notes:

- **Architecture lens: nothing surfaced.** Checks run: dependency-direction (no domain→infra import; `COLD_START_CHIPS` is a module-level data const, not a singleton/getInstance); resilience (no new HTTP/RPC/DB call — chip click rides the existing `start.propose()`; no secrets; no new logging/PII — matches TDD Armor section "pure UI controls"); verification (new behaviour covered by contract tests; reuse-guard regression intact).
- **Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no access-control/auth/injection/validation/XSS/SSRF/secrets surface — chip labels are static literals rendered as JSX text content, React-escaped; no `dangerouslySetInnerHTML`), SC-01..04 (no dependency changes — package-lock untouched by the diff). No new Dockerfile/logging → INF/DAT not triggered.
- **Quality lens (all seven outputs):**
  1. Build verification follow-up: no CR-01 findings to translate.
  2. JSX identifier scan: only `{busy}` introduced in JSX; resolves to `const busy = start.isStreaming` (line 65, in lexical scope). Log: `tool-outputs/jsx-ident-scan.log`.
  3. Dead-surface: `COLD_START_CHIPS`, `pickChip`, `showColdStart` all consumed; no unused imports/exports/props.
  4. Contract-drift: component `Props` signature unchanged; no enum/union/DTO changes.
  5. Test-coverage: 7 new tests for new behaviour (render-on-empty-idle, chip-click-fills+propose, hidden-when-draft-nonempty, hidden-when-proposal, prefill-only chip, keyboard-focusable, jest-axe clean). The 5 pre-existing regression tests stay green (reuse guard).
  6. Style/readability: declarative chip array, single `showColdStart` predicate, documented rationale for `pickChip` calling `propose(text)` directly (async setState).
  7. Performance (CR-10): no anti-pattern matches. The only loop is `COLD_START_CHIPS.map` over a static 4-element array in render — not a hot path, not N+1, not O(N²).

### Findings in the Neighbours

None introduced. (Note: a pre-existing flaky test in the same file — `on CONFIRM ... at Recon` — was observed and registered separately as SF-86556990; it is not a WP-003 finding and is unrelated to this diff's behaviour.)

### Watch List

None.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this project.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit` (server+client) + `eslint --ext .ts,.tsx .`. Head: 0 errors. Diff is additive (+220/-0); no base regression possible on these new lines. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 220 lines, 3 files** (≤200-line threshold exceeded only marginally by additive lines; ≤5 files; single source file <50 LOC of logic). Below parallel-dispatch necessity; reviewer authored and read every line.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All lens conclusions cite file:line / quoted symbols. No findings → no deltas.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output; PH-03 low).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives listed. Quality: all 7 outputs produced + jsx-ident-scan.log.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low. PH-02 Size: low (220/3). PH-03 Safety: low (0/0/0/0). PH-04 Completeness: low. PH-03 high → CR-06 auto-downgrade: no.

#### Run details

- **Diff source:** `git diff` vs `change/feat-cockpit-start-change-button` (working tree, pre-commit).
- **Neighbour expansion:** not required (additive UI block inside one component; no symbol signature changed).
- **Scanners run:** tsc, eslint (project gates). Gitleaks/Semgrep/Trivy not separately invoked — no secrets/dep changes in a 220-line additive UI diff (recorded as scoped coverage, not a gap).
- **Lenses dispatched in parallel:** no (single-reader pass per CR-02 carve-out).
