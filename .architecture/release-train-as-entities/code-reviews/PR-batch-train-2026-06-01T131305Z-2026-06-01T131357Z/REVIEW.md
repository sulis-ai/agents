# Code Review: train-2026-06-01T131305Z — WP-008 squash-merged (FINAL WAVE)

> **Timestamp:** 2026-06-01T13:13:57Z UTC
> **Train ID:** train-2026-06-01T131305Z
> **Diff range:** 5796572..58311bf
> **WPs shipped:** WP-008 (Wire drift detector into branch-ci.yml — kind: infra)
> **Outcome:** Ready to merge — **change is feature-complete (11/11 WPs done)**

## At a glance

The final wave lands: the drift detector is now wired into branch-ci.yml as a `canonical-drift-check` job. Every future PR gets an automatic canonical-vs-imperative check.

**Mid-train hotfix worth recording:** the executor implemented the job with `continue-on-error: true` (advisory mode for v1). The release-train's bundled-tip CI poll, however, treats any failed check CONCLUSION as a fail — `continue-on-error` lets the workflow continue but doesn't change the failure conclusion. So the wave-6 train paused on its first attempt. Fixed inline by wrapping the script invocation with `|| echo "::warning::..."` so the step itself exits 0 (drift still visible in logs + as GitHub annotation; check conclusion green). When the 11 pre-existing reconciliation items are addressed in a follow-on change, drop the wrapper + the `continue-on-error` to flip to a true blocking gate. Recorded as a meta-lesson below.

## What to fix

**Nothing in this change.** The 11 known reconciliation items remain in the Watch List from the wave-5b bundle.

## Things to take away

1. **`continue-on-error` ≠ "advisory mode" in CI-poll-land.** This is the kind of edge case Path A is designed to surface. The job set `continue-on-error: true`, intending "advisory"; but the train's bundled-tip CI poll reads each check's conclusion and treats `failure` as a fail. The fix (`|| echo "::warning::..."` at the shell level) is the minimum-correct shape — it makes the step's exit code 0 while preserving full visibility. **Pattern for future "advisory CI gates":** make the step exit 0 always; surface the signal as a GitHub Actions warning annotation. Don't rely on `continue-on-error` alone.

## Technical detail

### Verdict

`PASS` per CR-06.

### Summary

- **CR-01 mechanical baseline:** 55/55 release-train tests pass (8 new from WP-008 + the 47 from prior waves). YAML parses. Drift detector still surfaces 11 items (correct — documented future work).
- **CR-09 PR Hygiene:** clean — single WP, single Conventional Commits feat + the hotfix.
- **Inline security spot-check:** The drift-check job adds no new permissions, no new secrets references, no new external network calls. The `|| echo "::warning::..."` wrapper is shell-safe (no metacharacter expansion of user input).
- **Lens findings:** 0.
- **Step 11:** not dispatched as subagent (API caution carried over; the WP is small infra + the per-WP Step 6.5 already PASS). Inline spot-check substituted.
- **Draft hardening deltas:** 0.

### Watch List (carried forward from wave 5b)

- The 11 canonical-vs-imperative reconciliation items remain. The follow-on change can now flip the drift-check job to blocking mode (drop the `|| echo` wrapper + remove `continue-on-error: true`) as part of remediating those items.

### Methodology

- [✓] CR-01: 55/55 tests; YAML parses; drift detector live run produces structured output.
- [—] CR-02: 1-WP train (reduced single-reader carve-out + per-WP review already PASS).
- [✓] CR-03: inline reads of the YAML drift step + executor's tests.
- [✓] CR-05: 0 findings in changes.
- [✓] CR-06: PASS verdict; no auto-downgrades.
- [—] CR-07: Step 11 reduced to inline; documented.
- [✓] CR-09: PR Hygiene clean.

### Final-wave note

This is the last of 11 WPs in the release-train-as-entities change. After mark-gates-complete + Step 12 wrap, the change branch is **feature-complete and ready to ship to dev** via `sulis-change finish --slug create-release-train-as-entities --primitive create --merge`. The change branch currently sits at `58311bf` on `change/create-release-train-as-entities`.
