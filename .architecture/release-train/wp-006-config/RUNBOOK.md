# WP-006 — `main` branch protection: go-live runbook

> **STATUS: RECORDED — DO NOT APPLY TO LIVE `main` YET.**
> Founder decision (2026-05-28): record the config + verification procedure now;
> apply at **go-live** (next cycle, with the first real release-train cut), not
> during this change (which ships via the old manual flow). This change does not
> touch live `main` governance.

## Why deferred (founder-gated)

- The release Action (`release-on-merge.yml`) pushes the bump commit + tag
  **directly** to `main` after the dev→main PR merges. Whether
  `github-actions[bot]` (the default `GITHUB_TOKEN`) can bypass a **required PR**
  with `enforce_admins:false` is **not guaranteed** — `enforce_admins:false`
  exempts human admins, not necessarily the Actions token. Must be proven on a
  throwaway before reliance, or the release silently fails at the push step.
- Applying require-PR to live `main` now would change how the ~18 other in-flight
  change branches reach `main` and could block the existing manual promote
  (`promote-dev-to-main.yml`, which pushes directly). The train isn't live until
  next cycle, so there is no need to touch live `main` today.

## Rollback baseline (captured 2026-05-28, pre-change)

`main` protection at capture time (see `main-protection-baseline.json` verbatim):
- `enforce_admins`: **false** ← the bot-push enabler is ALREADY in place
- `required_linear_history`: true
- `allow_force_pushes`: false · `allow_deletions`: false
- `required_pull_request_reviews`: **null** (no PR required today)
- `required_status_checks`: **null** (no required checks today)
- The team currently promotes via `promote-dev-to-main.yml` — a manual
  `workflow_dispatch` that fast-forwards `main` to `dev` and pushes directly as
  the bot.

## The config to apply (at go-live)

```bash
gh api -X PUT repos/sulis-ai/agents/branches/main/protection \
  --input - <<'JSON'
{
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "required_status_checks": { "strict": false, "contexts": ["branch-ci"] },
  "enforce_admins": false,
  "required_linear_history": true,
  "restrictions": null
}
JSON
```

- `required_pull_request_reviews` with 0 approvals = **require a dev→main PR**
  (no direct human pushes), without forcing a reviewer.
- `required_status_checks.contexts`: **`branch-ci` only.** **MUST NOT include
  `version-check`** — it is advisory this cycle; requiring it would block the
  next dev→main PR carrying pre-existing unlabelled commits (self-lockout, the
  spec's "What to avoid"). Confirm the exact check context name at apply time
  (`gh api repos/sulis-ai/agents/commits/dev/check-runs --jq '.check_runs[].name'`).
- `enforce_admins: false` — the load-bearing setting. With it on, the bot's bump
  push is blocked and the release silently fails.

## Go-live verification (MUST, before relying on the train)

1. **Throwaway bot-push proof.** On a scratch repo (or a protected scratch branch
   on a disposable repo), apply this exact config and trigger a workflow that
   pushes a bump-shaped commit + tag as `github-actions[bot]` using the default
   `GITHUB_TOKEN`. Confirm the push **succeeds** under the protection. If it
   FAILS: add `github-actions[bot]` (or the app) to the branch-protection
   **bypass list** via a repository ruleset, or grant the workflow a PAT/app
   token with bypass, and re-test. Do not apply to live `main` until a bot push
   is proven to land under the chosen config.
2. **Apply + read-back.** Apply to live `main`; read back
   (`gh api repos/sulis-ai/agents/branches/main/protection`) and assert it
   matches this config verbatim.
3. **First real cut.** Run `/sulis:release-train` to open the dev→main PR; merge
   it; confirm `release-on-merge.yml` bumped all three version values, assembled
   the CHANGELOG, deleted the consumed changesets, tagged `v<metadata>`, and
   **pushed back to `main`** as the bot (the proof the bypass works end-to-end).

## Also at go-live — retire the manual-bump mechanism (paired with WP-007's docs)

WP-007 retires the manual bump from the *documented* flow now; the *mechanism*
retires here, at go-live, once the train is proven:

- Remove (or neuter) `promote-dev-to-main.yml`'s hand-typed `version` input —
  the bot now derives the version from changesets. Until this runs, the manual
  promote stays functional (this change's own ship + the in-flight changes use
  it). Do this only AFTER the throwaway bot-push proof + the first real train cut
  succeed, so there's always a working promotion path.

## Rollback

Re-apply the captured baseline (no required PR, no required checks; enforce_admins
stays false):

```bash
gh api -X PUT repos/sulis-ai/agents/branches/main/protection --input - <<'JSON'
{ "required_pull_request_reviews": null, "required_status_checks": null,
  "enforce_admins": false, "required_linear_history": true, "restrictions": null }
JSON
```
