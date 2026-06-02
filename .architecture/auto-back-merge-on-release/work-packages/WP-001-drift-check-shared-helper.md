---
id: WP-001
title: Author plugins/sulis/scripts/drift_check.sh — the shared dev-behind-main drift helper
status: pending
change_id: auto-back-merge-on-release
kind: backend
primitive: create
group: GENERATE
sequence_id: WP-001
dependsOn: []
blocks: [WP-006, WP-007, WP-009]
estimated_token_cost:
  input: 2k
  output: 2k
tdd_section: §4.2 comp-drift-helper; §5.5 Defence in depth; §3 Canonical Identifiers (back-integrate label + PR title prefix consumed here)
adrs: [ADR-003]
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_drift_check_clean.sh
---

## Context

Creates the **shared bash drift helper** at
`plugins/sulis/scripts/drift_check.sh`. It is the only place where the
two-skill drift gate (ADR-003, FR-009, FR-010) is implemented — both
`/sulis:release-train` (WP-006) and `/sulis:change start` (WP-007)
source-or-execute this single script. Authoring the helper before either
call site exists is the contract-first move: WP-006 and WP-007 bind to
its contract (exit code, stderr message format, label/title strings),
which means we settle the contract in one place before two skill prose
edits would otherwise be tempted to copy-paste-and-drift.

The helper is also the place where two of the four canonical identifiers
from TDD §3 land in code: the **`back-integrate` PR label** and the
**back-merge PR title prefix**. Every other component that reads or
writes those strings (the reusable workflow in WP-003, the
release-train drift message in WP-006) cross-references this file to
keep them character-for-character aligned.

Per the user's hoisting note on the change brief: this WP exists
specifically so a single creator owns `drift_check.sh`. The
discover-project lesson (L-08 — "multiple WPs creating the same file")
is avoided by isolating the create here.

Cross-component string anchors (TDD §3) sourced here:

| String | Anchor in this WP |
|---|---|
| `back-integrate` PR label | `LABEL="back-integrate"` (bash constant near the top) |
| Back-merge PR title prefix | `TITLE_PREFIX="chore: back-integrate main → dev"` (used in the `gh pr list` filter + recovery message) |
| `base=dev`, `head=main` | `BASE_BRANCH="dev"`, `HEAD_BRANCH="main"` (referenced in the recovery message) |

The `dev-sha-at-open` pin format is NOT read here — that belongs to the
reusable workflow (WP-003) at robot-run time. The helper only checks
the post-condition: is `origin/main` an ancestor of `origin/dev`?

## Contract

### Files created

```
plugins/sulis/scripts/
└── drift_check.sh                (executable, bash, ~60 LOC)
```

### Helper contract — what callers depend on

The helper is invoked one of two ways:

```bash
# Mode 1 — execute as a script (used by /sulis:release-train, /sulis:change start)
plugins/sulis/scripts/drift_check.sh

# Mode 2 — source for shared constants (used by unit tests + future call sites)
source plugins/sulis/scripts/drift_check.sh
```

**Exit codes:**

| Exit | Meaning |
|---|---|
| `0` | `origin/main` is an ancestor of `origin/dev`. No drift. Safe to proceed. |
| `1` | Drift detected, OR `git fetch origin` failed, OR `git` / `gh` unavailable. Caller should refuse to proceed. |

**Stdout:** silent on success (exit 0). On exit 0 the helper produces
no output — callers should not parse anything.

**Stderr on exit 1:**

The helper prints **one** of the following messages to stderr, choosing
based on a `gh pr list --base dev --label back-integrate --state open --json number,url` query:

- **If ≥1 open `back-integrate` PR exists** (the raced-path PR is
  pending merge):

  ```
  drift_check: dev is behind main. An open back-integrate PR is waiting:
    PR #<NUMBER>: <URL>
  Merge that PR, then re-run.
  ```

- **If no open `back-integrate` PR exists** (manual operator bypass or
  a back-merge PR has been closed without merging — MUC-003 / MUC-007
  recovery surface):

  ```
  drift_check: dev is behind main, and no back-integrate PR is open.
  Recovery (UC-005):
    git fetch origin
    git checkout dev
    git merge --ff-only origin/main || git merge origin/main
    git push origin dev
  ```

The exact strings are part of WP-009's parity tests; do not paraphrase
once landed.

### Implementation contract

The helper, in order:

1. `git fetch origin` — required so the ancestor check sees the latest
   tips. Failure (network, no remote) → exit 1 with a fetch-failed line
   prefixed `drift_check: git fetch failed:`.
2. `git merge-base --is-ancestor origin/main origin/dev` — the
   load-bearing check. Exit 0 if this succeeds; otherwise compose the
   drift message and exit 1.
3. Detection of an existing back-integrate PR uses `gh pr list --base
   dev --label "$LABEL" --state open --json number,url --limit 1`.
   The `gh` invocation must tolerate `gh` being unauthenticated (e.g. in
   a local clone with no token) — when `gh` exits non-zero the helper
   falls through to the "no open PR" branch of the message (the
   recovery procedure is still correct).
4. Performance budget: NFR-007 — the helper completes in under 5
   seconds on a typical repo. The implementation is two git commands
   and one `gh` query, all O(log N) or constant; the dominant cost is
   `git fetch`.

### What the helper does NOT do

- It does not write to stdout on success — silent-success keeps it
  callable from skill prose without polluting transcripts.
- It does not modify the working tree, the index, or any branch.
- It does not read or write the `dev-sha-at-open` pin. That lives in
  the workflow (WP-003) and in `/sulis:release-train` (WP-006).
- It is **not** a Python wrapper. NFR-007 named bash (under-5-second
  deterministic execution); the boring choice for two git commands and
  a `gh` call.

### Test fixtures created alongside (used by WP-009)

```
plugins/sulis/scripts/tests/fixtures/drift_check/
├── repo-clean/         (a fixture clone where origin/main IS ancestor of origin/dev)
├── repo-drifted/       (a fixture clone where origin/dev is behind origin/main; no open PR)
└── gh-stubs/           (canned `gh` responses used by WP-009 to simulate "PR open" vs "no PR")
```

Only the directory structure + a README explaining "fixtures populated
during WP-009 test authoring" are required from this WP. The fixture
content lands in WP-009.

## Definition of Done

### Red — Failing tests written

WP-009 owns the full test set, but this WP authors the three smoke
tests that prove the helper's contract holds before any caller exists.

- [ ] `plugins/sulis/scripts/tests/unit/test_drift_check_help_message.sh`
      — `drift_check.sh --help 2>&1 | grep -q 'dev-behind-main drift'`
      (smoke; the helper supports `--help` so callers can self-document).
- [ ] `plugins/sulis/scripts/tests/unit/test_drift_check_constants_sourceable.sh`
      — `source drift_check.sh && [[ "$LABEL" == "back-integrate" ]] &&
      [[ "$TITLE_PREFIX" == "chore: back-integrate main → dev" ]]`.
      Cross-component string parity test (WP-009 expands this against
      the workflow and the release-train SKILL.md).
- [ ] `plugins/sulis/scripts/tests/unit/test_drift_check_exit_codes.sh`
      — exercises the helper in two scripted git remote fixtures
      (`repo-clean/` exits 0; `repo-drifted/` exits 1 with a non-empty
      stderr line beginning `drift_check:`).

Each test is `bash`, runs in under a second, and is invoked by a
top-level `plugins/sulis/scripts/tests/run.sh` that this WP also
creates (a 5-line orchestrator that does `for t in unit/*.sh; do
"$t"; done`).

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/scripts/drift_check.sh` exists, is executable
      (`chmod +x`), and implements the contract above.
- [ ] `LABEL="back-integrate"`, `TITLE_PREFIX="chore: back-integrate
      main → dev"`, `BASE_BRANCH="dev"`, `HEAD_BRANCH="main"` declared
      as top-level shell variables.
- [ ] `--help` prints a five-line synopsis naming exit codes 0 and 1.
- [ ] The three Red tests pass; `plugins/sulis/scripts/tests/run.sh`
      exits 0.
- [ ] The two fixture directories under
      `plugins/sulis/scripts/tests/fixtures/drift_check/` exist with
      README placeholders (content lands in WP-009).

### Blue — Refactor complete

- [ ] No `set -e` in the file — explicit `if … fi` branches per the
      project's bash convention (failure semantics need to be precise
      around `gh` unauthenticated).
- [ ] `set -u` and `set -o pipefail` are set.
- [ ] No subshell that swallows the exit code of the ancestor check.
- [ ] All four canonical strings (LABEL, TITLE_PREFIX, BASE_BRANCH,
      HEAD_BRANCH) are declared once at the top of the file — every
      other reference is a variable expansion. WP-009 asserts this
      by grepping for literal occurrences of `back-integrate` outside
      the constant declaration line.
- [ ] The drift message format is byte-for-byte identical to the
      contract above (WP-009 owns the parity test).
- [ ] No PII, secrets, or `$GITHUB_TOKEN` references — the helper
      runs entirely against `origin` and `gh`'s ambient auth.

## Sequence

- **dependsOn:** — (head of graph; no upstream code dependencies)
- **blocks:**
  - WP-006 — `/sulis:release-train` Step 1 invokes this helper
  - WP-007 — `/sulis:change start` preflight invokes this helper
  - WP-009 — the test suite exercises this helper across clean /
    drifted / branch-protection-rejected fixtures
- **Parallelisable with:** WP-002 (move workflow into plugin),
  WP-004 (shim template), WP-008 (GIT-12 append) — all four can run
  truly in parallel from t=0.

## Estimated Token Cost

- **Input:** ~2k (TDD §3 + §4.2 + §5.5 + ADR-003 + the existing
  `release-on-merge.yml` to crib `gh pr list` invocation patterns)
- **Output:** ~2k (drift_check.sh ≈ 60 LOC + 3 smoke tests + run.sh
  orchestrator + README placeholders)
- **Total:** ~4k

## Notes

- **Why this is WP-001 and not WP-005 (per the change brief's hoist
  question):** the helper is the cross-component contract for two
  skill edits + the unit-test suite. Splitting the helper-create out
  of `/sulis:change start` (its original WP-005 partner) eliminates
  the multi-creator hazard from the discover-project L-08 lesson —
  one WP, one creator, one file. Both consumers (WP-006, WP-007)
  then become pure `extend` operations on existing SKILL.md files.
- **No `gh auth` dependency:** the helper deliberately tolerates an
  unauthenticated `gh` and falls through to the "no open PR" branch
  of the recovery message. The recovery procedure is still correct
  in that branch — it just doesn't tell the user about an existing
  PR. The user will see the PR the next time `gh auth login`
  succeeds; the procedure won't have done any harm in the interim.
- **Performance budget enforcement:** WP-009 includes
  `test_drift_check_under_5_seconds.sh` — a hard timeout of 5 seconds
  against `repo-clean/` and `repo-drifted/`. This WP doesn't need to
  add the timeout assertion itself; WP-009 owns the NFR-007 enforcement.
- **Touch surface:** 4 files in this WP (drift_check.sh + 3 unit tests
  + run.sh + 2 fixture-directory READMEs ≈ 7 path entries). Well under
  the MUST ≤ 15 ceiling.

## Verification Plan

Per TDD §9.5 ("kind: backend" adapter — bash unit tests + local
end-to-end against a fixture clone):

- **Adapter:** `backend` (bash + scripted git remotes).
- **Concrete artifact:** `plugins/sulis/scripts/tests/unit/test_drift_check_clean.sh`
  (WP-009 expands this to the full eight-test suite in TDD §6.1; this
  WP authors the three smoke tests + the run.sh orchestrator that
  WP-009 extends).
- **What this WP's verification proves:** the helper's contract
  (exit codes, stderr format, sourceable constants) holds in
  isolation, before either skill call site exists. WP-009's full
  suite proves the contract continues to hold under the eight
  failure-mode fixtures named in TDD §6.1.
- **Acceptance criteria:** all three Red tests pass against the local
  fixture clones; `--help` prints the synopsis; the canonical-string
  constants source correctly into the test harness.
