#!/usr/bin/env bash
# test_drift_check_exit_codes.sh
#
# Exercises drift_check.sh in two scripted git-remote fixtures:
#   - repo-clean: origin/main is ancestor of origin/dev → exit 0, silent
#   - repo-drifted: origin/dev is behind origin/main → exit 1 + stderr
#                   line beginning 'drift_check:'
#
# WP-009 owns the full eight-fixture suite; this WP authors the two
# exit-code smoke tests + the silence-on-success contract.
#
# WP-001 Definition of Done — Red item 3 of 3.

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="$SCRIPT_DIR/../../drift_check.sh"

if [[ ! -x "$HELPER" ]]; then
    echo "FAIL: $HELPER missing or not executable" >&2
    exit 1
fi

TMP="$(mktemp -d -t drift-check-test-XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

# Build a fake "remote" we can fetch from. Use bare repo + working clone.
build_remote() {
    local remote_dir="$1"
    git init --bare --initial-branch=main "$remote_dir" >/dev/null
}

# Build a working clone with a single commit on main.
seed_main() {
    local work_dir="$1"
    local remote_dir="$2"
    git clone --quiet "$remote_dir" "$work_dir"
    (
        cd "$work_dir"
        git config user.email "test@example.com"
        git config user.name "Test"
        git checkout -b main 2>/dev/null || git checkout main
        echo "seed" > seed.txt
        git add seed.txt
        git commit --quiet -m "seed main"
        git push --quiet origin main
    )
}

# ---- Fixture A: repo-clean (main == dev) ----
REMOTE_A="$TMP/remote-clean.git"
WORK_A="$TMP/work-clean"
build_remote "$REMOTE_A"
seed_main "$WORK_A" "$REMOTE_A"
(
    cd "$WORK_A"
    git checkout -b dev
    git push --quiet origin dev
)

# Run helper; expect exit 0 and zero stdout output.
STDOUT_A="$(cd "$WORK_A" && "$HELPER" 2>/dev/null)"
RC_A=$?
if [[ $RC_A -ne 0 ]]; then
    echo "FAIL[clean]: expected exit 0, got $RC_A" >&2
    exit 1
fi
if [[ -n "$STDOUT_A" ]]; then
    echo "FAIL[clean]: expected silent stdout, got:" >&2
    echo "$STDOUT_A" >&2
    exit 1
fi

# ---- Fixture B: repo-drifted (dev behind main) ----
REMOTE_B="$TMP/remote-drifted.git"
WORK_B="$TMP/work-drifted"
build_remote "$REMOTE_B"
seed_main "$WORK_B" "$REMOTE_B"
(
    cd "$WORK_B"
    # Create dev at the seed point, then advance main past it.
    git checkout -b dev
    git push --quiet origin dev
    git checkout main
    echo "more-on-main" > more.txt
    git add more.txt
    git commit --quiet -m "advance main past dev"
    git push --quiet origin main
)

STDERR_B_FILE="$TMP/stderr-b.txt"
( cd "$WORK_B" && "$HELPER" 2>"$STDERR_B_FILE" )
RC_B=$?
if [[ $RC_B -ne 1 ]]; then
    echo "FAIL[drifted]: expected exit 1, got $RC_B" >&2
    cat "$STDERR_B_FILE" >&2
    exit 1
fi

STDERR_B="$(cat "$STDERR_B_FILE")"
if ! grep -q '^drift_check:' <<<"$STDERR_B"; then
    echo "FAIL[drifted]: stderr first line did not begin with 'drift_check:'" >&2
    echo "--- stderr ---" >&2
    echo "$STDERR_B" >&2
    exit 1
fi

# Drift message must mention 'dev is behind main' regardless of PR
# detection branch.
if ! grep -q 'dev is behind main' <<<"$STDERR_B"; then
    echo "FAIL[drifted]: stderr did not mention 'dev is behind main'" >&2
    echo "--- stderr ---" >&2
    echo "$STDERR_B" >&2
    exit 1
fi

echo "PASS: $(basename "$0")"
exit 0
