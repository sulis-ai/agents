---
id: WP-008
title: Append GIT-12 — Auto-back-merge on release (MUST) — to git-workflow-standard.md
status: pending
change_id: auto-back-merge-on-release
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-008
dependsOn: []
blocks: [WP-009]
estimated_token_cost:
  input: 2k
  output: 3k
tdd_section: §4.2 comp-git12-rule; §3 Canonical Identifiers; §6.6 Documentation review
adrs: [ADR-004]
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/unit/test_git12_section_present.sh
---

## Context

Appends a new `## GIT-12: Auto-back-merge on release (MUST)`
section to `plugins/sulis/references/git-workflow-standard.md`
after the existing `GIT-11` section. Per ADR-004, this is a pure
append — no doc re-versioning, no existing-section edits, no
cross-cutting renames.

GIT-12's body (per TDD §4.2 + §6.6):

1. **The invariant statement** — "dev's history is append-only
   relative to the release robot; every release produces either a
   fast-forwarded dev OR an open `back-integrate`-labelled PR".
2. **The mechanism** — names the reusable workflow + the consumer
   shim + the pin + the drift gate as the four moving parts.
3. **Worked example 1 — clean path** (FR-007): release PR opens, dev
   is unchanged during window, workflow fast-forwards dev to main.
4. **Worked example 2 — raced path** (FR-008): release PR opens,
   another commit lands on dev during the window, workflow opens
   the `back-integrate`-labelled PR with auto-merge enabled.
5. **Worked example 3 — manual recovery** (UC-005): if the back-
   merge mechanism fails (workflow disabled, branch protection
   misconfigured, etc.), the documented manual recovery procedure.
6. **Cross-references to GIT-05** (direct merge to dev), **GIT-06**
   (release train), **GIT-09** (no rewrite) — the three rules
   GIT-12 composes with.

This WP has **no code dependencies**. It's a pure standards-doc
append. It can land at t=0 alongside WP-001, WP-002, WP-004 — and
indeed should, because WP-006's prose can reference GIT-12 by name
once it exists.

**Why this isn't tagged as a code-impacting WP:** the standards
file is read by humans (and by Sulis agents at session start). It
doesn't execute code. The "tests" for this WP are doc-shape grep
assertions, not runtime tests.

## Contract

### Files modified

```
plugins/sulis/references/git-workflow-standard.md   (+ ~150 LOC appended after GIT-11)
```

### GIT-12 section shape

```markdown
## GIT-12: Auto-back-merge on release (MUST)

**The invariant.** dev's history is append-only relative to the
release robot. Every release produces either a fast-forwarded dev
(dev's HEAD == main's HEAD) OR an open back-integrate-labelled PR
that will fast-forward dev to main once merged. No release ever
leaves dev silently behind main.

**The mechanism.** Four moving parts:

1. The reusable release workflow at
   `plugins/sulis/templates/workflows/release-on-merge.yml`
   carries the bump + tag + push-main steps + a back-merge step
   block (read pin / decide+act / verify atomicity).
2. The consumer shim at `.github/workflows/release-on-merge.yml`
   `uses:` the reusable workflow at a SemVer plugin tag.
3. `/sulis:release-train` writes a `dev-sha-at-open: <40-hex-SHA>`
   HTML comment into the release PR body before opening the PR.
4. `/sulis:release-train` and `/sulis:change start` invoke
   `plugins/sulis/scripts/drift_check.sh` as a defence-in-depth
   drift gate — refusing to operate against a stale dev.

### Worked example 1 — clean path

Dev has no new commits between release-PR-open and release-PR-merge:

1. Drop a changeset on dev. Merge to dev.
2. Run `/sulis:release-train`. The skill writes
   `<!-- dev-sha-at-open: abc123... -->` into the release PR body
   and opens the PR.
3. Review and merge the release PR.
4. The reusable workflow fires. It reads the pin (`abc123...`)
   and compares to `git ls-remote origin dev` (also `abc123...`).
   Equal → fast-forward `git push origin main:dev`. Done.
5. Post-condition: `dev == main`. No PR opened.

### Worked example 2 — raced path

Dev gets a new commit between release-PR-open and release-PR-merge
(e.g. a hotfix lands directly on dev):

1. Drop a changeset on dev. Merge to dev. dev's HEAD is `abc123...`.
2. Run `/sulis:release-train`. The skill writes
   `<!-- dev-sha-at-open: abc123... -->` into the release PR body
   and opens the PR.
3. A separate hotfix PR merges to dev. dev's HEAD is now `def456...`.
4. Review and merge the release PR.
5. The reusable workflow fires. It reads the pin (`abc123...`)
   and compares to `git ls-remote origin dev` (now `def456...`).
   Not equal → open a back-integrate PR with:
   - base: dev
   - head: main
   - title: `chore: back-integrate main → dev (post-release v<NEW>)`
   - label: `back-integrate`
   - auto-merge enabled (merges on CI green)
6. Post-condition: dev != main, but `gh pr list --base dev --label
   back-integrate --state open` returns 1 PR. Atomicity holds.
7. CI green → PR auto-merges → dev fast-forwards to main on the
   merge.

### Worked example 3 — manual recovery (UC-005)

If the back-merge mechanism is disabled or unavailable (workflow
removed, branch protection misconfigured, GitHub Actions outage):

1. `/sulis:release-train` or `/sulis:change start` invocation
   surfaces the drift via `drift_check.sh` — refuses to proceed.
2. Manual recovery:
   ```bash
   git fetch origin
   git checkout dev
   git merge --ff-only origin/main || git merge origin/main
   git push origin dev
   ```
3. The `--ff-only` attempt is the boring case (dev is a strict
   ancestor of main — fast-forward succeeds). The fall-through to
   a merge commit handles the case where dev has commits not on
   main (unusual; usually means manual operator activity happened
   on dev directly).
4. After the merge lands, `drift_check.sh` will exit 0 — the gate
   re-opens.

### Cross-references

- **GIT-05 (Direct merge to dev on CI green):** the only path
  commits reach dev is direct merge from a feature branch. GIT-12
  is the invariant that says those merges aren't undone by stale
  back-integrations.
- **GIT-06 (Release train ceremony):** GIT-06 describes the dev →
  main promotion path. GIT-12 closes the loop by guaranteeing dev
  catches up with main atomically after each promotion.
- **GIT-09 (No rewrite):** GIT-12 enforces no-force-push at the
  workflow level — the back-merge mechanism never uses `--force`
  or `--force-with-lease`. Rejection of a fast-forward push falls
  through to PR-open, not to force.

### Compliance check at every change

Every `/sulis:change start` invocation runs `drift_check.sh`. The
gate refuses to start a new change branch off a stale dev. This is
the developer-side enforcement of GIT-12.
```

### Canonical-string compliance

The four canonical strings (`dev-sha-at-open`, `back-integrate`,
title prefix, base/head) all appear in this section's worked
examples. WP-009's `test_canonical_strings_parity.sh` asserts that
the strings in GIT-12 match the strings in `drift_check.sh` and the
reusable workflow byte-for-byte.

### What this WP is NOT

- It does NOT modify any existing section of `git-workflow-standard.md`.
  Pure append after GIT-11 (ADR-004).
- It does NOT introduce a calibration window — GIT-12 ships as MUST
  from day one because every line of the rule is enforced
  programmatically by the workflow + the drift gate, not by
  operator vigilance.
- It does NOT re-version the standards file. ADR-004 explicitly
  rejects doc re-versioning here.

## Definition of Done

### Red — Failing tests written

- [ ] `plugins/sulis/scripts/tests/unit/test_git12_section_present.sh`
      — asserts `plugins/sulis/references/git-workflow-standard.md`
      contains a section `## GIT-12: Auto-back-merge on release (MUST)`
      AFTER the existing `## GIT-11` section (textual ordering check).
- [ ] `plugins/sulis/scripts/tests/unit/test_git12_invariant_statement.sh`
      — asserts GIT-12's body contains the invariant statement
      ("append-only relative to the release robot") AND the four-
      moving-parts mechanism list AND the three worked examples
      (clean, raced, manual recovery).
- [ ] `plugins/sulis/scripts/tests/unit/test_git12_canonical_string_parity.sh`
      — asserts the four canonical strings (`dev-sha-at-open`,
      `back-integrate`, `chore: back-integrate main → dev`, base=
      `dev`/head=`main`) appear in GIT-12 byte-for-byte the same as
      in `drift_check.sh` and the reusable workflow YAML.
- [ ] `plugins/sulis/scripts/tests/unit/test_git12_cross_references.sh`
      — asserts GIT-12 cross-references GIT-05, GIT-06, GIT-09 by
      ID.

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/references/git-workflow-standard.md` modified —
      new `## GIT-12` section appended after GIT-11.
- [ ] Invariant statement, mechanism list, three worked examples,
      and three cross-references all present.
- [ ] Four canonical strings appear character-for-character matching
      WP-001's constants and WP-003's literals.
- [ ] No existing GIT-NN section content is modified.
- [ ] Four Red tests pass.

### Blue — Refactor complete

- [ ] Worked examples mirror the historical commit pattern: each
      example reads like a sequence the reader can replay from
      `git log`.
- [ ] Cross-references use the canonical `GIT-NN` form (the standards
      file's existing convention).
- [ ] Plain-English at the reader-facing level (operators reading
      the standard during onboarding); internal IDs (FR-NN, ADR-NN,
      MUC-NN) appear only in section anchors or footnotes, not in
      the runnable prose.
- [ ] No new heading levels above `##` (the section is a peer of
      GIT-01..GIT-11 — same heading depth).

## Sequence

- **dependsOn:** — (no upstream code dependencies; can run from t=0)
- **blocks:**
  - WP-009 — `test_canonical_strings_parity.sh` reads GIT-12 as one
    of the four sources whose strings must agree.
- **Parallelisable with:** WP-001, WP-002, WP-003, WP-004, WP-005,
  WP-006, WP-007 — all different files.

## Estimated Token Cost

- **Input:** ~2k (the existing `git-workflow-standard.md` + TDD §4.2
  + §3 + ADR-004 + the historical back-integration commits referenced
  in TDD §1 for the worked example tone)
- **Output:** ~3k (150 LOC standards-doc prose + 4 unit tests ≈ 60 LOC)
- **Total:** ~5k

## Notes

- **Why MUST severity at ship:** every line of GIT-12 is enforced
  programmatically (the workflow's post-condition, the drift gate's
  exit code, the static no-force-push grep). Operator compliance is
  not required because the robot does the work. MUST is honest about
  what the rule actually says — non-compliance is impossible by
  construction, not by discipline. Per the standards-authorship
  rule, calibration windows exist for principles that depend on
  operator vigilance; GIT-12 doesn't.
- **Why pure append (ADR-004):** the existing GIT-NN sections don't
  need editing — none of them say anything inconsistent with GIT-12.
  GIT-05 / GIT-06 / GIT-09 are referenced as composing rules, not
  superseded. Modifying existing sections would invite review at
  every cross-reference, defeating the "small surface, atomic
  change" discipline.
- **Why three worked examples and not one or two:** the SRD's
  FR-007 (worked-example coverage) names three paths explicitly —
  clean, raced, manual recovery. UC-005 specifies the manual
  recovery procedure verbatim; this section is where it lives in
  the standards.
- **Touch surface:** 1 file modified + 4 unit tests ≈ 5 path entries.
  Well under MUST ≤ 15.

## Verification Plan

Per TDD §9.5 ("kind: methodology — at-least-one-other-eyes review at
PR time"):

- **Adapter:** `methodology` (standards-doc reviewer review + bash
  unit tests for structural shape).
- **Concrete artifact:**
  `plugins/sulis/scripts/tests/unit/test_git12_section_present.sh`.
  The parity test
  (`test_git12_canonical_string_parity.sh`) is the cross-WP
  enforcement that GIT-12, `drift_check.sh`, the reusable workflow,
  and WP-006's pin format ALL use the same canonical strings.
- **What this WP's verification proves:** GIT-12 exists at the
  correct heading depth after GIT-11; its body contains the
  invariant, mechanism, three worked examples, and three cross-
  references; its canonical strings byte-match the strings in code.
  The documentation review (TDD §6.6) is the human-eye acceptance —
  the PR reader checks the worked examples for tone + completeness.
- **Acceptance criteria:** all four Red tests pass; a reviewer at
  PR time confirms the worked examples are unambiguous and mirror
  the historical commit pattern.
