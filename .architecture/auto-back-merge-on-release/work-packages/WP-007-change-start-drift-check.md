---
id: WP-007
title: Extend /sulis:change start preflight — invoke drift_check.sh before branch creation
status: pending
change_id: auto-back-merge-on-release
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-007
dependsOn: [WP-001]
blocks: [WP-009]
estimated_token_cost:
  input: 2k
  output: 2k
tdd_section: §4.2 comp-drift-check-cs; §5.5 Defence in depth (L3)
adrs: [ADR-003]
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/unit/test_change_start_drift_check_called.sh
---

## Context

Extends `plugins/sulis/skills/change/SKILL.md` (specifically the
`start` action's preflight) with **one** new sub-step: invoke
`plugins/sulis/scripts/drift_check.sh` as the first action before
any branch creation logic.

Per TDD §4.2 + §5.5 (L3), this is the developer-side drift gate.
The release-train gate (WP-006) catches drift at release time; this
gate catches drift at change-start time. A feature branch cut off a
drifted dev would re-introduce stale content into the next release
— this preflight stops that at the earliest point.

**Why one sub-step, not two:** `/sulis:change start` doesn't write
a pin (only release-train does). The only edit is the drift-check
preflight. This WP is the smaller half of the "two consumers of the
shared helper" pattern; WP-006 is the larger half.

**Why this WP shares the same dep (WP-001) as WP-006 but ships
separately:** different SKILL.md files (release-train/SKILL.md vs
change/SKILL.md). Splitting them avoids artificial coupling — if a
future change touches release-train's pin logic, that change need
not also re-validate the change-start preflight.

## Contract

### Files modified

```
plugins/sulis/skills/change/SKILL.md  (+ ~15 LOC in the `start` action preflight)
```

### The new sub-step

A new bullet inserted as the **first** preflight action in the
`start` action's prose, BEFORE any branch creation or change-record
setup:

> **Preflight — refuse to start a change off a stale dev (FR-010, ADR-003).**
>
> A new change branch cut off a `dev` that's behind `main` will
> re-introduce stale content into the next release. Run the shared
> drift helper before doing any work:
>
> ```bash
> if ! bash plugins/sulis/scripts/drift_check.sh; then
>   exit 1
> fi
> ```
>
> The helper's stderr message names the recovery procedure — either
> wait for the open back-integrate PR to merge, or run the UC-005
> manual recovery if no PR is open. On exit code 1 the skill STOPS;
> no change record is created; no branch is cut.
>
> Per TDD §5.5 L3: this is the developer entry-point's defence-in-
> depth layer. The release-train gate (WP-006) is L2; the workflow
> itself is L1.

### Where in the `start` flow this goes

`/sulis:change start` currently does (high-level):

1. Parse arguments (change-name, etc.).
2. Resolve project root + load context.
3. Create change record + branch.
4. Hand off to specify / design / etc.

This WP inserts the drift check between step 2 and step 3 — after
path resolution (so we know which repo we're in and `git fetch
origin` makes sense), before any side-effect (no change record, no
branch). The exact insertion point is the first sub-step of "Step 3"
in the SKILL.md's current structure, before any `git checkout -b` /
`mkdir .changes/...` lines.

### What this WP is NOT

- It does NOT add drift checking to other `/sulis:change` actions
  (`list`, `resume`, `ship`, `discard`). Only `start` cuts a new
  branch off `dev`. Other actions operate on existing branches.
- It does NOT invent any new canonical strings; the helper owns all
  shared strings.
- It does NOT add a `--skip-drift-check` flag. NFR-005 (opt-out) is
  satisfied by the helper-level documented manual recovery path, not
  by a skill-level bypass flag. A bypass flag would defeat the gate.

## Definition of Done

### Red — Failing tests written

- [ ] `plugins/sulis/scripts/tests/unit/test_change_start_drift_check_called.sh`
      — asserts `plugins/sulis/skills/change/SKILL.md` contains the
      drift-check sub-step in the `start` action's preflight section,
      AND an `exit 1` on helper failure, AND that the sub-step
      appears BEFORE the first `git checkout -b` / branch creation
      reference in the file.
- [ ] `plugins/sulis/scripts/tests/integration/test_change_start_drift_gate_blocks.sh`
      — sets up a fixture local repo where `origin/dev` is behind
      `origin/main` (no open PR), invokes the documented start-action
      shell snippet, asserts non-zero exit AND no branch was created.

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/skills/change/SKILL.md` modified — the `start`
      action's preflight gains the drift-check sub-step as its
      first action.
- [ ] The sub-step references `plugins/sulis/scripts/drift_check.sh`
      by its canonical path (NO inlined helper logic; NO copy-paste
      of `git merge-base --is-ancestor` into the SKILL.md prose).
- [ ] Two Red tests pass.

### Blue — Refactor complete

- [ ] The sub-step's prose mirrors WP-006's drift-check sub-step in
      tone and structure (single source of truth, two call sites,
      both citing TDD §5.5 + ADR-003).
- [ ] No copy-paste of the recovery message into the SKILL.md — the
      helper owns the recovery message; this prose just tells the
      reader the helper will print it.
- [ ] No new dependencies (no new helpers; no new tools).
- [ ] FE compliance: the executable snippet is plain shell; no
      internal IDs appear inside the shell snippet itself (the
      bullet's heading can reference `FR-010` / `ADR-003` /
      `MUC-003` as anchors, but the runnable code is unannotated).

## Sequence

- **dependsOn:** WP-001 (the SKILL.md's sub-step references
  `plugins/sulis/scripts/drift_check.sh`).
- **blocks:**
  - WP-009 — the unit + integration tests exercise the SKILL.md
    sub-step against fixture remotes.
- **Parallelisable with:** WP-002, WP-003, WP-004, WP-005, WP-006,
  WP-008 — all different files. Strictly serial only with WP-001.

## Estimated Token Cost

- **Input:** ~2k (the existing `change/SKILL.md` + TDD §4.2 + §5.5
  + ADR-003 + WP-006's drift-check sub-step for prose parity)
- **Output:** ~2k (15 LOC of SKILL.md prose + 2 tests ≈ 50 LOC + 1
  fixture local repo setup script)
- **Total:** ~4k

## Notes

- **Why split from WP-006 despite identical mechanism:** different
  files, different test fixtures, different consumer surface
  (release-train operates at release time; change-start operates at
  development time). Splitting keeps each WP small (one file each)
  and avoids the "edit two files for one logical change" merge-
  conflict surface that the WP-08.5 cross-kind contract pattern is
  designed to prevent.
- **Why no `--skip-drift-check` flag:** a bypass flag would defeat
  the gate. Operators who must bypass have the documented manual
  recovery procedure (UC-005) — that's the conscious, audited
  bypass. The skill's prose can refuse to operate; the operator's
  shell never has to.
- **Why no integration test for `git push --force-with-lease` or
  similar:** `/sulis:change start` never pushes. It only cuts a
  branch off `origin/dev`. The drift check is upstream of any push.
- **Touch surface:** 1 file modified + 2 tests + 1 fixture setup ≈
  4 path entries. Well under MUST ≤ 15.

## Verification Plan

Per TDD §9.5 ("kind: skill behaviour"):

- **Adapter:** `methodology` (SKILL.md prose verified by bash unit
  tests that grep the prose and execute the snippet against fixture
  remotes).
- **Concrete artifact:**
  `plugins/sulis/scripts/tests/unit/test_change_start_drift_check_called.sh`.
  The integration variant
  (`test_change_start_drift_gate_blocks.sh`) is the load-bearing
  one — it proves the gate actually stops a branch from being cut
  on a drifted dev.
- **What this WP's verification proves:** the SKILL.md's `start`
  action contains the drift-check sub-step as its first preflight
  action; the gate is observable on a fixture drifted clone (no
  branch is created, non-zero exit).
- **Acceptance criteria:** both Red tests pass; the SKILL.md prose
  is plain-English (FE-04 30-second scannable); no helper logic is
  inlined.
