# Code Review: PR-feat-wp-005-redesigned-card — Redesigned change card

> **Timestamp:** 2026-06-09T203813Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-005)
> **Branch:** feat/wp-005-redesigned-card → change/feat-cockpit-board-refresh
> **Files changed:** 6 modified + 11 new (6 component/util source + css, 5 test files)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request rebuilds the board's change card to match the signed-off design: a top line with the change handle on the left and a small liveness probe plus a short time on the right, slim progress dots, the intent, the slug, and a single foot read at the bottom. That foot read is the important rule here — a card either shows a loud "Waiting on you" banner (when the change needs you) or a quieter health badge (when it doesn't), never both at once.

There are no build errors, the change is well-scoped to the card and its three new pieces, and every new piece ships with its own tests. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

A couple of small things for awareness only (no action required):

- The card now reads three fields that the data contract guarantees are always present (whether the change needs you, its health, and when it was last active). Two older test files were still building practice data without those fields — a leftover from when those fields were first added. They've been brought up to date in this same change, so the whole test suite stays green.
- One small helper inside the liveness probe is exported even though only the probe itself uses it right now. That's deliberate — it mirrors how the old liveness dot was written, so its logic can be tested directly. Harmless.

## How this pull request is shaped

**Size — clean.** About 220 changed lines in the tracked files plus six small new files (the largest is 122 lines). Comfortably reviewable.

**Scope — clean.** Everything is the card and its parts. No unrelated changes rode along. The live-board wiring and the alternate card states (selected, loading, degraded, shipped) are deliberately left to their own later pieces of work.

**Safety — clean.** No database changes, no schema changes, no infrastructure, no secrets. This is a display-only change — the card shows information, it never writes anything.

**Completeness — clean.** Six new source files, five new test files. Every new component has a dedicated test, and the accessibility check runs against every card variant in both light and dark mode.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every file >50 lines read end-to-end (authored this session); all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high, 0 medium findings (CR-09 / PH-01..PH-04)
- **In the changes:** 2 findings (0 critical, 0 high, 0 medium, 2 low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (no findings at or above medium; nothing to harden)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced — presentational components, no domain→infra import, no new fetch |
| Security | 0 | 0 | nothing surfaced — no input handling, no secrets, no external call; attentionWhy strings are a fixed enumerable set (NFR-SEC-03) |
| Quality | 2 (low) | 0 | exported-but-internal helper `resolveProbeState`; stale consumer fixtures (fixed in this PR) |

### Build Verification (CR-01)

Mechanical baseline ran clean on HEAD: `tsc --noEmit -p client` → exit 0 (0 errors); `eslint` on changed+new files → exit 0. Base branch already had a latent `tsc` error in `StageColumn.test.tsx` + `contract-links.test.tsx` (their `makeChange` fixtures omitted WP-001's required `Change` fields); this PR resolves it by bringing the fixtures into contract conformance. Net delta: 0 new errors, 1 pre-existing error cleared. See `tool-outputs/typecheck-head.log`, `tool-outputs/eslint-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern: the card)
  module_fan_out: 1 top-level dir (apps/cockpit/client/src)
  severity: none

Size (PH-02):
  lines_added: ~219 (tracked) + ~496 (new files), lines_removed: 62
  files_changed: 6 modified + 11 new
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (well within reviewable bounds)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (every new component has a test)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `client/src/components/LivenessProbe.tsx:42` — low (quality)

**What:** `resolveProbeState` is exported but referenced only within its own module.

**Quoted text:** `export function resolveProbeState(`

**Why it matters:** Minimal — a slightly wider public surface than strictly used today. It is exported deliberately to mirror the prior `resolveLivenessDotState` pattern (the component it replaces) so the state-resolution logic stays unit-testable in isolation.

**Recommendation:** Keep as-is (intentional testability surface, consistent with the existing convention). No delta.

#### `client/src/tests/StageColumn.test.tsx`, `client/src/tests/contract-links.test.tsx` — low (quality, resolved in-PR)

**What:** Both `makeChange` fixtures omitted the WP-001 required `Change` fields (`needsAttention`, `health`, `lastActivityAt`).

**Why it matters:** A latent contract violation on the base branch (pre-existing `tsc` error, masked at runtime because the old card never read those fields). The redesigned card consumes `needsAttention.flagged` + `health`, exposing it.

**Recommendation:** Already fixed in this PR — both fixtures now carry conformant defaults. No further action.

### Findings in the Neighbours

None. The card's consumers (`StageColumn`, `Board`, `Dashboard`, `ProductSwitcher`) were exercised by their existing suites and pass unchanged. `LivenessDot`, `RelativeTime`, `StageBadge` remain consumed by other surfaces (SidebarItem / TurnCard·Chat·ChatMessage / ChangeNav·ThreadHeader·ThreadView·StageColumn respectively) — no orphans introduced.

### Watch List

None.

### Cross-Reference

- No prior `.security/cockpit-board-refresh/` report to cite.
- No existing hardening deltas to dedupe against.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p client` (exit 0) + `eslint` on changed+new (exit 0). Base had 1 pre-existing fixture `tsc` error, cleared by this PR. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch.** Diff is small (≈220 tracked lines + 6 small new files; largest 122 lines). Single-reader pass justified by diff size and by the reviewer being the author with full end-to-end knowledge of every file; all three lenses still applied explicitly.
- [✓] **CR-03 Full-file reads.** Every changed/new file >50 lines authored + re-read end-to-end this session (LivenessProbe.tsx 122, LivenessProbe.module.css 120, ChangeHealthBadge.tsx 89, ChangeHealthBadge.module.css 80, ChangeCard.tsx ~140, ChangeCard.module.css ~150, WaitingOnYou.module.css 51). Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 2 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read; every lens produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — presentational components, no domain→infra import, no new network, WPF-01/02/07 honoured. Security: nothing surfaced — no input/secrets/external-call; attentionWhy is a fixed enumerable set (NFR-SEC-03). Quality: JSX identifier scan clean (all idents in lexical scope; see jsx-ident-scan.log), no dead surface above note, no contract drift (ChangeHealthBadge exhaustive over ChangeHealthState via Record), every new source file has a test, CR-10 perf — no anti-pattern matches in changed files.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat concern). PH-02 Size: none. PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (0 new source without test). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-board-refresh` (tracked) + untracked new files in the worktree.
- **Neighbour expansion:** git grep over `client/src` for the card's consumers + the retained components' other consumers.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** tsc, eslint (project mechanical floor). No Semgrep/Gitleaks/Trivy signal in a tokens-only presentational diff.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (small diff); all three lenses applied in sequence with explicit output.
