---
id: WP-006
title: Extend /sulis:release-train SKILL.md — drift-check preflight (Step 1) + dev-sha-at-open pin writer (Step 5)
status: pending
change_id: auto-back-merge-on-release
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-006
dependsOn: [WP-001]
blocks: [WP-009]
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: §4.2 comp-pin-writer + comp-drift-check-rt; §3 Canonical Identifiers (dev-sha-at-open pin format); §5.5 Defence in depth (L2)
adrs: [ADR-003, ADR-005]
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/unit/test_pin_write_format.sh
---

## Context

Extends `plugins/sulis/skills/release-train/SKILL.md` in **two
related ways** that share the same upstream dependency
(WP-001's `drift_check.sh`) and therefore ship in one WP:

1. **Step 1 — drift-check preflight** (FR-009, ADR-003, L2 of TDD §5.5):
   the first action after path resolution invokes `drift_check.sh`.
   On non-zero exit, the skill exits non-zero with the helper's
   stderr message — no further work. This is the "release-train
   refuses to operate against a stale dev" guard.

2. **Step 5 — `dev-sha-at-open` pin writer** (FR-001, ADR-005, TDD §3):
   before the release PR's body file is passed to `gh pr create
   --body-file`, run `git rev-parse origin/dev` and append
   `\n\n<!-- dev-sha-at-open: <40-hex-SHA> -->` to the body file.
   The append-only discipline (ADR-005) ensures the bottom-of-body
   comment written by the skill is the one the workflow's regex
   picks up first.

**Why one WP, not two?** Both extensions live in the same SKILL.md
file. Both depend on the same upstream artifact (`drift_check.sh`).
Splitting them would create artificial sequencing inside one file.
Per the WP-08.5 cross-kind shape note in the change brief, the
helper IS the contract; both consumer-edits in this WP bind to the
same contract surface.

**Files that do NOT change in this WP:**

- `plugins/sulis/skills/change/SKILL.md` — that's WP-007 (the other
  drift-check call site; different file, different WP).
- `plugins/sulis/scripts/drift_check.sh` — WP-001 owns the helper.
- The reusable workflow — WP-003 owns the pin READER.

## Contract

### Files modified

```
plugins/sulis/skills/release-train/SKILL.md  (+ ~40 LOC across two locations)
```

### Step 1 — drift-check preflight

A new bullet inserted as the **first** action in the skill's "Step 1"
section, immediately after path resolution:

> **Preflight — refuse to operate against a stale dev (FR-009, ADR-003).**
>
> Run `plugins/sulis/scripts/drift_check.sh`. On exit code 1, print
> the helper's stderr verbatim and **STOP** the skill with a non-zero
> exit. Do not proceed to changeset detection. The helper's recovery
> message (which references either an open back-integrate PR or the
> UC-005 manual recovery procedure) is the user's next step.
>
> ```bash
> if ! bash plugins/sulis/scripts/drift_check.sh; then
>   exit 1
> fi
> ```
>
> Per TDD §5.5 L2: the drift check is defence-in-depth. The workflow
> (L1) is the primary atomicity guard; this preflight catches drift
> caused by manual operator bypass (MUC-003), an open-but-unmerged
> back-merge PR (MUC-007), or a customised-and-broken consumer shim
> (MUC-004).

### Step 5 — pin writer

A new sub-step inserted inside Step 5 (the release-PR-open step),
immediately BEFORE the `gh pr create --body-file <BODY_FILE>`
invocation:

> **Append `dev-sha-at-open` pin to the release PR body (FR-001, ADR-005, TDD §3).**
>
> Per TDD §3 Canonical Identifiers, the pin format is the HTML
> comment `<!-- dev-sha-at-open: <40-hex-SHA> -->` at the bottom of
> the PR body. Append-only — the workflow's pin-read step (WP-003)
> uses the first match, which under append-only is always the
> original write.
>
> ```bash
> DEV_SHA=$(git rev-parse origin/dev)
> printf '\n\n<!-- dev-sha-at-open: %s -->\n' "$DEV_SHA" >> "$BODY_FILE"
> ```
>
> `git rev-parse origin/dev` returns a 40-char hex SHA — the regex
> `dev-sha-at-open: ([a-f0-9]{40})` (WP-003) requires exactly this
> format. Confirm `origin/dev` is fresh: the preflight drift check
> ran a `git fetch origin` earlier; if for any reason this step
> runs without an earlier fetch, run `git fetch origin dev` first.

### Canonical-string compliance

The pin format string `dev-sha-at-open: ` MUST match WP-003's regex
character-for-character. WP-009's `test_pin_write_format.sh` and
`test_pin_read_parity.sh` enforce this by writing a fixture body
through this WP's prose, reading it back through WP-003's regex, and
asserting the recovered SHA equals the written SHA.

### What this WP is NOT

- It does NOT add new release-train workflow steps (e.g. a
  post-release back-merge step). The back-merge happens in the
  GitHub Actions workflow (WP-003), not in the release-train skill.
- It does NOT touch the release-train skill's bump/changeset logic.
- It does NOT version-bump the SKILL.md's own version number — that
  happens through the changeset machinery on the next release.

## Definition of Done

### Red — Failing tests written

- [ ] `plugins/sulis/scripts/tests/unit/test_release_train_drift_check_called.sh`
      — asserts the release-train SKILL.md contains a Step 1
      reference to `drift_check.sh` AND an `exit 1` on helper failure.
      Grep-based check on the SKILL.md text.
- [ ] `plugins/sulis/scripts/tests/unit/test_pin_write_format.sh`
      — TDD §6.1: inspect a fixture release-PR body produced by the
      modified `/sulis:release-train` prose; assert the HTML comment
      matches `<!-- dev-sha-at-open: [a-f0-9]{40} -->` exactly.
      Fixture: a recorded body file produced by manually running the
      skill's Step 5 snippet against a test git remote.
- [ ] `plugins/sulis/scripts/tests/unit/test_pin_read_parity.sh`
      — TDD §6.1: given a fixture PR body containing the comment,
      the workflow's pin-extraction regex (WP-003) produces the same
      SHA the writer (this WP) wrote. Byte-for-byte parity test
      across the producer/consumer seam.
- [ ] `plugins/sulis/scripts/tests/unit/test_release_train_pin_step_ordering.sh`
      — asserts the pin-write prose appears in the SKILL.md BEFORE
      the `gh pr create --body-file` invocation (textual ordering
      check). Reversing the order would land an unpinned PR; this
      test catches that regression.

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/skills/release-train/SKILL.md` modified — Step 1
      gains the drift-check preflight as its first sub-step.
- [ ] `plugins/sulis/skills/release-train/SKILL.md` modified — Step 5
      gains the pin-write sub-step BEFORE the `gh pr create` call.
- [ ] Both new sub-steps reference the canonical sources by anchor
      (TDD §3 for the pin format; ADR-003 for the drift gate;
      ADR-005 for the append-only discipline).
- [ ] Four Red tests pass.

### Blue — Refactor complete

- [ ] The drift-check sub-step uses the helper at its canonical path
      (`plugins/sulis/scripts/drift_check.sh`) — no copy-paste of the
      helper's logic into the SKILL.md prose. ADR-003's
      single-source-of-truth discipline preserved.
- [ ] The pin format string `<!-- dev-sha-at-open: %s -->` is
      character-for-character what WP-003's regex captures. The
      space between `:` and `<SHA>` is part of the canonical format
      — WP-009 asserts this.
- [ ] No internal taxonomy in the SKILL.md prose visible to the
      founder (FE-09 — track calibration state in dot-prefixed
      files, not in user-facing prose). Internal IDs (`FR-001`,
      `ADR-003`, `MUC-007`) appear only in section anchors or
      comments — not in the executable shell snippets or in the
      Step 1 / Step 5 headings.
- [ ] No new dependencies introduced (no new helper scripts; no new
      tools beyond `git` and `bash`).

## Sequence

- **dependsOn:** WP-001 (the SKILL.md's drift-check sub-step
  references `plugins/sulis/scripts/drift_check.sh`, which WP-001
  creates).
- **blocks:**
  - WP-009 — the unit + integration tests exercise this SKILL.md's
    prose against fixture remotes.
- **Parallelisable with:** WP-002, WP-003, WP-004, WP-005, WP-007,
  WP-008 — all different files.

## Estimated Token Cost

- **Input:** ~3k (the existing release-train SKILL.md + TDD §4.2 +
  §3 + §5.5 + ADR-003 + ADR-005)
- **Output:** ~3k (40 LOC of SKILL.md prose + 4 unit tests ≈ 80 LOC
  + 1 fixture body file)
- **Total:** ~6k

## Notes

- **Why the pin-write step is BEFORE `gh pr create`, not after:**
  the workflow's pin-read step (WP-003) reads the PR body via
  `gh api .../pulls --jq '.[0].body'` — which returns the body at
  the time of the API call. If the pin were written by a follow-up
  `gh pr edit --body-file`, there'd be a window where the PR exists
  without a pin; if the merge happened in that window, the workflow
  would see no pin. Writing the pin into the body BEFORE `gh pr
  create` eliminates the window.
- **Why `git rev-parse origin/dev` and not `git rev-parse HEAD`:**
  `HEAD` after the bump commits is on a release branch, not on dev.
  We need the SHA of `origin/dev` at the moment the release PR
  opens — that's what `git rev-parse origin/dev` gives us (after
  the drift-check's `git fetch origin` earlier in the skill flow).
- **Why append-only matters (ADR-005):** if a future change were to
  re-write the pin in-place (`sed -i 's/dev-sha-at-open: .*/.../'`),
  the workflow's first-match regex would still find the pin — but
  manually-edited PR bodies might end up with multiple stale pins,
  and the first match wouldn't be the canonical one. Append-only
  means the bottom-of-body comment is always the canonical write,
  and the regex's first-match-from-top behaviour still produces a
  deterministic extraction.
- **Touch surface:** 1 file modified (SKILL.md) + 4 unit tests + 1
  fixture body file ≈ 6 path entries. Well under MUST ≤ 15.

## Verification Plan

Per TDD §9.5 ("kind: skill behaviour — bash unit tests + local
end-to-end against a fixture clone"):

- **Adapter:** `methodology` (the SKILL.md is methodology prose;
  verification is via bash unit tests that grep the prose for
  required sub-steps + execute the prose's shell snippets against
  fixture remotes).
- **Concrete artifact:**
  `plugins/sulis/scripts/tests/unit/test_pin_write_format.sh`. The
  parity test (`test_pin_read_parity.sh`) is the cross-WP seam test
  that proves WP-006's writer and WP-003's reader agree.
- **What this WP's verification proves:** the SKILL.md contains
  both required sub-steps (preflight drift check + pin write); the
  pin format is character-for-character what the workflow regex
  captures; the pin-write sub-step is positioned BEFORE the PR-open
  call. End-to-end verification of the full release flow
  (release-train → release PR merge → workflow → back-merge) is
  WP-009's bootstrap-from-zero test + the marketplace n=1 dogfood.
- **Acceptance criteria:** all four Red tests pass; pin-write
  format byte-equals the workflow regex's capture; SKILL.md prose
  is plain-English for the operator-facing reader.
