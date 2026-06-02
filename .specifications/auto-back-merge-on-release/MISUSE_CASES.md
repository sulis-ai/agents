# MISUSE_CASES — auto-back-merge-on-release

The adversarial sweep. Each misuse case names what the system MUST refuse,
detect, or recover from. Every misuse case has a `System response (REQUIRED)`
field that is the load-bearing negative requirement.

References to existing artifacts:
- Manual recovery commits demonstrating prior drift incidents:
  `0e85c24`, `8612834`, `d93517c` (the third pass is the immediate ancestor
  of this change).
- Existing release workflow: `.github/workflows/release-on-merge.yml`
- Git workflow rules: `plugins/sulis/references/git-workflow-standard.md`
  (GIT-01..GIT-11 today; GIT-12 added by this change).

---

## MUC-001: Force-pushed dev during raced release

**Abusive actor:** None required — this is a race condition between the
release robot and legitimate developer activity on dev. The "adversary" is
time.

**Targets:** UC-001 (clean release path), UC-002 (raced release path).

**Misuse flow:**
1. A release PR is opened against `dev@SHA_A`.
2. Founder merges the release PR; main advances to `main@SHA_R` (the release
   commit).
3. Before the release robot runs its back-merge step, a developer's normal
   work merges to dev → dev is now at `dev@SHA_B ≠ SHA_A`.
4. Robot runs back-merge step. A naïve implementation would `git push --force
   origin main:dev`, overwriting `SHA_B` and losing developer work.

**System response (REQUIRED):** The workflow MUST verify dev's current SHA
against the snapshot pin recorded at release-PR-open. If they differ, the
workflow MUST NOT force-push. Instead, it opens a back-merge PR (UC-002 path)
with base=dev, head=main, and never overwrites dev's history. This is FR-001
and FR-002.

**Related NFRs:** NFR-002 (no force-push), NFR-006 (atomicity of back-merge).

---

## MUC-002: Branch protection blocks bot push to dev

**Abusive actor:** Repo admin who has configured branch protection to require
PR review on dev (legitimate posture; the threat is that the workflow
silently fails).

**Targets:** UC-001 (clean release path).

**Misuse flow:**
1. Repo admin enables "Require pull request reviews before merging" on dev.
2. Clean release path fires: dev unchanged, robot attempts `git push origin
   main:dev`.
3. Push is rejected by GitHub branch protection.
4. Naïve implementation: workflow exits non-zero with an opaque GitHub error,
   release stays half-done, dev stays drifted.

**System response (REQUIRED):** The workflow MUST detect the push rejection
and fall through to the back-merge PR path (UC-002). The job log MUST surface
the rejection reason. The robot MUST NOT exit failed if the PR-open step
succeeds — half-success is success. This is FR-003.

**Related NFRs:** NFR-004 (visibility), NFR-006 (atomicity).

---

## MUC-003: Manual operator bypasses the workflow

**Abusive actor:** A maintainer who pushes a release commit directly to main
(bypassing `/sulis:release-train`), perhaps during an incident or because
they're unfamiliar with the tooling.

**Targets:** UC-006 (regression detection).

**Misuse flow:**
1. Maintainer manually edits plugin.json + marketplace.json + CHANGELOG.md,
   commits with author = themselves (not the bot), pushes directly to main.
2. The release-on-merge workflow's loop-guard (`if author !=
   github-actions[bot]`) lets the workflow run.
3. Workflow runs, detects no pending changesets (because maintainer didn't
   use the changeset flow), exits early via the `skip=true` path.
4. Result: main has a release commit; the back-merge step never fires; dev
   stays drifted.
5. Next `/sulis:release-train` invocation reads dev's now-stale plugin.json
   and tries to compute a "next version" that's actually a re-release of
   what's already on main.

**System response (REQUIRED):** The drift detection check in
`/sulis:release-train` (FR-009) MUST run `git merge-base --is-ancestor
origin/main origin/dev` BEFORE computing the next version. If main is not an
ancestor of dev, refuse with a clear error pointing at the back-merge
recovery procedure (UC-005). The error message MUST name the manual recovery
procedure documented in GIT-12.

**Related NFRs:** NFR-005 (visibility of drift).

---

## MUC-004: Fork-consumer customises shim and breaks the contract

**Abusive actor:** A downstream consumer who edits their shim file to
override inputs or add steps, then runs into a release failure they can't
diagnose.

**Targets:** UC-003 (fork-consumer inheritance).

**Misuse flow:**
1. Consumer copies the canonical shim, then edits it: adds an extra step
   between `uses:` and the workflow inputs; changes the version pin; etc.
2. Consumer's release runs; the reusable workflow's interface contract is
   violated; bump succeeds but back-merge step doesn't fire because the
   consumer's edit clobbered a required input.
3. Consumer's dev silently drifts. Next release fails the
   `/sulis:release-train` drift check (FR-009) but the error blames "drift"
   not "shim".

**System response (REQUIRED):** The drift-detection error message (FR-009)
MUST include a hint that the user's shim file may be the cause if back-merge
appears not to have fired. The reusable workflow MUST surface its actual
inputs in the GitHub Actions UI so consumer customisation is visible. This
is FR-006.

**Related NFRs:** NFR-005 (fork-consumer transparency).

---

## MUC-005: Two releases in flight collide

**Abusive actor:** None — this is a concurrency edge case when two release
PRs (A and B) get merged in close succession.

**Targets:** UC-002 (raced path).

**Misuse flow:**
1. Release PR A is opened against `dev@SHA_X`. Merged at `T0`; release
   robot starts.
2. Before A's robot finishes, release PR B is opened against `dev@SHA_X`
   too. Merged at `T1` (very shortly after T0).
3. A's robot bumps main and back-merges (dev moves to A's tag).
4. B's robot tries to bump and finds plugin.json already at A's version.
   What is B's bump basis? What does B back-merge?

**System response (REQUIRED):** The workflow MUST use a GitHub Actions
`concurrency: group: release-on-merge` directive (already present in the
current workflow, line 49) with `cancel-in-progress: false`. This
serialises the robot runs: B waits until A finishes before starting.
When B does run, it reads main's now-post-A state, computes versions
against THAT, and back-merges accordingly. The serialisation ensures B's
back-merge sees A's main-tip. This is FR-004 (carried over from existing
workflow).

**Related NFRs:** NFR-006 (atomicity).

---

## MUC-006: Breaking change to the reusable workflow

**Abusive actor:** A future maintainer who changes the reusable workflow's
input schema or behaviour without a version bump that consumers can opt
into.

**Targets:** UC-003 (fork-consumer inheritance).

**Misuse flow:**
1. Maintainer renames a workflow input or removes a step, ships it in
   plugin version vN.
2. Consumers shimming `@sulis-vN-1` keep working.
3. Consumers shimming `@dev` (always-track opt-in) break on their next
   release without warning.

**System response (REQUIRED):** The shim documentation (FR-006, FR-008)
MUST recommend pinning to a SemVer tag by default. The `@dev` always-track
mode MUST be documented as opt-in with an explicit warning that breaking
changes to the workflow are not communicated through changesets and are
the consumer's risk to accept. Breaking changes to the workflow inputs
MUST be released as a major plugin version bump per GIT-08 SemVer rules.

**Related NFRs:** NFR-003 (backward compatibility).

---

## MUC-007: Open back-merge PR left to rot

**Abusive actor:** Time. A raced back-merge PR opens (UC-002), CI is slow
or fails, no one notices the PR, and meanwhile another release happens.

**Targets:** UC-002, UC-006.

**Misuse flow:**
1. Raced release: back-merge PR-A opens on dev.
2. CI on PR-A fails (perhaps due to a flaky test).
3. No one merges PR-A. Days pass.
4. Another release happens. PR-B opens on dev. Now dev has two open
   back-merge PRs and is drifted from main twice over.

**System response (REQUIRED):** The drift-detection check in
`/sulis:release-train` (FR-009) MUST also enumerate any open back-merge PRs
(by label or title prefix) and surface them in the error. The user should
not be able to draft a new release PR while a prior back-merge PR is open.
The reusable workflow MUST label back-merge PRs with a known label (e.g.,
`back-integrate`) so they are discoverable. This is FR-009 extended.

**Related NFRs:** NFR-005 (visibility).
