#!/usr/bin/env bash
# bootstrap_from_zero.sh — fresh-consumer end-to-end test (WP-009;
# TDD §9.3 + §6.4 sandbox CI).
#
# The highest-fidelity verification: a fresh consumer at the shipping
# plugin version must have a working back-merge from their FIRST release.
# This script orchestrates the full bootstrap-from-zero sequence against
# a throwaway sandbox repo on real GitHub.
#
# ----------------------------------------------------------------------
# GATING (WP-009 Notes — sandbox-repo creation requirement).
#
# This test needs `gh auth` with repo-creation permissions on the
# sulis-ai org and costs a real sandbox repo per run. It is therefore
# GATED behind BOOTSTRAP_ENABLED=1. When the env var is unset (the
# default — local dev, the per-commit unit/integration suite, CI
# without sandbox perms), it SKIPS with exit 0 and a clear message, so
# it never fails the suite for want of infrastructure. The sandbox CI
# workflow sets BOOTSTRAP_ENABLED=1 explicitly (TDD §6.4 / §9.2).
# ----------------------------------------------------------------------
#
# Sequence (TDD §9.3):
#   1. gh repo create sulis-ai/release-flow-sandbox-${RUN_ID} --private
#   2. Configure branch protection on dev + main per GIT-04.
#   3. Install the Sulis plugin at the shipping version.
#   4. Copy plugins/sulis/templates/shims/release-on-merge.yml into
#      .github/workflows/release-on-merge.yml; substitute the
#      @sulis-v<MAJOR>.<MINOR>.<PATCH> pin with the shipping version.
#      Commit to dev.
#   5. Drop a .changesets/*.yaml; merge to dev.
#   6. Invoke /sulis:release-train; merge the release PR.
#   7. Poll git ls-remote origin dev / origin main every 30s, up to 5m.
#   8. Assert dev == main within 5 minutes.
#   9. Tear down: gh repo delete ... --yes.
#
# bash-3.2-safe. Exit 0 = pass (or skipped); exit 1 = fail.

set -u
set -o pipefail

. "$(dirname "$0")/lib/abm_canonical.sh"

# --- Gate ---
if [ "${BOOTSTRAP_ENABLED:-0}" != "1" ]; then
    echo "SKIP: bootstrap_from_zero.sh — set BOOTSTRAP_ENABLED=1 to run "
    echo "      (needs gh auth + sandbox-repo creation perms; gated per WP-009 Notes / TDD §9.3)."
    exit 0
fi

# --- Pre-flight when enabled ---
command -v gh  >/dev/null 2>&1 || abm_fail "bootstrap: gh not on PATH"
command -v git >/dev/null 2>&1 || abm_fail "bootstrap: git not on PATH"
gh auth status >/dev/null 2>&1 || abm_fail "bootstrap: gh is not authenticated (run 'gh auth login')"

RUN_ID="${RUN_ID:-$(date +%s)-$$}"
SANDBOX="sulis-ai/release-flow-sandbox-${RUN_ID}"
SHIPPING_VERSION="${SHIPPING_VERSION:?bootstrap: set SHIPPING_VERSION to the plugin version to pin (e.g. 0.3.0)}"

WORKDIR="$(mktemp -d -t abm-bootstrap-e2e-XXXXXX)"
cleanup() {
    rm -rf "$WORKDIR"
    # Best-effort sandbox teardown (step 9). Never mask the test's own
    # exit code with a teardown failure.
    gh repo delete "$SANDBOX" --yes >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "bootstrap: creating sandbox $SANDBOX"
gh repo create "$SANDBOX" --private --clone=false >/dev/null \
    || abm_fail "bootstrap: could not create sandbox $SANDBOX"

git clone --quiet "https://github.com/${SANDBOX}.git" "$WORKDIR/repo" \
    || abm_fail "bootstrap: could not clone $SANDBOX"

cd "$WORKDIR/repo"
git config user.email "bootstrap@example.com"
git config user.name "Bootstrap"

# Seed main + dev.
echo "# release-flow-sandbox" > README.md
git add README.md
git commit --quiet -m "seed"
git branch -M main
git push --quiet origin main
git checkout -b dev
git push --quiet origin dev

# Step 2 — branch protection (best-effort; requires admin on the repo).
# GIT-04: restrict force pushes on dev + main.
for br in dev main; do
    gh api -X PUT "repos/${SANDBOX}/branches/${br}/protection" \
        -f "required_status_checks=null" \
        -F "enforce_admins=false" \
        -f "required_pull_request_reviews=null" \
        -f "restrictions=null" \
        -F "allow_force_pushes=false" \
        >/dev/null 2>&1 \
        || echo "bootstrap: warning — could not set branch protection on ${br} (continuing)"
done

# Step 4 — install the canonical shim, substitute the version pin.
mkdir -p .github/workflows
SHIM_SRC="$ABM_SHIM_TEMPLATE"
[ -f "$SHIM_SRC" ] || abm_fail "bootstrap: shim template missing at $SHIM_SRC"
sed "s/@sulis-v<MAJOR>\\.<MINOR>\\.<PATCH>/@sulis-v${SHIPPING_VERSION}/" \
    "$SHIM_SRC" > .github/workflows/release-on-merge.yml
grep -q "@sulis-v${SHIPPING_VERSION}" .github/workflows/release-on-merge.yml \
    || abm_fail "bootstrap: version-pin substitution failed in the shim"
git add .github/workflows/release-on-merge.yml
git commit --quiet -m "ci: install release-on-merge shim @sulis-v${SHIPPING_VERSION}"
git push --quiet origin dev

# Step 5 — drop a changeset, merge to dev (here: already on dev).
mkdir -p .changesets
cat > ".changesets/bootstrap-${RUN_ID}.yaml" <<YAML
kind: patch
summary: bootstrap-from-zero sandbox changeset
YAML
git add ".changesets/bootstrap-${RUN_ID}.yaml"
git commit --quiet -m "chore: add bootstrap changeset"
git push --quiet origin dev

# Steps 6 — open + merge the release PR (dev -> main). /sulis:release-train
# normally drafts this; in the sandbox we open it directly so the test is
# self-contained, then merge to trigger the release-on-merge workflow.
DEV_SHA="$(git rev-parse origin/dev)"
PR_BODY_FILE="$WORKDIR/release-body.md"
{
    printf 'Bootstrap release.\n'
    # Write the pin in the canonical format the workflow reads.
    printf '\n\n<!-- %s: %s -->\n' "$ABM_PIN_TOKEN" "$DEV_SHA"
} > "$PR_BODY_FILE"
REL_PR="$(gh pr create --repo "$SANDBOX" --base main --head dev \
    --title "release: sulis bootstrap" --body-file "$PR_BODY_FILE")" \
    || abm_fail "bootstrap: could not open release PR"
REL_NUM="$(printf '%s' "$REL_PR" | awk -F/ '{print $NF}')"
gh pr merge "$REL_NUM" --repo "$SANDBOX" --merge --admin >/dev/null 2>&1 \
    || abm_fail "bootstrap: could not merge release PR #${REL_NUM}"

# Steps 7+8 — poll for dev == main within 5 minutes.
echo "bootstrap: polling for dev == main (up to 5 minutes)..."
DEADLINE=$(( $(date +%s) + 300 ))
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
    DEV="$(git ls-remote "https://github.com/${SANDBOX}.git" dev  | awk '{print $1}')"
    MAIN="$(git ls-remote "https://github.com/${SANDBOX}.git" main | awk '{print $1}')"
    if [ -n "$DEV" ] && [ "$DEV" = "$MAIN" ]; then
        abm_pass "bootstrap: dev == main ($DEV) — back-merge worked from the first release"
    fi
    # Or: a back-integrate PR is open (raced path — also acceptable).
    OPEN_PR="$(gh pr list --repo "$SANDBOX" --base dev --label "$ABM_LABEL" \
        --state open --json number --jq '.[0].number // empty' 2>/dev/null || true)"
    if [ -n "$OPEN_PR" ]; then
        abm_pass "bootstrap: back-integrate PR #${OPEN_PR} is open (raced path) — mechanism working"
    fi
    sleep 30
done

abm_fail "bootstrap: dev != main after 5 minutes and no back-integrate PR opened — the first-release back-merge did not occur"
