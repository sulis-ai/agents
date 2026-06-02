---
id: WP-005
title: Replace marketplace's .github/workflows/release-on-merge.yml with a shim (n=1 dogfood)
status: pending
change_id: auto-back-merge-on-release
kind: infra
primitive: substitute-replace
group: SUBSTITUTE
sequence_id: WP-005
dependsOn: [WP-002, WP-003, WP-004]
blocks: [WP-009]
estimated_token_cost:
  input: 2k
  output: 2k
tdd_section: §4.2 comp-marketplace-shim; §6.5 n=1 dogfood; §9.1 user-observable behaviour
adrs: [ADR-001]
verification:
  adapter: infra
  artifact: plugins/sulis/scripts/tests/integration/test_marketplace_shim_calls_reusable.sh
---

## Context

This WP is the **SUBSTITUTE-Replace** that turns the marketplace's
own ~280-line `.github/workflows/release-on-merge.yml` into a ~10-line
shim that `uses:` the plugin's reusable workflow. It's the n=1
dogfood: the marketplace's next production release exercises the
exact code path consumers will use.

Per TDD §6.5 + §9.1, this is the only environment where the full
chain runs end-to-end (release-train writes pin → release PR merges
→ reusable workflow reads pin → fast-forward or PR-open → post-
condition). If the marketplace's release after this change ships
succeeds and `dev == main` within 5 minutes (TDD §9.1), the design
is observed-working in the substrate that motivated it.

**Why this depends on WP-002, WP-003 AND WP-004:**

- **WP-002** moves the workflow into the plugin (the path the shim
  references must exist).
- **WP-003** adds the back-merge steps (otherwise the shim would
  point at a half-finished workflow — the very "released with half
  the new design" interval WP-002's Notes section warned against).
- **WP-004** ships the canonical shim template (which this WP copies
  into `.github/workflows/`).

**Replace, not Wrap:** per the change catalogue's "Replace rather
than wrap" priority and the No-Band-Aid-Wrappers MUST rule, the
marketplace's old workflow is replaced wholesale. The existing
workflow IS the subject being replaced; no historical state needs
preserving (the workflow's behaviour is preserved in the reusable
workflow at the plugin path; the marketplace just stops carrying its
own copy).

**Atomicity:** the diff is one-file. Either the shim is in place and
calls the plugin's reusable workflow, or the original workflow is
still in place. There is no half-shimmed state.

## Contract

### Files modified

```
.github/workflows/release-on-merge.yml      (280 → ~12 lines — substitute-replace)
```

### Files NOT modified

- `plugins/sulis/templates/shims/release-on-merge.yml` — the template
  this WP copies from (WP-004's deliverable).
- `plugins/sulis/templates/workflows/release-on-merge.yml` — the
  reusable workflow this shim calls (WP-002+WP-003's deliverable).

### Shim shape (after replace)

The new `.github/workflows/release-on-merge.yml` matches WP-004's
canonical template **with the placeholder substituted**:

```yaml
# .github/workflows/release-on-merge.yml
# Sulis canonical release-on-merge shim — see plugins/sulis/templates/shims/release-on-merge.yml
# Installed: <DATE>
# Pinned: sulis-v<CURRENT_SHIPPING_VERSION>

name: Release on merge to main

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release:
    uses: sulis-ai/agents/plugins/sulis/templates/workflows/release-on-merge.yml@sulis-v<CURRENT_SHIPPING_VERSION>
    permissions:
      contents: write
      pull-requests: write
    secrets: inherit
```

`<CURRENT_SHIPPING_VERSION>` is the SemVer version of the Sulis
plugin tag that includes WP-002 + WP-003 (the reusable workflow at
its first complete state). At execution time, this WP MUST be the
LAST one to land before the release that publishes the tag — the
shim's pin must reference a version that actually exists. Execution
flow:

1. Land WP-001..WP-004, WP-006, WP-007, WP-008, WP-009 first.
2. Ship a release with all of those landed (this is the version the
   shim will pin to).
3. Land WP-005 (this WP) — the shim now points at the version just
   shipped.
4. The next release exercises the shim end-to-end (the n=1 dogfood).

The release shipping this change is therefore a **two-step
sequence** — the design ships in step 2's release; the shim flips
in step 3 (post-release, on the next dev merge); the n=1 dogfood is
step 4's release. Per HANDOFF_TO_SEA and the SRD's verification plan,
this sequencing is intentional and documented in GIT-12 (WP-008)
under "release-train operator procedure for self-bootstrapping
changes".

### What this WP is NOT

- Not a refactor — it's a wholesale Replace per the change catalogue.
- Not a parallel-run / blue-green deploy — the workflow is the
  release pipeline itself; there's no "run both in parallel" mode
  without diverging the release behaviour.
- Not a feature flag — there's no opt-in toggle. The shim is the
  workflow; there is no other workflow.

## Definition of Done

### Red — Failing tests written

- [ ] `plugins/sulis/scripts/tests/integration/test_marketplace_shim_calls_reusable.sh`
      — asserts `.github/workflows/release-on-merge.yml` has:
      - A `uses:` clause pointing at
        `sulis-ai/agents/plugins/sulis/templates/workflows/release-on-merge.yml`
        at a SemVer tag matching `^sulis-v[0-9]+\.[0-9]+\.[0-9]+$`
        (i.e. NOT the unsubstituted `<MAJOR>.<MINOR>.<PATCH>`
        placeholder).
      - `on: { push: { branches: [main] } }` (same trigger as before).
      - `permissions: { contents: write, pull-requests: write }` at
        both top level and job level.
      - `secrets: inherit`.
      - File length ≤ 25 lines (sanity check — a 280-line shim
        regression would fail).
- [ ] `plugins/sulis/scripts/tests/integration/test_marketplace_shim_matches_canonical_template.sh`
      — diffs the marketplace's shim against WP-004's canonical
      template AFTER substituting `<MAJOR>.<MINOR>.<PATCH>` →
      `<CURRENT_SHIPPING_VERSION>` in both. The two MUST be
      byte-identical apart from the version substitution + the
      installation date header comment.
- [ ] `plugins/sulis/scripts/tests/integration/test_marketplace_shim_actionlint.sh`
      — `actionlint .github/workflows/release-on-merge.yml` exits 0.

### Green — Implementation makes tests pass

- [ ] `.github/workflows/release-on-merge.yml` is replaced wholesale
      with the shim shape above.
- [ ] The `uses:` SemVer tag is the version that contains WP-002 +
      WP-003 (the executor MUST verify this — checking that the
      referenced tag exists on the remote before committing).
- [ ] Three Red tests pass.
- [ ] No backup file (`release-on-merge.yml.bak` or similar) left in
      the repo — the substitute-replace is total; git history is the
      record of the previous shape.

### Blue — Refactor complete

- [ ] `actionlint` reports zero issues.
- [ ] `yamllint` reports zero issues.
- [ ] Header comment names the file as a Sulis shim, the installation
      date, and the pinned version. The comment is the only mention
      of internal IDs in the file (filename `release-on-merge.yml` is
      identical to the upstream template's path — intentional, makes
      grep across consumer repos trivial).
- [ ] The git commit that lands this WP has a body explaining the
      "this is the n=1 dogfood; next release exercises the full
      chain end-to-end" framing — future operators reading `git log`
      should understand why a 280-line workflow vanished.

## Sequence

- **dependsOn:**
  - WP-002 (the reusable workflow at `plugins/sulis/templates/workflows/`
    must exist)
  - WP-003 (the reusable workflow must have the back-merge steps —
    otherwise the n=1 dogfood is a "shim that calls a half-finished
    workflow")
  - WP-004 (the canonical shim template — this WP literally copies
    it)
- **blocks:**
  - WP-009 — `test_marketplace_n_equals_1_dogfood.sh` checks that
    after the next release, `git rev-parse origin/dev == git
    rev-parse origin/main` within the 5-minute window (TDD §9.1).
- **Parallelisable with:** WP-006, WP-007 (release-train + change
  SKILL.md edits — different files). Strictly serial with
  WP-002+WP-003+WP-004.

## Estimated Token Cost

- **Input:** ~2k (the existing 280-line `.github/workflows/release-on-merge.yml`
  + WP-004's canonical template + TDD §4.2 + §6.5)
- **Output:** ~2k (12-line shim + 3 integration tests ≈ 50 LOC)
- **Total:** ~4k

## Notes

- **Why this is a SUBSTITUTE-Replace and NOT a Wrap:** per the
  catalogue's Ports-vs-Wrappers discriminator — *"whose interface
  is the public face of this new code?"*. The shim's public face is
  GitHub Actions' `workflow_call` contract — which is **external**.
  Per No-Band-Aid-Wrappers, Wrap is permitted for external subjects.
  But there is no internal subject to wrap here at all: the old
  workflow is being entirely removed; the new shim is a direct
  consumer of the external (GitHub-defined) reusable-workflow
  protocol. Substitute-replace is the right primitive — old code
  out, new code in, no transitional layer.
- **Why depending on three WPs (WP-002, WP-003, WP-004) is OK
  despite the SHOULD ≤ 5 deps rule:** all three are upstream
  contracts that physically must exist before this WP can land. The
  alternative is bundling — putting WP-002+WP-003+WP-005 into one
  WP — which would violate atomicity. Three deps is the minimum
  honest dependency count for this Replace.
- **No back-out plan needed in this WP — git revert is the back-out.**
  If the n=1 dogfood reveals a problem in the reusable workflow,
  reverting WP-005's commit restores the old behaviour atomically.
  The fact that the old workflow's content lives in
  `plugins/sulis/templates/workflows/release-on-merge.yml` after
  WP-002 means a revert can't "lose" the production-tested logic —
  it just stops calling the plugin-side copy.
- **Touch surface:** 1 file modified + 3 integration tests ≈ 4 path
  entries. Well under MUST ≤ 15.

## Verification Plan

Per TDD §9.5 ("kind: infrastructure") + §6.5 (n=1 dogfood):

- **Adapter:** `infra` (integration tests on shim shape + the
  marketplace's next production release as the dogfood signal).
- **Concrete artifact:**
  `plugins/sulis/scripts/tests/integration/test_marketplace_shim_calls_reusable.sh`.
  The dogfood signal itself (TDD §9.1 user-observable behaviour) is
  verified by an out-of-band check after the next release lands —
  WP-009's `test_marketplace_n_equals_1_dogfood.sh` formalises this
  as a one-off integration check that runs against `git ls-remote`
  immediately after the release tag lands.
- **What this WP's verification proves:** the marketplace's shim has
  the canonical shape, references the correct reusable workflow at
  a real SemVer tag, lints clean. The end-to-end correctness (the
  release ACTUALLY back-merging) is the n=1 dogfood signal observed
  on the next release after this lands.
- **Acceptance criteria:** all three Red tests pass; the
  marketplace's release after this WP ships satisfies the TDD §9.1
  user-observable check (`git rev-parse origin/dev == git rev-parse
  origin/main` within 5 minutes OR a back-integrate PR is open).
