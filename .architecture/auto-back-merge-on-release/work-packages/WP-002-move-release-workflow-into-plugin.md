---
id: WP-002
title: Move release-on-merge.yml into the plugin as a reusable workflow (no back-merge yet)
status: pending
change_id: auto-back-merge-on-release
kind: infra
primitive: refactor
group: REORGANISE
sequence_id: WP-002
dependsOn: []
blocks: [WP-003, WP-005, WP-009]
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: §4.2 comp-reusable-workflow (bump+tag+push-main half); §5.1 Concurrency model; §5.4 Reusable workflow versioning
adrs: [ADR-001]
characterisation_test: tests/methodology/workflow/test_release_on_merge_yaml_unchanged_behaviour.sh — diffs the new reusable workflow's bump+tag+push-main steps against the pre-move workflow YAML; assert byte-equivalent (modulo the `on:` block + `permissions:` re-declaration).
verification:
  adapter: infra
  artifact: plugins/sulis/scripts/tests/unit/test_no_force_push_static.sh
---

## Context

This WP is the **REORGANISE-Move** half of the reusable-workflow
introduction. The marketplace's existing
`.github/workflows/release-on-merge.yml` (~280 lines) is **moved**
into the plugin at `plugins/sulis/templates/workflows/release-on-merge.yml`
with three structural adjustments:

1. The top-level `on:` block changes from `push.branches:[main]` to
   `workflow_call:` (no inputs — per TDD §4.2 the reusable workflow
   currently accepts zero inputs).
2. The job-level `permissions:` block is **explicitly re-declared**
   (GitHub does not inherit caller permissions into reusable workflows
   — TDD §5.8). The block carries `contents: write` and
   `pull-requests: write`.
3. The `concurrency:` directive (TDD §5.1) — `group: release-on-merge,
   cancel-in-progress: false` — is preserved verbatim.

**No back-merge steps are added in this WP.** That is WP-003. This
WP's only behavioural delta is "the same release work, callable as a
reusable workflow". The deliberate split prevents one PR from being
both a refactor (move) and a feature (back-merge) — REORGANISE-Move
must precede the EXPAND-Extend that adds new steps.

The marketplace's own `.github/workflows/release-on-merge.yml` is
**NOT touched in this WP**. The marketplace continues to run its
existing copy until WP-005 replaces it with a shim. Two copies coexist
briefly (in this WP and through WP-003) — the marketplace's own copy
is the source of truth in production, the plugin-side copy is the
in-flight design that nothing currently calls.

**Characterisation test (REORGANISE MUST per `references/change-primitives.md`):**
the move must not change the bump+tag+push-main behaviour. The
characterisation test diffs the new reusable workflow's steps against
the pre-move YAML, after stripping the `on:` and `permissions:`
blocks (the two structural adjustments). Byte-equivalent → safe to
proceed to WP-003.

## Contract

### Files created

```
plugins/sulis/templates/workflows/
└── release-on-merge.yml          (~285 lines — the existing workflow's
                                   job + steps, wrapped in `on:
                                   workflow_call`, with re-declared
                                   permissions)
```

### Files NOT touched

- `.github/workflows/release-on-merge.yml` (the marketplace's own
  workflow) — remains in place. WP-005 replaces it with a shim, AFTER
  WP-003 has added the back-merge steps to the reusable workflow.
- `plugins/sulis/templates/shims/release-on-merge.yml` — that's WP-004.

### Structural shape of the new file

```yaml
# plugins/sulis/templates/workflows/release-on-merge.yml
name: Release on merge to main (reusable)
on:
  workflow_call:    # zero inputs (TDD §5.4 — forward-looking for major-bump on input change)

concurrency:
  group: release-on-merge
  cancel-in-progress: false

permissions:
  contents: write       # bump commits, tag, push to main, future fast-forward push to dev
  pull-requests: write  # future gh pr create / gh pr merge --auto (WP-003)

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      # ... existing bump+tag+push-main steps, copied verbatim from
      # the pre-move workflow ...
```

The job body's steps are character-for-character copies of the
existing workflow's `release` job steps. The characterisation test
(below) enforces this by diff.

### Canonical-string adoption

Per TDD §3, this WP does NOT introduce any of the four canonical
strings (`dev-sha-at-open` pin, `back-integrate` label, back-merge PR
title prefix, base/head). Those are introduced by WP-003 (which adds
the back-merge step block to this file).

### What "reusable workflow" means here

The file is the GitHub-native reusable workflow pattern: a YAML at a
path under `plugins/sulis/templates/workflows/`, with `on:
workflow_call`, callable from a consumer's `.github/workflows/*.yml`
via `uses: sulis-ai/agents/plugins/sulis/templates/workflows/release-on-merge.yml@<TAG>`.
Per CP-01..05 + TDD §4.4, this is GitHub's documented pattern — taken
silently, no defence required.

## Definition of Done

### Red — Failing tests written

The characterisation test is the load-bearing Red test. It must fail
before this WP's code change lands and pass after.

- [ ] `plugins/sulis/scripts/tests/methodology/test_release_on_merge_yaml_unchanged_behaviour.sh`
      — diffs the steps block of
      `plugins/sulis/templates/workflows/release-on-merge.yml` against
      a captured snapshot of the pre-move `.github/workflows/release-on-merge.yml`
      steps block (snapshot file:
      `plugins/sulis/scripts/tests/fixtures/release-on-merge/pre-move-snapshot.yml`).
      Test asserts: after stripping `on:`, `permissions:`, `name:` and
      `concurrency:` block YAML, the remaining `jobs.release.steps`
      key is byte-identical. Test fails before WP-002 ships (no file
      exists at `plugins/sulis/templates/workflows/release-on-merge.yml`)
      and passes after.

- [ ] `plugins/sulis/scripts/tests/unit/test_concurrency_present.sh`
      — TDD §6.1: asserts the reusable workflow YAML contains
      `concurrency:` with `group: release-on-merge` and
      `cancel-in-progress: false`. WP-009 owns the full suite; this
      WP authors the one test that catches a missing concurrency
      block.

- [ ] `plugins/sulis/scripts/tests/unit/test_no_force_push_static.sh`
      — TDD §5.2 (static layer) + §6.1: asserts `grep -nE
      '(\+main:dev|--force|--force-with-lease).*dev' plugins/sulis/templates/workflows/release-on-merge.yml`
      returns zero hits. This test exists as a guardrail for future
      changes; it passes trivially after this WP because the moved
      content has no force flags. WP-009 carries the same test
      forward; this WP gets the test running early so the file is
      protected from the moment it's created.

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/templates/workflows/release-on-merge.yml` created.
- [ ] Top-level `on: workflow_call` (no inputs).
- [ ] `concurrency: { group: release-on-merge, cancel-in-progress: false }`
      block preserved verbatim from the source.
- [ ] `permissions:` block re-declared at job level: `contents: write`,
      `pull-requests: write`.
- [ ] All `release` job steps from the source workflow copied
      character-for-character — no edits, no reformatting, no
      reordering.
- [ ] `plugins/sulis/scripts/tests/fixtures/release-on-merge/pre-move-snapshot.yml`
      exists (a captured copy of the source workflow's steps block,
      used as the characterisation test's golden file).
- [ ] All three Red tests pass.
- [ ] **The marketplace's own `.github/workflows/release-on-merge.yml`
      is NOT modified** — it stays in production unchanged until
      WP-005.

### Blue — Refactor complete

- [ ] YAML lints clean (`yamllint` or `actionlint`).
- [ ] Step IDs (`id: bump-version`, etc.) match the source so any
      future cross-reference from documentation continues to work.
- [ ] File header comment names the file as "reusable; called via
      `uses:` from a consumer shim" with a pointer at the canonical
      shim template path (which is WP-004's deliverable — the comment
      can reference the path even before WP-004 lands).
- [ ] No TODO / FIXME / placeholder comments — the file is production-
      ready as a reusable; the back-merge steps come in WP-003 as a
      separate diff.
- [ ] No secrets, tokens, or PATs introduced — the existing workflow's
      auth surface (`secrets.GITHUB_TOKEN`) is the only auth needed.

## Sequence

- **dependsOn:** — (no upstream code dependencies; can run from t=0)
- **blocks:**
  - WP-003 — adds the back-merge step block to this same file
  - WP-005 — the marketplace shim references the path this WP creates
  - WP-009 — the unit + integration tests run against this file
- **Parallelisable with:** WP-001 (drift_check.sh), WP-004 (shim
  template), WP-008 (GIT-12 append).

## Estimated Token Cost

- **Input:** ~3k (the existing 280-line `.github/workflows/release-on-merge.yml`
  + TDD §4.2 + §5.1 + §5.8 + ADR-001)
- **Output:** ~3k (the moved workflow ≈ 285 LOC + fixture snapshot +
  characterisation test ≈ 30 LOC + 2 unit-test stubs)
- **Total:** ~6k

## Notes

- **Why this is a REORGANISE-Move, not a CREATE:** the new file is
  the old file's content under a new path with two structural
  adjustments (`on:` shape, `permissions:` re-declaration). Per
  `references/change-primitives.md`, that is Move + Refactor — the
  Reorganise group. Splitting from EXPAND-Extend (which WP-003
  handles) keeps the refactor characterisation test honest: it can
  prove byte-equivalence of the existing behaviour before any new
  behaviour is added.
- **Why the characterisation test is mandatory:** per the change
  catalogue's "Characterisation Tests Before Refactor (MUST)" rule.
  This Move runs against a 280-line YAML that has been hand-tuned
  through three production releases — any silent reformatting would
  be a behaviour change in disguise. The byte-diff test catches that.
- **Why we DON'T touch `.github/workflows/release-on-merge.yml`
  here:** until WP-003 lands the back-merge steps + WP-004 publishes
  the canonical shim, the new reusable workflow is incomplete
  (missing the feature it exists to provide). The marketplace's
  production releases continue using the old workflow until WP-005
  flips the shim — at which point the new reusable workflow is
  complete and the old workflow is replaced atomically. This avoids a
  "released with half the new design" interval.
- **No new dependencies introduced.** GitHub's reusable-workflow
  feature is generally available since 2021; no `uses: actions/`
  version bumps required.
- **Touch surface:** 3 files (the moved workflow + the fixture
  snapshot + the characterisation test + 2 unit-test stubs ≈ 5 path
  entries). Well under the MUST ≤ 15 ceiling.

## Verification Plan

Per TDD §9.5 ("kind: infrastructure — sandbox CI runs the workflow
against a real repo"):

- **Adapter:** `infra` (sandbox CI runs the workflow + local
  characterisation test).
- **Concrete artifact:** `plugins/sulis/scripts/tests/unit/test_no_force_push_static.sh`.
  The characterisation test
  (`tests/methodology/test_release_on_merge_yaml_unchanged_behaviour.sh`)
  is the more specific load-bearing artifact for the REORGANISE
  primitive; the static no-force-push check is the simplest one-line
  citation that proves behaviour is held.
- **What this WP's verification proves:** the move preserves byte-
  equivalent step behaviour; the static guardrail catches any future
  force-flag introduction; concurrency is preserved. The full
  end-to-end behaviour (clean / raced / branch-protection paths) is
  WP-003's verification (after the back-merge steps are added) and
  WP-009's regression suite.
- **Acceptance criteria:** characterisation test passes;
  `actionlint` reports zero issues on the new file; no production
  workflow files are modified in this WP's diff.
