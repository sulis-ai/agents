---
# Identity (WP-01)
id: WP-003
title: "release-on-merge.yml GHA — the bump authority"
kind: infra                             # GitHub Actions workflow
source: feature
parent_phase: release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: high                      # mutates version files + tags + pushes to main as the bot

# Change primitive
primitive: create
group: expand

acceptance_criteria:
  - ".github/workflows/release-on-merge.yml exists; trigger: push to main"
  - "no pending .changesets/*.yaml → logs 'nothing to release' and exits 0 (admin/docs-only release)"
  - "with changesets → computes cumulative tier (max) and the next version, bumps ALL THREE values at one tier: plugin.json .version, marketplace.json sulis-entry .version, marketplace.json .metadata.version (ADR-003)"
  - "assembles a CHANGELOG.md entry from the changeset summaries (header uses the PLUGIN version: '## v<plugin> — <date>')"
  - "git rm's the consumed .changesets/*.yaml"
  - "commits as github-actions[bot]; tags v<marketplace metadata.version>; pushes commit + tag"
  - "VERSION_DRIFT guard: aborts BEFORE bumping if plugin.json .version != marketplace sulis-entry .version"
  - "post-bump verification: re-reads all three values; fails the workflow if any did not move to the expected next version"
  - "loop-guard: job is skipped when head_commit.message starts with the bot's own release-commit prefix (no infinite re-trigger)"

test_plan:
  unit: []                              # bash-in-YAML; tier math mirrors WP-001 (proven there)
  integration: []
  verification:
    - "post-bump verification step INSIDE the workflow (re-reads all three files; fails on mismatch) — the self-test"
    - "VERIFIED ON A REAL CUT (spec 'How we'll know it's done'): the NEXT release after this change ships runs the GHA against accumulated changesets and produces the right version + assembled CHANGELOG + tag"
    - "the workflow's tier math matches _changeset.py for the same inputs (cross-check by hand against WP-001's test vectors)"
verification_gates: [infra]             # workflow lint + the real-cut verification

# Lineage (WP-06)
derived_from:
  - finding: spec::.changes/release-train.SPEC.md::WP-3
    found_in: .changes/release-train.SPEC.md
    severity_at_discovery: n/a
generated_by:
  activity: draft-architecture/release-train
  agent: sulis-engineering-architect
addresses_findings:
  - "issue-66::ship-flow-does-not-mandate-version-bump (the bump-authority half)"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: [WP-008]                     # the bump math + the bash YAML reader conform to the FINALISED contract (tier map + format rules from WP-008, which transitively carries the WP-001 keystone)
blocks: [WP-006]                         # WP-006 (branch protection) lands with this WP so the bot can push

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Delete .github/workflows/release-on-merge.yml. The repo returns to the
  manual promote-dev-to-main.yml + hand-typed version flow. No data migration;
  no version files touched by the removal.
---

# WP-003 — `release-on-merge.yml` GHA (the bump authority)

## Context

TDD §Form (the **consumer** of the changeset seam; the one bump authority) +
§Armor (VERSION_DRIFT + post-bump verification + loop-guard). ADR-003 (the
three-value dual-version scheme + tag rule), ADR-004 (GHA-as-authority, the
accepted bash/Python duplication). Depends on WP-001 (its bash mirrors
`_changeset.py`'s tier math, conforming to the same contract). Lands with WP-006
(branch protection so the bot can push). Models honest-claude's
`.github/workflows/release-on-merge.yml`, adapted to Sulis's three-value scheme.

## Contract — the workflow

`on: push: branches: [main]`. One job, `permissions: contents: write`, with a
job-level loop-guard `if:`.

Steps:

1. **checkout** `fetch-depth: 0`, `token: ${{ secrets.GITHUB_TOKEN }}`.
2. **Check for pending changesets** — `.changesets/*.yaml` empty → set
   `skip=true`, log "No pending changesets. Nothing to release." All later steps
   `if: skip != 'true'`. (Exit 0 either way.)
3. **VERSION_DRIFT guard (BEFORE bump)** — read `plugin.json .version` and
   `marketplace.json .plugins[]|select(.name=="sulis").version`; if they differ,
   `echo "VERSION_DRIFT: plugin=$P marketplace-sulis=$M"` and `exit 1`.
4. **Compute next version** — cumulative tier = `max` over each changeset's
   `tier:` (major > minor > patch). Apply to the **plugin** series
   (`OLD_PLUGIN`) → `NEW_PLUGIN`, and to the **marketplace metadata** series
   (`OLD_META`) → `NEW_META`. (The sulis-entry version equals the plugin
   version.) Emit `new_plugin`, `new_meta`, `tier` as outputs. This is the bash
   mirror of `_changeset.next_version` (ADR-004); cross-check against WP-001's
   test vectors.
5. **Assemble CHANGELOG body** — for each changeset, extract `tier` + `summary`;
   build the entry. Prepend a new section to `plugins/sulis/CHANGELOG.md` whose
   header is **`## v<NEW_PLUGIN> — <date>`** (plugin version, per ADR-003), then
   a tier line + the bulleted summaries. Match the existing CHANGELOG section
   shape (bold tier sentence, then bullets).
6. **Apply the bump — all THREE values** (ADR-003):
   ```bash
   jq --arg v "$NEW_PLUGIN" '.version=$v' plugins/sulis/.claude-plugin/plugin.json   > /tmp/p && mv /tmp/p plugins/sulis/.claude-plugin/plugin.json
   jq --arg v "$NEW_PLUGIN" '(.plugins[]|select(.name=="sulis")).version=$v' .claude-plugin/marketplace.json > /tmp/m && mv /tmp/m .claude-plugin/marketplace.json
   jq --arg v "$NEW_META"   '.metadata.version=$v' .claude-plugin/marketplace.json   > /tmp/m && mv /tmp/m .claude-plugin/marketplace.json
   ```
7. **Post-bump verification** — re-read all three; if `plugin.json .version != NEW_PLUGIN`
   OR `marketplace sulis-entry != NEW_PLUGIN` OR `metadata.version != NEW_META`,
   `echo "post-bump verification failed: …"` and `exit 1`.
8. **Delete consumed changesets** — `git rm .changesets/*.yaml`.
9. **Commit + tag + push** — `git config user.name "github-actions[bot]"` etc.;
   commit message `release: sulis v<NEW_PLUGIN> (v<NEW_META>)` + the assembled
   body; `git tag "v<NEW_META>"`; `git push origin main`; `git push origin
   "v<NEW_META>"`.

**The loop-guard** is the job-level `if:` — skip when
`github.event.head_commit.message` starts with `release: sulis` (the bot's own
commit prefix), so the push-back in step 9 doesn't re-trigger.

> **Interaction with the existing `release-prod.yml`:** the pushed `v<NEW_META>`
> tag triggers `release-prod.yml` (already present), which turns the tag into a
> GitHub Release using the top CHANGELOG section. This WP's CHANGELOG header
> (plugin version) is what `release-prod.yml`'s `awk` reads — confirm the header
> shape matches what that workflow expects (it reads the first `## ` section,
> shape-agnostic, so a `## v0.78.0 — <date>` header is fine).

## Definition of Done — Red / Green / Blue

### Red

The "failing test" for an infra WP is the **post-bump verification step**
itself: author it first as the guard that *would* fail if the bump were
incomplete. Before the bump steps exist, the workflow does nothing useful — the
verification is the assertion. Hand-trace the tier math against WP-001's
`test_next_version_*` vectors and assert the bash produces identical results.

### Green

Author `.github/workflows/release-on-merge.yml` with all nine steps. Keep the
bash boring: explicit `jq` paths, no clever one-liners that hide the three
edits. All guards present (VERSION_DRIFT, post-bump verification, loop-guard,
nothing-to-release exit 0).

### Blue

- **Consider collapsing the bash/Python duplication** (ADR-004 alt 2): if
  `python3 -c "import sys; sys.path.insert(0,'plugins/sulis/scripts'); import
  _changeset; …"` is clean from the checked-out repo, prefer calling
  `_changeset.cumulative_tier` + `_changeset.next_version` over re-implemented
  bash — it removes the duplication and makes the contract literally single-
  source. The contract is unchanged either way; only do this if it stays simple.
- Confirm the CHANGELOG header shape matches `release-prod.yml`'s `awk` reader.
- Confirm the loop-guard prefix matches the exact commit message in step 9.

## Estimated token cost

input: ~8k / output: ~6k

## Notes

- **`kind: infra`** — GitHub Actions workflow; gates are workflow lint + the
  real-cut verification. No unit tests (bash-in-YAML); the tier math is proven
  in `_changeset.py` (WP-001) and the post-bump verification is the in-workflow
  self-test.
- **Verified on a real cut** (spec): the GHA's true acceptance is the next
  release after this change ships producing a correct three-value bump + tag.
  This WP ships *with* WP-006 so the bot can push at that point.
- **Three values, one tier, tag from metadata** is the single most error-prone
  detail — ADR-003 is the reference; the post-bump verification is the safety
  net.
