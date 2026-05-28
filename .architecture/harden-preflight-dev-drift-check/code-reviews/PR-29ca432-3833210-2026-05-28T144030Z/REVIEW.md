# Code Review: batch train-2026-05-28T143933Z — WP-004

> **Timestamp:** 2026-05-28T144030Z (ISO 8601 UTC)
> **Scope:** bundled-tip review (Step 10.5) — single-WP train
> **Range:** 29ca432..3833210 on `change/harden-preflight-dev-drift-check`
> **WPs:** WP-004 (`wpx-preflight protection-status` + one-time warning + extract-now)
>
> **Outcome:** Ready to merge

## At a glance

WP-004 adds the `protection-status` enum subcommand and the one-time
unprotected-repo warning on both run-all and ship, and completes the
extract-now refactor (the free-plan predicate now lives once in the shared
library, imported by both scripts). The warnings are plain English and never
block. Nothing needs attention. This is the final piece of CH-01KSQB.

## What to fix

No issues that need attention.

---

## Technical detail

### Verdict

`PASS` per CR-06. 0 critical/high/medium/low. Build Verification empty
(combined-tip branch-ci green; full unit suite 780 passed / 1 skipped). Changed
source read end-to-end.

### Summary — composition focus (Step 10.5)

- **Extract-now refactor (the real composition concern):** `_FREEPLAN_403_MARKER`
  + `is_freeplan_protection_403` now live ONCE in `_wpxlib.py` (lines 678/681);
  `wpx-arrival-check` and `wpx-preflight` BOTH import the single shared home (no
  duplicated predicate left behind). CLAUDE.md #2 satisfied. arrival-check's
  RC-02 free-plan characterisation tests preserved (CI green confirms). The
  symbol was de-underscored (`_is_…` → `is_…`) to signal its now-shared status —
  a sensible visibility change.
- **`protection-status` subcommand:** closed three-state enum
  (protected / unavailable-free-plan / unconfigured); always `ok:true` (never
  blocks); reuses the extracted predicate. The new `gh api` subprocess call
  carries a `timeout=30` + `TimeoutExpired → unconfigured` (a per-WP-review
  finding the executor fixed inline) — still never blocks.
- **Two founder-facing warnings (run-all Step 0 + change/ship step 4):** plain
  English, no rule codes / HTTP status / tool names; one consistent voice across
  both surfaces; fire only on `unavailable-free-plan`; once per invocation;
  explicitly non-blocking ("I'll carry on now" / "Carrying on with the ship
  now"). `protected`/`unconfigured` emit nothing — matches the spec (public/
  protected repos see no warning).

| Lens | Findings | Note |
|---|---|---|
| Architecture | 0 | extract-now done correctly; single predicate home; clean imports |
| Security | 0 | read-only protection probe; the only new external call now has a timeout |
| Quality | 0 | tests-first (3 new + existing); per-WP timeout finding fixed inline |

### Methodology (CR-08 self-attestation)

- [✓] **CR-01 Mechanical baseline.** Combined-tip branch-ci green (manifest +
  compileall + pytest 780 passed + routing-coverage gate). Stdlib-only repo.
- [✓] **CR-02 Dispatch shape.** Single-reader. Single-WP train; genuine code
  surface ~150 source lines + the extraction; per-WP reviewed clean at Step 6.5
  (one timeout finding fixed inline); combined-tip CI green; internal tooling.
  Proportionate.
- [✓] **CR-03 Full-file reads.** Extraction (`_wpxlib`/arrival-check/preflight
  imports), `protection-status` path, and both skill warning additions read
  end-to-end via the merged delta.
- [✓] **CR-04 Evidence.** Observations cite file:line + diff hunks.
- [✓] **CR-05 Severity.** 0/0/0/0.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture/Security/Quality all produced
  output; nothing surfaced.
- [✓] **CR-09 PR Hygiene.** Scope clean (single WP), Size moderate (subcommand +
  2 skill edits + extraction), Safety clean (read-only probe; new call now
  timed out; 0 migrations/schema/infra/secrets), Completeness clean (tests
  present).

### Run details

- **Diff source:** git range 29ca432..3833210 (the WP-004 squash-merge).
- **Composition focus:** verified the extract-now (WP-002 predicate → `_wpxlib`,
  both scripts import) and the WP-003→WP-004 CLI-subcommand seam. All consumers
  now in tree; this completes the change's 4-WP set.
- **Note:** the executor flagged a self-recovered journal-bookkeeping drift
  (chained Bash calls with suppressed output silently no-oped; reconstructed at
  Step 7). Code/tests/commit/push were always correct. Logged to the tooling
  backlog (not a finding against this diff).
