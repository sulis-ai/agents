---
platform: github-actions
title: GitHub Actions — Platform Contract
status: active
harness-run: 01KT419R8MQBQ6BNZPXDSKZBHZ
oldest-retrieval-date: 2026-06-02
freshness-window-days: 180
produced-by: faithful-generation-harness
change_id: "01KT3X2M0JHFN583DKKV77W83C"
---

# GitHub Actions — Platform Contract

This is our outside-in, evidence-grounded record of how **GitHub Actions**
actually behaves where our release pipeline depends on it. Every rule below is
bound to GitHub's own documentation (re-retrieved live on the date shown), and
the load-bearing rules are confirmed by a real-world probe. It exists so we
conform to GitHub's real contract instead of assuming it and discovering the
gap when a release breaks — which is exactly what happened in
[#137](https://github.com/sulis-ai/agents/issues/137).

It was produced by running the faithful-generation-harness (run
`01KT419R8MQBQ6BNZPXDSKZBHZ`) against GitHub's documentation as the closed
source set. The harness binds each claim to a verbatim quote, flags anything
it cannot ground as an inference, and refuses to invent a source — which is
why rule 3 below carries no citation rather than a fabricated one. The
claim-entry schema each rule conforms to is defined in
[`../standards/PLATFORM_CONTRACT_STANDARD.md`](../standards/PLATFORM_CONTRACT_STANDARD.md).

## The rules, in plain language

1. **Put reusable workflows directly in `.github/workflows/`.** A reusable
   workflow called with `uses:` only resolves there — a subfolder doesn't
   work. (This is the rule the v0.87.0 release broke.)
2. **A robot-token action won't kick off the next workflow.** When a step uses
   the built-in `GITHUB_TOKEN`, the events it raises won't start a *new*
   workflow run (so a tag pushed that way won't trigger the release-publish
   job). You have to trigger the follow-on explicitly.
3. **Branch protection may not be enforceable on a private free-plan repo.**
   We rely on this for the "branch checks are advisory here" detection — but we
   could not re-confirm it in GitHub's current docs, so it is carried as an
   open assumption, not a grounded fact, pending a probe on a paid private repo.

## Claims (machine-readable — conforms to the claim-entry schema)

```yaml
- claim: "Reusable workflows must live directly in the `.github/workflows` directory; subdirectories of `workflows` are not supported, so a workflow called via `uses:` only resolves there."
  source: "https://docs.github.com/en/actions/sharing-automations/reusing-workflows"
  retrieval-date: "2026-06-02"
  quote: "As with other workflow files, you locate reusable workflows in the `.github/workflows` directory of a repository. Subdirectories of the `workflows` directory are not supported."
  inferred: false
  load_bearing: true
  probe: "Place a reusable workflow in `.github/workflows/` and call it via `uses:` (resolves); place the same file in a subdirectory and call it (fails to resolve)."
  probe-result: "confirmed"
  probe-evidence: "The v0.87.0 release of this repo failed because a reusable workflow was placed in `plugins/sulis/templates/workflows/` instead of `.github/workflows/`; GitHub could not resolve it via `uses:`. Captured as issue #137; fixed by restoring the self-contained workflow to `.github/workflows/` (commit 10d318b)."

- claim: "Events triggered by the built-in `GITHUB_TOKEN` will not create a new workflow run (with the exception of `workflow_dispatch` and `repository_dispatch`), to prevent recursive runs."
  source: "https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow"
  retrieval-date: "2026-06-02"
  quote: "When you use the repository's `GITHUB_TOKEN` to perform tasks, events triggered by the `GITHUB_TOKEN` will not create a new workflow run, with the following exceptions:"
  inferred: false
  load_bearing: true
  probe: "Push a tag (or other event) from a step authenticated with the default `GITHUB_TOKEN` and observe that an `on:`-matching workflow does NOT start a new run."
  probe-result: "confirmed"
  probe-evidence: "A release tag pushed using `GITHUB_TOKEN` did not trigger the downstream release-publish workflow; the GitHub Release had to be created manually via `gh release create v1.132.0`. Encoded as the `bot-tag-doesn't-trigger-release-prod` failure mode."

- claim: "Branch protection cannot be enforced as a required-status gate on a private repository on a free plan, so branch-level CI checks are advisory there rather than blocking."
  inferred: true
  load_bearing: false
  probe: "On a private repo on a free plan, attempt to configure a required status check and confirm it cannot be enforced as a merge gate."
  probe-result: "deferred:paid-private-repo-for-branch-protection-probe"
  probe-evidence: "Deferred — confirming this needs a paid private repo. This is our operational inference from the #52 unprotected-repo detection; GitHub's current `about-protected-branches` docs no longer carry a verbatim plan-availability sentence to bind it to (re-checked 2026-06-02), so the harness refused to assign a source. The closest groundable statement — 'You can enable branch restrictions in public repositories owned by a GitHub Free organization and in all repositories owned by an organization using GitHub Team or GitHub Enterprise Cloud' — is org-scoped and does not support the private-free-plan claim, so it is intentionally not bound here."
```

## Provenance

- **Harness run:** `01KT419R8MQBQ6BNZPXDSKZBHZ` (faithful-generation-harness;
  LifecycleRun persisted under
  `.brain/instances/product-development/lifecyclerun/`).
- **Verdict:** partial-unattributed — rules 1–2 are source-bound and
  probe-confirmed; rule 3 is honestly flagged as an inference with no fabricated
  source and a deferred probe.
- **Triggering incident:** [#137](https://github.com/sulis-ai/agents/issues/137)
  — the reusable-workflow-location flaw that broke the v0.87.0 release.
- **Deferred probes:**
  `deferred:scratch-github-actions-probe-repo` (a repeatable probe pipeline for
  rules 1–2; both are confirmed from real incidents for now) and
  `deferred:paid-private-repo-for-branch-protection-probe` (rule 3).
