#!/usr/bin/env bash
# drift_check.sh — dev-behind-main drift detector.
#
# Single source of truth for the "is origin/main an ancestor of
# origin/dev?" check. Both /sulis:release-train (WP-006) and
# /sulis:change start (WP-007) source-or-execute this script; the
# reusable workflow's FR-011 post-condition check also calls it.
#
# Exit codes:
#   0 — origin/main is an ancestor of origin/dev. No drift. Silent.
#   1 — drift detected, OR `git fetch origin` failed, OR git/gh
#       unavailable. A human-readable message is printed to stderr.
#
# Modes:
#   ./drift_check.sh           Run the full check (default).
#   ./drift_check.sh --help    Print the synopsis to stdout, exit 0.
#   source ./drift_check.sh    Read the canonical constants without
#                              running the check (set
#                              DRIFT_CHECK_SOURCED_ONLY=1 first).
#
# Per ADR-003: bash, not Python. Boring, three responsibilities:
# fetch → ancestor check → compose error message. See WP-001 for the
# contract, TDD §4.2 for the component card, FR-009/FR-010 for the
# functional requirements.

set -u
set -o pipefail

# ---------------------------------------------------------------------
# Canonical-string constants (TDD §3 — cross-component identifiers).
# Every other component that reads or writes these strings sources them
# from this file so they stay character-for-character aligned.
# ---------------------------------------------------------------------
LABEL="back-integrate"
TITLE_PREFIX="chore: back-integrate main → dev"
BASE_BRANCH="dev"
HEAD_BRANCH="main"

# When sourced for constants only, return without running the check.
# Callers set DRIFT_CHECK_SOURCED_ONLY=1 before `source`-ing the file.
if [[ "${DRIFT_CHECK_SOURCED_ONLY:-0}" == "1" ]]; then
    return 0 2>/dev/null || exit 0
fi

# ---------------------------------------------------------------------
# --help — five-line synopsis. Names exit codes 0 and 1 per WP-001 DoD.
# ---------------------------------------------------------------------
print_help() {
    cat <<'HELP'
drift_check.sh — dev-behind-main drift detector (ADR-003).
Usage: drift_check.sh [--help]
  exit 0  origin/main is ancestor of origin/dev (no drift, silent)
  exit 1  drift detected OR fetch/tool failure (message on stderr)
Sourceable: set DRIFT_CHECK_SOURCED_ONLY=1 to read constants only.
HELP
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    print_help
    exit 0
fi

# ---------------------------------------------------------------------
# Pre-flight: git must be available. Inside a repo with `origin` remote.
# ---------------------------------------------------------------------
if ! command -v git >/dev/null 2>&1; then
    echo "drift_check: git not found on PATH; cannot verify drift." >&2
    exit 1
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "drift_check: not inside a git repository; cannot verify drift." >&2
    exit 1
fi

# ---------------------------------------------------------------------
# Step 1 — fetch latest tips from origin so the ancestor check sees
# the truth. Failure here is exit 1 with a fetch-failed prefix.
# ---------------------------------------------------------------------
FETCH_ERR="$(git fetch origin 2>&1)"
FETCH_RC=$?
if [[ $FETCH_RC -ne 0 ]]; then
    echo "drift_check: git fetch failed: ${FETCH_ERR}" >&2
    exit 1
fi

# ---------------------------------------------------------------------
# Step 2 — is origin/main an ancestor of origin/dev? If yes, exit 0
# silently. The ancestor check is O(log N) per ADR-003 rationale.
# ---------------------------------------------------------------------
if git merge-base --is-ancestor "origin/${HEAD_BRANCH}" "origin/${BASE_BRANCH}"; then
    exit 0
fi

# ---------------------------------------------------------------------
# Step 3 — drift detected. Compose the recovery message. The "is there
# an open back-integrate PR?" branch depends on `gh`; if `gh` is
# unavailable or unauthenticated, fall through to the "no open PR"
# recovery message (the recovery procedure is still correct).
# ---------------------------------------------------------------------
PR_INFO=""
if command -v gh >/dev/null 2>&1; then
    # Tolerate gh errors (unauthenticated, rate-limited, offline).
    # --jq '.[0]' returns the first match or empty if no PRs.
    PR_INFO="$(gh pr list \
        --base "$BASE_BRANCH" \
        --label "$LABEL" \
        --state open \
        --json number,url \
        --limit 1 \
        --jq '.[0] | "PR #\(.number): \(.url)"' \
        2>/dev/null || true)"
fi

if [[ -n "$PR_INFO" ]]; then
    {
        echo "drift_check: dev is behind main. An open back-integrate PR is waiting:"
        echo "  $PR_INFO"
        echo "Merge that PR, then re-run."
    } >&2
else
    {
        echo "drift_check: dev is behind main, and no back-integrate PR is open."
        echo "Recovery (UC-005):"
        echo "  git fetch origin"
        echo "  git checkout ${BASE_BRANCH}"
        echo "  git merge --ff-only origin/${HEAD_BRANCH} || git merge origin/${HEAD_BRANCH}"
        echo "  git push origin ${BASE_BRANCH}"
    } >&2
fi

exit 1
