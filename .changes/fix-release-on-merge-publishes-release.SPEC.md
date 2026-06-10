# fix: release-on-merge publishes the GitHub Release directly

Closes #110, #148.

## Problem

`release-on-merge.yml` bumps versions, tags `v<meta>`, and pushes the tag with
the default `GITHUB_TOKEN`. The GitHub Release page was meant to be published
by the tag-triggered `release-prod.yml` (`on: push: tags: ['v*.*.*']`). But
GitHub's recursion guard deliberately does NOT fire `on: push` workflows for a
ref pushed with the default `GITHUB_TOKEN`, so `release-prod` never ran for the
bot-pushed tags. Result: ~48 tags landed (up to v1.180.0) with no Release page
— the latest published Release was stuck at v1.132.0. `/plugin update` was
unaffected (it keys off the marketplace version + tag), but the human-facing
Release notes page was absent on every release.

(#148 is the same defect seen from the docs side: the release-train SKILL prose
claims the robot "publishes the GitHub Release", which was untrue until now.)

## Fix

Add a `Publish GitHub Release` step to `release-on-merge.yml` immediately after
`Commit, tag, push` (before the best-effort brain emission). It mirrors
`release-prod.yml`: derive notes from the CHANGELOG top section and
`gh release create "$TAG" --title "$TAG" --notes-file … --verify-tag ||
gh release edit …`. Creating a Release via the API in-job is NOT gated by the
workflow-recursion guard, so it fires on every release. Gated on
`steps.detect.outputs.skip != 'true'`; uses the job's existing
`permissions: contents: write` + `GH_TOKEN: ${{ github.token }}`.

`release-prod.yml` stays as the fallback for a manual / PAT tag push; it
no-ops here because the Release already exists (its create-or-edit is
idempotent). With this fix the release-train SKILL's "publishes the GitHub
Release" prose (lines 292/451) becomes accurate — no prose change needed (#148
option (a)).

## Tests

GitHub Actions workflow change — no unit test. Validated: the YAML parses, the
new step is ordered after the tag-push and before the brain emission, is
skip-gated, and carries `GH_TOKEN`. The real proof is the next release
publishing its Release page (and backfilling the ~48 missing pages is a
separate one-time `gh release create` sweep if desired).
