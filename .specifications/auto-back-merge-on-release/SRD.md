# SRD — auto-back-merge-on-release

| Field | Value |
|-------|-------|
| Change kind | extend |
| Primitive | release-train workflow |
| Specification status | draft |
| Date | 2026-06-02 |
| Repo root | `/Users/iain/Documents/repos/agents-change-extend-auto-back-merge-on-release` |

## Summary

The Sulis marketplace's dev→main release flow leaves dev behind main on every
release — the robot bumps version files, deletes changesets, and tags on main,
but never pushes those changes back to dev. The marketplace has manually
recovered three times (commits `0e85c24`, `8612834`, `d93517c`) and the gap
remains. This change makes the recovery automatic.

The structural fix has three components: (1) move the release workflow into
the plugin as a *reusable workflow*; (2) extend it with a back-merge step that
fast-forwards dev to main when possible, opens a back-merge PR when raced,
and never force-pushes; (3) add a *drift-detection* check to
`/sulis:release-train` and `/sulis:change start` that refuses to operate
against a stale dev. The marketplace's own `.github/workflows/release-on-merge.yml`
becomes a thin shim calling the reusable workflow — the n=1 dogfood.

The new rule is documented as **GIT-12: Auto-back-merge on release (MUST)** in
`plugins/sulis/references/git-workflow-standard.md`.

This SRD covers six use cases (UC-001..UC-006), fourteen functional
requirements (FR-001..FR-014), eight NFRs, and seven misuse cases. Diagrams
are at `diagrams/`. The glossary at `GLOSSARY.md` locks vocabulary.

## Goals

- **G-01** Eliminate manual back-integration commits on dev after every
  release. The three historical commits prove the manual gap; future
  releases produce zero.
- **G-02** Make the back-merge mechanism inheritable by fork-consumers via
  the standard plugin update path (no consumer-side code changes beyond
  installing a 10-line shim).
- **G-03** Surface drift defensively — if back-merge somehow fails (manual
  bypass, broken shim), the next release-train invocation refuses to draft
  a release PR rather than re-bumping against stale state.
- **G-04** Codify the rule in the standards (GIT-12) so future maintainers
  (and audit) can read the invariant.

## Actors

- **Founder** — drives releases via `/sulis:release-train`; merges release
  PRs in the GitHub UI.
- **Developer on dev** — lands normal feature work on dev. Their merges may
  fall inside the race window of a release.
- **Release robot** — `github-actions[bot]`, the identity under which the
  workflow runs. Scoped via `GITHUB_TOKEN` with `contents: write` and
  `pull-requests: write`.
- **Consumer maintainer** — owner of a fork-consumer repo. Installs the
  plugin, adds the shim once.
- **Standards reader** — anyone (founder, future maintainer, code audit)
  consulting `git-workflow-standard.md` to understand the invariant.

## Use Cases

### UC-001: Clean release path

**Actor:** Release robot (triggered by founder's merge of the release PR).
**Trigger:** Push to `origin/main` from a founder-merged release PR.
**Preconditions:**
- Release PR's body contains a machine-readable line `dev-sha-at-open: <40-char SHA>`.
- Dev's current HEAD SHA equals the pin (no developer commits landed during the race window).
- Branch protection on dev allows fast-forward push by `github-actions[bot]`.

**Main flow:**
1. Workflow trigger fires on push to main.
2. Workflow performs the existing bump+tag+push steps against main.
3. Workflow reads the `dev-sha-at-open` pin from the release PR body that
   produced the head commit.
4. Workflow runs `git ls-remote origin dev` to obtain the current dev SHA.
5. Workflow compares current dev SHA against the pin. They match.
6. Workflow runs `git push origin main:dev` (fast-forward).
7. Push succeeds. Dev's HEAD is now identically main's HEAD.
8. Workflow exits success. The post-condition check (NFR-006) confirms
   `origin/dev == origin/main`.

**Postconditions:**
- Dev's HEAD equals main's HEAD.
- No back-merge PR exists.
- No merge commit on dev (it's a fast-forward).
- Workflow job log shows `clean release path — fast-forward succeeded`.

**Negative requirements (from MISUSE_CASES):**
- MUST NOT force-push to dev (MUC-001).
- MUST NOT exit success if the post-condition check fails (NFR-006).

See: [SD-001 clean release path](diagrams/sequence-diagrams.md#sd-001-clean-release-path-uc-001),
[PF-001 robot decision flow](diagrams/process-flows.md#pf-001-release-robot-decision-flow-uc-001--uc-002-combined),
[ST-001 dev state](diagrams/state-diagrams.md#st-001-dev-branch-state-relative-to-main).

### UC-002: Raced release path

**Actor:** Release robot (same trigger as UC-001).
**Trigger:** Push to `origin/main` from a founder-merged release PR, where
dev's SHA has changed during the race window.
**Preconditions:**
- Release PR's body contains the `dev-sha-at-open` pin.
- Dev's current HEAD SHA does NOT equal the pin (developer commits landed
  during the race window), OR the pin is absent/malformed (safe-default
  case).

**Main flow:**
1. Workflow trigger fires on push to main.
2. Workflow performs bump+tag+push to main (identical to UC-001 steps 2).
3. Workflow reads the pin from the release PR body.
4. Workflow runs `git ls-remote origin dev`.
5. Workflow compares current dev SHA against the pin. They differ (raced
   path) OR the pin is absent/malformed (safe-default to raced path).
6. Workflow opens a pull request:
   - base: `dev`, head: `main`
   - title: `chore: back-integrate main → dev (post-release v<NEW_META>)`
   - body: references the release tag and explains the raced path
   - labels: `back-integrate`
7. Workflow enables auto-merge on the PR (squash or merge — either works).
8. CI runs on the PR.
   - If CI green: PR auto-merges; dev gains a merge commit by
     `github-actions[bot]`.
   - If CI fails: PR stays open; UC-006 (drift detection) will block the
     next release until the PR is resolved.

**Postconditions:**
- A `back-integrate`-labelled PR exists in `open` (CI pending or failed) or
  `merged` (CI passed) state.
- Workflow exits success once the PR is open (the PR is the deliverable;
  its merge can be asynchronous).

**Negative requirements:**
- MUST NOT force-push to dev (MUC-001).
- MUST NOT exit success if the PR-open step itself failed (NFR-006).
- MUST label the PR with `back-integrate` so UC-006 can find it (MUC-007).

See: [SD-002 raced release path](diagrams/sequence-diagrams.md#sd-002-raced-release-path-uc-002).

### UC-003: Fork-consumer inheritance via shim

**Actor:** Consumer maintainer.
**Trigger:** Consumer adds a 10-line shim file once; thereafter every
release in the consumer's repo inherits back-merge behaviour.
**Preconditions:**
- Consumer has installed the Sulis plugin at v0.87.0 or later (the version
  shipping this change).
- Consumer's repo follows the two-branch model (GIT-01).

**Main flow:**
1. Consumer adds `.github/workflows/release-on-merge.yml` to their repo
   with this content (the canonical shim template; FR-006):
   ```yaml
   name: release-on-merge
   on:
     push:
       branches: [main]
   permissions:
     contents: write
     pull-requests: write
   jobs:
     release:
       uses: sulis-ai/agents/plugins/sulis/templates/workflows/release-on-merge.yml@sulis-v0.87.0
   ```
2. Consumer commits the shim to dev. Normal CI runs.
3. Consumer's next release: founder runs `/sulis:release-train`, opens
   release PR; merges PR; consumer's `.github/workflows/release-on-merge.yml`
   fires.
4. GitHub Actions resolves `uses:` to the plugin's reusable workflow at
   `@sulis-v0.87.0`.
5. The reusable workflow executes against the consumer's repo state.
6. Bump, tag, push, back-merge all happen exactly as in UC-001 / UC-002.

**Postconditions:**
- Consumer's release flow is functionally equivalent to the marketplace's.
- Consumer can opt out by deleting the shim file (NFR-005).
- Consumer can upgrade the pinned plugin version when they want fixes by
  bumping the `@sulis-v0.87.0` reference.

**Negative requirements:**
- The plugin MUST NOT write files into the consumer's `.github/workflows/`
  during install (NFR-003). The shim is opt-in.
- The reusable workflow MUST NOT assume any consumer-specific paths beyond
  the conventions documented in GIT-01 + the changeset format.

See: [SD-003 fork-consumer inheritance](diagrams/sequence-diagrams.md#sd-003-fork-consumer-inherits-via-shim-uc-003).

### UC-004: First-time setup detection (deferred to follow-on)

**Actor:** Consumer maintainer running `/sulis:discover-project`.
**Trigger:** Consumer runs `/sulis:discover-project` on a fresh or
near-fresh repo.

**Note:** The full UC-004 (offer to install the shim) is deferred to a
follow-on change per the change brief. THIS spec documents only the
detection signal so the follow-on has clear requirements to consume:

**Main flow (the part this spec owns):**
1. Consumer runs `/sulis:discover-project`.
2. Discover-project checks for `.github/workflows/release-on-merge.yml`.
3. If absent, OR present but not a shim referencing the plugin's reusable
   workflow at the consumer's installed plugin version: surface a hint in
   the discovery output: `Your release flow is not back-merging. See
   GIT-12 in git-workflow-standard.md for the canonical shim.`

**Postconditions:**
- Consumer is aware of the gap.
- No write happens (this change is detection only; install is deferred).

**Out of scope here, in scope for follow-on:**
- An interactive prompt to install the shim file.
- A `/sulis:bootstrap-workflows` skill that produces the shim.

See: [UC diagram](diagrams/use-cases.md).

### UC-005: Recovery from pre-existing drift

**Actor:** Consumer maintainer (or founder, for the marketplace itself —
this is the n=4 manual recovery if this spec doesn't ship, or n=1 last
manual recovery before the spec takes effect).
**Trigger:** Consumer discovers drift — either by failing UC-006's check
or by manual inspection of `git log dev` vs `git log main`.
**Preconditions:**
- Dev is behind main (the invariant violated).
- No back-merge PR is currently open (otherwise: merge it first).

**Main flow:**
1. Consumer fetches: `git fetch origin`.
2. Consumer checks out dev: `git checkout dev && git pull origin dev`.
3. Consumer merges main into dev with no-fast-forward: `git merge --no-ff
   origin/main`.
4. Git produces a merge commit. Commit message: `chore: back-integrate
   origin/main into dev` (matching the historical pattern at commits
   `0e85c24`, `8612834`, `d93517c`).
5. Conflicts on `plugins/sulis/.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json`, `plugins/sulis/CHANGELOG.md`,
   `.changesets/*`: resolve in favour of `origin/main` (main is the
   authority for these).
6. Other conflicts (rare): resolve case-by-case, preferring dev's content
   for non-release files.
7. Push: `git push origin dev`.
8. Verify: `git merge-base --is-ancestor origin/main origin/dev` exits 0.

**Postconditions:**
- The invariant holds again.
- Future releases from this point forward use the automatic path (assuming
  the shim is installed).

This procedure is documented in GIT-12 worked examples in
`git-workflow-standard.md` (FR-008).

See: [PF-003 manual recovery](diagrams/process-flows.md#pf-003-manual-recovery-procedure-uc-005).

### UC-006: Drift detection refuses release-train

**Actor:** Founder running `/sulis:release-train` or `/sulis:change start`.
**Trigger:** Either skill invoked while `origin/dev` is behind `origin/main`.
**Preconditions:** None — this is the first thing the skill does.

**Main flow:**
1. Founder invokes `/sulis:release-train` (or `/sulis:change start`).
2. Skill runs `git fetch origin` to ensure local refs are current.
3. Skill runs `git merge-base --is-ancestor origin/main origin/dev`.
4. If exit 0 (main is ancestor of dev — invariant holds): proceed normally.
5. If exit non-zero (drifted): skill enumerates open PRs with label
   `back-integrate`.
6. Skill refuses with one of two error messages:
   - **If a back-merge PR is open:** `Back-merge PR #N is open. Merge it
     (or resolve its CI failures), then retry.`
   - **If no back-merge PR is open:** `Dev is behind main. This usually
     means a release shipped without back-integration (e.g., manual main
     push, broken shim). Recover per GIT-12 manual procedure:
     git fetch && git checkout dev && git merge --no-ff origin/main && git push origin dev.`

**Postconditions:**
- Skill exits non-zero without modifying any git state.
- Founder has a clear next step.

**Negative requirements:**
- MUST NOT auto-recover (UC-005 is intentionally manual — automatic
  recovery here would mask the underlying cause).
- MUST NOT proceed in any form against a drifted dev — defence in depth.

See: [SD-004 drift refusal](diagrams/sequence-diagrams.md#sd-004-drift-detection-refusal-in-sulisrelease-train-uc-006),
[PF-002 drift detection](diagrams/process-flows.md#pf-002-drift-detection-in-sulisrelease-train-uc-006).

## Functional Requirements

### FR-001: Dev SHA pinned at release-PR-open

`/sulis:release-train` MUST include a machine-readable line in the release
PR body of the form `dev-sha-at-open: <40-char SHA>`, recording
`origin/dev`'s HEAD SHA at the moment the PR is opened.

**Acceptance:** Inspect the body of a release PR opened by
`/sulis:release-train` against the current marketplace dev branch; the
line is present and matches `git rev-parse origin/dev` at the same moment.

### FR-002: Reusable workflow fast-forwards on match

The reusable workflow MUST, after the existing bump+tag+push-main steps,
read the pin from the merged release PR body and run `git push origin
main:dev` when dev's current SHA equals the pin.

**Acceptance:** End-to-end test: open a release PR; do not commit anything
to dev during the window; merge the PR; observe that dev's HEAD advances
to main's HEAD via fast-forward (no merge commit appears on dev).

### FR-003: Reusable workflow opens PR when raced

The reusable workflow MUST, when dev's current SHA differs from the pin OR
the pin is absent/malformed OR the fast-forward push is rejected, open a
pull request with base=`dev`, head=`main`, title prefix `chore:
back-integrate main → dev`, label `back-integrate`, and enable auto-merge.

**Acceptance:** End-to-end test: open a release PR; commit a no-op change
to dev during the race window; merge the release PR; observe that a PR
with the expected title and label appears, auto-merge is enabled, and PR
merges when CI passes.

### FR-004: Concurrency serialised

The reusable workflow MUST use `concurrency: group: release-on-merge,
cancel-in-progress: false` to serialise multiple release runs. This is
carried forward from the existing workflow (line 49 of the current
`release-on-merge.yml`).

**Acceptance:** Inspect the reusable workflow YAML; the concurrency block
is present with `cancel-in-progress: false`.

### FR-005: Reusable workflow lives in the plugin

The release-and-back-merge workflow MUST live at
`plugins/sulis/templates/workflows/release-on-merge.yml` and be declared
as a `workflow_call` reusable workflow. Updates to the workflow ship via
plugin version bumps.

**Acceptance:** File exists at the named path with `on: workflow_call`
defined; plugin's CHANGELOG entry for the shipping version names the
workflow change.

### FR-006: Consumer shim is the integration point

A canonical shim template MUST be provided at
`plugins/sulis/templates/shims/release-on-merge.yml` and documented in
the plugin README. The shim is ~10 lines, references the reusable workflow
via `uses:` at a SemVer plugin tag, and grants `contents: write,
pull-requests: write` permissions.

**Acceptance:** Template file exists; README section describes shim
installation; shim works when copied into a consumer's
`.github/workflows/` and committed.

### FR-007: GIT-12 rule documented

`plugins/sulis/references/git-workflow-standard.md` MUST be extended with
a new rule **GIT-12: Auto-back-merge on release (MUST)**, placed after
the existing GIT-11. The rule states the invariant, names the reusable
workflow + shim as the mechanism, and references this SRD for detail.

**Acceptance:** Section `## GIT-12: Auto-back-merge on release (MUST)`
exists in the standard; severity is MUST; cross-references to GIT-05
(direct merge to dev) and GIT-06 (release train) are present.

### FR-008: GIT-12 worked examples

GIT-12 MUST include two worked examples in `git-workflow-standard.md`:
(a) the clean release path showing the fast-forward, and (b) the manual
recovery procedure (UC-005) for consumers in pre-existing drift.

**Acceptance:** Both examples present under GIT-12; manual recovery
mirrors the historical pattern at commits `0e85c24`, `8612834`, `d93517c`.

### FR-009: Drift detection in /sulis:release-train

`/sulis:release-train` MUST run, as its first action after `git fetch
origin`, the check `git merge-base --is-ancestor origin/main origin/dev`.
On non-zero exit, the skill MUST refuse to proceed. The refusal message
MUST include:
- A statement that dev is behind main.
- A reference to GIT-12.
- If an open PR with label `back-integrate` exists: its number + a
  directive to merge it first.
- Otherwise: the explicit recovery command (UC-005 step 3 + step 7).

**Acceptance:** Inspect `/sulis:release-train` SKILL.md; the check + the
refusal logic are present. End-to-end test against a deliberately drifted
local clone produces the expected refusal.

### FR-010: Drift detection in /sulis:change start

`/sulis:change start` MUST run the same drift check before creating a new
change branch. On detected drift, refuse with the same error structure
(FR-009).

**Acceptance:** Same as FR-009, for `/sulis:change start`.

### FR-011: Post-condition NFR-006 enforced in workflow

The reusable workflow MUST, as its final step, verify either (a)
`origin/dev` SHA equals `origin/main` SHA, OR (b) a PR matching `head:main
base:dev label:back-integrate state:open|merged` exists. If neither, exit
non-zero with an explicit log line naming what went wrong.

**Acceptance:** Step exists in the workflow YAML; chaos test (simulate
both push and PR-open failing) confirms the workflow exits 1 with a
descriptive log.

### FR-012: Migration of marketplace's own workflow

The marketplace's `.github/workflows/release-on-merge.yml` MUST be migrated
from the current ~280-line implementation to the 10-line shim form
(FR-006), and the current implementation MUST be moved to the plugin
location (FR-005). This is a single atomic change in this PR.

**Acceptance:** Diff shows the marketplace shim is ≤ 20 lines and uses the
plugin's reusable workflow; the prior 280-line content appears at the
plugin location with the addition of the back-merge steps (FR-002, FR-003,
FR-011).

### FR-013: Regression test — clean path

A test in the marketplace CI MUST exercise the clean path end-to-end:
construct a workspace where dev and main start at the same SHA, simulate
the bump+tag+push, then assert the fast-forward step runs and dev's HEAD
advances to main's HEAD.

**Acceptance:** Test exists, passes in CI, fails when FR-002 is regressed
(e.g., by removing the fast-forward push step).

### FR-014: Regression test — raced path

A test MUST exercise the raced path: dev advances by one commit during
the simulated window, then assert that the workflow opens a PR (not a
force-push) with the expected title, label, and auto-merge enabled.

**Acceptance:** Test exists, passes in CI, fails when FR-003 is regressed
(e.g., if a future change adds `--force` to the push step).

## Business Rules

- **BR-01** Dev's history is append-only relative to the release robot.
  The robot may only advance dev via fast-forward or via the merge of a
  back-merge PR. Force-push is forbidden. (Encoded as NFR-002, MUC-001.)
- **BR-02** A release is "atomically successful" iff main has been bumped
  AND dev has either fast-forwarded OR has an open back-merge PR. The
  workflow's exit status reflects this. (Encoded as NFR-006, FR-011.)
- **BR-03** Default version-pin shape for consumers is SemVer tag
  (`@sulis-vN.M.K`). Always-track (`@dev`) is opt-in. (Encoded as NFR-008,
  FR-006, MUC-006.)
- **BR-04** Drift is a defensive trip-wire, not a recovery mechanism.
  Detection refuses; recovery is manual (UC-005). This is by design: an
  auto-recovery would mask the underlying cause and silently re-establish
  the same hole the spec exists to close.

## Out of Scope

- Building the `/sulis:bootstrap-workflows` skill (deferred follow-on).
- Extending `/sulis:discover-project` beyond the detection signal in
  UC-004.
- Auto-configuration of branch protection rules.
- Retroactively rewriting `git-workflow-standard.md` to fold the GIT-12
  invariant into GIT-06 (the existing GIT-06 stays as-is; GIT-12 is
  additive).
- Handling non-fast-forward dev rewrites by humans (those violate
  GIT-09 and are out of scope for this mechanism — they should never
  happen and have their own enforcement path).

## Cross-References

- Existing release workflow this change extends: `.github/workflows/release-on-merge.yml`
- Existing standard this change extends: `plugins/sulis/references/git-workflow-standard.md` (GIT-01..GIT-11)
- Historical manual recovery commits: `0e85c24`, `8612834`, `d93517c`
- Glossary: [GLOSSARY.md](GLOSSARY.md)
- Misuse cases: [MISUSE_CASES.md](MISUSE_CASES.md)
- NFRs: [NFR.md](NFR.md)
- Diagrams: [use-cases.md](diagrams/use-cases.md), [sequence-diagrams.md](diagrams/sequence-diagrams.md), [process-flows.md](diagrams/process-flows.md), [state-diagrams.md](diagrams/state-diagrams.md), [data-flows.md](diagrams/data-flows.md)
- Primitive tree: [PRIMITIVE_TREE.jsonld](PRIMITIVE_TREE.jsonld)

## Verification Plan

This section satisfies the verification-by-design methodology that shipped earlier in this session.

### User-observable behaviour we're verifying

- After every release in the marketplace's own repo, `git rev-parse origin/dev` equals `git rev-parse origin/main` within 5 minutes of the release commit landing on main (clean path) OR a PR labelled `back-integrate` appears on the repo's PR list (raced path).
- The next `/sulis:release-train` invocation reports a clean next-version (no "dev is behind main" refusal).
- No new commits of the form `chore: back-integrate origin/main into dev` are created manually after this change ships — every back-integration is robot-authored.

### Verification environments

| Environment | Role |
|-------------|------|
| **Local** | Test fixtures simulate two git remotes; the workflow's bash logic runs against scripted SHAs (`ls-remote` mocked). Validates FR-002 / FR-003 / FR-011 logic without GitHub Actions runtime. |
| **CI (sandbox)** | The reusable workflow runs in a real GitHub Actions context against a throwaway test repo. Validates that branch protection interactions, PR-open API calls, and `concurrency:` directive behave as expected. |
| **Production (the marketplace itself)** | n=1 dogfood. The marketplace's first release after this change ships is the first production-grade verification. |

### Bootstrap-from-zero

A fresh consumer who installs the plugin update and adds the shim must have a working back-merge from their first release. Verification:
1. Create empty test repo; configure `dev` and `main` branch protection per GIT-04.
2. Install Sulis plugin via marketplace at the shipping version.
3. Add the canonical shim (FR-006) to `.github/workflows/release-on-merge.yml` on dev.
4. Drop a `.changesets/*.yaml` file; merge to dev; run `/sulis:release-train`.
5. Merge the resulting release PR.
6. Assert: dev and main are at the same SHA within 5 minutes; no manual intervention needed.

### Per-integration verification strategy

| Integration | Verification approach |
|-------------|----------------------|
| GitHub Actions runtime | Real — the workflow IS the implementation; we cannot meaningfully mock the runtime without losing the thing we're testing. CI is the test. |
| Branch protection rules | Real — test against actual `dev` and `main` protected branches in the sandbox repo. Mocking would skip the very thing UC-006 + MUC-002 are about. |
| Bot token (GITHUB_TOKEN) | Real — provided by Actions; tested by observing actual pushes / PR opens. |
| Race condition (dev moved during window) | Simulated — chaos test mocks `git ls-remote origin dev` to return a SHA != pin; asserts PR-open path fires. Real-world race is hard to provoke reliably, so the chaos-test path is load-bearing. |
| Drift detection | Real — construct a local clone where dev is behind main; invoke `/sulis:release-train` and `/sulis:change start`; assert refusal with the expected message. |

### Per-kind verification adapter

- **Infrastructure (the workflow YAML):** Verification is "does the workflow do what it should in CI?" The acceptance criteria on FR-002, FR-003, FR-004, FR-011 are observable in the workflow's job log + post-condition state.
- **Methodology (GIT-12 rule in the standards doc):** Verification is "does a reader looking at GIT-12 understand the invariant, the mechanism, and the recovery procedure?" Reviewed via at-least-one-other-eyes pass at PR time.
- **Skill behaviour (drift detection in /sulis:release-train + /sulis:change start):** Acceptance criteria on FR-009, FR-010 are observable via skill invocation against scripted git state.

### Infrastructure needs surfaced (deferred to follow-on)

- **Discovery extension** to detect missing or stale workflow shims in fork-consumer repos. Detection signal is in scope here (UC-004); the install action is deferred.
- **`/sulis:bootstrap-workflows` skill** (or extension of `/sulis:discover-project`) that installs the shim files for consumers. Deferred.
- **Branch protection rule auto-setup** via the GitHub API for fresh consumer setup. Deferred — depends on access patterns we don't have.
- **Workflow drift detector for the GIT-12 rule itself** — there's an existing canonical-step-annotation drift detector for `release-on-merge.yml`; the new back-merge steps should get `canonical:step:` annotations and be added to the drift catalogue. Deferred to follow-on if the canonical instance doesn't already cover the back-merge step.
