---
# Identity (WP-01)
id: WP-007
title: "Standards + docs + retire the manual bump from the documented flow"
kind: docs
source: feature
parent_phase: release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: low                       # documentation; no executable behaviour

# Change primitive
primitive: docs
group: reinforce

acceptance_criteria:
  - "git-workflow-standard.md records the new release ceremony: changeset-per-change → /sulis:release-train → GHA bump (the GHA is the bump authority)"
  - "git-workflow-standard.md GIT-06 (dev→main promotion) no longer expects a human to hand-pick/type a version — the GHA derives it from changesets"
  - "the /sulis:change ship docs + lifecycle no longer carry a manual-bump expectation GOING FORWARD"
  - "cross-links #66 (the root cause this closes)"
  - "explicitly notes that THIS change's own ship still does a manual bump ONE last time (the train isn't live yet); WP-007 retires the manual bump from the documented flow going forward, it does NOT block this change's final manual-bump ship"

test_plan:
  unit: []
  integration: []
  verification:
    - "branch-ci green (markdown link-integrity / docs lint)"
    - "no remaining doc instructs a human to hand-pick a SemVer version for a normal release (grep the standards + ship docs)"
verification_gates: [docs]

# Lineage (WP-06)
derived_from:
  - finding: spec::.changes/release-train.SPEC.md::WP-7
    found_in: .changes/release-train.SPEC.md
    severity_at_discovery: n/a
generated_by:
  activity: draft-architecture/release-train
  agent: sulis-engineering-architect
addresses_findings:
  - "issue-66::ship-flow-does-not-mandate-version-bump (the documented-ceremony half)"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: [WP-005]                      # documents the full flow once all the machinery is in place
blocks: []

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Revert the documentation edits. Pure docs; no behaviour change.
---

# WP-007 — Standards + docs + retire the manual bump

## Context

TDD §Form (the documented ceremony) — the REINFORCE/Document primitive that
records the new flow. ADR-004 (the GHA is the bump authority; the manual bump in
the *promotion* ceremony is what's retired). Depends on WP-005 (documents the
complete flow only once every machinery piece is in place). This is the WP that
resolves TDD "Ambiguity resolved" #1 in the docs: the manual bump lives in the
**dev→main promotion ceremony** (GIT-06 + `promote-dev-to-main.yml`'s hand-typed
`version` input), and that is what is retired from the documented flow.

## Contract — the documentation edits

1. **`plugins/sulis/references/git-workflow-standard.md`**
   - Update the **summary** + **GIT-06 (dev→main promotion)** to describe the new
     ceremony: *each change writes a changeset on ship → `/sulis:release-train`
     opens the reviewed dev→main PR → the `release-on-merge.yml` GHA computes the
     cumulative version from the changesets and bumps + tags as the bot.* The
     human no longer hand-picks/types a SemVer version for a normal release.
   - Keep GIT-08 (SemVer) — the *scheme* is unchanged; only *who/what* applies it
     moves from a human to the GHA.
   - Note the hot-fix path (GIT-11) is unaffected (hot-fixes are their own
     release; out of scope for the train).
   - Add a version-history row.

2. **`plugins/sulis/skills/change/SKILL.md`** (the ship docs + lifecycle)
   - Ensure the ship flow's narration + the "When NOT to invoke" / promotion
     notes describe the new world: ship writes a changeset (WP-002) and does not
     bump; releasing is `/sulis:release-train` + the GHA, not a hand-typed
     version. (WP-002 added the step; WP-007 cleans up any *surrounding* prose
     that still implies a manual bump expectation.)

3. **Cross-link #66** in the git-workflow-standard provenance/version-history and
   in a one-line note in the release ceremony section.

4. **The one-last-manual-bump carve-out (MUST state explicitly):** add a short
   note (in the standard's version-history row and/or a ship-docs aside) that
   **this change's own ship still does a manual bump ONE last time** because the
   train isn't live yet — WP-007 retires the manual bump from the documented
   flow **going forward**, and does **not** block this change's final
   manual-bump ship.

## Definition of Done — Red / Green / Blue

### Red

Docs WP; the surrogate-failing-state is a grep: **before** this WP, the
standards + ship docs still instruct a human to pick/type a version for a normal
release (GIT-06 mechanics step 3 "Tag the resulting commit with a SemVer release
tag"; `promote-dev-to-main.yml`'s `version` input). The acceptance gate is that,
**after**, no normal-release doc instructs a human to hand-pick a version.

### Green

Make the edits above. Keep the prose boring + accurate; reference the ADRs
(ADR-001, ADR-004) rather than re-deriving the rationale (Respect-Don't-Restate).

### Blue

- `grep` the standards + ship docs for residual manual-bump language for normal
  releases; confirm none remains (the hot-fix GIT-11 path legitimately keeps its
  own tag step — don't touch it).
- Confirm the one-last-manual-bump carve-out is stated explicitly so the
  executor of *this* change isn't confused into skipping its own (still-manual)
  bump.
- Confirm the cross-link to #66 is present.

## Estimated token cost

input: ~6k / output: ~4k

## Notes

- **`kind: docs`.** No executable behaviour; gates are link-integrity + the grep
  for residual manual-bump language.
- **Does NOT block this change's final manual-bump ship.** The train goes live
  for the NEXT release; this change ships through the OLD flow (manual bump) one
  last time per the spec's bootstrapping point 5. WP-007 changes the *documented*
  flow, not this change's own ship.
