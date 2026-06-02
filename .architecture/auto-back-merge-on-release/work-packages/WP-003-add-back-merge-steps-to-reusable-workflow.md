---
id: WP-003
title: Add the back-merge step block to the reusable workflow (pin-read + decide+act + post-condition)
status: pending
change_id: auto-back-merge-on-release
kind: infra
primitive: extend
group: EXPAND
sequence_id: WP-003
dependsOn: [WP-002]
blocks: [WP-005, WP-009]
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: §4.2 comp-reusable-workflow (back-merge block); §5.2 No-force-push invariant; §5.3 Atomicity (NFR-006); §5.6 Pin tampering / safe defaults; §5.7 Visibility & audit; §3 Canonical Identifiers
adrs: [ADR-002, ADR-005, ADR-006]
verification:
  adapter: infra
  artifact: plugins/sulis/scripts/tests/integration/test_clean_release_e2e.sh
---

## Context

This WP **extends** the reusable workflow created in WP-002 by
appending three new steps at the end of the `release` job:

1. **pin-read** — extract the `dev-sha-at-open: <40-hex-SHA>` HTML
   comment from the merged release PR's body via `gh api repos/{owner}/{repo}/commits/${GITHUB_SHA}/pulls`
   and regex `dev-sha-at-open: ([a-f0-9]{40})`. Missing or malformed
   pin → `DEV_SHA_PIN=""` (safe default — TDD §5.6 / ADR-006).
2. **decide+act** — if `DEV_SHA_PIN` is non-empty AND `git ls-remote
   origin dev` returns a SHA byte-equal to the pin, fast-forward
   `main:dev` (`git push origin main:dev`). Otherwise, fall through
   to the raced-path: `gh pr create --base dev --head main --label
   back-integrate --title 'chore: back-integrate main → dev (post-
   release v<NEW_META>)'` followed by `gh pr merge --auto --merge`.
   FF push rejected for ANY reason → fall through to the raced path
   (TDD §5.2 — runtime layer). **No `--force` / `--force-with-lease`
   ever.**
3. **post-condition** — assert atomicity (NFR-006). The workflow exits
   non-zero unless `origin/dev == origin/main` OR `gh pr list --base
   dev --label back-integrate --state open` returns ≥1 PR OR a
   recently-merged back-integrate PR is detectable. Exit 1 with a log
   line naming the failure mode if neither holds.

These three steps live entirely inside the reusable workflow at
`plugins/sulis/templates/workflows/release-on-merge.yml`. WP-002 moved
the file; this WP adds the load-bearing block.

**Canonical strings consumed (TDD §3):**

- `dev-sha-at-open` regex — `dev-sha-at-open: ([a-f0-9]{40})` (ADR-006).
- `back-integrate` label — sourced from `LABEL` constant exposed by
  WP-001's `drift_check.sh` (or, if the workflow chooses not to source
  the helper, the literal `back-integrate` matches WP-001's constant
  character-for-character — WP-009 enforces parity).
- Back-merge PR title prefix — `chore: back-integrate main → dev`
  (TDD §3 + WP-001's `TITLE_PREFIX`).
- base=`dev`, head=`main` — TDD §3.

**Permissions surface** — the workflow's job-level `permissions:`
block (already in WP-002) declares `contents: write` and
`pull-requests: write`. No additional secrets needed.

## Contract

### Files modified

```
plugins/sulis/templates/workflows/release-on-merge.yml  (+ ~80 LOC — three new steps appended)
```

### Step 1 — `pin-read`

```yaml
- name: Read dev-sha-at-open pin from release PR
  id: pin
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    PR_BODY=$(gh api "repos/${{ github.repository }}/commits/${{ github.sha }}/pulls" --jq '.[0].body // ""')
    DEV_SHA_PIN=$(printf '%s\n' "$PR_BODY" | grep -oE 'dev-sha-at-open: [a-f0-9]{40}' | head -n1 | awk '{print $2}')
    echo "dev_sha_pin=${DEV_SHA_PIN}" >> "$GITHUB_OUTPUT"
    if [[ -z "$DEV_SHA_PIN" ]]; then
      echo "::notice::pin absent or malformed; raced-path will be taken"
    fi
```

**Why `// ""` (jq default empty):** when the merge commit isn't
associated with a PR (e.g. someone direct-pushed to main; out of
scope but defensive), the jq query returns null. Default-empty makes
the regex below safe.

**Why `head -n1`:** ADR-005 mandates append-only — the bottom-of-body
comment written by `/sulis:release-train` is always the last one if
writes are append-only. `grep -oE` returns lines in order; `head -n1`
picks the first match, which under append-only is the original pin
write. (If multiple pins are present because someone manually edited
the body, the first-match rule still produces a deterministic
extraction.)

### Step 2 — `decide+act`

```yaml
- name: Fast-forward dev to main, or open raced-path PR
  id: backmerge
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    DEV_SHA_PIN: ${{ steps.pin.outputs.dev_sha_pin }}
    NEW_META: ${{ steps.bump.outputs.new_version }}    # cross-step ref into the existing bump step's output
  run: |
    set -u
    git fetch origin dev main

    CURRENT_DEV=$(git ls-remote origin dev | awk '{print $1}')

    if [[ -n "$DEV_SHA_PIN" && "$CURRENT_DEV" == "$DEV_SHA_PIN" ]]; then
      echo "back-merge: clean path, attempting fast-forward dev → main"
      if git push origin main:dev; then
        echo "back-merge: clean path, dev fast-forwarded to main"
        echo "path=clean" >> "$GITHUB_OUTPUT"
        exit 0
      else
        echo "::warning::fast-forward push rejected; falling through to raced path"
      fi
    else
      echo "back-merge: raced path (pin=${DEV_SHA_PIN:-<empty>}, current_dev=${CURRENT_DEV})"
    fi

    # Raced-path: open the back-integrate PR and enable auto-merge (ADR-002).
    PR_TITLE="chore: back-integrate main → dev (post-release v${NEW_META})"
    PR_BODY="Auto-opened by release-on-merge workflow. Fast-forward of \`dev\` to \`main\` was not safe (race during the release window or push rejected). Auto-merge is enabled; CI green will merge."
    PR_URL=$(gh pr create --base dev --head main --label back-integrate --title "$PR_TITLE" --body "$PR_BODY")
    PR_NUM=$(printf '%s' "$PR_URL" | awk -F/ '{print $NF}')
    gh pr merge "$PR_NUM" --auto --merge
    echo "back-merge: raced path, PR #${PR_NUM} opened with auto-merge enabled"
    echo "path=raced" >> "$GITHUB_OUTPUT"
    echo "pr_number=${PR_NUM}" >> "$GITHUB_OUTPUT"
```

**Why no `--force`/`--force-with-lease`:** TDD §5.2 — the only push
the workflow makes targeting dev is a plain `git push origin main:dev`,
which git refuses if it isn't a fast-forward. Branch protection on
dev provides the third layer.

**Why the FF rejection falls through to PR-open:** TDD §5.2 (runtime
layer) — any rejection (branch protection, race, network) is handled
the same way: open the PR. The workflow never escalates to force.

### Step 3 — `post-condition`

```yaml
- name: Verify atomicity (NFR-006)
  if: always()    # run regardless of upstream failures
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    set -u
    git fetch origin dev main
    DEV=$(git ls-remote origin dev | awk '{print $1}')
    MAIN=$(git ls-remote origin main | awk '{print $1}')

    if [[ "$DEV" == "$MAIN" ]]; then
      echo "post-condition: dev == main (${DEV})"
      exit 0
    fi

    OPEN_PR=$(gh pr list --base dev --label back-integrate --state open --json number --limit 1 --jq '.[0].number // empty')
    if [[ -n "$OPEN_PR" ]]; then
      echo "post-condition: back-integrate PR #${OPEN_PR} is open"
      exit 0
    fi

    MERGED_PR=$(gh pr list --base dev --label back-integrate --state merged --limit 1 --json number,mergedAt --jq '.[0].number // empty')
    if [[ -n "$MERGED_PR" ]]; then
      echo "post-condition: back-integrate PR #${MERGED_PR} was merged"
      exit 0
    fi

    echo "::error::post-condition failed: dev != main (${DEV} != ${MAIN}) AND no back-integrate PR is open or recently merged"
    echo "::error::atomicity invariant violated (NFR-006). Manual recovery: see GIT-12 worked example 3."
    exit 1
```

**Why `if: always()`:** the post-condition must run even if Step 2
failed — the invariant being checked is "the release ended in a valid
state", which is most important precisely when an earlier step failed.

**Why three branches (dev==main, open PR, merged PR):** TDD §5.3
defines the atomic-success set. The merged-PR branch covers the case
where the back-merge PR opened in Step 2 has already been auto-merged
by CI before this step runs (rare on quick CI; common on slow CI).

### Canonical-string compliance

| Identifier | Source | Use in this WP |
|---|---|---|
| `dev-sha-at-open: ([a-f0-9]{40})` regex | TDD §3 + ADR-006 | Step 1's grep pattern |
| `back-integrate` label | TDD §3 + WP-001's `LABEL` | Step 2's `--label`; Step 3's `gh pr list --label` |
| `chore: back-integrate main → dev` title prefix | TDD §3 + WP-001's `TITLE_PREFIX` | Step 2's `PR_TITLE` |
| base=`dev`, head=`main` | TDD §3 | Step 2's `gh pr create --base dev --head main`; Step 3's `gh pr list --base dev` |

WP-009's `test_canonical_strings_parity.sh` asserts character-for-
character equality between this workflow's string literals and
`drift_check.sh`'s constants.

## Definition of Done

### Red — Failing tests written

- [ ] `plugins/sulis/scripts/tests/integration/test_clean_release_e2e.sh`
      — UC-001: dev and main at same SHA → simulate bump+tag+push on
      main with a pinned PR body → assert FF step ran → assert
      `git rev-parse dev == git rev-parse main`. Test runs against a
      scripted local git remote + a stub `gh` on `$PATH` (the boring
      mocking choice per TDD §6.2).
- [ ] `plugins/sulis/scripts/tests/integration/test_raced_release_e2e.sh`
      — UC-002: dev advances by one commit during the window →
      simulate workflow → assert a `back-integrate`-labelled PR opens
      with auto-merge enabled and the expected title prefix.
      Assertions cover all four canonical strings (label, title
      prefix, base, head).
- [ ] `plugins/sulis/scripts/tests/integration/test_branch_protection_fallthrough.sh`
      — MUC-002: dev's FF push rejected (simulated via a pre-receive
      hook on the test fixture) → assert workflow falls through to
      PR-open path; no `--force` retry.
- [ ] `plugins/sulis/scripts/tests/integration/test_atomicity_failure_exits_nonzero.sh`
      — Both push and PR-open fail (stub `gh pr create` exits non-zero)
      → assert workflow exits 1 with a log line naming what went
      wrong; the post-condition step is the one that exits non-zero.
- [ ] `plugins/sulis/scripts/tests/unit/test_post_condition_step_present.sh`
      — TDD §6.1: static assertion that the YAML contains a step
      with `if: always()` running the post-condition check, and that
      it references `back-integrate` and `--base dev`.
- [ ] `plugins/sulis/scripts/tests/unit/test_no_force_push_static.sh`
      (re-run; this WP MUST NOT add `--force` flags).

### Green — Implementation makes tests pass

- [ ] Three new steps appended to
      `plugins/sulis/templates/workflows/release-on-merge.yml`:
      pin-read, decide+act, post-condition.
- [ ] Step IDs: `pin`, `backmerge`, (post-condition step doesn't need
      an ID — nothing cross-references it).
- [ ] All canonical strings (label, title prefix, base, head, pin
      regex) appear in the workflow as literals matching WP-001's
      constants byte-for-byte.
- [ ] `if: always()` on the post-condition step.
- [ ] No `--force`, `--force-with-lease`, or `+main:dev` anywhere in
      the file (`test_no_force_push_static.sh` continues to pass).
- [ ] Five Red tests pass; the existing `test_no_force_push_static.sh`
      passes.

### Blue — Refactor complete

- [ ] `actionlint` reports zero issues.
- [ ] No inline GitHub Expression in shell unquoted (e.g. ` ${{ ... }} `
      always goes through `env:` ports — protects against shell
      injection if a PR title ever contained shell metacharacters,
      MUC-related defence).
- [ ] All three steps use the existing `bump-version` step's
      `outputs.new_version` via cross-step `${{ steps.bump.outputs.* }}`
      — no re-computation of the version.
- [ ] Step log lines (`back-merge: clean path...`, `back-merge: raced
      path, PR #N opened`) are single-line per TDD §5.7 — grep-friendly.
- [ ] No secrets logged. `GH_TOKEN` is only ever passed via `env:` to
      `gh`; never printed.

## Sequence

- **dependsOn:** WP-002 (the reusable workflow file must exist).
- **blocks:**
  - WP-005 — the marketplace shim's first production release exercises
    these three steps end-to-end.
  - WP-009 — the regression + chaos test suite exercises these steps
    against scripted remotes.
- **Parallelisable with:** WP-001 (drift_check.sh — separate file),
  WP-004 (shim template — separate file), WP-006 (release-train SKILL.md
  — separate file), WP-007 (change SKILL.md — separate file), WP-008
  (GIT-12 — separate file). Strictly serial with WP-002.

## Estimated Token Cost

- **Input:** ~4k (WP-002's moved YAML to know where to append + TDD
  §4.2 + §5.2 + §5.3 + §5.6 + §5.7 + ADR-002 + ADR-005 + ADR-006 +
  WP-001's canonical-string constants)
- **Output:** ~4k (three new YAML steps ≈ 80 LOC + 4 integration test
  files ≈ 200 LOC + 1 unit-test stub)
- **Total:** ~8k

## Notes

- **Why EXPAND-Extend, not REORGANISE:** the new steps are net-new
  behaviour appended to existing job. Existing steps are not edited,
  reformatted, or reordered. No characterisation test required for
  this WP — WP-002's already proved the pre-extension behaviour holds.
- **Why three steps and not one:** each step has a single
  responsibility (read, decide+act, verify). The `if: always()` on
  the post-condition step needs to be a separate step — that's how
  GitHub's `always()` conditional resolves at step granularity. Step
  2 must not have `if: always()` because we want it to skip when the
  upstream bump step failed (no point trying to back-merge a release
  that didn't release).
- **Why the back-merge PR is labelled `back-integrate`, not `back-merge`:**
  TDD §3 + GLOSSARY — "back-integration" is the noun (the act);
  "back-merge" is the verb/operation; the label is named after the
  act (the durable thing the label represents). The label is the
  searchable index entry that `drift_check.sh` and the post-condition
  step both grep for.
- **No retry loop on FF rejection.** First failure falls through to
  PR-open. Retrying FF would just hammer the branch protection layer
  for no benefit — branch protection rejection means the workflow is
  in the "needs review" regime and the PR-open path is the right
  exit.
- **Touch surface:** 1 file modified + 4 integration tests + 1 unit
  test ≈ 6 path entries. Well under the MUST ≤ 15 ceiling.

## Verification Plan

Per TDD §9.5 ("kind: infrastructure — sandbox CI runs the workflow
against a real repo") + §6.2 (regression tests against scripted local
git remotes with stub `gh`):

- **Adapter:** `infra` (integration tests against scripted local git
  remotes; sandbox CI for the real-runtime layer that mocks can't
  cover).
- **Concrete artifact:**
  `plugins/sulis/scripts/tests/integration/test_clean_release_e2e.sh`.
  The four integration tests in this WP's Red set collectively cover
  FR-002, FR-003, FR-011, FR-013, FR-014, MUC-001, MUC-002. The chaos
  test for the race window (TDD §6.3) is part of WP-009.
- **What this WP's verification proves:** the three new steps
  implement the clean path, the raced path, and the branch-protection
  fall-through correctly; the post-condition catches atomicity
  failures; no force flags are introduced. End-to-end behaviour in
  the real GitHub Actions runtime is verified in WP-009's sandbox CI
  pass (TDD §9.2).
- **Acceptance criteria:** all five Red tests pass + the existing
  `test_no_force_push_static.sh` continues to pass + `actionlint` is
  clean on the modified file.
