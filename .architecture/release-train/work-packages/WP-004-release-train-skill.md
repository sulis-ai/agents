---
# Identity (WP-01)
id: WP-004
title: "/sulis:release-train skill — drafts the dev→main release PR (read-only)"
kind: docs                              # a new SKILL.md (skill body)
source: feature
parent_phase: release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: low                       # read-only on origin; only side effect is opening a PR

# Change primitive
primitive: create
group: expand

acceptance_criteria:
  - "plugins/sulis/skills/release-train/SKILL.md exists; on-demand /sulis:release-train"
  - "reads .changesets/*.yaml + origin/main..origin/dev; computes cumulative tier + expected version (all three values per ADR-003)"
  - "drafts the dev→main PR body + a CHANGELOG preview from changeset summaries"
  - "opens the dev→main PR via gh pr create — READ-ONLY on origin otherwise (no commits, no working-tree edits, no version bump)"
  - "--dry-run is the default-first-pass: surfaces the draft + the gh command, opens NO PR"
  - "--draft opens the PR as a GitHub draft"
  - "'no changesets is valid' — admin-only release; the PR still opens, the GHA will detect nothing-to-release and skip the bump"
  - "aborts on VERSION_DRIFT (plugin.json != marketplace sulis-entry) and on an existing open dev→main release PR"

test_plan:
  unit: []                              # SKILL.md body; the computation reuses _changeset.py (WP-001)
  integration: []
  verification:
    - "branch-ci green (markdown / skill-shape)"
    - "--dry-run on this repo's accumulated changesets produces the correct cumulative tier + expected version + CHANGELOG preview with NO side effects (the safe live check)"
verification_gates: [docs]

# Lineage (WP-06)
derived_from:
  - finding: spec::.changes/release-train.SPEC.md::WP-4
    found_in: .changes/release-train.SPEC.md
    severity_at_discovery: n/a
generated_by:
  activity: draft-architecture/release-train
  agent: sulis-engineering-architect
addresses_findings:
  - "issue-66::release-cut-from-changesets (the on-demand release step)"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: [WP-008]                     # reuses _changeset.read_changesets/cumulative_tier/next_version against the FINALISED tier map + format (WP-008, which transitively carries the WP-001 keystone)
blocks: [WP-005]

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Delete plugins/sulis/skills/release-train/. No state is created by the skill
  (it is read-only bar the PR it opens); removing it leaves the GHA + changesets
  intact — releases would then be cut by opening the dev→main PR by hand.
---

# WP-004 — `/sulis:release-train` skill

## Context

TDD §Form (the **read-only consumer** of the changeset seam). ADR-001 (the
on-demand release step), ADR-003 (the three-value expected version it previews),
ADR-004 (the GHA owns the actual bump — this skill only *previews* + opens the
PR). Depends on WP-001 (reuses `read_changesets` / `cumulative_tier` /
`next_version`). Models honest-claude's `release-train` SKILL.md, adapted to
Sulis's dual-version preview + the existing `/sulis:change` ship vocabulary.

This is a **consumer** in the CONTRACT_FIRST seam — it reads the changeset YAML
to compute the preview. It never writes a changeset and never bumps; the single
authority for the bump is the GHA (WP-003).

## Contract — the skill

`/sulis:release-train [--dry-run] [--draft]`. Default-first-pass is `--dry-run`.

Workflow (mirroring honest's shape):

1. **Pre-flight** — `gh auth status`; `git fetch origin`; `COMMITS_AHEAD =
   origin/main..origin/dev` (0 → "nothing to release", stop); check for an
   existing open `dev→main` PR (`gh pr list --base main --head dev` → if open,
   surface + ask how to proceed); **VERSION_DRIFT** check (`plugin.json .version`
   vs `marketplace sulis-entry` — differ → abort).
2. **Discover** — `read_changesets('.changesets')` (via `python3 -c` with
   `sys.path` at `$SCRIPTS_DIR`); the merged feature commits
   `origin/main..origin/dev`; current versions from `plugin.json` +
   `marketplace.json` (all three).
3. **Compute the manifest** — `cumulative_tier(changesets)`;
   `next_version(plugin, tier)` → expected plugin version;
   `next_version(meta, tier)` → expected marketplace metadata version; expected
   tag `v<expected_meta>`. If `cumulative_tier` is `None` (no changesets):
   `version_bump_will_happen = false` — note it; the PR still opens (admin-only).
4. **Draft the PR body + CHANGELOG preview** — title by tier; body lists the
   changesets that will be consumed, the expected three-value bump, the expected
   tag, and a test plan ("confirm the bot bump fired; `/plugin update` pulls the
   new version"). Breaking/major → prominent callout + confirm.
5. **Surface + confirm** — print the full draft. On `--dry-run` (default):
   surface the draft + the exact `gh pr create` command; open **no** PR. Without
   `--dry-run`: open the PR (`gh pr create --base main --head dev [--draft]`),
   surface the URL.

**Read-only on origin** bar the PR (FE-09: report what's now true, not the
machinery). Founder-English throughout (the skill is founder-invocable).

## Definition of Done — Red / Green / Blue

### Red

SKILL.md body; the executable computation is WP-001 (proven). The
surrogate-failing-state: before this WP, there is no `/sulis:release-train` —
the only way to cut a release is opening the `dev→main` PR by hand and letting
the GHA bump. The acceptance gate is a `--dry-run` against the repo's real
accumulated changesets producing the correct cumulative tier + three-value
expected version + CHANGELOG preview with **no** side effects.

### Green

Author `plugins/sulis/skills/release-train/SKILL.md` per the contract. Reuse
`_changeset.read_changesets/cumulative_tier/next_version` via `python3 -c` —
do **not** re-implement the tier math in the skill (EP-03; the skill is a thin
read-only orchestrator over WP-001). Include the `--dry-run` / `--draft` flags,
the VERSION_DRIFT abort, the existing-open-PR abort, and the no-changesets-is-
valid path.

### Blue

- Confirm the skill computes the expected version by **calling WP-001**, not by
  duplicating `next_version` — single source of truth.
- Confirm the preview's three-value expectation matches ADR-003 exactly (plugin,
  sulis-entry, metadata; tag from metadata).
- Confirm founder-English framing + no mechanism narration; the skill is
  founder-invocable.
- Add `## Composition` notes: `/sulis:change ship` writes changesets that
  accumulate on `dev`; this skill batches them into the release PR; the GHA
  (WP-003) does the actual bump on merge.

## Estimated token cost

input: ~7k / output: ~5k

## Notes

- **`kind: docs`** — a new SKILL.md. The computation it drives is `_changeset.py`
  (WP-001, `kind: backend`, fully unit-tested). The `--dry-run` default makes the
  safe live check trivial and side-effect-free.
- **One bump authority** — this skill *previews* the version and *opens* the PR;
  it never bumps. The GHA is the authority (ADR-004). Keeping the skill read-only
  is the load-bearing constraint.
