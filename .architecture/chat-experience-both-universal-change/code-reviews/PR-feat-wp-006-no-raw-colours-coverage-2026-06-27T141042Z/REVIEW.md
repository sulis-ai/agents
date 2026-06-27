# Code Review: feat/wp-006-no-raw-colours-coverage — Extend no-raw-colours coverage to the status-line surfaces

> **Timestamp:** 2026-06-27T141042Z (ISO 8601 UTC)
> **Author:** Sulis executor (WP-006)
> **Branch:** feat/wp-006-no-raw-colours-coverage → change/feat-chat-experience-both-universal-change
> **Files changed:** 1
>
> **Outcome:** Ready to merge

---

## At a glance

This change widens an existing safety check so it now also watches the new
"working / finished" status-line styles. It touches one file — a test — and
adds nothing to the product itself. The build is clean, the check has been
proven to still catch a bad colour if one were ever added, and it passes over
the real styles (which were already built the right way). Nothing needs
attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: one test file, 137 changed lines, one type of
change (a test improvement). No database changes, no new dependencies, no
configuration or infrastructure touched. This is exactly the shape a reviewer
hopes to see — easy to read in full and easy to be confident about.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the
single changed file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`npx tsc --noEmit -p client` → exit 0 (no errors). `npx eslint <changed>` →
exit 0 (no errors). Base and head both clean; no PR-introduced errors. Raw
outputs in `tool-outputs/typecheck-head.log` and `tool-outputs/eslint-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {test}                   → clean
  module_fan_out: 1 dir (apps/cockpit)         → clean
  severity: clean

Size (PH-02):
  lines_added: 82, lines_removed: 55, total: 137
  files_changed: 1
  generated_ratio: 0
  lock_file_ratio: 0
  severity: clean (≤200 line band; 1 file)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0  (the diff IS test code)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring: the four CSS modules the test scans
(`Thread.module.css`, `Chat.module.css`, `ChatStatusLine.module.css`,
`Composer.module.css`) plus `tokens.css`. All are read-only inputs to the
test; none modified by this PR. `ProductChatDock.axe.test.tsx` (the sibling
hex guard) verified green independently (9/9). No gap exposed.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this change
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p client` (exit 0); `npx eslint client/src/tests/no-raw-colours.thread-chat.test.ts` (exit 0). Base + head both clean. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 137 lines, 1 file** (≤200 lines AND ≤5 files — within the carve-out).
- [✓] **CR-03 Full-file reads.** The single changed file (199 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; mechanical-floor outputs captured in tool-outputs/.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — no new domain imports, singletons, resilience primitives, or contract gaps (test-only change reading CSS via node:fs). Security: nothing surfaced — no secrets, no network/IO to untrusted input, no injection surface; the only `new RegExp` is built from the hardcoded NAMED_COLOURS literal, not user input (no ReDoS/injection). Quality: tests-for-new-behaviour present (the diff IS the test); no dead surface; no contract drift; no CR-10 perf anti-pattern (loops are pure in-memory over fixed small arrays — 4 modules, ~18 colour names); no JSX (file is .ts).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single `test:` type, 1 dir). PH-02 Size: clean (137 lines / 1 file). PH-03 Safety: clean (0 migrations/schemas/secrets/infra). PH-04 Completeness: clean (diff is test code). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff HEAD` (working-tree change, pre-commit) on feat/wp-006-no-raw-colours-coverage
- **Neighbour expansion:** string scan of the four scanned CSS modules + tokens.css; sibling axe guard verified independently
- **Neighbour cap:** 5 of 5 considered, 0 excluded
- **Scanners run:** tsc, eslint (mechanical floor). No secret/CVE scanner needed — no dependency or secret surface in the diff.
- **Scanners unavailable:** gitleaks/trivy/semgrep not invoked (no applicable surface: 0 dependency changes, 0 secret patterns, test-only file)
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (137 lines / 1 file)
