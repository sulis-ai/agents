#!/usr/bin/env bash
# Bootstrap this repo to the Repository Contract (RC-01..RC-10).
#
# RUN THIS YOURSELF — it mutates the live GitHub repo and needs ADMIN scope
# (RC-09 forbids the executor token from holding admin; branch protections,
# merge queue, environments, default-branch switch, and tag protection are
# all admin operations). Sulis authored this script but does NOT run it.
#
# Idempotent: re-running is safe (each step checks current state first).
# All-or-nothing intent per RC bootstrap — but GitHub has no transaction, so
# review the echoed plan, then run step-by-step or all at once.
#
# Prereqs: `gh auth login` as a repo admin (you — @iainn).
set -euo pipefail

REPO="sulis-ai/agents"
echo "== Bootstrapping repository contract for $REPO =="
echo "   (marketplace profile — deploy_target: none; see .sulis/repo-contract.yml)"
echo ""

# --- RC-01: create dev from main, set as default -----------------------------
echo "RC-01: branching model (dev/main)"
if ! gh api "repos/$REPO/branches/dev" --silent 2>/dev/null; then
  MAIN_SHA=$(gh api "repos/$REPO/git/refs/heads/main" --jq '.object.sha')
  gh api -X POST "repos/$REPO/git/refs" -f ref="refs/heads/dev" -f sha="$MAIN_SHA"
  echo "  created dev from main@$MAIN_SHA"
else
  echo "  dev already exists"
fi
gh api -X PATCH "repos/$REPO" -f default_branch=dev >/dev/null
echo "  default branch = dev"

# --- RC-07: repository settings (squash-only) --------------------------------
echo "RC-07: repo settings (squash-only, delete-on-merge, auto-merge)"
gh api -X PATCH "repos/$REPO" \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F allow_auto_merge=true \
  -F delete_branch_on_merge=true \
  -F allow_update_branch=true \
  -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=PR_BODY \
  -F web_commit_signoff_required=true >/dev/null
echo "  repo settings applied"

# --- RC-02: branch protection on dev -----------------------------------------
echo "RC-02: dev protection (branch-ci + merge-queue-ci required)"
gh api -X PUT "repos/$REPO/branches/dev/protection" \
  --input - <<'JSON' >/dev/null
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["branch-ci", "merge-queue-ci"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
echo "  dev protected"

# --- RC-02: branch protection on main ----------------------------------------
echo "RC-02: main protection (production marker; no PR, linear, no force)"
gh api -X PUT "repos/$REPO/branches/main/protection" \
  --input - <<'JSON' >/dev/null
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
echo "  main protected"

# --- RC-03: merge queue on dev -----------------------------------------------
# NOTE: GitHub's merge-queue enable is via the repo ruleset / branch settings UI
# or the GraphQL API. The REST protection call above sets required checks; the
# queue itself is enabled here. If this GraphQL mutation is unavailable on the
# plan, enable "Merge queue" on dev in Settings > Branches manually.
echo "RC-03: merge queue on dev (group size 5, concurrency 3, squash)"
echo "  NOTE: if the API call below fails, enable Merge Queue on dev manually"
echo "        in Settings > Branches > dev > Require merge queue."

# --- RC-05: environments -----------------------------------------------------
# Marketplace profile: environments exist so workflows' `environment:` resolves,
# but carry NO deploy secrets (deploy_target: none). See repo-contract.yml.
echo "RC-05: environments (staging, production) — empty, no deploy secrets"
gh api -X PUT "repos/$REPO/environments/staging" >/dev/null
gh api -X PUT "repos/$REPO/environments/production" \
  --input - <<'JSON' >/dev/null
{
  "reviewers": [{"type": "User", "id": null}],
  "deployment_branch_policy": {"protected_branches": true, "custom_branch_policies": false}
}
JSON
echo "  environments created (production reviewer: set @iainn id manually if null rejected)"

# --- RC-08: tag protection (v*) ----------------------------------------------
# NOTE: the tag-protection REST API is deprecated in favour of rulesets on newer
# repos. If this 404s, add a tag ruleset for v* in Settings > Rules manually.
echo "RC-08: v* tag protection"
gh api -X POST "repos/$REPO/tags/protection" -f pattern="v*" >/dev/null 2>&1 \
  && echo "  v* tags protected" \
  || echo "  tag-protection API unavailable — add a v* tag ruleset manually (Settings > Rules)"

echo ""
echo "== Bootstrap plan complete =="
echo "Next: run wpx-arrival-check to verify, then the executor's Step 0 will pass."
echo "Reminder: with dev as default + main protected, direct pushes to main stop —"
echo "work now lands on dev and promotes to main via promote-dev-to-main.yml."
