# n=1 dogfood — post-ship observable acceptance

> **Status:** post-ship, manual/observed. NOT a CI-executable test.
> This document IS the acceptance artifact for the highest-fidelity
> verification of the auto-back-merge mechanism (TDD §6.5 / §9.1).

## Why this is documented, not coded

The auto-back-merge mechanism's true proof is the marketplace eating
its own reusable workflow: the **next real release** after this change
ships must auto-back-merge `dev → main` within ~5 minutes of the
release commit landing on `main`. This requires a real GitHub release
(a real `dev → main` promotion that triggers the real
`release-on-merge` workflow against the real GitHub Actions runtime) —
it **cannot** run in branch CI or the per-commit test suite. It is the
n=1 dogfood: the marketplace is consumer #1 of its own workflow
(WP-005 made `.github/workflows/release-on-merge.yml` a shim that
`uses:` the reusable workflow via a local-path reference).

The CI-runnable proxies for this observable are:

| Property the dogfood proves | CI proxy in this suite |
|---|---|
| The shim invokes the reusable workflow correctly | `integration/test_loop_guard_survives_indirection.sh` (shim `uses:` + `secrets: inherit` + loop-guard indirection) |
| Clean path fast-forwards dev to main | `chaos/test_race_window.sh` (decide+act logic, clean vs raced) |
| Raced path opens a back-integrate PR, never force-pushes | `chaos/test_race_window.sh` + `chaos/test_missing_pin_falls_through.sh` |
| The pin the release-train writes is the pin the workflow reads | `unit/test_pin_write_read_parity.sh` |
| The four canonical strings agree across all sources | `unit/test_canonical_strings_parity.sh` |

These proxies make the dogfood's success the EXPECTED outcome — but
only an actual release observes the full chain end-to-end.

## The observable (what to check after the next release)

After the next `dev → main` promotion of this repository:

1. Within ~5 minutes of the `release: sulis vX.Y.Z` commit landing on
   `main`, confirm **one** of:
   - `git ls-remote origin dev` equals `git ls-remote origin main`
     (the clean fast-forward path landed), **or**
   - a PR labelled `back-integrate` (base `dev`, head `main`) is open
     or recently merged on the repo (the raced path landed):
     `gh pr list --base dev --label back-integrate`.
2. The `release-on-merge` workflow run log contains exactly one of:
   - `back-merge: clean path, dev fast-forwarded to main`, or
   - `back-merge: raced path, PR #N opened with auto-merge enabled`.
3. The next `/sulis:release-train` invocation reports a clean
   next-version (no drift refusal) — i.e. `drift_check.sh` exits 0,
   confirming `dev` is no longer behind `main`.
4. No human-authored `chore: back-integrate origin/main into dev`
   commit appears on `dev` (every back-integration is robot-authored).

## Provenance

Three prior **manual** back-integrations on `dev` (commits `0e85c24`,
`8612834`, `d93517c`) demonstrated the gap this change closes. The
observable above is satisfied when the next release produces a
robot-authored back-integration with no manual intervention — the
fourth back-integration, and the first automatic one.

## Recording the result

When the next release is observed, append a dated one-line record here:

```
- YYYY-MM-DD vX.Y.Z — <clean | raced> path; dev==main within <N>m; observed by <who>
```
