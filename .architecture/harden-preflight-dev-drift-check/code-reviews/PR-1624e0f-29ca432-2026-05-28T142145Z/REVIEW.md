# Code Review: batch train-2026-05-28T142045Z — WP-003

> **Timestamp:** 2026-05-28T142145Z (ISO 8601 UTC)
> **Scope:** bundled-tip review (Step 10.5) — single-WP train
> **Range:** 1624e0f..29ca432 on `change/harden-preflight-dev-drift-check`
> **WPs:** WP-003 (`wpx-preflight dev-clean` + run-all Step-0 gate)
>
> **Outcome:** Ready to merge

## At a glance

WP-003 adds the `wpx-preflight dev-clean` tool and wires it as a Step-0 gate
into the run-all loop. It builds on WP-001's helper (already on the branch) —
the import resolves and the combined tip passed CI. The run-all blocker copy
is plain English. Nothing needs attention.

## What to fix

No issues that need attention.

---

## Technical detail

### Verdict

`PASS` per CR-06. 0 critical/high/medium/low. Build Verification empty
(combined-tip branch-ci green; full unit suite 777 passed / 1 skipped, the +5
new tests included). Changed source read end-to-end.

### Summary

- **Producer/consumer seam (the one real Step-10.5 concern):** `wpx-preflight`
  imports `from _wpxlib import _preflight_ci_conclusion` (WP-001, merged at
  1624e0f) and calls it with `(repo, branch)`. The import resolves on the
  change branch and the combined-tip CI is green — the seam is sound.
- **Envelope contract:** `wpx-preflight` emits the same `{ok, errors, warnings}`
  shape as `wpx-arrival-check`; verdict→envelope mapping correct (green/
  unknown/pending → ok:true/exit 0; failed → ok:false/exit 2 + PRE-01 error
  naming count + check names). A local envelope builder is used (the sibling
  `_Report` lives in a non-importable executable) — documented choice, fine.
- **run-all Step-0 wiring:** reuses the existing CW-04 base-branch detection
  (does not re-derive); hard-stops on `ok:false` (no override — matches the
  train pausing on red); proceeds byte-for-byte unchanged on `ok:true`;
  advisory `warnings` (no CI recorded / in-flight) do NOT block. Blocker copy
  is founder-English — no IDs/rule-codes/script-names, leads with the action
  ("<BASE_BRANCH> has N pre-existing CI failures — fix these first…").

| Lens | Findings | Note |
|---|---|---|
| Architecture | 0 | clean port reuse of WP-001 helper; no new infra coupling |
| Security | 0 | read-only CI probe; no input/auth/mutation/secrets/new-deps |
| Quality | 0 | tests-first (5 subprocess + mock_gh tests); founder-English blocker |

### Methodology (CR-08 self-attestation)

- [✓] **CR-01 Mechanical baseline.** Combined-tip branch-ci green (manifest
  validity + compileall + pytest + routing-coverage gate). No separate
  typechecker (stdlib-only repo).
- [✓] **CR-02 Dispatch shape.** Single-reader. Single-WP train; genuine code
  surface ~150 source lines (wpx-preflight + SKILL.md Step 0); already per-WP
  reviewed clean at Step 6.5; combined-tip CI green; internal tooling, no
  attack surface. Proportionate.
- [✓] **CR-03 Full-file reads.** `wpx-preflight` import/envelope/PRE-01 paths
  and the run-all Step-0 addition read end-to-end via the merged delta.
- [✓] **CR-04 Evidence.** Observations cite file + diff hunks.
- [✓] **CR-05 Severity.** 0/0/0/0.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture/Security/Quality all produced
  output; nothing surfaced.
- [✓] **CR-09 PR Hygiene.** Scope clean (single WP), Size small, Safety clean
  (read-only probe, 0 migrations/schema/infra/secrets), Completeness clean
  (tests present).

### Run details

- **Diff source:** git range 1624e0f..29ca432 (the WP-003 squash-merge).
- **Composition focus:** verified the WP-001→WP-003 producer/consumer seam
  (helper import). Consumers of WP-003's CLI (WP-004) not yet in tree.
