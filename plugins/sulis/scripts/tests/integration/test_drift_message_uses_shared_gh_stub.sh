#!/usr/bin/env bash
# verifies: plugins/sulis/scripts/drift_check.sh
#
# test_drift_message_uses_shared_gh_stub.sh — exercises drift_check.sh's
# `gh`-dependent recovery-message branch via the SHARED gh stub
# (WP-009 DoD Blue: "Stub gh lives in one place ... reused across tests
# via a PATH prefix").
#
# drift_check.sh, when it detects drift, composes one of two recovery
# messages: (a) "an open back-integrate PR is waiting: PR #N" when
# `gh pr list` returns a match, or (b) the manual-recovery steps when no
# PR is open. The exit-code smoke test (test_drift_check_exit_codes.sh)
# covers the drift/clean exit codes but NOT this `gh`-driven branch —
# because invoking the real `gh` in a unit test is non-deterministic.
#
# This test fills that gap using the shared, STUB_MODE-driven `gh` stub
# at fixtures/drift_check/gh-stubs/gh: with STUB_MODE=pr-open the stub
# returns one back-integrate PR, so drift_check.sh must surface the
# "open back-integrate PR is waiting" branch.

set -u
set -o pipefail

. "$(dirname "$0")/../lib/abm_canonical.sh"

[ -x "$ABM_DRIFT_CHECK" ] || abm_fail "drift_check.sh missing or not executable"

SHARED_GH_STUB_DIR="$ABM_REPO_ROOT/plugins/sulis/scripts/tests/fixtures/drift_check/gh-stubs"
[ -x "$SHARED_GH_STUB_DIR/gh" ] || abm_fail "shared gh stub missing/-not-executable at $SHARED_GH_STUB_DIR/gh"

TMP="$(mktemp -d -t abm-drift-msg-XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

# Build a drifted local remote (dev behind main) so drift_check.sh
# reaches the recovery-message composition.
REMOTE="$TMP/origin.git"
git init --bare --initial-branch=main "$REMOTE" >/dev/null
WORK="$TMP/work"
git clone --quiet "$REMOTE" "$WORK"
(
    cd "$WORK"
    git config user.email "test@example.com"
    git config user.name "Test"
    echo seed > seed.txt; git add seed.txt; git commit --quiet -m seed
    git push --quiet origin main
    git checkout -b dev; git push --quiet origin dev
    git checkout main
    echo more > more.txt; git add more.txt; git commit --quiet -m "advance main"
    git push --quiet origin main
)

# Run drift_check.sh with the SHARED gh stub first on PATH, STUB_MODE
# set so `gh pr list` reports one open back-integrate PR.
STDERR_FILE="$TMP/stderr.txt"
(
    cd "$WORK"
    PATH="$SHARED_GH_STUB_DIR:$PATH"
    export PATH STUB_MODE="pr-open"
    "$ABM_DRIFT_CHECK"
) 2> "$STDERR_FILE"
RC=$?

# Drift → exit 1.
if [ "$RC" -ne 1 ]; then
    cat "$STDERR_FILE" >&2
    abm_fail "expected drift exit 1 with the shared stub; got $RC"
fi

# The PR-open branch must surface: message references an open
# back-integrate PR (the stub returns PR #4242).
if ! grep -qi 'open back-integrate PR' "$STDERR_FILE"; then
    echo "--- stderr ---" >&2; cat "$STDERR_FILE" >&2
    abm_fail "drift recovery message did not surface the 'open back-integrate PR' branch with STUB_MODE=pr-open"
fi

abm_pass "drift_check.sh surfaces the open-back-integrate-PR recovery branch via the shared gh stub (STUB_MODE=pr-open)"
