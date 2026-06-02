---
id: WP-004
title: Author the canonical consumer shim template at plugins/sulis/templates/shims/release-on-merge.yml
status: pending
change_id: auto-back-merge-on-release
kind: infra
primitive: create
group: GENERATE
sequence_id: WP-004
dependsOn: []
blocks: [WP-005, WP-009]
estimated_token_cost:
  input: 2k
  output: 2k
tdd_section: §4.2 comp-shim-template; §5.4 Reusable workflow versioning; §5.8 Permissions surface
adrs: [ADR-001]
verification:
  adapter: infra
  artifact: plugins/sulis/scripts/tests/unit/test_shim_template_shape.sh
---

## Context

Creates the **canonical consumer shim template** at
`plugins/sulis/templates/shims/release-on-merge.yml`. This is the
file that consumers (including the marketplace itself via WP-005)
copy once into their `.github/workflows/` to wire the reusable workflow.

Per TDD §4.2 + §5.4, the shim is a tiny (~10-line) YAML that:

1. Triggers on `push.branches: [main]` (the consumer's own merge to
   main).
2. Re-declares `permissions:` block (`contents: write` +
   `pull-requests: write`) because GitHub does not inherit caller
   permissions into reusable workflows (TDD §5.8).
3. Has a single job that `uses:` the reusable workflow at a SemVer
   plugin tag (`@sulis-v<MAJOR>.<MINOR>.<PATCH>`) — ADR-001's
   default.

The shim is also documented in `plugins/sulis/README.md` with
installation instructions, the `@dev` opt-in pattern (MUC-006's
system response), and the link to GIT-12 for the invariant the shim
participates in upholding.

**Crucial — this WP does NOT touch `.github/workflows/release-on-merge.yml`.**
That's WP-005's job (and only AFTER WP-003 has landed the back-merge
steps in the reusable workflow). This WP only produces the canonical
template; WP-005 is the n=1 dogfood that uses it.

**Why this WP can land before WP-002 / WP-003:** the shim is purely
declarative — it references the reusable workflow's path by SemVer
tag but doesn't execute anything until WP-005 (the consumer) flips
to it. The path it references (`plugins/sulis/templates/workflows/release-on-merge.yml`)
is contractually settled by TDD §4.2 even if WP-002 hasn't physically
moved the file yet. The shim template is a static artifact that
documents the intended consumer shape.

## Contract

### Files created

```
plugins/sulis/templates/shims/
└── release-on-merge.yml          (~12 lines — the canonical consumer shim)
```

### Files modified

```
plugins/sulis/README.md           (+ ~30 lines — shim installation section)
```

### Shim template shape

```yaml
# plugins/sulis/templates/shims/release-on-merge.yml
#
# Canonical Sulis consumer shim — copy this file into your repo at
# .github/workflows/release-on-merge.yml.
#
# Pin to a Sulis plugin SemVer tag (default). Breaking changes to the
# reusable workflow ship as a major plugin version bump (per GIT-08).
#
# Opt-in `@dev` always-track is documented at the bottom of this file
# and in plugins/sulis/README.md. Breaking changes to @dev are NOT
# communicated through changesets; that's the consumer's risk to accept.

name: Release on merge to main

on:
  push:
    branches: [main]

permissions:
  contents: write       # bump commits, tag, push to main, fast-forward push to dev
  pull-requests: write  # gh pr create / gh pr merge --auto for raced-path back-merge

jobs:
  release:
    uses: sulis-ai/agents/plugins/sulis/templates/workflows/release-on-merge.yml@sulis-v<MAJOR>.<MINOR>.<PATCH>
    permissions:
      contents: write
      pull-requests: write
    secrets: inherit

# Opt-in: replace the tag above with `@dev` to always-track HEAD.
# Risk: breaking changes are not communicated through changesets.
# Default: pin to a Sulis plugin SemVer tag.
```

**Why `<MAJOR>.<MINOR>.<PATCH>` is a placeholder string, not a
real version:** the shim template ships in the plugin BEFORE the
plugin's first release that contains the reusable workflow. The
README's installation instructions tell the consumer to replace the
placeholder with the current Sulis plugin version (which they read
from the marketplace listing). WP-009's `test_shim_template_shape.sh`
asserts the placeholder is literally `<MAJOR>.<MINOR>.<PATCH>` and
not a real version (consumers must make a conscious choice).

**Why `secrets: inherit`:** the reusable workflow needs
`secrets.GITHUB_TOKEN`; without `inherit` the consumer's calling
context's secrets don't flow through. GitHub's documented pattern.

**Why `permissions:` is declared at BOTH the top level and the job
level:** the top-level block applies to the calling workflow's own
context; the job-level block applies to the called reusable workflow.
GitHub's documentation is explicit that both are needed — re-stated
in the shim's header comment.

### README modifications

The marketplace's `plugins/sulis/README.md` gains a new section
(after the existing Skills/Agents inventory, near the bottom):

> ## Installing the release-on-merge workflow
>
> Sulis ships a reusable GitHub Actions workflow that handles the
> bump+tag+push-main+back-merge sequence atomically. To wire it into
> your repo:
>
> 1. Copy `plugins/sulis/templates/shims/release-on-merge.yml` into
>    your repo at `.github/workflows/release-on-merge.yml`.
> 2. Replace the `@sulis-v<MAJOR>.<MINOR>.<PATCH>` placeholder with
>    the current Sulis plugin version.
> 3. Configure branch protection on `dev` and `main` per GIT-04.
> 4. Drop a changeset and merge the release PR — the workflow does
>    the rest.
>
> See [GIT-12](references/git-workflow-standard.md#git-12-auto-back-merge-on-release-must)
> for the invariant the workflow upholds.
>
> ### Opt-in: always-track @dev
>
> Replace the SemVer pin with `@dev` to always-track HEAD. Breaking
> changes to the reusable workflow are not communicated through
> changesets and are the consumer's risk to accept. Only use this in
> projects with strong test coverage and active maintenance.

### Canonical-string compliance

This WP introduces no new canonical strings. The four canonical
strings (`dev-sha-at-open`, `back-integrate`, title prefix,
base/head) all live inside the reusable workflow (WP-003), not the
shim — the shim is just a `uses:` reference.

## Definition of Done

### Red — Failing tests written

- [ ] `plugins/sulis/scripts/tests/unit/test_shim_template_shape.sh`
      — asserts the shim YAML has:
      - `on: { push: { branches: [main] } }`
      - `permissions: { contents: write, pull-requests: write }` at
        the top level
      - exactly one job named `release` with a `uses:` pointing at
        the reusable workflow's path
      - the `uses:` references a SemVer tag template
        `@sulis-v<MAJOR>.<MINOR>.<PATCH>` (not a hardcoded version)
      - `secrets: inherit`
      - the job-level `permissions:` block re-declares `contents:
        write` and `pull-requests: write`
- [ ] `plugins/sulis/scripts/tests/unit/test_shim_readme_section.sh`
      — asserts `plugins/sulis/README.md` contains a section heading
      `## Installing the release-on-merge workflow` AND mentions the
      `@dev` opt-in.
- [ ] `plugins/sulis/scripts/tests/unit/test_shim_actionlint.sh`
      — replaces `<MAJOR>.<MINOR>.<PATCH>` with `0.0.0` in a temp copy
      of the shim, runs `actionlint`, asserts zero issues. The
      placeholder substitution is to make the shim syntactically
      valid for the linter — `actionlint` can't validate against an
      unresolvable tag, so we substitute and lint the shape.

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/templates/shims/release-on-merge.yml` exists
      with the shape above.
- [ ] Header comment names the file as the canonical Sulis consumer
      shim, names the SemVer pin discipline (ADR-001), and points
      at the README + GIT-12.
- [ ] `<MAJOR>.<MINOR>.<PATCH>` placeholder is literally those
      characters, not a real version.
- [ ] `plugins/sulis/README.md` gains the installation section.
- [ ] Three Red tests pass.

### Blue — Refactor complete

- [ ] `actionlint` on the substituted shim is clean.
- [ ] YAML formatting matches the rest of `plugins/sulis/templates/`
      (2-space indent, no trailing spaces).
- [ ] README section is in plain English (FE-01..FE-10 compliance) —
      no internal IDs (`WP-NNN`, `ADR-NNN`) in the consumer-facing
      prose; one link to GIT-12 is acceptable because GIT-12 is the
      consumer-facing rule name.
- [ ] No secrets, tokens, or environment-specific paths.

## Sequence

- **dependsOn:** — (no upstream code dependencies; the path the shim
  references is contractually settled in TDD even before WP-002
  physically moves the workflow file)
- **blocks:**
  - WP-005 — the marketplace's own `.github/workflows/release-on-merge.yml`
    is replaced with a copy of this template (the n=1 dogfood)
  - WP-009 — `test_bootstrap_from_zero.sh` copies this template into
    a sandbox repo and validates the bootstrap sequence
- **Parallelisable with:** WP-001 (drift_check.sh), WP-002 (move
  workflow), WP-008 (GIT-12 append) — all four are independent files
  at t=0.

## Estimated Token Cost

- **Input:** ~2k (TDD §4.2 + §5.4 + §5.8 + ADR-001 + the existing
  README structure)
- **Output:** ~2k (12-line shim + 30 lines README + 3 unit tests ≈
  60 LOC)
- **Total:** ~4k

## Notes

- **Why this is GENERATE-Create, not EXTEND:** it's a net-new file
  at a new path. The README modification is small but co-located —
  the shim and its installation instructions ship together so they
  can't drift.
- **Why no integration test in this WP:** the shim only works when
  there's a reusable workflow to call. The bootstrap-from-zero test
  in WP-009 is the integration surface that exercises the shim end-
  to-end against a real sandbox repo. This WP's unit tests just
  prove the file's shape.
- **Why ship the shim template before WP-005 flips the marketplace:**
  the shim is documentation that downstream consumers need from day
  one. Shipping it as part of the change means the README's
  installation instructions are valid the moment the plugin tag lands
  — no "wait for the next release to use this" interval. WP-005's
  n=1 dogfood uses this same file.
- **Why `<MAJOR>.<MINOR>.<PATCH>` and not a version-bumping script:**
  consumers are encouraged to make a conscious choice about which
  Sulis version to pin to. A bumping script would obscure that
  decision. The README's instruction to "replace with the current
  Sulis plugin version" is one extra step in exchange for explicit
  consent.
- **Touch surface:** 2 files (shim + README modification) + 3 unit
  tests ≈ 5 path entries. Well under MUST ≤ 15.

## Verification Plan

Per TDD §9.5 ("kind: infrastructure"):

- **Adapter:** `infra` (unit tests on YAML shape + actionlint
  conformance; full bootstrap-from-zero verification in WP-009).
- **Concrete artifact:** `plugins/sulis/scripts/tests/unit/test_shim_template_shape.sh`.
- **What this WP's verification proves:** the canonical shim has the
  correct shape (push trigger, permissions, uses path, SemVer-tag
  placeholder, secrets inherit); the README documents the
  installation procedure; `actionlint` accepts the substituted shim.
  Full end-to-end correctness (sandbox repo + real CI + real release)
  lives in WP-009's bootstrap-from-zero test.
- **Acceptance criteria:** all three Red tests pass; the README
  installation section reads cleanly in plain English (FE-04 30-
  second scannable).
