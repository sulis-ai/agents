# Trunk-based release Workflow — the Path-A re-model (canonical-first draft)

> **What this is:** the canonical-entity half of the Model A cutover for the
> release pipeline. The release pipeline is encoded as a brain `Workflow`
> (`instances/release-train/`: `Step`s + `Trigger`s + `FailureMode`s) with the
> drift detector bridging it to the imperative (`.github/workflows/release-on-merge.yml`).
> Model A is a **re-model of that Workflow** — delete the Steps/FailureModes that
> only exist to serve the `dev→main` promotion, then let the imperative follow
> and the drift detector enforce the match.
> **Status:** draft / input to the plugin-evolution thread. Execute as part of
> the cutover (migration step 4: "simplify the release robot"), AFTER the final
> `dev→main` release (→0.89.0) and the default-branch flip. Don't land it before
> the trunk exists — it would describe a pipeline that isn't real yet.
> **Source of truth:** canonical at `sulis-ai/plugins`
> `.specifications/business-dna/instances/release-train/`; vendored into the
> agents plugin. Change canonical → recompile/vendor → imperative follows.

## Current Workflow (15 Steps) — what's coupled to two-branch

```
1. detect-pending-changesets          (reads dev's .changesets)
2. preflight-version-drift
3. preflight-cross-branch-drift   ◀── DELETE (ancestry drift only exists across dev↔main)
4. compute-next-version
5. draft-pr-body-and-changelog
6. open-release-pr                ◀── DELETE (no dev→main PR on a trunk)
7. wait-for-checks-and-mergeability ◀ DELETE (CI gating moves to the per-feature PR)
8. gate-founder-confirmation           (KEEP — founder approves the release)
9. squash-merge                   ◀── DELETE (the dev→main squash that diverged the branches)
10. bump-version-files                 (KEEP)
11. write-changelog-entry              (KEEP)
12. commit-bump-as-bot                 (CHANGE — commit on main directly, not via the promotion PR)
13. tag-and-push                       (KEEP — the release IS the tag)
14. publish-github-release             (KEEP — + wire `gh release create`, #148)
15. emit-release-entity                (KEEP — the Release brain entity)
```

Steps 3, 6, 7, 9 exist **only** because integration (`dev`) and release (`main`)
are different branches. On a trunk they have nothing to do.

## Re-modelled Workflow (trunk-based) — ~10 Steps

```
Trigger: operator invokes /sulis:release on main (or a cadence) — NOT "open a dev→main PR"

1. detect-pending-changesets     (reads main's .changesets accumulated since the last tag)
2. preflight-version-drift       (plugin.json vs computed-from-changesets sanity)
3. compute-next-version          (from changeset tiers)
4. gate-founder-confirmation     (founder approves the version + changelog)
5. bump-version-files            (plugin.json + marketplace entry + umbrella)
6. write-changelog-entry
7. commit-bump-on-main           (committed directly to the trunk; loop-guard on actor==bot stays)
8. tag-and-push                  (the tag IS the release; consumers on default=main resolve it)
9. publish-github-release        (+ gh release create — #148)
10. emit-release-entity          (Release entity: the immutable shipped unit @ this tag)
```

The release is no longer a *merge between branches* — it's a *bump + tag on the
trunk*. The marketplace's "read the default branch" behaviour serves the release
**by construction** (default = main = the just-tagged content).

## The diff (what gets deleted — the "delete machinery" made concrete)

**Steps deleted (4):**
- `preflight-cross-branch-drift` — no cross-branch ancestry to drift.
- `open-release-pr` — no `dev→main` PR; main is the trunk.
- `wait-for-checks-and-mergeability` (on a *release* PR) — CI gating moves to the **per-feature PR into main** (re-apply `branch-ci` as a required check on `main`, which it lacks today).
- `squash-merge` (`dev→main`) — the squash that diverged the branches; gone. Work already merged at its feature-PR.

**FailureModes deleted** (confirm exact `@id`s against `failuremodes.jsonld`):
- The **cross-branch / ancestry-drift** guard (the one that blocks the next change after a squash divergence — moot with one line).
- The **auto-back-merge** failure mode (back-merging main's bump onto dev — no `dev` to back-merge to).

**FailureModes kept (still real on a trunk):**
- **Robot loop-guard** (`actor == github-actions[bot]`) — the bump commit on main must not re-trigger the robot.
- **`bot-tag-doesn't-trigger-release-prod`** — a `GITHUB_TOKEN`-pushed tag doesn't trigger downstream workflows (grounded in the GitHub Actions platform contract); still applies to `tag-and-push` → `publish-github-release`.

**Steps changed (2):**
- `detect-pending-changesets` now reads **main's** `.changesets`.
- `commit-bump-as-bot` commits **directly to main** (no promotion PR).

Net: **15 → 10 Steps**, two FailureModes deleted. The shrink *is* the model being right (Model A's promise is to remove machinery; you can see it removed in the entities).

## The §8 reconciliation is a precondition, not part of this Workflow

The FIRST run after the cutover must not re-count the ~28 already-released
changesets sitting on `dev` (see the context brief §8). That's a **one-off
reconciliation** before/at the final `dev→main` release (→0.89.0), not a Step in
the steady-state trunk Workflow. The trunk Workflow above is the *steady state*
after that one-off. (The clean rule for the one-off: a changeset is genuinely-new
iff its content commit is on `dev` but not on `main`; `main` carries 0 changesets,
all consumed.)

## Why this fits the Release/Deployment encoding

- **`Release`** = the immutable shipped unit = **the tag** (build once). Step 10
  emits it. One Release per tag, never rebuilt.
- **`Deployment`** = a (Release × channel/environment) binding. For the plugin
  the "deployment" is *default-branch = main = the channel*; a future
  canary/beta channel is a **separate repo's `Deployment` of the same Release**,
  not a branch. For the products Sulis builds, a Deployment is the same image
  promoted to dev/staging/prod by config.
- `Release`/`Deployment` are **events** (immutable occurrences) — consistent with
  the events-vs-living split (living = Requirement/Design/Scenario evolve;
  events = Release/Deployment/TestRun are point-in-time records).

## How to execute (Path-A order)

1. **Canonical first:** edit `instances/release-train/{steps,failuremodes,triggers,workflow}.jsonld`
   in `sulis-ai/plugins` to the shape above (delete the 4 Steps + 2 FailureModes,
   change the 2). Validate via the brain rubric.
2. **Vendor** the updated instance into the agents plugin (the DR-027 mirror).
3. **Imperative follows:** simplify `.github/workflows/release-on-merge.yml` to
   match (drop the promotion-PR + back-merge + ancestry-guard logic).
4. **Drift detector bridges:** `check-canonical-drift.py` enforces canonical ↔
   imperative parity — it's the safety net that the simplified robot matches the
   re-modelled Workflow.

This is deliberately **after** the default-branch flip — the trunk has to exist
before its release Workflow is real.
