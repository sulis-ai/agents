# Code Review: feat/wp-002-chat-status-line — Shared ChatStatusLine

> **Timestamp:** 2026-06-27T132003Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-chat-status-line → change/feat-chat-experience-both-universal-change
> **Files changed:** 3 (458 insertions, 0 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds one new, self-contained status line for the chat — the
"Sulis is working…" / "Finished — over to you" row that sits above the message
box. It is three brand-new files (the component, its styles, and its tests) and
changes nothing that already existed, so it cannot break other screens. The
build is clean, the colours come entirely from the shared theme (so light and
dark both work for free), and the screen-reader behaviour is tested. There is
nothing that needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 458 lines across 3 tightly-related files, all for one
component. Easy to review in full.

**Scope — clean.** A single feature (`feat:`), one folder. No mixing of
refactors, migrations, or unrelated changes.

**Safety — clean.** No database migrations, no schema/IDL changes, no
infrastructure files, no secrets.

**Completeness — clean.** The new component ships with its own test file
(18 cases), including accessibility checks. No source-without-tests gap.

---

## Technical detail

> Internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the changes; Build Verification empty;
all changed files >50 lines read end-to-end; all three lenses produced output.
No auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings — Scope/Size/Safety/Completeness all clean (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (the diff is purely additive new files; no existing symbol is called into or modified)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (correct dependency direction: imports the lifecycle TYPE only, no hook; ADR-002 honoured) |
| Security | 0 | 0 | — (no network, no secrets, no injection surface; gitleaks clean) |
| Quality | 0 | 0 | — (18 tests incl. jest-axe; statusSlot directly unit-tested) |

### Build Verification (CR-01)

`npx tsc --noEmit -p client` → exit 0 (clean). `npx eslint` on the two TS/TSX
files → exit 0 (clean). No PR-introduced errors. (eslint cannot parse the
`.module.css` file; CSS is covered by the no-raw-colours characterisation
pattern, extended to this module by WP-006 per ADR-004.)

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 dir → severity none
Size (PH-02):         lines_added 458, removed 0; files_changed 3 → severity none
Safety (PH-03):       migrations 0; schemas 0; infra 0; secret hits 0 → severity none
Completeness (PH-04): new_source_without_test 0 (component ships its test) → severity none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The change is three new untracked files; it introduces no edits to
existing modules and exposes no neighbour gaps. `ChatStatusLine` is consumed by
WP-004 (`Composer`) and WP-005 (`ProductChatDock`), which do not yet exist on
this branch — integration review of those mount sites belongs to their WPs.

### Watch List

- The presentational `dismissed` latch resets only via the inline "Got it"
  affordance and the caller's `onDismissFinished`. The contract also mentions
  dismissal "by the founder's next interaction (focus/typing/sending)" — that
  caller-driven reset is wired at the mount sites (WP-004/WP-005), not here.
  Noted, not a finding — this component's contract is the slot derivation + the
  explicit affordance, which are covered.

### Cross-Reference

- No prior security report for this project.
- No existing hardening deltas relevant.
- No neighbour pattern suggesting a full audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p client` (exit 0); `eslint` on changed TS/TSX (exit 0). Base clean, head clean. Coverage gap: CSS module not eslint-parseable — covered by the no-raw-colours pattern (ADR-004 / WP-006).
- [✓] **CR-02 Dispatch shape.** Diff 458 lines / 3 files. Single-reader pass: the three files are one tightly-coupled component the reviewer authored and read in full; lens scans (architecture/security/quality) each run mechanically below. Justified by diff size + single-component scope.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (component 136 lines, css 101, test 221). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings raised; nothing to evidence. Lens scans cited with commands.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (dependency direction correct, no singletons/infra/network). Security: nothing surfaced (no secrets/injection/network; gitleaks clean). Quality: nothing surfaced (jsx-ident-scan resolved {chips}, {dismiss}; no dead surface; tests present incl. axe; CR-10 no anti-pattern matches — no loops/async).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (458/3). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (test ships with source). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached` (staged new files) vs `change/feat-chat-experience-both-universal-change`
- **Neighbour expansion:** n/a — purely additive new files, no modified symbols to expand from
- **Scanners run:** gitleaks (clean)
- **Scanners available but not needed:** semgrep, ast-grep (no signals in a 3-file presentational diff)
- **Lenses:** run as scoped mechanical scans + full-file read (single-component diff)
